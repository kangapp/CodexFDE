"""Frozen independent contract for the candidate's own minimal Harness."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from eval.l06_runner import run
from eval.report_contract import validate_report


def ok(): return 'verified'
def fail(): raise AssertionError('expected=5, actual=8')
def crash(): raise RuntimeError('dependency unavailable; business result unknown')


class RunnerContract(unittest.TestCase):
    def test_pass_and_report(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'report.json'
            report, code=run([('a','blocking',ok)], report_path=path)
            self.assertEqual(code,0)
            self.assertEqual(json.loads(path.read_text('utf8')),report)
            self.assertIsNotNone(datetime.fromisoformat(report['generated_at']).tzinfo)
            self.assertIsInstance(report['results'][0]['duration_ms'],int)
            self.assertGreaterEqual(report['results'][0]['duration_ms'],0)
            validate_report(report,('a',),code,'all')

    def test_blocking_is_not_majority_vote(self):
        report,code=run([('a','blocking',ok),('b','blocking',fail),('c','blocking',ok)])
        self.assertEqual(code,1,'HARNESS-BLOCK: one blocking failure must stop delivery')
        self.assertEqual(report['summary']['blocking_failed'],1)
        self.assertIn('actual=8',report['results'][1]['error']['message'])
        validate_report(report,('a','b','c'),code,'all')

    def test_observing_keeps_warning(self):
        report,code=run([('a','blocking',ok),('b','observing',fail)])
        self.assertEqual(code,0);self.assertEqual(report['summary']['observing_failed'],1)
        validate_report(report,('a','b'),code,'all')

    def test_exception_keeps_reason_and_continues(self):
        called=[]
        report,code=run([('a','blocking',crash),('b','blocking',lambda: called.append('b'))])
        self.assertEqual(called,['b']);self.assertEqual(code,1,'HARNESS-ERROR')
        self.assertEqual(report['results'][0]['error']['type'],'RuntimeError')
        self.assertIn('unknown',report['results'][0]['error']['message'])

    def test_observing_exception_is_not_silently_promoted(self):
        report,code=run([('a','observing',crash)])
        self.assertEqual(code,0);self.assertEqual(report['summary']['observing_failed'],1)

    def test_invalid_selection(self):
        for entries,kwargs in [([],{}),([('a','blocking',ok)],{'names':[]}),
          ([('a','blocking',ok)],{'names':['missing']}),
          ([('a','observing',ok)],{'suite':'blocking'}),
          ([('a','blocking',ok)],{'suite':'wrong'}),
          ([('a','blocking',ok),('a','blocking',ok)],{})]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):run(entries,**kwargs)

    def test_subset_is_explicit(self):
        report,code=run([('a','blocking',ok),('b','observing',fail)],names=['a'])
        self.assertEqual([r['name'] for r in report['results']],['a'])
        self.assertEqual(report['requested_cases'],['a'])

    def test_write_failure_cannot_reuse_old_report(self):
        with tempfile.TemporaryDirectory() as temp:
            old=Path(temp)/'old.json';old.write_text('old evidence','utf8')
            blocker=Path(temp)/'file';blocker.write_text('ordinary file','utf8')
            with self.assertRaises(OSError):run([('a','blocking',ok)],report_path=blocker/'new.json')
            self.assertEqual(old.read_text('utf8'),'old evidence')
            with self.assertRaises(FileExistsError):run([('a','blocking',ok)],report_path=old)

    def test_consumer_rejects_summary_or_exit_contradiction(self):
        report,code=run([('a','blocking',ok)])
        report['summary']['passed']=0
        with self.assertRaises(RuntimeError):validate_report(report,('a',),code,'all')
        report['summary']['passed']=1
        with self.assertRaises(RuntimeError):validate_report(report,('a',),1,'all')


if __name__=='__main__':unittest.main()
