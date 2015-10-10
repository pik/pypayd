import argparse
import os
import unittest
from test import test_wallet, test_qr, test_pypayd, test_priceinfo


class BlockchainInterfaces(unittest.TestCase): pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='pypayd_tests', description='Tests for PyPayd')
    parser.add_argument("-r","--required-only", help="test only required install", action='store_true')
    args = parser.parse_args()
    if not args.required_only:
        test_wallet.WalletTests.test3_toEncryptedFile = test_wallet.WalletTests.toEncryptedFile
        test_wallet.WalletTests.test4_fromEncryptedFile = test_wallet.WalletTests.fromEncryptedFile
    loader = unittest.TestLoader()
    #loader.sortTestMethodsUsing = None
    tests = unittest.TestSuite()
    for module in [test_wallet, test_qr, test_pypayd, test_priceinfo]:
        tests.addTests(loader.loadTestsFromModule(module))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(tests)

