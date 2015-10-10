import unittest
import os
from pypayd import config
from pypayd.wallet import PyPayWallet
from .fixtures import *

class WalletTests(unittest.TestCase):
    def tearDownClass():
        fp = os.path.join(config.DATA_DIR, wallet_file_name)
        if os.path.isfile(fp):
            os.remove(fp)

    def test1_WalletCounterWallet(self):
        wal = PyPayWallet.fromMnemonic(mnemonic, mnemonic_type="counterwalletseed", netcode = 'BTC')
        self.assertIsNotNone(wal)
        self.assertEqual(wal.hwif(as_private=True), priv_hwif_main)

    def test2_FromHwif(self):
        wal = PyPayWallet.fromHwif(priv_hwif_main,  netcode='BTC')
        self.assertEqual(wal.hwif(as_private=True), priv_hwif_main)
        wal = PyPayWallet.fromHwif(pub_hwif_main, netcode='BTC')
        self.assertEqual(wal.hwif(), pub_hwif_main)

    #@unittest.skipIf(args.required_only is True)
    def toEncryptedFile(self):
        wal= PyPayWallet.fromHwif(priv_hwif_main, netcode='BTC')
        self.assertIsNotNone(wal.toEncryptedFile(test_pw, file_name= wallet_file_name, store_private=False))
        wal.keypath = wallet.KeyPath('0/11/11')
        self.assertIsNot(wal.toEncryptedFile(test_pw, file_name= wallet_file_name, store_private=True, force=True), 0)

    def fromEncryptedFile(self):
        wal = PyPayWallet.fromEncryptedFile(test_pw, file_name=wallet_file_name, netcode='BTC')
        self.assertEqual(wal.hwif(as_private=True), priv_hwif_main)
        self.assertEqual(str(wal.keypath), '0/11/11')

    def test5_WalletCurrentAddress(self):
        wal = PyPayWallet.fromHwif(priv_hwif_main, keypath="0/0/1", netcode='BTC')
        self.assertEqual(wal.getCurrentAddress(), addresses[str(wal.keypath)])

    def test6_WalletNewAddress(self):
        wal = PyPayWallet.fromHwif(priv_hwif_main, keypath="0/0/1", netcode='BTC')
        self.assertEqual(wal.getNewAddress(), addresses[str(wal.keypath)])

    def test7_WalletDynamicKeyPath(self):
        wal = PyPayWallet.fromHwif(priv_hwif_main, keypath="0/0/1", netcode='BTC')
        wal.keypath.incr()
        self.assertEqual(wal.getCurrentAddress(), addresses[str(wal.keypath)])
        wal.keypath.incr(x=-1)
        self.assertEqual(wal.getCurrentAddress(), addresses[str(wal.keypath)])
        wal.keypath.incr(pos=1)
        wal.keypath.set_pos(1, -1)
        self.assertEqual(wal.getCurrentAddress(), addresses[str(wal.keypath)])

if __name__ == '__main__':
    unittest.main()
