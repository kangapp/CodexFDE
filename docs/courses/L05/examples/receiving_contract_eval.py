"""Read persistent receipt state in a specified candidate; use fresh temporary DBs.

Return-only mode intentionally models the older observation, not full acceptance.
No production database is opened and no source code is changed.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument('--return-only', action='store_true')
    parser.add_argument('--opening', type=int, default=20)
    parser.add_argument('--quantity', type=int, default=8)
    args = parser.parse_args()
    if min(args.opening, args.quantity) <= 0:
        parser.error('opening and quantity must be positive')
    root = args.candidate.resolve()
    if not (root / 'flowerp/service.py').is_file():
        parser.error('candidate must contain flowerp/service.py')
    sys.path.insert(0, str(root))
    from flowerp.service import ERPService
    from flowerp.store import ERPStore
    import flowerp.service
    assert Path(flowerp.service.__file__).resolve() == root / 'flowerp/service.py'
    observations, failures = [], []
    def require(condition, requirement, expected, actual):
        if not condition:
            failures.append({'requirement': requirement, 'expected': expected, 'actual': actual})
    with tempfile.TemporaryDirectory(prefix='l05-contract-') as temp:
        store = ERPStore(Path(temp) / 'receiving.db')
        service = ERPService(store)
        sku = 'L05-RECEIPT'
        service.add_product(sku, '收货核对商品', 1000)
        service.receive_stock(sku, args.opening, 'opening')
        def state():
            # Complete rows, including identity and timestamps, not just row count.
            return {'stock': store.row('SELECT * FROM stock WHERE sku=?', (sku,)),
                    'events': store.rows('SELECT * FROM inventory_events WHERE sku=? ORDER BY rowid', (sku,))}
        def expected_business(receipts):
            # Business expectations are calculated from inputs, not service results.
            return {'stock': {'sku': sku, 'on_hand': sum(q for _, q in receipts), 'reserved': 0},
                    'events': [{'event_key': key, 'sku': sku, 'quantity': quantity,
                                'reserved_delta': 0, 'event_type': 'receive', 'reference': 'manual'}
                               for key, quantity in receipts]}
        def business_state(snapshot):
            # Generated timestamps are compared on replay, not predicted in advance.
            fields = ('event_key', 'sku', 'quantity', 'reserved_delta', 'event_type', 'reference')
            return {'stock': {key: snapshot['stock'][key] for key in ('sku', 'on_hand', 'reserved')},
                    'events': [{key: event[key] for key in fields} for event in snapshot['events']]}
        initial = state()
        first_result = service.receive_stock(sku, args.quantity, 'receipt-A')
        first = state()
        replay_result = service.receive_stock(sku, args.quantity, 'receipt-A')
        replay = state()
        expected = args.opening + args.quantity
        require(first_result['on_hand'] == expected and replay_result['on_hand'] == expected
                and replay_result.get('idempotent_replay'), 'RETURN-ONLY',
                {'first': expected, 'replay': expected, 'replay_flag': True},
                {'first': first_result['on_hand'], 'replay': replay_result['on_hand'],
                 'replay_flag': replay_result.get('idempotent_replay')})
        observations.extend([{'step': name, 'on_hand': s['stock']['on_hand'],
                              'event_count': len(s['events']), 'event_keys': [x['event_key'] for x in s['events']]}
                             for name, s in [('opening', initial), ('first-A', first), ('replay-A', replay)]])
        if not args.return_only:
            receipts = [('opening', args.opening), ('receipt-A', args.quantity)]
            first_expected = expected_business(receipts)
            require(business_state(first) == first_expected,
                    'AC-FIRST', first_expected, business_state(first))
            require(first == replay, 'AC-REPLAY',
                    first, replay)
            service.receive_stock(sku, args.quantity, 'receipt-B')
            independent = state()
            new_expected = expected_business(receipts + [('receipt-B', args.quantity)])
            require(business_state(independent) == new_expected,
                    'AC-NEW', new_expected, business_state(independent))
            observations.append({'step': 'new-B', 'on_hand': independent['stock']['on_hand'],
                                 'event_count': len(independent['events'])})
            for quantity in (0, -1):
                before = state()
                try:
                    service.receive_stock(sku, quantity, f'invalid-{quantity}')
                except ValueError:
                    rejected = True
                else:
                    rejected = False
                after = state()
                require(rejected, 'AC-INVALID', 'ValueError', f'quantity={quantity}, rejected={rejected}')
                require(before == after, 'AC-UNCHANGED',
                        {'quantity': quantity, 'state': before}, {'quantity': quantity, 'state': after})
                observations.append({'step': f'invalid-{quantity}', 'rejected': rejected, 'state_unchanged': before == after})
    print(json.dumps({'case': 'return_only' if args.return_only else 'receiving_contract',
                      'status': 'fail' if failures else 'pass', 'source': str(root / 'flowerp/service.py'),
                      'observations': observations, 'failures': failures,
                      'scope': 'sequential requests; no concurrency or same-key different-content guarantee'}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
