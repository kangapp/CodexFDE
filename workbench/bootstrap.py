"""L01 工作台：保存任务依据与运行记录，完整性检查仍待人工审核。"""
from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
import sqlite3


DEFAULT_RUNTIME = ".runtime/course/L01-workbench"
PHASES = ("red", "diff", "green", "observation")


def _require_text(**fields):
    for name, value in fields.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} 不能为空")


def _snapshot(source):
    path = Path(source).resolve()
    # 禁止通用换行转换，以保留源文件的原始文本内容。
    with path.open(encoding="utf-8", newline="") as stream:
        return str(path), stream.read()


def _observed_time(value):
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.utcoffset() is None:
        raise ValueError("observed_at 必须包含时区")
    return instant


def _evidence_complete(records):
    observations = [(row, _observed_time(row["observed_at"])) for row in records]
    for green, green_time in observations:
        if green["phase"] != "green" or green["returncode"] != 0:
            continue
        command = green["command"]
        if any(row["command"] == command and row["returncode"] != 0 and time > green_time
               for row, time in observations):
            continue
        for red, red_time in observations:
            if red["phase"] == "red" and red["returncode"] != 0 and red["command"] == command:
                if any(row["phase"] == "diff" and row["returncode"] == 0
                       and red_time < time < green_time for row, time in observations):
                    return True
    return False


