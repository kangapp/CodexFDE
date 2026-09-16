"""Read-only installation checks, with ERP checks in its own interpreter."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import subprocess
import sys

from . import external_project

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_CHECK = """import json, pathlib, sys
import flowerp, eval
root = pathlib.Path.cwd().resolve()
paths = {name: str(pathlib.Path(module.__file__).resolve())
         for name, module in [('flowerp', flowerp), ('eval', eval)]}
assert all(pathlib.Path(path).is_relative_to(root) for path in paths.values()), 'package imported from another repository'
assert sys.prefix != sys.base_prefix, 'product interpreter is not a virtual environment'
print(json.dumps({'python': sys.executable, 'packages': paths}))
"""


def check_environment(*, product: bool = False, product_root=None) -> dict:
    checks = []

    def record(name, ok, detail):
        checks.append({'name': name, 'ok': bool(ok), 'detail': detail})

    record('python', sys.version_info >= (3, 10), sys.version.split()[0])
    record('virtual_environment', sys.prefix != sys.base_prefix, sys.executable)
    for name in ('workbench', 'eval'):
        try:
            module = importlib.import_module(name)
            path = Path(module.__file__).resolve()
            record(name, path.is_relative_to(ROOT / name), str(path))
        except (ImportError, TypeError, OSError) as error:
            record(name, False, str(error))
    for name in ('workbench_web/index.html', 'harness_web/index.html'):
        record(name, (ROOT / name).is_file(), str(ROOT / name))
    if product or product_root is not None:
        try:
            root = external_project.flowerp_root(product_root)
            result = subprocess.run(
                [external_project.python_for(root), '-X', 'utf8', '-c', PRODUCT_CHECK],
                cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=30,
            )
            if result.returncode:
                record('flowerp', False, result.stderr.strip()[-4000:] or f'exit {result.returncode}')
            else:
                record('flowerp', True, json.loads(result.stdout.strip()))
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            record('flowerp', False, str(error))
    return {'ok': all(item['ok'] for item in checks), 'scope': 'installation',
            'product_checked': product or product_root is not None, 'checks': checks}
