import requests
import os
from src import wallet, db, payments, api, config, priceinfo
from src.priceinfo import ticker
from src.payments import PaymentHandler
from src.wallet import PyPayWallet
import time
import unittest
import ast
import logging
import json
'''
class QRCode(unittest.TestCase):
    def test_qr(self):
        address = "1HB5XMLmzFVj8ALj6mfBsbifRoD4miY36v"
        #assertDoesNotRaise(qr.bitcoinqr(address)) 
        #get QR from blockchain.info assert is equivalent 
'''

class PriceInfoTests(unittest.TestCase): 
    
    def testDummyTicker(self): 
        self.assertEqual(ticker.getPrice(ticker="dummy"), 350)
        self.assertEqual(ticker.getPriceInBTC(ticker="dummy", amount=175.0), 0.5)
        
    def testBitstampTicker(self):
        btc_price, last_updated = priceinfo.bitstampTicker()
        self.assertTrue((time.time() - float(last_updated) < 60))
        self.assertTrue(float(btc_price) > 0)
    
    def testCoindeskTicker(self): 
        btc_price, last_updated = priceinfo.coindeskTicker()
        self.assertTrue((time.time() - float(last_updated) < 60))
        self.assertTrue(float(btc_price) > 0)

mnemonic= "like just love know never want time out there make look eye"
priv_hwif_main = "xprv9s21ZrQH143K2jhRQJezi4Zw33cwbUUPvJEY4oAEXzzsBT6SvPziuLg1wLyk8aFnB3m3sGqHzD5smZgE4DToj7Pk77dbVy9oWKVDb2b8nVg"
pub_hwif_main = 'xpub661MyMwAqRbcFDmtWLC15CWfb5TRzwCFHXA8sBZr6LXr4FRbTwJyT8zVndatFTL3nGfwyNi6AxhWF5sazTfKXWWZLzRBsAkJ2dykobXC9No'
pub_hwif_test = 'tpubD6NzVbkrYhZ4X1xjxXB6H7r2vCZ5zKhJq9kSDjczSFHjoY6JYAA4bafL2fffmxHHaBCraxDxi4XYwGNCPKWZQwxrQbAVYhQXcbaAZaJhwBc'
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

class BlockchainInterfaces(unittest.TestCase): pass

headers = {'content-type': 'application/json'}

