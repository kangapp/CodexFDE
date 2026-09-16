"""Observe the real reference adapter with simulated subprocess results.

No Codex session is started, no hook is enabled, and no Harness is executed.
The wrapper returning zero means the observation completed, not quality passed.
"""
from pathlib import Path
import argparse
import contextlib
import io
import json
import runpy
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]


def observe(mode):
    target = ROOT / '.codex/hooks/quality_gate.py'
    main = runpy.run_path(str(target))['main']
    event = '{bad-json' if mode == 'malformed' else json.dumps({
        'hook_event_name': 'Stop', 'cwd': str(ROOT),
        'stop_hook_active': mode == 'reentry',
    })
    stdout, stderr = io.StringIO(), io.StringIO()
    outcome = subprocess.CompletedProcess(['simulated-harness'],
        1 if mode == 'block' else 0,
        'ORDER-TOTAL expected=12000 actual=5000' if mode == 'block' else 'pass', '')
    failure = (subprocess.TimeoutExpired('simulated-harness', 0.01)
               if mode == 'timeout' else FileNotFoundError('simulated missing command')
               if mode == 'command-error' else None)
    returned, error = None, None
    with patch('sys.stdin', io.StringIO(event)), patch('subprocess.run',
            return_value=outcome, side_effect=failure) as command, \
            contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            returned = main()
        except Exception as exc:
            error = type(exc).__name__
    raw = stdout.getvalue()
    try:
        response = json.loads(raw)
    except json.JSONDecodeError:
        response = None
    return {'mode': mode, 'evidence_kind': 'adapter_with_test_double',
            'handler': str(target), 'input': event,
            'harness_call_count': command.call_count,
            'subprocess_timeout_configured': bool(command.call_args and
                'timeout' in command.call_args.kwargs),
            'handler_return': returned, 'exception': error,
            'stdout': raw, 'stderr': stderr.getvalue(), 'response': response,
            'real_codex_event': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['pass', 'block', 'reentry', 'malformed',
                                        'timeout', 'command-error'])
    print(json.dumps(observe(parser.parse_args().mode), ensure_ascii=False, indent=2))
