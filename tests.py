import requests
import os
from src import wallet, priceinfo, qr
from src.wallet import PyPayWallet
import unittest
'''
class QRCode(unittest.TestCase):
    def test_qr(self):
        address = "1HB5XMLmzFVj8ALj6mfBsbifRoD4miY36v"
        #assertDoesNotRaise(qr.bitcoinqr(address)) 
        #get QR from blockchain.info assert is equivalent
'''
mnemonic= "like just love know never want time out there make look eye"
priv_hwif_main = "xprv9s21ZrQH143K2jhRQJezi4Zw33cwbUUPvJEY4oAEXzzsBT6SvPziuLg1wLyk8aFnB3m3sGqHzD5smZgE4DToj7Pk77dbVy9oWKVDb2b8nVg"
pub_hwif_main = 'xpub661MyMwAqRbcFDmtWLC15CWfb5TRzwCFHXA8sBZr6LXr4FRbTwJyT8zVndatFTL3nGfwyNi6AxhWF5sazTfKXWWZLzRBsAkJ2dykobXC9No'
test_pw = "test"
addresses = {"0/0/1": "1BxhLe9ikyAWrL89uV2q8tFF3TtyxuKKX4", "0/0/2": "1ZEofWQUcqSKaKcofPTBujZaUDEmKLeAL", "0/1/1": "13z2Qj2adQMTVyHFKFpeWqCxMHqrhx5cAo"}
wallet_file_name="test_wallet.txt"
class WalletTests(unittest.TestCase): 
    
    def testWalletElectrum(self): 
        wal = PyPayWallet.fromMnemonic(mnemonic, mnemonic_type="electrumseed")
        self.assertIsNotNone(wal)
        self.assertEqual(wal.hwif(as_private=True), priv_hwif_main)
        
    def testWalletCounterWallet(self): 
        wal = PyPayWallet.fromMnemonic(mnemonic, mnemonic_type="counterwalletseed")
        self.assertIsNotNone(wal)
        self.assertEqual(wal.hwif(as_private=True), priv_hwif_main)
        
    def testFromHwif(self): 
        wal = PyPayWallet.fromHwif(priv_hwif_main,  netcode='BTC')
        self.assertEqual(wal.hwif(as_private=True), priv_hwif_main) 
        wal = PyPayWallet.fromHwif(pub_hwif_main, netcode='BTC')
        self.assertEqual(wal.hwif(), pub_hwif_main)
  
    def testToEncryptedFile(self): 
        wal= PyPayWallet.fromHwif(priv_hwif_main, netcode='BTC')
        self.assertIsNotNone(wal.toEncryptedFile(test_pw, file_dir = "", file_name= wallet_file_name, store_private=False))
        self.assertIsNotNone(wal.toEncryptedFile(test_pw, file_dir ="", file_name= wallet_file_name, store_private=True, force=True))
  
    def testFromEncrytptedFile(self): 
        wal = PyPayWallet.fromEncryptedFile(test_pw,file_dir ="", file_name=wallet_file_name, netcode='BTC')
        self.assertEqual(wal.hwif(as_private=True), priv_hwif_main)
        
    def testWalletCurrentAddress(self): 
        wal = PyPayWallet.fromHwif(priv_hwif_main, keypath="0/0/1", netcode='BTC') 
        self.assertEqual(wal.getCurrentAddress(), addresses[str(wal.keypath)])
        
    def testWalletNewAddress(self): 
        wal = PyPayWallet.fromHwif(priv_hwif_main, keypath="0/0/1", netcode='BTC') 
        self.assertEqual(wal.getNewAddress(), addresses[str(wal.keypath)])
        
    def testWalletDynamicKeyPath(self): 
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
