"""Observe current envelope boundaries with local, explicitly fake identities.

All files are temporary. No external platform is contacted or authenticated.
The wrapper succeeding means observations completed, not evidence was accepted.
"""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from workbench.ci_evidence import build_envelope


def run(mode):
    with tempfile.TemporaryDirectory(prefix='l08-envelope-') as temp:
        report = Path(temp) / 'report.json'
        output = Path(temp) / 'envelope.json'
        raw = '{bad' if mode == 'malformed' else '{}' if mode == 'empty-report' else '{"suite":"blocking","summary":{"decision":"pass"}}'
        if mode not in ('missing', 'stale-output'):
            report.write_text(raw, encoding='utf8')
        identity = {} if mode == 'missing-identity' else {'GITHUB_SHA': 'SIMULATED-SHA', 'GITHUB_RUN_ID': 'SIMULATED-RUN'}
        if mode == 'stale-output':
            old = '{"report_decision":"pass","run_id":"SIMULATED-OLD"}'
            output.write_text(old, encoding='utf8')
            env = os.environ.copy()
            env.update(identity)
            completed = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'workbench.ci_evidence',
                                        '--report', str(report), '--output', str(output)],
                                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)
            return {'mode': mode, 'exit_code': completed.returncode,
                    'old_output_remains': output.read_text(encoding='utf8') == old,
                    'stderr': completed.stderr, 'real_remote_run': False}
        result, error = None, None
        try:
            result = build_envelope(report, env=identity)
        except (FileNotFoundError, SystemExit, json.JSONDecodeError) as exc:
            error = {'type': type(exc).__name__, 'message': str(exc)}
        if mode == 'tampered':
            report.write_text(raw + '\n', encoding='utf8')
            import hashlib
            return {'mode': mode, 'original_envelope': result,
                    'current_hash_matches': result['report_sha256'] == hashlib.sha256(report.read_bytes()).hexdigest(),
                    'real_remote_run': False}
        return {'mode': mode, 'envelope': result, 'error': error, 'real_remote_run': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['missing', 'missing-identity', 'malformed', 'empty-report', 'tampered', 'stale-output'])
    print(json.dumps(run(parser.parse_args().mode), ensure_ascii=False, indent=2))
