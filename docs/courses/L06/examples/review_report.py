"""Check report consistency AND its command/candidate link. Not human acceptance."""
import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from eval.report_contract import validate_report


def review(report_path,record_path,candidate,names,suite):
    record=json.loads(record_path.read_text('utf-8-sig'))
    command=record['command']
    if Path(record['cwd']).resolve()!=candidate.resolve():raise ValueError('运行记录不是本次候选')
    if '--report-path' not in command:raise ValueError('命令未声明报告路径')
    reported=Path(command[command.index('--report-path')+1])
    if not reported.is_absolute():reported=Path(record['cwd'])/reported
    if reported.resolve()!=report_path.resolve():raise ValueError('报告不是本次命令指定的文件，不能借用旧报告')
    report=json.loads(report_path.read_text('utf-8-sig'))
    validate_report(report,tuple(names),record['exit_code'],suite)
    if any(r['level']!='blocking' for r in report['results']):raise ValueError('本轮必需检查不能降为观察项')
    if datetime.fromisoformat(report['generated_at']).tzinfo is None:raise ValueError('报告缺少带时区的实际时间')
    for row in report['results']:
        if type(row.get('duration_ms')) is not int or row['duration_ms']<0:raise ValueError('耗时无效')
        if not row['passed'] and not row.get('evidence'):raise ValueError('失败缺少原因')
    return {'consistent':True,'decision':report['summary']['decision'],
            'report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),
            'record':str(record_path.resolve()),'candidate':str(candidate.resolve()),
            'boundary':'核对命令路径、候选和报告自洽；不提供防篡改签名，不代替人审'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--record',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--case',action='append',required=True);p.add_argument('--suite',default='all');a=p.parse_args()
    try:print(json.dumps(review(a.report,a.record,a.candidate,a.case,a.suite),ensure_ascii=False))
    except (ValueError,RuntimeError,OSError,KeyError,TypeError) as e:
        print(json.dumps({'consistent':False,'reason':str(e)},ensure_ascii=False));raise SystemExit(1)
