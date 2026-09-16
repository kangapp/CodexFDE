"""Observe multi-line reservations in the registered independent FlowERP project.

The controller resolves the project through the workbench process boundary and
re-runs this file with that project's Python. The worker uses a temporary
database only. No product source is copied into the course repository.

write-error installs a labelled SQLite trigger in that temporary database only.
It aborts the second reservation insert, exercising rollback after writes begin.
No remote CI or Codex session is started.
"""
from pathlib import Path
import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile


COURSE_ROOT = Path(__file__).resolve().parents[4]


def run(mode, product_root):
    sys.path.insert(0, str(product_root))
    from flowerp.store import ERPStore
    from flowerp.identity import IdentityService, SYSTEM_PRINCIPAL
    from flowerp import MasterDataService
    from flowerp.inventory import InventoryService
    from flowerp.sales import SalesService
    from flowerp.models import InsufficientStock

    with tempfile.TemporaryDirectory(prefix='l08-atomic-') as temp:
        store = ERPStore(Path(temp) / 'orders.db')
        IdentityService(store).ensure_local_defaults()
        master, inventory, sales = MasterDataService(store), InventoryService(store), SalesService(store)
        actor = SYSTEM_PRINCIPAL
        products = [master.create_product(actor, 'L08-' + sku, sku, 1000, 500) for sku in ('A', 'B')]
        customer = master.create_customer(actor, 'L08-C', '课程客户', credit_limit_cents=100000)
        for i, product in enumerate(products):
            inventory.receive(actor, product['id'], 'LOC-MAIN-STOCK',
                              2 if mode == 'shortage' and i == 1 else 5, f'l08-opening-{i}')
        order = sales.create_order(actor, customer['id'], [
            {'product_id': products[0]['id'], 'quantity': 2},
            {'product_id': products[1]['id'], 'quantity': 3}])
        sales.confirm(actor, order['id'])
        tables = ('stock_balance', 'stock_reservations', 'sales_document_lines', 'sales_documents')
        before = {table: store.rows(f'SELECT * FROM {table} ORDER BY rowid') for table in tables}
        if mode == 'write-error':
            product_id = products[1]['id'].replace("'", "''")
            with store.connect() as conn:
                conn.execute(f"CREATE TRIGGER l08_second_write BEFORE INSERT ON stock_reservations "
                             f"WHEN NEW.product_id='{product_id}' BEGIN "
                             "SELECT RAISE(ABORT, 'L08 injected second-write failure'); END")
        error = None
        try:
            sales.reserve(actor, order['id'])
        except (InsufficientStock, sqlite3.IntegrityError) as exc:
            error = {'type': type(exc).__name__, 'message': str(exc)}
        after = {table: store.rows(f'SELECT * FROM {table} ORDER BY rowid') for table in tables}
        balances = [inventory.balance(actor, p['id'], 'LOC-MAIN-STOCK') for p in products]
        current = sales.order(actor, order['id'])
        if mode == 'pass':
            assert error is None and current['status'] == 'reserved'
            assert [b['reserved'] for b in balances] == [2, 3]
            assert [b['available'] for b in balances] == [3, 2]
            assert len(after['stock_reservations']) == 2
        else:
            assert error is not None and before == after, (error, before, after)
            assert current['status'] == 'confirmed'
            assert [b['reserved'] for b in balances] == [0, 0]
            if mode == 'write-error':
                assert 'L08 injected second-write failure' in error['message']
            else:
                assert error['type'] == 'InsufficientStock'
        return {'mode': mode, 'evidence_kind': 'actual_service_temporary_database',
                'product_root': str(product_root),
                'status': current['status'], 'reserved': [b['reserved'] for b in balances],
                'available': [b['available'] for b in balances], 'error': error,
                'all_observed_tables_unchanged': before == after,
                'observed_tables': list(tables),
                'before': before, 'after': after,
                'real_remote_run': False}


def run_in_product_environment(mode):
    sys.path.insert(0, str(COURSE_ROOT))
    from workbench.external_project import flowerp_root, python_for

    root = flowerp_root()
    command = [python_for(root), '-X', 'utf8', str(Path(__file__).resolve()),
               mode, '--product-root', str(root)]
    completed = subprocess.run(command, cwd=root, text=True, encoding='utf-8')
    return completed.returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['pass', 'shortage', 'write-error'])
    parser.add_argument('--product-root', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.product_root:
        raise SystemExit(run_in_product_environment(args.mode))
    product_root = Path(args.product_root).resolve()
    if not (product_root / 'flowerp/server.py').is_file():
        raise SystemExit('product root must be an independent FlowERP repository')
    print(json.dumps(run(args.mode, product_root), ensure_ascii=False, indent=2))
