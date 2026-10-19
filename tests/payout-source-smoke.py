"""Dependency-free tests of financial input validation (not Django integration)."""
import ast
import hashlib
import json
import re
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

source = ast.parse((Path(__file__).resolve().parents[1] / 'payouts' / 'service.py').read_text())
functions = [n for n in source.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in
             {'PayoutSafetyError', '_whole_tzs', '_profile_recipient', '_recipient_fingerprint'}]
namespace = {'Decimal': Decimal, 're': re, 'json': json, 'hashlib': hashlib,
             'BANK_CODES': frozenset('CRDB NMB ABSA'.split())}
exec(compile(ast.Module(body=functions, type_ignores=[]), '<payout-extracted-security-functions>', 'exec'), namespace)


class PayoutValidationSmoke(unittest.TestCase):
    def test_positive_integer_tzs(self):
        self.assertEqual(namespace['_whole_tzs'](100000), 100000)
        for amount in ('1.12', '-1', '0', 'NaN', 'Infinity'):
            with self.subTest(amount=amount), self.assertRaises(namespace['PayoutSafetyError']):
                namespace['_whole_tzs'](amount)

    def test_recipient_rejects_wrong_phone(self):
        profile = SimpleNamespace(is_complete=True, account_name='A Teacher', payout_method='mobile_money',
                                  phone_number='+255700000001', mobile_network='M-Pesa')
        self.assertEqual(namespace['_profile_recipient'](profile)['recipient_phone'], '255700000001')
        profile.phone_number = '+123999999'
        with self.assertRaises(namespace['PayoutSafetyError']):
            namespace['_profile_recipient'](profile)

    def test_recipient_rejects_unsupported_bank(self):
        profile = SimpleNamespace(is_complete=True, account_name='A Teacher', payout_method='bank',
                                  bank_name='Someone Else Bank', bank_account_number='1234567890')
        with self.assertRaises(namespace['PayoutSafetyError']):
            namespace['_profile_recipient'](profile)
        profile.bank_name = 'CRDB'
        self.assertEqual(namespace['_profile_recipient'](profile)['recipient_bank'], 'CRDB')

    def test_recipient_fingerprint_changes_on_tamper(self):
        one = {'channel': 'mobile', 'recipient_phone': '255700000001', 'recipient_name': 'Teacher'}
        two = {**one, 'recipient_phone': '255700000002'}
        self.assertNotEqual(namespace['_recipient_fingerprint'](one), namespace['_recipient_fingerprint'](two))


if __name__ == '__main__':
    unittest.main()
