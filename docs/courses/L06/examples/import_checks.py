"""Frozen checks for the actual L06 import candidate and its original L05 tests."""
import argparse
import io
import json
import tempfile
import unittest
from pathlib import Path
from flowerp.identity import IdentityService, SYSTEM_PRINCIPAL
from flowerp.import_export import ImportExportService
from flowerp.import_batch import submit
from flowerp.models import Conflict
from flowerp.store import ERPStore
from .l06_runner import run


def batch(count, invalid=False):
    return 'sku,name,sales_price_cents\n' + ''.join(
        f'NEW-{i},{"" if invalid and i == count else "商品"+str(i)},1290\n'
        for i in range(1, count+1))


def check_import(count, invalid=False, preview=False):
    with tempfile.TemporaryDirectory(prefix='l06-import-check-') as temp:
        store=ERPStore(Path(temp)/'case.db'); IdentityService(store).ensure_local_defaults()
        service=ImportExportService(store)
        seed=service.validate_csv(SYSTEM_PRINCIPAL,'products',
                                  'sku,name,sales_price_cents\nKEEP,原有商品,990\n')
        service.commit(SYSTEM_PRINCIPAL,seed['id'])
        state=lambda:store.rows('SELECT * FROM product_master ORDER BY id')
        before=state(); rejected=False
        if preview:
            job=service.validate_csv(SYSTEM_PRINCIPAL,'products',batch(count))
            assert job['status']=='ready' and state()==before, 'AC-PREVIEW: product rows changed'
            return 'preview ready; product table unchanged'
        try:submit(service,batch(count,invalid))
        except Conflict:rejected=True
        after=state(); detail=f'rows={count}; rejected={rejected}; added={len(after)-len(before)}'
        if invalid:
            assert rejected and after==before, 'AC-BATCH: expected rejected=True added=0; '+detail
        else:
            assert not rejected and len(after)-len(before)==count, 'AC-VALID: '+detail
            actual={r['sku']:(r['name'],r['sales_price_cents']) for r in after}
            expected={f'NEW-{i}':('商品'+str(i),1290) for i in range(1,count+1)}
            expected['KEEP']=('原有商品',990)
            assert actual==expected, f'AC-CONTENT: expected={expected}; actual={actual}'
        return detail


def original_tests(module):
    stream=io.StringIO(); tests=unittest.defaultTestLoader.loadTestsFromName(module)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(tests)
    assert result.testsRun>0 and result.wasSuccessful(),stream.getvalue()
    return stream.getvalue()


def help_image():
    raise AssertionError('教学观察项：操作文字完整，选读帮助待补辅助图')


def entries(count):
    return [('valid_batch','blocking',lambda:check_import(count)),
            ('invalid_batch_no_write','blocking',lambda:check_import(count,invalid=True)),
            ('preview_no_product_write','blocking',lambda:check_import(count,preview=True)),
            ('l05_personal_receiving','blocking',lambda:original_tests('tests.test_l05_receiving')),
            ('l05_personal_scope','blocking',lambda:original_tests('tests.test_l05_scope')),
            ('help_image','observing',help_image)]


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rows',type=int,default=3);p.add_argument('--report-path',required=True);a=p.parse_args()
    if not 2<=a.rows<=100:p.error('rows must be between 2 and 100')
    report,code=run(entries(a.rows),report_path=a.report_path)
    print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(code)
