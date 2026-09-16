"""Read-only scope Eval with teaching-list and real Git candidate modes.

Git mode checks final tracked differences and non-ignored untracked paths.
It does not enforce a runtime sandbox or capture every historical write.
"""
import argparse
import json
import subprocess
from pathlib import Path, PurePosixPath

ALLOWED = {'flowerp/service.py', 'tests/test_receiving.py'}


def check_changes(changed, allowed=ALLOWED):
    invalid = []
    for value in changed:
        path = PurePosixPath(value.replace('\\', '/'))
        if path.is_absolute() or '..' in path.parts or ':' in value or path.as_posix() not in allowed:
            invalid.append(value)
    return invalid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--defect', action='store_true')
    parser.add_argument('--repo', type=Path, help='真实候选仓库根目录')
    parser.add_argument('--base', help='事先记录的基线提交')
    parser.add_argument('--allow-file', type=Path, help='执行前确认的JSON路径数组，保存在候选外')
    args = parser.parse_args()
    if args.repo:
        if not args.base or not args.allow_file or args.defect:
            parser.error('真实候选模式需要 --base 和 --allow-file，不能带 --defect')
        try:
            def git(*parts):
                return subprocess.check_output(['git', '-C', str(args.repo), *parts])
            root = Path(git('rev-parse', '--show-toplevel').decode().strip()).resolve()
            if root != args.repo.resolve():
                raise ValueError('--repo 必须是仓库根目录')
            base = git('rev-parse', '--verify', args.base + '^{commit}').decode().strip()
            allowed = json.loads(args.allow_file.read_text(encoding='utf-8-sig'))
            if not isinstance(allowed, list) or not all(isinstance(x, str) for x in allowed):
                raise ValueError('授权清单必须是JSON字符串数组')
            # --no-renames exposes both old and new paths; compare final tree to base.
            raw = git('diff', '--no-ext-diff', '--no-renames', '--name-only', '-z', base, '--')
            raw += git('ls-files', '--others', '--exclude-standard', '-z')
            changed = sorted(set(x.decode('utf-8') for x in raw.split(b'\0') if x))
            invalid = check_changes(changed, allowed)
            print(json.dumps({'case': 'actual_candidate_scope', 'requirement': 'ENG-SCOPE',
                              'status': 'fail' if invalid else 'pass', 'base': base,
                              'repository': str(root), 'changed': changed, 'unexpected': invalid,
                              'source': 'git diff base plus non-ignored untracked paths',
                              'limits': '不覆盖被忽略文件、已撤销写入、仓库外写入或子模块内部差异'}, ensure_ascii=False))
            return 1 if invalid else 0
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            print(json.dumps({'status': 'error', 'reason': str(error)}, ensure_ascii=False))
            return 2
    if args.base or args.allow_file:
        parser.error('--base 与 --allow-file 只能用于 --repo 模式')
    changed = ['flowerp/service.py', 'tests/test_receiving.py']
    if args.defect:
        changed.append('web/styles.css')
    invalid = check_changes(changed)
    print(json.dumps({'case': 'declared_scope', 'status': 'fail' if invalid else 'pass',
                      'changed': changed, 'unexpected': invalid,
                      'source': 'explicit teaching input, not a real task Diff'}, ensure_ascii=False))
    return 1 if invalid else 0


if __name__ == '__main__':
    raise SystemExit(main())
