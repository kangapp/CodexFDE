"""Run L06 stock checks and the unchanged L05 scripts against an explicit candidate.

The adapters preserve each L05 script's exit and evidence; they do not reimplement
its assertions. The candidate must be a Git root for the engineering check.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--allow-file', type=Path, required=True)
    parser.add_argument('--report-path', type=Path, required=True)
    parser.add_argument('--opening', type=int, default=8)
    parser.add_argument('--reserved', type=int, default=3)
    args = parser.parse_args()
    if not 0 < args.reserved < args.opening:
        parser.error('require 0 < reserved < opening')
    root = args.candidate.resolve()
    source = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(root))
    from eval import harness
    from flowerp import ERPService, ERPStore
    from flowerp.models import InsufficientStock, OrderLine
    import flowerp.service
    if Path(flowerp.service.__file__).resolve() != root / 'flowerp/service.py':
        parser.error('loaded service is not in the requested candidate')
    if Path(harness.__file__).resolve() != root / 'eval/harness.py':
        parser.error('loaded Harness is not in the requested candidate')

    def stock_contract():
        with tempfile.TemporaryDirectory(prefix='l06-contract-') as directory:
            store = ERPStore(Path(directory) / 'stock.db')
            service = ERPService(store)
            service.add_product('L06-A', '口径实验商品', 1000)
            service.receive_stock('L06-A', args.opening, 'opening')
            order = service.create_order('教学订单', [OrderLine('L06-A', args.reserved, 1000)], 'A')
            service.reserve_order(order['id'])
            expected = args.opening - args.reserved
            query = service.product('L06-A')
            rows = list(csv.DictReader(io.StringIO(service.export_inventory().lstrip('\ufeff'))))
            selected = [row for row in rows if row['sku'] == 'L06-A']
            if len(selected) != 1:
                raise AssertionError(f'AC-CSV-ROW: expected=1, actual={len(selected)}')
            exported = selected[0]
            if query['available'] != expected or int(exported['available']) != expected:
                raise AssertionError(f"AC-AVAILABLE: expected={expected}, query={query['available']}, csv={exported['available']}, on_hand={args.opening}, reserved={args.reserved}")
            def state():
                return store.row('SELECT * FROM stock WHERE sku=?', ('L06-A',))
            before = state()
            excessive = service.create_order('教学超额订单', [OrderLine('L06-A', expected + 1, 1000)], 'B')
            try:
                service.reserve_order(excessive['id'])
            except InsufficientStock:
                pass
            else:
                raise AssertionError('AC-REJECT: excessive reservation was accepted')
            if state() != before:
                raise AssertionError('AC-UNCHANGED: rejected reservation changed stock row')
            return f'AC-AVAILABLE expected={expected}, query={expected}, csv={expected}; AC-REJECT quantity={expected+1}; AC-UNCHANGED complete stock row unchanged'

    def script_eval(script, *parts):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(source / 'docs/courses/L05/examples' / script), *map(str, parts)], capture_output=True, text=True, encoding='utf-8', cwd=root)
        if result.returncode:
            raise AssertionError(f'L05 exit={result.returncode}: {result.stdout} {result.stderr}')
        return result.stdout.strip()

    entries = [
        ('stock_query_csv_contract', 'blocking', stock_contract),
        ('l05_receiving_contract', 'blocking', lambda: script_eval('receiving_contract_eval.py', '--candidate', root)),
        ('l05_actual_write_scope', 'blocking', lambda: script_eval('write_scope_eval.py', '--repo', root, '--base', args.base, '--allow-file', args.allow_file.resolve())),
    ]
    argv = ['harness', '--suite', 'all', '--report-path', str(args.report_path.resolve())]
    for name, _, _ in entries:
        argv.extend(['--case', name])
    # Adapter registration is local to this invocation. Student integration must
    # register equivalent entries in their own candidate's actual quality entry.
    with patch.object(harness, 'EVALS', entries), patch.object(sys, 'argv', argv):
        return harness.main()


if __name__ == '__main__':
    raise SystemExit(main())
