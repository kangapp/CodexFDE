"""Teaching scaffold: normal and forbidden paths must both be distinguished."""
import unittest
from eval.l05_scope import check_changes


class ScopeContract(unittest.TestCase):
    def test_allowed(self):
        self.assertEqual(check_changes(['flowerp/service.py'], {'flowerp/service.py'}), [], 'ENG-SCOPE: 合法修改不能误报')

    def test_forbidden(self):
        self.assertEqual(check_changes(['flowerp/service.py','web/unexpected.txt'], {'flowerp/service.py'}),
                         ['web/unexpected.txt'], 'ENG-SCOPE: 越界修改必须指出路径')


if __name__ == '__main__':
    unittest.main()