class PyPayState(unittest.TestCase):

    def setUpClass(): 
        #logging
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        console.setFormatter(formatter)
        logger.addHandler(console)
        logging.getLogger("requests").setLevel(logging.WARN)
        #config
        config.AUTH_REQUIRED = False
        config.GEN_NEW = False
        config.KEYPATH = '0/0/1'
        config.DEFAULT_CURRENCY = 'USD'
        config.MAX_LEAF_TX = 999
        config.DEFAULT_TICKER = 'dummy'
        config.POLLING_DELAY = 60
        #setup
        pypay_wallet = wallet.PyPayWallet.fromHwif(pub_hwif_test)
        database = db.PyPayDB(os.path.join("", "pypayd_tests.db"))
        database._dropAllTables()
        database._initTables()
        global handler
        handler = PaymentHandler(database=database, wallet=pypay_wallet)
        #handler.run() 
        global api_serv
        api_serv = api.API()
        api_serv.serve_forever(handler)
        global url
        time.sleep(.2)
        host, port= api_serv.server.socket.getsockname()
        url = 'http://' + host + ':' + str(port)
        #time.sleep(10000)
        
    def tearDownClass():
        api_serv.server.stop()
        
    def test1CreateOrder(self): 
        payload = {'id': 0, 'params': {'amount': 20.0, 'order_id': 'DUMMY_ORD_1', 'qr_code': True}, 'jsonrpc': '2.0', 'method': 'create_order'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(res['order_id'], payload['params']['order_id']) 
        self.assertEqual(res['amount'], '0.0570001')
        self.assertEqual(res['timeleft'], config.ORDER_LIFE)
        self.assertEqual(res['receiving_address'], 'mrUedhEhZzbmdSbmd41CxoTZuTVgrwdL7p')
        self.assertTrue(res['exact_amount']) 
        self.assertIsNotNone(res['qr_image'])
        #return error on creating the same order_id twice
        #check this since failed creations are skipping special digits atm
        payload = {'id': 0, 'params': {'amount': 40.0, 'order_id': 'DUMMY_ORD_1', 'qr_code': False}, 'jsonrpc': '2.0', 'method': 'create_order'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()
        self.assertIsNotNone(res['result']['error'])
        #self.assertEqual(res['error']['data']['type'], 'ConstraintError') 
        payload = {'id': 0, 'params': {'amount': 40.0, 'order_id': 'DUMMY_ORD_2', 'qr_code': True}, 'jsonrpc': '2.0', 'method': 'create_order'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(res['amount'], '0.1140003')
        
    def test2GetOrder(self): 
        payload = {'id': 0, 'params': {'bindings' : {'order_id': 'DUMMY_ORD_1' }}, 'jsonrpc': '2.0', 'method': 'get_orders'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['rowid'], 1)
        self.assertEqual(res['order_id'], 'DUMMY_ORD_1')
        self.assertEqual(res['native_price'], 20)
        self.assertEqual(res['native_currency'], config.DEFAULT_CURRENCY)
        self.assertIsNone(res['item_number'])
        self.assertFalse(res['filled']) 
        self.assertEqual(res['special_digits'], 1)
        self.assertEqual(res['keypath'], config.KEYPATH)
        self.assertTrue((time.time() - res['creation_time'] < 60))
        self.assertEqual(res['max_life'], config.ORDER_LIFE)
        
    def test3OrderReceived(self): 
        handler.pollActiveAddresses()
        payload = {'id': 0, 'params': {'bindings':{'order_id': 'DUMMY_ORD_2'}}, 'jsonrpc': '2.0', 'method': 'get_orders'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['filled'], 'c90c454b38fb6d449d52a0cb724a847e1b0210ecea796722c1fe798780eacd6b')
        self.assertEqual(res['order_id'], 'DUMMY_ORD_2')
        payload = {'id': 0, 'params': {'bindings':{'txid': 'c90c454b38fb6d449d52a0cb724a847e1b0210ecea796722c1fe798780eacd6b'}}, 'jsonrpc': '2.0', 'method': 'get_payments'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['amount'], 0.1140003)
        self.assertEqual(res['special_digits'], 3)
        self.assertEqual(res['order_id'], 'DUMMY_ORD_2')
        self.assertEqual(res['block_number'], 325705)
        self.assertEqual(res['receiving_address'], 'mrUedhEhZzbmdSbmd41CxoTZuTVgrwdL7p')
        self.assertEqual(res['valid'], 1)
        self.assertEqual(ast.literal_eval(res['source_address'])[0], 'mudvdSecGyVyZA6QczmdPczyFavb7rfaTi')
        self.assertEqual(ast.literal_eval(res['notes']), [])
        
    def test4InvalidReceived(self): 
        payload = {'id': 0, 'params': {'bindings':{'txid': 'b28c7fc0b6e710d657c7c83f0bdbb32ba494595d154e6883fecfd59691dd34ac'}}, 'jsonrpc': '2.0', 'method': 'get_payments'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['amount'], 0.0570333) 
        self.assertEqual(res['special_digits'], 333)
        self.assertEqual(ast.literal_eval(res['notes'])[0], 'order not found for special digits 333') 
        self.assertEqual(ast.literal_eval(res['source_address'])[0], 'n1RheG8Yx1bynzgjgHyBzobmubpRH9AM5f')
        self.assertEqual(res['valid'], 0)
        self.assertEqual(res['receiving_address'], 'mrUedhEhZzbmdSbmd41CxoTZuTVgrwdL7p') 
        
    def test5KeypathOverflow(self): 
        payload = {'id': 0, 'params': {'amount': 20.0, 'qr_code': False}, 'jsonrpc': '2.0', 'method': 'create_order'}
        for i in range(config.MAX_LEAF_TX-2): 
            res = requests.post( url, data=json.dumps(payload), headers=headers)
            time.sleep(.01)
        res = res.json()['result']
        self.assertEqual(res['receiving_address'], 'mg5C6ibPHeGh6goEXEMq1pwtSTowkHS8td') 
        self.assertEqual(res['amount'], '0.0570001')
        order_id = res['order_id']
        handler.pollActiveAddresses()
        payload = {'id': 0, 'params': {'bindings':{'order_id': order_id}}, 'jsonrpc': '2.0', 'method': 'get_orders'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['keypath'], '0/0/2')
        self.assertEqual(res['filled'], '86f1f6bf74612d3c31652d3834bf7359c169c8b60ada8f960d22c7dd568f84b9')
        payload = {'id': 0, 'params': {'bindings':{'order_id': 'U94KHGMvAyRkR4enrs6Lpx9ey4M'}}, 'jsonrpc': '2.0', 'method': 'get_payments'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        for tx in res: 
            self.assertEqual(tx['special_digits'], 1)
            self.assertEqual(tx['order_id'], order_id) 
            
    def test6GenNewAddress(self): 
        payload = {'id': 0, 'params': {'amount': 100.0, 'qr_code': False, 'gen_new': True}, 'jsonrpc': '2.0', 'method': 'create_order'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'] 
        self.assertEqual(res['amount'], '0.286') 
        self.assertEqual(res['exact_amount'], False) 
        self.assertEqual(res['receiving_address'], 'miXzTXvkEsfVmkwMjLCHfXAjboodrgQQ9Z')
        payload = {'id': 0, 'params': {'amount': 100.0, 'qr_code': False, 'gen_new': False}, 'jsonrpc': '2.0', 'method': 'create_order'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(res['receiving_address'], 'mjPS9N4T6cjcWLvdkv4jtCrzNA6C6qm8uv')
        self.assertEqual(res['amount'], '0.2860001') 
        self.assertTrue(res['exact_amount']) 
        order_id = res['order_id']
        payload = {'id': 0, 'params': {'bindings':{'receiving_address': 'mjPS9N4T6cjcWLvdkv4jtCrzNA6C6qm8uv'}}, 'jsonrpc': '2.0', 'method': 'get_address'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['keypath'], '0/0/4') 
        self.assertEqual(res['max_tx'], config.MAX_LEAF_TX)
        self.assertTrue(res['special_digits'] > 0) 
        
    def test7SpecialDigits(self): pass
     
    def test8ArbitraryKeypath(self): pass
    
    def test9Polling(self): pass

if __name__ == '__main__': 
    loader = unittest.TestLoader()
    #loader.sortTestMethodsUsing = None
    tests = loader.loadTestsFromName(__name__)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(tests)
    
