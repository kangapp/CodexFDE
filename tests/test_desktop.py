from pathlib import Path
from contextlib import closing
import tempfile
import unittest
from unittest.mock import patch

import io
import json
import sqlite3
from workbench.desktop import launch, inspect_service, main, wait_for_product_release, stop_workbench
import hashlib
import os


class DesktopLaunchTests(unittest.TestCase):
    def test_entry_restarts_workbench_by_default_and_reuse_opts_out(self):
        for options, expected in [([], True), (['--reuse'], False)]:
            with patch('workbench.desktop.launch', side_effect=lambda *a, **k: {'state':'started','url':'http://localhost'}) as run, \
                 patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(0, main(options))
                self.assertEqual(expected, run.call_args_list[0].kwargs['restart'])
                self.assertNotIn('restart', run.call_args_list[1].kwargs)

    def test_restart_waits_for_old_listener_then_starts_new_service(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('workbench.desktop.inspect_service', side_effect=['same','free','same']), \
             patch('workbench.desktop.stop_workbench') as stop, \
             patch('workbench.desktop.subprocess.Popen') as process:
            process.return_value.poll.return_value = None
            process.return_value.pid = 123
            result = launch(Path(directory), restart=True)
            self.assertEqual('restarted', result['state'])
            stop.assert_called_once()
            process.assert_called_once()

    def test_stop_only_targets_verified_command_and_keeps_runtime_files(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            evidence = runtime / 'evidence.txt'
            evidence.write_text('keep')
            args = ['python.exe','-m','workbench.cli','serve-workbench','--port','8001',
                    '--runtime-dir',str(runtime)]
            for command, allowed in [(args, True), (['python.exe','other.py'], False),
                                     (args[:-1]+[str(runtime / 'other')], False)]:
                with patch('workbench.desktop.inspect_service', side_effect=['same','free']), \
                     patch('workbench.desktop.urllib.request.build_opener') as opener, \
                     patch('workbench.desktop.listener_process', return_value=(123456,command)), \
                     patch('workbench.desktop.subprocess.run') as run, \
                     patch('sys.stdout', new_callable=io.StringIO):
                    opener.return_value.open.return_value.__enter__.return_value = io.StringIO('{"items":[]}')
                    run.return_value.returncode = 0
                    if allowed:
                        stop_workbench(runtime,8001)
                        self.assertEqual(['taskkill.exe','/PID','123456','/F'],run.call_args.args[0])
                    else:
                        with self.assertRaisesRegex(RuntimeError,'不是指定目录'):
                            stop_workbench(runtime,8001)
                        run.assert_not_called()
                    self.assertEqual('keep',evidence.read_text())

    def test_active_work_prevents_termination(self):
        with patch('workbench.desktop.inspect_service', return_value='same'), \
             patch('workbench.desktop.urllib.request.build_opener') as opener, \
             patch('workbench.desktop.listener_process') as listener:
            opener.return_value.open.return_value.__enter__.side_effect = [
                io.StringIO('{"items":[{"id":"I1"}]}'), io.StringIO('{"stage":"executing"}')]
            with self.assertRaisesRegex(RuntimeError,'运行中的事项'):
                stop_workbench(Path('.'),8001)
            listener.assert_not_called()

    def test_expiring_writer_lease_is_waited_for_without_rewriting_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'flowerp.db'
            with closing(sqlite3.connect(path)) as conn, conn:
                conn.execute('CREATE TABLE instance_leases (lease_name TEXT, owner_id TEXT, expires_at TEXT)')
                conn.execute("INSERT INTO instance_leases VALUES ('sqlite-primary-writer','previous-instance',datetime('now','+60 seconds'))")
            def expire_lease(_seconds):
                with closing(sqlite3.connect(path)) as conn, conn:
                    conn.execute("UPDATE instance_leases SET expires_at=datetime('now','-1 second')")
            with patch('sys.stdout', new_callable=io.StringIO) as output, \
                 patch('workbench.desktop.time.sleep', side_effect=expire_lease) as sleep:
                wait_for_product_release(Path(directory), timeout=3)
                sleep.assert_called_once_with(.5)
                self.assertIn('无需重复点击', output.getvalue())
            with closing(sqlite3.connect(path)) as conn:
                self.assertEqual('previous-instance', conn.execute('SELECT owner_id FROM instance_leases').fetchone()[0])

    def test_active_writer_is_not_overridden_or_launched_over(self):
        with tempfile.TemporaryDirectory() as directory:
            with closing(sqlite3.connect(Path(directory) / 'flowerp.db')) as conn, conn:
                conn.execute('CREATE TABLE instance_leases (lease_name TEXT, expires_at TEXT)')
                conn.execute("INSERT INTO instance_leases VALUES ('sqlite-primary-writer',datetime('now','+60 seconds'))")
            with self.assertRaisesRegex(RuntimeError, '另一个实例'):
                wait_for_product_release(Path(directory), timeout=0)

    def test_flowerp_reuse_requires_the_same_data_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            payload = {'service':'flowerp', 'status':'ok', 'runtime_id':hashlib.sha256(os.path.normcase(str(runtime.resolve())).encode()).hexdigest()}
            for target, expected in [(runtime, 'same'), (runtime / 'another', 'occupied')]:
                with patch('workbench.desktop.urllib.request.build_opener') as opener:
                    opener.return_value.open.return_value.__enter__.return_value = io.StringIO(json.dumps(payload))
                    self.assertEqual(expected, inspect_service(8000, target, 'flowerp'))

    def test_malformed_health_is_not_adopted(self):
        with patch('workbench.desktop.urllib.request.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value = io.StringIO('[]')
            self.assertEqual('occupied', inspect_service(8000, Path('.'), 'flowerp'))

    def test_product_failure_keeps_workbench_access_and_returns_failure(self):
        with patch('workbench.desktop.launch', side_effect=[
            {'state': 'reused', 'url': 'http://127.0.0.1:8001'}, RuntimeError('端口占用')
        ]), patch('workbench.desktop.webbrowser.open') as browser, \
             patch('sys.stdout', new_callable=io.StringIO), patch('sys.stderr', new_callable=io.StringIO):
            self.assertEqual(1, main(['--open-browser']))
            browser.assert_called_once_with('http://127.0.0.1:8001')

    def test_reopen_reuses_same_service_without_spawning(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('workbench.desktop.inspect_service', return_value='same'), \
             patch('workbench.desktop.subprocess.Popen') as process:
            self.assertEqual('reused', launch(Path(directory))['state'])
            process.assert_not_called()

    def test_other_service_is_not_reused_or_terminated(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('workbench.desktop.inspect_service', return_value='occupied'), \
             patch('workbench.desktop.subprocess.Popen') as process:
            with self.assertRaisesRegex(RuntimeError, '其他服务'):
                launch(Path(directory))
            process.assert_not_called()

    def test_child_failure_keeps_log_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('workbench.desktop.inspect_service', return_value='free'), \
             patch('workbench.desktop.subprocess.Popen') as process:
            process.return_value.poll.return_value = 1
            with self.assertRaisesRegex(RuntimeError, '未能启动'):
                launch(Path(directory))
            self.assertEqual(1, len(list(Path(directory).glob('startup-logs/*.log'))))
