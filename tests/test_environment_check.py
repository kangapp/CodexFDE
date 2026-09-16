"""Installation checks must not hide missing or cross-repository packages."""
import json
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from workbench import environment_check as env


class EnvironmentCheckTests(unittest.TestCase):
    def test_workbench_check_does_not_require_customer(self):
        with patch.object(env.external_project, 'flowerp_root', side_effect=AssertionError('customer must be optional')):
            result = env.check_environment()
        self.assertTrue(result['ok'], result)
        self.assertFalse(result['product_checked'])

    def test_missing_customer_returns_actionable_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            result = env.check_environment(product_root=directory)
        self.assertFalse(result['ok'])
        self.assertEqual('flowerp', result['checks'][-1]['name'])
        self.assertIn('独立客户仓库', result['checks'][-1]['detail'])

    def test_customer_import_failure_and_timeout_are_not_green(self):
        with patch.object(env.external_project, 'flowerp_root', return_value=Path('/product')), \
             patch.object(env.external_project, 'python_for', return_value='product-python'), \
             patch.object(env.subprocess, 'run') as run:
            run.return_value = subprocess.CompletedProcess([], 1, '', "ModuleNotFoundError: flowerp")
            result = env.check_environment(product=True)
            self.assertFalse(result['ok'])
            self.assertEqual('product-python', run.call_args.args[0][0])
            self.assertEqual(Path('/product'), run.call_args.kwargs['cwd'])
            run.side_effect = subprocess.TimeoutExpired('product-python', 30)
            self.assertFalse(env.check_environment(product=True)['ok'])

    def test_cli_reports_nonzero_for_invalid_customer(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'workbench.cli',
                                     'environment-check', '--product-root', directory],
                                    cwd=env.ROOT, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertFalse(json.loads(result.stdout)['ok'])

    def test_l00_import_commands_run_in_workbench_environment(self):
        lesson = next((env.ROOT / 'docs/courses/L00').glob('L00*.md')).read_text(encoding='utf-8')
        commands = re.findall(r'-c "([^"\n]*imports-ok[^"\n]*)"', lesson)
        self.assertEqual(2, len(commands))
        for command in commands:
            self.assertNotIn('flowerp', command)
            result = subprocess.run([sys.executable, '-X', 'utf8', '-c', command], cwd=env.ROOT,
                                    capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual('imports-ok', result.stdout.strip())

    def test_workspace_commands_use_each_platform_environment(self):
        workspace = json.loads((env.ROOT / 'docs/courses/FlowERP-AI研发工作台.code-workspace').read_text(encoding='utf-8'))
        for task in workspace['tasks']['tasks']:
            with self.subTest(task=task['label']):
                self.assertEqual('${workspaceFolder}/.venv/bin/python', task['command'])
                self.assertEqual('${workspaceFolder}/.venv/Scripts/python.exe', task['windows']['command'])
                args = task['args']
                module = args[args.index('-m') + 1]
                self.assertIsNotNone(importlib.util.find_spec(module), module)