class BootstrapLedger:
    """CLI 与课程 Eval 共用的本地账本；构造对象不会创建文件。"""

    def __init__(self, runtime_dir=DEFAULT_RUNTIME):
        self.database = Path(runtime_dir).resolve() / "workbench.db"

    @contextmanager
    def _connection(self, *, readonly=False, initialize=False):
        if not initialize and not self.database.is_file():
            raise ValueError("工作台未初始化，请先运行 workbench-init")
        mode = "rwc" if initialize else ("ro" if readonly else "rw")
        connection = sqlite3.connect(self.database.as_uri() + f"?mode={mode}", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                connection.execute("BEGIN" if readonly else "BEGIN IMMEDIATE")
                if not initialize and not connection.execute("SELECT 1 FROM workbench").fetchone():
                    raise ValueError("工作台未初始化，请先运行 workbench-init")
                yield connection
        finally:
            connection.close()

    def initialize(self, owner, name="我的 AI 研发工作台"):
        _require_text(name=name, owner=owner)
        if self.database.exists():
            raise ValueError("工作台账本已存在，不能重复初始化")
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connection(initialize=True) as connection:
            connection.execute("""CREATE TABLE workbench (
                id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT NOT NULL, owner TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE projects (
                project_id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL,
                path TEXT NOT NULL, purpose TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE tasks (
                task_id TEXT PRIMARY KEY NOT NULL,
                project_id TEXT NOT NULL REFERENCES projects(project_id),
                requirement_id TEXT NOT NULL, request TEXT NOT NULL, actor TEXT NOT NULL,
                spec_path TEXT NOT NULL, spec_snapshot TEXT NOT NULL,
                problem_path TEXT NOT NULL, problem_snapshot TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE evidence (
                evidence_id INTEGER PRIMARY KEY,
                task_id TEXT NOT NULL REFERENCES tasks(task_id), phase TEXT NOT NULL,
                command TEXT NOT NULL, output_path TEXT NOT NULL, output TEXT NOT NULL,
                returncode INTEGER NOT NULL, observed_at TEXT NOT NULL
            )""")
            connection.execute("INSERT INTO workbench VALUES (1, ?, ?)", (name, owner))
        return {"name": name, "owner": owner}

    def add_project(self, project_id, name, path=".", purpose="保存任务与运行记录"):
        _require_text(project_id=project_id, name=name, path=str(path), purpose=purpose)
        directory = Path(path).resolve()
        if not directory.is_dir():
            raise ValueError("项目路径必须是已存在的目录")
        project = {"project_id": project_id, "name": name, "path": str(directory), "purpose": purpose}
        with self._connection() as connection:
            if connection.execute("SELECT 1 FROM projects WHERE project_id = ?", (project_id,)).fetchone():
                raise ValueError("项目编号已存在，不能覆盖原项目")
            connection.execute("""INSERT INTO projects (project_id, name, path, purpose)
                                  VALUES (:project_id, :name, :path, :purpose)""", project)
        return project

    def create_task(self, project_id, task_id, request, spec_file, *, problem_file,
                    requirement_id=None, actor=None):
        # 省略值仅供既有 Eval 调用；CLI 始终要求显式提供全部必需字段。
        requirement_id = task_id if requirement_id is None else requirement_id
        _require_text(project_id=project_id, task_id=task_id,
                      requirement_id=requirement_id, request=request)
        spec_path, spec_snapshot = _snapshot(spec_file)
        problem_path, problem_snapshot = _snapshot(problem_file)
        with self._connection() as connection:
            if actor is None:
                actor = connection.execute("SELECT owner FROM workbench").fetchone()["owner"]
            _require_text(actor=actor)
            if not connection.execute("SELECT 1 FROM projects WHERE project_id = ?", (project_id,)).fetchone():
                raise ValueError("项目不存在，请先登记项目")
            if connection.execute("SELECT 1 FROM tasks WHERE task_id = ?", (task_id,)).fetchone():
                raise ValueError("任务编号已存在，不能覆盖原任务")
            task = {"task_id": task_id, "project_id": project_id, "requirement_id": requirement_id,
                    "request": request, "actor": actor, "spec_path": spec_path, "spec_snapshot": spec_snapshot,
                    "problem_path": problem_path, "problem_snapshot": problem_snapshot}
            connection.execute("""INSERT INTO tasks
                (task_id, project_id, requirement_id, request, actor,
                 spec_path, spec_snapshot, problem_path, problem_snapshot)
                VALUES (:task_id, :project_id, :requirement_id, :request, :actor,
                        :spec_path, :spec_snapshot, :problem_path, :problem_snapshot)""", task)
        return {**task, "evidence": []}

    def add_evidence(self, task_id, phase, command, output_file, returncode, observed_at):
        _require_text(task_id=task_id, command=command)
        if phase not in PHASES:
            raise ValueError("记录阶段必须是 red、diff、green 或 observation")
        if type(returncode) is not int:
            raise ValueError("returncode 必须是整数")
        _observed_time(observed_at)
        output_path, output = _snapshot(output_file)
        record = {"task_id": task_id, "phase": phase, "command": command,
                  "output_path": output_path, "output": output,
                  "returncode": returncode, "observed_at": observed_at}
        with self._connection() as connection:
            if not connection.execute("SELECT 1 FROM tasks WHERE task_id = ?", (task_id,)).fetchone():
                raise ValueError("任务不存在，不能追加记录")
            cursor = connection.execute("""INSERT INTO evidence
                (task_id, phase, command, output_path, output, returncode, observed_at)
                VALUES (:task_id, :phase, :command, :output_path, :output, :returncode, :observed_at)""", record)
            record["evidence_id"] = cursor.lastrowid
        return record

    def status(self, require_project=None, require_task=None, require_red_green_evidence=False):
        report = {"ok": False, "workbench": {}, "projects": [], "tasks": [], "evidence": [],
                  "missing": [], "evidence_complete": False,
                  "acceptance": "pending_human_review", "flowerp_connected": False}
        try:
            with self._connection(readonly=True) as connection:
                report["workbench"] = dict(connection.execute("SELECT name, owner FROM workbench").fetchone())
                projects = [dict(row) for row in connection.execute("SELECT * FROM projects ORDER BY project_id")]
                tasks = [dict(row) for row in connection.execute("SELECT * FROM tasks ORDER BY task_id")]
                evidence = [dict(row) for row in connection.execute("SELECT * FROM evidence ORDER BY evidence_id")]
        except (ValueError, OSError, sqlite3.Error) as error:
            report["error"] = str(error)
            report["missing"].append("workbench_unavailable")
            return report

        missing = report["missing"]
        if require_project is not None and not any(p["project_id"] == require_project for p in projects):
            missing.append("required_project_missing")
        required_task = next((t for t in tasks if t["task_id"] == require_task), None)
        if require_task is not None:
            if required_task is None:
                missing.append("required_task_missing")
            elif require_project is not None and required_task["project_id"] != require_project:
                missing.append("task_project_mismatch")
        if require_red_green_evidence and require_task is None:
            missing.append("require_task_needed_for_evidence")

        report["projects"] = [p for p in projects if require_project is None or p["project_id"] == require_project]
        report["tasks"] = [t for t in tasks
                           if (require_task is None or t["task_id"] == require_task)
                           and (require_project is None or t["project_id"] == require_project)]
        task_ids = {t["task_id"] for t in report["tasks"]}
        report["evidence"] = [row for row in evidence if row["task_id"] in task_ids]
        for task in report["tasks"]:
            task["evidence"] = [row for row in report["evidence"] if row["task_id"] == task["task_id"]]
        report["evidence_complete"] = bool(report["tasks"]) and all(
            _evidence_complete(task["evidence"]) for task in report["tasks"])
        if require_red_green_evidence and not report["evidence_complete"]:
            missing.append("same_command_red_diff_green_missing")
        report["ok"] = not missing
        return report


def add_bootstrap_commands(subparsers):
    commands = {
        "workbench-init": ("初始化个人工作台", ("name", "owner")),
        "workbench-project-add": ("登记项目", ("project-id", "name", "path", "purpose")),
        "workbench-task-create": ("保存任务与需求快照", ("project-id", "task-id", "requirement-id",
                                                      "request", "actor", "spec-file", "problem-file")),
        "workbench-evidence-add": ("追加实际运行记录", ("task-id", "command-text", "output-file", "observed-at")),
        "workbench-status": ("只读查询工作台与证据", ()),
    }
    for command, (help_text, fields) in commands.items():
        parser = subparsers.add_parser(command, help=help_text)
        parser.add_argument("--runtime-dir", default=DEFAULT_RUNTIME)
        for field in fields:
            parser.add_argument("--" + field, required=True)
        if command == "workbench-evidence-add":
            parser.add_argument("--phase", choices=PHASES, required=True)
            parser.add_argument("--returncode", type=int, required=True)
        elif command == "workbench-status":
            parser.add_argument("--require-project")
            parser.add_argument("--require-task")
            parser.add_argument("--require-red-green-evidence", action="store_true")


def run_bootstrap_command(args):
    result = {"ok": True, "flowerp_connected": False}
    try:
        ledger = BootstrapLedger(args.runtime_dir)
        if args.command == "workbench-init":
            result["workbench"] = ledger.initialize(args.owner, args.name)
        elif args.command == "workbench-project-add":
            result["project"] = ledger.add_project(args.project_id, args.name, args.path, args.purpose)
        elif args.command == "workbench-task-create":
            result["task"] = ledger.create_task(args.project_id, args.task_id, args.request, args.spec_file,
                problem_file=args.problem_file, requirement_id=args.requirement_id, actor=args.actor)
        elif args.command == "workbench-evidence-add":
            result["evidence"] = ledger.add_evidence(args.task_id, args.phase, args.command_text,
                args.output_file, args.returncode, args.observed_at)
        else:
            result = ledger.status(args.require_project, args.require_task, args.require_red_green_evidence)
    except (ValueError, OSError, sqlite3.Error) as error:
        result = {"ok": False, "flowerp_connected": False, "error": str(error)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1
