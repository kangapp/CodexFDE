"""Runnable teaching scaffold. Add and explain at least one independent assertion."""
import os
from pathlib import Path
import tempfile
import unittest

from flowerp.service import ERPService
from flowerp.store import ERPStore


class ReceivingContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='l05-personal-')
        self.addCleanup(self.temp.cleanup)
        self.store = ERPStore(Path(self.temp.name) / 'case.db')
        self.service = ERPService(self.store)
        self.service.add_product('A', '收货测试', 100)
        self.opening = int(os.environ.get('L05_OPENING', '20'))
        self.quantity = int(os.environ.get('L05_QUANTITY', '8'))
        self.service.receive_stock('A', self.opening, 'opening')

    def state(self):
        return {'stock': self.store.row('SELECT * FROM stock WHERE sku=?', ('A',)),
                'events': self.store.rows('SELECT * FROM inventory_events WHERE sku=? ORDER BY rowid', ('A',))}

    def receive(self, key):
        try:
            self.service.receive_stock('A', self.quantity, key)
        except Exception as exc:
            self.fail(f'AC-RECEIVE: 合法收货 {key} 应完成，实际 {type(exc).__name__}: {exc}')

    def assert_business(self, keys):
        state = self.state()
        receipts = [('opening', self.opening)] + [(key, self.quantity) for key in keys]
        self.assertEqual({k:state['stock'][k] for k in ('sku','on_hand','reserved')},
                         {'sku':'A','on_hand':sum(q for _,q in receipts),'reserved':0}, 'AC-STOCK')
        fields = ('event_key','sku','quantity','reserved_delta','event_type','reference')
        self.assertEqual([{k:r[k] for k in fields} for r in state['events']],
                         [dict(zip(fields,(key,'A',q,0,'receive','manual'))) for key,q in receipts], 'AC-LEDGER')

    def test_first(self):
        self.receive('receipt-A'); self.assert_business(['receipt-A'])

    def test_replay(self):
        self.receive('receipt-A'); self.assert_business(['receipt-A'])
        before = self.state(); self.receive('receipt-A')
        self.assertEqual(self.state(), before, 'AC-REPLAY: 完整库存与流水必须不变')

    def test_new(self):
        self.receive('receipt-A'); self.receive('receipt-B')
        self.assert_business(['receipt-A','receipt-B'])

    def test_invalid_unchanged(self):
        for quantity in (0,-1):
            with self.subTest(quantity=quantity):
                before = self.state()
                with self.assertRaises(ValueError, msg='AC-INVALID'):
                    self.service.receive_stock('A',quantity,f'invalid-{quantity}')
                self.assertEqual(self.state(),before,'AC-UNCHANGED')


if __name__ == '__main__':
    unittest.main()
