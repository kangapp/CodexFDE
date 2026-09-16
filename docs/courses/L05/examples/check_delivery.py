"""Freeze personal checks, then independently inspect actual executor evidence.

The execution manifest covers the executor interval, not preparation, later edits,
OS isolation, or named human acceptance. No database is written here.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

CHECKS = ('tests/test_l05_receiving.py','tests/test_l05_scope.py','eval/l05_scope.py')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_digest(path):
    # Git may check out the same source as CRLF on Windows. Only normalize EOL.
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def local(root, name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or ':' in name:
        raise ValueError('不可信的相对路径')
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('路径越出候选')
    return target


def verify(submission, runtime, allowed, frozen):
    data = json.loads(submission.read_text('utf-8-sig'))
    task = data['task']; task_id = task['id']
    if '/' in task_id or '\\' in task_id or not task_id.startswith('TASK-'):
        raise ValueError('任务编号无效')
    candidate = Path(data['isolation']['path']).resolve()
    evidence_path = runtime.resolve() / 'delivery' / task_id / 'evidence.json'
    executions = [event['evidence'] for event in task.get('events', [])
                  if (event.get('evidence') or {}).get('mode') == 'codex_exec']
    attempt = executions[-1].get('attempt_id') if executions else None
    if attempt:
        if not isinstance(attempt, str) or not attempt.isalnum():
            raise ValueError('执行尝试编号无效')
        evidence_path = evidence_path.parent / attempt / 'evidence.json'
    evidence = json.loads(evidence_path.read_text('utf-8-sig'))
    issues = []
    if attempt and evidence.get('attempt_id') != attempt:
        issues.append('执行记录与任务尝试编号不同')
    if Path(evidence['invocation']['workspace']).resolve() != candidate:
        issues.append('执行记录与最终候选不同')
    if evidence.get('mode') != 'codex_exec' or evidence.get('returncode') != 0 or not evidence.get('success'):
        issues.append('真实执行未成功')
    permitted = json.loads(allowed.read_text('utf-8-sig'))
    if not isinstance(permitted, list) or not all(isinstance(x,str) for x in permitted):
        raise ValueError('授权清单须为相对路径数组')
    changed = evidence['changed_files']; manifest = evidence['change_manifest']
    if len(set(changed)) != len(changed) or sorted(changed) != sorted(x['path'] for x in manifest):
        issues.append('修改清单不一致')
    unexpected = sorted(set(changed) - set(permitted))
    if unexpected: issues.append('ENG-SCOPE: '+', '.join(unexpected))
    for row in manifest:
        path = local(candidate,row['path'])
        actual = digest(path) if path.is_file() else None
        if actual != row['after_sha256']:
            issues.append('执行后文件又发生变化：'+row['path'])
    frozen_data = json.loads(frozen.read_text('utf-8-sig'))
    if set(frozen_data['files']) != set(CHECKS):
        raise ValueError('冻结清单不完整')
    for name, expected in frozen_data['files'].items():
        path = local(candidate,name)
        if not path.is_file() or check_digest(path) != expected:
            issues.append('个人检查丢失或改变：'+name)
    if task.get('status') != 'review' or not data.get('implementation_evidence'):
        issues.append('尚未满足课程差分条件或尚未进入待审核')
    return {'status':'fail' if issues else 'pass','task_id':task_id,'candidate':str(candidate),
            'source':str(evidence_path),'changed':changed,'unexpected':unexpected,'issues':issues,
            'boundary':'仅核对执行器采集区间、记录文件的现状及三份冻结检查；人工接受仍独立进行'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest='action',required=True)
    freeze=subs.add_parser('freeze');freeze.add_argument('--candidate',type=Path,required=True);freeze.add_argument('--output',type=Path,required=True)
    check=subs.add_parser('verify')
    for name in ('submission','runtime','allowed','frozen'):check.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.action=='freeze':
            value={'candidate':str(args.candidate.resolve()),'normalization':'CRLF to LF only','files':{n:check_digest(local(args.candidate,n)) for n in CHECKS}}
            with args.output.open('x',encoding='utf8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2)
            print(json.dumps(value,ensure_ascii=False));return 0
        result=verify(args.submission,args.runtime,args.allowed,args.frozen)
        print(json.dumps(result,ensure_ascii=False));return 1 if result['issues'] else 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'error','reason':str(exc)},ensure_ascii=False));return 2


if __name__=='__main__':
    raise SystemExit(main())
