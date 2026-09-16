"""Run one command, retain a unique UTF-8 receipt, and enforce its expected exit."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cwd', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--expect', type=int, required=True)
    parser.add_argument('--timeout', type=int, default=1200)
    parser.add_argument('--command-file', type=Path)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if args.command_file:
        if command:
            parser.error('use command-file or command arguments, not both')
        command = json.loads(args.command_file.read_text(encoding='utf-8-sig'))
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            parser.error('command-file must contain an array of strings')
    if not command or not args.cwd.is_dir():
        parser.error('command and existing working directory are required')
    args.evidence.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    target = args.evidence / (stamp + '.json')
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONUTF8'] = '1'
    try:
        p = subprocess.run(command, cwd=args.cwd, env=env, capture_output=True,
                           text=True, encoding='utf-8', errors='replace', timeout=args.timeout)
        code, stdout, stderr = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        code = 124
        stdout = exc.stdout.decode('utf-8', errors='replace') if isinstance(exc.stdout, bytes) else exc.stdout or ''
        stderr = 'TIMEOUT\n' + (exc.stderr.decode('utf-8', errors='replace') if isinstance(exc.stderr, bytes) else exc.stderr or '')
    except OSError as exc:
        code, stdout, stderr = 127, '', str(exc)
    result = {'name': args.name, 'cwd': str(args.cwd.resolve()), 'command': command,
              'exit_code': code, 'expected_exit': args.expect, 'stdout': stdout,
              'stderr': stderr, 'receipt': str(target.resolve()), 'time_utc': stamp}
    with target.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if code == args.expect else 1


if __name__ == '__main__':
    raise SystemExit(main())
