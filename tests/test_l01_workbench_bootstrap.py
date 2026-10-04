"""Spec v0.1 的真实 CLI 验收；这里的身份、输出与时间均为测试夹具。

仅通过公开命令创建和查询数据，不读取数据库表，不调用 bootstrap 内部函数。
这些测试的夹具记录不能用作本人正式红灯、绿灯或签收证据。
JSON 字段约定及验收映射见 lesson-01-submission/02-spec.md。
"""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC_TEXT = "# 测试用需求\n第一版只做 CLI。\n保留失败记录，不覆盖旧任务。\n"
PROBLEM_TEXT = "# 测试用原始问题\n再次接手时需要查到当时的目标与运行记录。\n"
TEST_COMMAND = json.dumps(["python", "-m", "unittest", "fixture_suite"], ensure_ascii=False)
DIFF_COMMAND = json.dumps(["git", "diff", "--", "workbench/bootstrap.py"])
RED_TIME = "2020-01-01T10:00:00+08:00"
DIFF_TIME = "2020-01-01T10:01:00+08:00"
GREEN_TIME = "2020-01-01T10:02:00+08:00"


class L01WorkbenchBootstrapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="l01-cli-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.runtime = self.root / "ledger"
        self.project_path = self.root / "project"
        self.project_path.mkdir()
        self.spec_file = self.root / "spec.md"
        self.problem_file = self.root / "problem.md"
        self.spec_file.write_text(SPEC_TEXT, encoding="utf-8")
        self.problem_file.write_text(PROBLEM_TEXT, encoding="utf-8")
        self.outputs = {}
        for phase, content in {
            "red": "FAIL: fixture capability missing\n",
            "diff": "fixture diff: add CLI behavior\n",
            "green": "OK: fixture checks passed\n",
            "observation": "fixture observation\n",
        }.items():
            output = self.root / f"{phase}.txt"
            output.write_text(content, encoding="utf-8")
            self.outputs[phase] = output
        self.maxDiff = None

    def cli(self, command, *, expected=0, runtime=None, **options):
        argv = [sys.executable, "-B", "-X", "utf8", "-m", "workbench.cli",
                command, "--runtime-dir", str(runtime if runtime is not None else self.runtime)]
        for name, value in options.items():
            argv.append("--" + name.replace("_", "-"))
            if value is not True:
                argv.append(str(value))
        result = subprocess.run(argv, cwd=ROOT, capture_output=True,
                                text=True, encoding="utf-8", timeout=30)
        detail = f"命令：{argv!r}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        # 先检查进程结果，缺少目标命令应成为明确断言失败，而不是 JSON 导入错误。
        self.assertEqual(expected, result.returncode, detail)
        try:
            body = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail(f"业务响应应为 JSON。\n{detail}")
        self.assertIsInstance(body, dict)
        self.assertIs(body.get("ok"), expected == 0, body)
        self.assertIs(body.get("flowerp_connected"), False, body)
        if expected:
            self.assertTrue(body.get("error") or body.get("missing"), body)
        return body

    def initialize(self, **overrides):
        options = {"name": "测试工作台", "owner": "FIXTURE-OWNER"}
        options.update(overrides)
        return self.cli("workbench-init", **options)

    def project(self, **overrides):
        options = {"project_id": "PROJECT-A", "name": "测试项目",
                   "path": self.project_path, "purpose": "保存任务与证据"}
        options.update(overrides)
        return self.cli("workbench-project-add", **options)

    def task(self, **overrides):
        options = {"project_id": "PROJECT-A", "task_id": "TASK-A",
                   "requirement_id": "REQ-A", "request": "实现五个 CLI 操作",
                   "actor": "FIXTURE-OWNER", "spec_file": self.spec_file,
                   "problem_file": self.problem_file}
        options.update(overrides)
        return self.cli("workbench-task-create", **options)

    def record(self, phase="red", **overrides):
        options = {"task_id": "TASK-A", "phase": phase, "command_text": TEST_COMMAND,
                   "output_file": self.outputs[phase], "returncode": 1,
                   "observed_at": RED_TIME}
        options.update(overrides)
        return self.cli("workbench-evidence-add", **options)

    def status(self, *, task=None, project=None, complete=False, expected=0, runtime=None):
        options = {}
        if task is not None:
            options["require_task"] = task
        if project is not None:
            options["require_project"] = project
        if complete:
            options["require_red_green_evidence"] = True
        body = self.cli("workbench-status", expected=expected, runtime=runtime, **options)
        self.assertIsInstance(body.get("workbench"), dict, body)
        for key in ("projects", "tasks", "evidence", "missing"):
            self.assertIsInstance(body.get(key), list, body)
        self.assertIsInstance(body.get("evidence_complete"), bool, body)
        self.assertEqual("pending_human_review", body.get("acceptance"), body)
        if expected:
            self.assertTrue(body["missing"], body)
        if complete and expected == 0:
            self.assertIs(body["evidence_complete"], True, body)
        return body

    def ledger(self, body):
        """只比较查询所见的保存内容，不把即时完整性结论当作持久数据。"""
        return {
            "workbench": body["workbench"],
            **{key: sorted(body[key], key=lambda row: json.dumps(row, sort_keys=True))
               for key in ("projects", "tasks", "evidence")},
        }

    def seed(self):
        self.initialize()
        self.project()
        self.task()

    def chain(self, *, task_id="TASK-A", times=(RED_TIME, DIFF_TIME, GREEN_TIME)):
        self.record("red", task_id=task_id, observed_at=times[0])
        self.record("diff", task_id=task_id, command_text=DIFF_COMMAND,
                    returncode=0, observed_at=times[1])
        self.record("green", task_id=task_id, returncode=0, observed_at=times[2])

    def assert_chain_missing(self, task_id="TASK-A"):
        body = self.status(task=task_id, complete=True, expected=1)
        self.assertIs(body["evidence_complete"], False, body)
        self.assertIn("same_command_red_diff_green_missing", body["missing"])
        return body

    def test_init_persists_and_runtime_directories_are_isolated(self):
        """A-01：每次 CLI 调用都是新进程，另一目录不能读到本账本。"""
        created = self.initialize()
        self.assertEqual("测试工作台", created["workbench"]["name"])
        self.assertEqual("FIXTURE-OWNER", created["workbench"]["owner"])
        self.assertTrue((self.runtime / "workbench.db").is_file())
        original = self.status()
        self.assertEqual(created["workbench"], original["workbench"])
        other = self.root / "other-ledger"
        self.cli("workbench-status", runtime=other, expected=1)
        self.assertFalse((other / "workbench.db").exists())
        self.initialize(runtime=other, name="另一工作台", owner="OTHER-OWNER")
        second = self.status(runtime=other)
        self.assertEqual("OTHER-OWNER", second["workbench"]["owner"])
        self.assertEqual([], second["projects"])
        self.assertEqual([], second["tasks"])
        self.assertEqual([], second["evidence"])
        self.assertEqual(self.ledger(original), self.ledger(self.status()))

    def test_reinitialization_preserves_existing_data(self):
        """A-01：重复初始化不能覆盖身份、任务或失败历史。"""
        self.seed()
        self.record()
        before = self.ledger(self.status())
        self.initialize(name="错误的新名称", owner="OTHER-OWNER", expected=1)
        self.assertEqual(before, self.ledger(self.status()))

    def test_empty_identity_does_not_initialize(self):
        """A-01/接口约定：空名称或所有者不能生成工作台。"""
        for field in ("name", "owner"):
            with self.subTest(field=field):
                self.initialize(**{field: "", "expected": 1})
                self.assertFalse((self.runtime / "workbench.db").exists())

    def test_project_registration_persists_and_duplicate_is_rejected(self):
        """A-02：登记后重查字段；重复项目请求保留原项目与任务。"""
        self.initialize()
        created = self.project()["project"]
        for key, value in {"project_id": "PROJECT-A", "name": "测试项目",
                           "path": str(self.project_path), "purpose": "保存任务与证据"}.items():
            self.assertEqual(value, created[key])
        self.assertEqual([created], self.status()["projects"])
        self.task()
        self.record()
        before = self.ledger(self.status())
        self.project(name="另一项目", path=self.root, purpose="替换目的", expected=1)
        self.assertEqual(before, self.ledger(self.status()))

    def test_invalid_project_inputs_leave_ledger_unchanged(self):
        """A-02/接口约定：无效登记不影响已有任务。"""
        self.seed()
        before = self.ledger(self.status())
        cases = [{"project_id": ""}, {"name": ""}, {"purpose": ""},
                 {"path": self.root / "missing-project"}]
        for case in cases:
            with self.subTest(case=case):
                options = {"project_id": "NEW-PROJECT", **case, "expected": 1}
                self.project(**options)
                self.assertEqual(before, self.ledger(self.status()))

    def test_task_creation_retains_identity_and_full_snapshots(self):
        """A-03：正常例，比较全文及归属，不只判断创建成功。"""
        self.initialize()
        self.project()
        self.project(project_id="PROJECT-B", name="另一个项目")
        created = self.task()["task"]
        expected = {"task_id": "TASK-A", "project_id": "PROJECT-A",
                    "requirement_id": "REQ-A", "request": "实现五个 CLI 操作",
                    "actor": "FIXTURE-OWNER", "spec_path": str(self.spec_file),
                    "spec_snapshot": SPEC_TEXT, "problem_path": str(self.problem_file),
                    "problem_snapshot": PROBLEM_TEXT}
        for key, value in expected.items():
            self.assertEqual(value, created[key])
        body = self.status(project="PROJECT-A", task="TASK-A")
        self.assertEqual([created], body["tasks"])
        self.assertEqual([], body["evidence"])

    def test_invalid_task_requests_leave_ledger_unchanged(self):
        """A-04：错误项目、源文件或空必需字段不产生半条任务。"""
        self.seed()
        self.record()
        before = self.ledger(self.status())
        cases = [{"project_id": "MISSING-PROJECT"},
                 {"spec_file": self.root / "missing-spec.md"},
                 {"problem_file": self.root / "missing-problem.md"}]
        cases += [{field: ""} for field in
                  ("project_id", "task_id", "requirement_id", "request", "actor")]
        for case in cases:
            with self.subTest(case=case):
                self.task(**{"task_id": "NEW-TASK", **case, "expected": 1})
                self.assertEqual(before, self.ledger(self.status()))

    def test_duplicate_task_id_cannot_overwrite_original_or_records(self):
        """A-05：错误例，拒绝重复编号后比较所有原任务与记录。"""
        self.seed()
        self.record()
        before = self.ledger(self.status())
        self.spec_file.write_text("# 另一份需求\n增加网页。\n", encoding="utf-8")
        self.problem_file.write_text("替换原问题", encoding="utf-8")
        self.task(request="增加网页", requirement_id="OTHER-REQ", actor="OTHER-ACTOR", expected=1)
        after = self.status()
        self.assertEqual(before, self.ledger(after))
        self.assertEqual(1, len(after["tasks"]))
        self.assertEqual(SPEC_TEXT, after["tasks"][0]["spec_snapshot"])
        self.assertEqual(1, after["evidence"][0]["returncode"])

    def test_source_file_edits_do_not_change_snapshots(self):
        """A-06：源文件修改或删除后，仍能查到保存时的全文。"""
        self.seed()
        self.record()
        before = self.ledger(self.status())
        for source in (self.spec_file, self.problem_file, self.outputs["red"]):
            source.write_text("已变化的新内容\n", encoding="utf-8")
        self.assertEqual(before, self.ledger(self.status()))
        for source in (self.spec_file, self.problem_file, self.outputs["red"]):
            source.unlink()
        self.assertEqual(before, self.ledger(self.status()))

    def test_evidence_append_preserves_failures_and_does_not_execute_commands(self):
        """A-07：导入成功与原执行成功不同；命令文本仅保存。"""
        self.seed()
        marker = self.root / "command-was-executed.txt"
        command = json.dumps([sys.executable, "-c",
                              f"from pathlib import Path; Path({str(marker)!r}).write_text('unexpected')"])
        failed = self.record(command_text=command, returncode=17)["evidence"]
        expected = {"task_id": "TASK-A", "phase": "red", "command": command,
                    "output_path": str(self.outputs["red"]),
                    "output": "FAIL: fixture capability missing\n", "returncode": 17}
        for key, value in expected.items():
            self.assertEqual(value, failed[key])
        self.assertIs(type(failed["returncode"]), int)
        self.assertEqual(datetime.fromisoformat(RED_TIME),
                         datetime.fromisoformat(failed["observed_at"].replace("Z", "+00:00")))
        passed = self.record("green", command_text=command, returncode=0,
                             observed_at=GREEN_TIME)["evidence"]
        self.assertEqual("OK: fixture checks passed\n", passed["output"])
        self.assertEqual(0, passed["returncode"])
        body = self.status(task="TASK-A")
        self.assertEqual(2, len(body["evidence"]))
        self.assertIn(failed, body["evidence"])
        self.assertIn(passed, body["evidence"])
        self.assertFalse(marker.exists(), "追加记录不得执行其中的命令文本")

    def test_invalid_evidence_requests_leave_ledger_unchanged(self):
        """A-08：拒绝无效追加后，原失败历史依然完整。"""
        self.seed()
        self.record()
        before = self.ledger(self.status())
        cases = [{"task_id": "MISSING-TASK"}, {"output_file": self.root / "missing-output.txt"},
                 {"observed_at": "not-a-time"}, {"observed_at": "2020-01-01T10:00:00"}]
        for case in cases:
            with self.subTest(case=case):
                self.record(**case, expected=1)
                self.assertEqual(before, self.ledger(self.status()))

    def test_missing_evidence_reports_missing_without_mutating_task(self):
        """A-09：缺证据只改变查询结论，不破坏已经创建的任务。"""
        self.seed()
        before = self.ledger(self.status())
        self.assert_chain_missing()
        self.assertEqual(before, self.ledger(self.status()))

    def test_valid_chain_is_complete_but_requires_human_review(self):
        """A-10：有效链通过完整性检查，但不能自动签收。"""
        self.seed()
        self.chain()
        before = self.ledger(self.status())
        body = self.status(project="PROJECT-A", task="TASK-A", complete=True)
        self.assertEqual([], body["missing"])
        self.assertEqual(3, len(body["evidence"]))
        self.assertEqual([0, 0, 1], sorted(row["returncode"] for row in body["evidence"]))
        self.assertEqual(before, self.ledger(self.status()))

    def test_observation_order_uses_instants_and_not_import_order(self):
        """A-10：先导入绿也不能改写真实观察顺序；比较时区对应的时刻。"""
        self.seed()
        self.record("green", returncode=0, observed_at="2020-01-01T04:00:00+00:00")
        self.record("red", observed_at="2020-01-01T10:00:00+08:00")
        self.record("diff", command_text=DIFF_COMMAND, returncode=0,
                    observed_at="2020-01-01T03:00:00+00:00")
        self.status(task="TASK-A", complete=True)

    def test_different_red_green_commands_cannot_form_chain(self):
        """A-11：另一条命令成功不能覆盖本命令的失败。"""
        self.seed()
        self.record()
        self.record("diff", command_text=DIFF_COMMAND, returncode=0, observed_at=DIFF_TIME)
        self.record("green", command_text='["python", "-m", "unittest", "other_suite"]',
                    returncode=0, observed_at=GREEN_TIME)
        self.assert_chain_missing()

    def test_invalid_observation_order_cannot_form_chain(self):
        """A-11：相等、倒序或换算时区后不成立的观察时间都不能通过。"""
        cases = [(RED_TIME, RED_TIME, GREEN_TIME), (RED_TIME, GREEN_TIME, GREEN_TIME),
                 (GREEN_TIME, DIFF_TIME, RED_TIME),
                 ("2020-01-01T10:00:00+00:00", "2020-01-01T11:00:00+08:00",
                  "2020-01-01T12:00:00+08:00")]
        for index, times in enumerate(cases):
            with self.subTest(times=times):
                self.runtime = self.root / f"time-case-{index}"
                self.seed()
                self.chain(times=times)
                self.assert_chain_missing()

    def test_zero_red_or_failed_diff_cannot_complete_chain(self):
        """A-11：阶段标签不能代替实际退出码。"""
        for index, (red_code, diff_code) in enumerate(((0, 0), (1, 1))):
            with self.subTest(red_code=red_code, diff_code=diff_code):
                self.runtime = self.root / f"code-case-{index}"
                self.seed()
                self.record(returncode=red_code)
                self.record("diff", command_text=DIFF_COMMAND, returncode=diff_code, observed_at=DIFF_TIME)
                self.record("green", returncode=0, observed_at=GREEN_TIME)
                self.assert_chain_missing()

    def test_chain_cannot_mix_tasks(self):
        """A-11：两项任务的记录不能拼成任一项任务的有效链。"""
        self.seed()
        self.task(task_id="TASK-B", requirement_id="REQ-B")
        self.record()
        self.record("diff", command_text=DIFF_COMMAND, returncode=0, observed_at=DIFF_TIME)
        self.record("green", task_id="TASK-B", returncode=0, observed_at=GREEN_TIME)
        self.assert_chain_missing("TASK-A")
        self.assert_chain_missing("TASK-B")

    def test_later_failure_invalidates_old_green(self):
        """A-11：后来再失败不能被旧绿灯掩盖，复验后仍保留全部失败。"""
        self.seed()
        self.chain()
        self.status(task="TASK-A", complete=True)
        self.record("observation", output_file=self.outputs["red"], returncode=1,
                    observed_at="2020-01-01T10:03:00+08:00")
        self.assert_chain_missing()
        self.chain(times=("2020-01-01T10:04:00+08:00", "2020-01-01T10:05:00+08:00",
                          "2020-01-01T10:06:00+08:00"))
        body = self.status(task="TASK-A", complete=True)
        self.assertEqual(7, len(body["evidence"]))
        self.assertEqual(3, sum(row["returncode"] != 0 for row in body["evidence"]))

    def test_unrelated_failed_observation_does_not_invalidate_chain(self):
        """A-11：另一条查询命令的失败不是本验收命令再次失败。"""
        self.seed()
        self.chain()
        self.record("observation", command_text='["workbench-status", "--require-task", "MISSING"]',
                    returncode=1, observed_at="2020-01-01T10:03:00+08:00")
        body = self.status(task="TASK-A", complete=True)
        self.assertEqual(4, len(body["evidence"]))

    def test_missing_task_query_and_recovery_preserve_data(self):
        """A-12：错误查询后恢复查询，全部原任务和记录仍保持。"""
        self.seed()
        self.chain()
        before = self.ledger(self.status())
        failed = self.status(project="PROJECT-A", task="MISSING-TASK", complete=True, expected=1)
        self.assertIn("required_task_missing", failed["missing"])
        self.status(project="PROJECT-A", task="TASK-A", complete=True)
        self.assertEqual(before, self.ledger(self.status()))

    def test_missing_project_and_wrong_parent_are_rejected(self):
        """A-12：不能把真实任务当成另一个项目的任务。"""
        self.seed()
        self.project(project_id="PROJECT-B", name="另一个项目")
        self.chain()
        before = self.ledger(self.status())
        self.status(project="MISSING-PROJECT", expected=1)
        self.status(project="PROJECT-B", task="TASK-A", complete=True, expected=1)
        self.status(project="PROJECT-A", task="TASK-A", complete=True)
        self.assertEqual(before, self.ledger(self.status()))

    def test_uninitialized_operations_do_not_create_database(self):
        """A-13：未初始化时不能由查询或业务请求偷偷创建账本。"""
        calls = [lambda: self.cli("workbench-status", expected=1),
                 lambda: self.project(expected=1), lambda: self.task(expected=1),
                 lambda: self.record(expected=1)]
        for index, call in enumerate(calls):
            with self.subTest(operation=index):
                call()
                self.assertFalse((self.runtime / "workbench.db").exists())


if __name__ == "__main__":
    unittest.main()
