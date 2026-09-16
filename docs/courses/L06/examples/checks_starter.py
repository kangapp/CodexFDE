"""Candidate registrations: stock plus the original L05 checks, no copied assertions."""
import argparse
import csv
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from flowerp import ERPService, ERPStore
from flowerp.models import InsufficientStock, OrderLine


def stock_consistency():
    opening=int(os.environ.get('L06_OPENING','8')); reserved=int(os.environ.get('L06_RESERVED','3'))
    if not 0 < reserved < opening:raise ValueError('require 0 < reserved < opening')
    with tempfile.TemporaryDirectory(prefix='l06-stock-') as temp:
        store=ERPStore(Path(temp)/'stock.db');service=ERPService(store)
        service.add_product('L06-A','口径检查',100)
        service.receive_stock('L06-A',opening,'opening')
        order=service.create_order('已有订单',[OrderLine('L06-A',reserved,100)],'order-A')
        service.reserve_order(order['id']);expected=opening-reserved
        query=service.product('L06-A')
        rows=list(csv.DictReader(io.StringIO(service.export_inventory().lstrip('\ufeff'))))
        exported=[row for row in rows if row['sku']=='L06-A']
        if len(exported)!=1:raise AssertionError(f'AC-CSV-ROW: expected=1 actual={len(exported)}')
        observed={'query':[query[k] for k in ('on_hand','reserved','available')],
                  'csv':[int(exported[0][k]) for k in ('on_hand','reserved','available')]}
        wanted=[opening,reserved,expected]
        if any(value!=wanted for value in observed.values()):
            raise AssertionError(f'AC-AVAILABLE: expected={wanted}, actual={observed}')
        def state():
            return {'stock':store.row('SELECT * FROM stock WHERE sku=?',('L06-A',)),
                    'events':store.rows('SELECT * FROM inventory_events WHERE sku=? ORDER BY rowid',('L06-A',))}
        excessive=service.create_order('超额订单',[OrderLine('L06-A',expected+1,100)],'order-B')
        before=state()
        try:service.reserve_order(excessive['id'])
        except InsufficientStock:pass
        else:raise AssertionError('AC-REJECT: excessive reservation was accepted')
        if state()!=before:raise AssertionError(f'AC-UNCHANGED: expected={before}, actual={state()}')
        return f'AC-AVAILABLE {observed}; reject {expected+1}; stock and inventory events unchanged'


def tests(module):
    stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromName(module)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    if result.testsRun==0 or not result.wasSuccessful():raise AssertionError(stream.getvalue())
    return stream.getvalue()


def l05_receiving():return tests('tests.test_l05_receiving')
def l05_scope():return tests('tests.test_l05_scope')
def harness_contract():return tests('tests.test_l06_runner')


ENTRIES=[('l06_stock_consistency','blocking',stock_consistency),
         ('l05_personal_receiving','blocking',l05_receiving),
         ('l05_personal_scope','blocking',l05_scope)]


def main():
    from eval.l06_runner import run
    parser=argparse.ArgumentParser();parser.add_argument('--report-path',required=True)
    args=parser.parse_args()
    report,code=run(ENTRIES,report_path=args.report_path)
    print(json.dumps(report,ensure_ascii=False,indent=2));return code


if __name__=='__main__':raise SystemExit(main())
