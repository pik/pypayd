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
import subprocess as sp
from base64 import b64decode
from src import qr
#Move all Test Constants to test_config
from test_config import *

#There appears to be only one up-to-date python library for decoding QRCodes
#It does not have an automated install, it is python2 only and it depends on Zbars
#So just test using checkout_put w/ Zbars or skip test if Zbars does not exist.

class QRCode(unittest.TestCase):

    def test_gen_qr(self):
        payload_in = "1HB5XMLmzFVj8ALj6mfBsbifRoD4miY36v"
        qr_image = qr.bitcoinqr(payload_in)
        #convert from web to img form
        qr_image = qr_image.replace("data:image/png;base64,", '', 1)
        qr_image = b64decode(qr_image.encode('utf-8'))
        with open("tests/qr_test.png", "wb") as wfile:
            wfile.write(qr_image)
        try:
            payload_out = sp.check_output(['zbarimg', '-q', 'tests/qr_test.png'])
            self.assertEqual(payload_out.decode('utf-8').rstrip('\n'), "QR-Code:bitcoin:" + payload_in)
        except FileNotFoundError:
            print("zbarimg not found skipping qr test")

    def setUpClass():
        try:
            sp.check_output(['zbarimg', '-h'])
        except FileNotFoundError:
            unittest.skip(QRCode.test_gen_qr)

class PriceInfoTests(unittest.TestCase):

    def testDummyTicker(self):
        self.assertEqual(ticker.getPrice(ticker="dummy"), 350)
        self.assertEqual(ticker.getPriceInBTC(ticker="dummy", amount=175.0), 0.5)

    def testBitstampTicker(self):
        btc_price, last_updated = priceinfo.bitstampTicker()
        self.assertTrue((time.time() - float(last_updated) < TOLERABLE_TICKER_DELAY))
        self.assertTrue(float(btc_price) > 0)

    def testCoindeskTicker(self):
        btc_price, last_updated = priceinfo.coindeskTicker()
        self.assertTrue((time.time() - float(last_updated) < TOLERABLE_TICKER_DELAY))
        self.assertTrue(float(btc_price) > 0)

    def testBitcoinaverageglobalaverageTicker(self):
        btc_price, last_updated = priceinfo.bitcoinaverageglobalaverageTicker()
        self.assertTrue((time.time() - float(last_updated) < TOLERABLE_TICKER_DELAY))
        self.assertTrue(float(btc_price) > 0)

class WalletTests(unittest.TestCase):
    def tearDownClass():
        os.remove(os.path.join(config.DATA_DIR, wallet_file_name))

    def test1_WalletCounterWallet(self):
        wal = PyPayWallet.fromMnemonic(mnemonic, mnemonic_type="counterwalletseed", netcode = 'BTC')
        self.assertIsNotNone(wal)
        self.assertEqual(wal.hwif(as_private=True), priv_hwif_main)

    def test2_FromHwif(self):
        wal = PyPayWallet.fromHwif(priv_hwif_main,  netcode='BTC')
        self.assertEqual(wal.hwif(as_private=True), priv_hwif_main)
        wal = PyPayWallet.fromHwif(pub_hwif_main, netcode='BTC')
        self.assertEqual(wal.hwif(), pub_hwif_main)

    def test3_ToEncryptedFile(self):
        wal= PyPayWallet.fromHwif(priv_hwif_main, netcode='BTC')
        self.assertIsNotNone(wal.toEncryptedFile(test_pw, file_name= wallet_file_name, store_private=False))
        wal.keypath = wallet.KeyPath('0/11/11')
        self.assertIsNot(wal.toEncryptedFile(test_pw, file_name= wallet_file_name, store_private=True, force=True), 0)

    def test4_FromEncryptedFile(self):
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

class BlockchainInterfaces(unittest.TestCase): pass

class PyPayState(unittest.TestCase):

    def setUpClass():
        #logging
        logger = logging.getLogger()
        logger.setLevel(logging.WARN)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('\n%(message)s')
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
        config.POLLING_DELAY = 30
        config.DB = "tests_pypayd.db"
        config.DATA_DIR = "tests"
        config.RPC_PORT = 3434
        #setup
        pypay_wallet = wallet.PyPayWallet.fromHwif(pub_hwif_test)
        database = db.PyPayDB(os.path.join(config.DATA_DIR, "pypayd_tests.db"))
        database._dropAllTables()
        database._initTables()
        global handler
        handler = PaymentHandler(database=database, wallet=pypay_wallet)
        #dummy recorder
        global dummy
        if DUMMY_RECORD:
            config.BLOCKCHAIN_SERVICE = 'dummy'
            from src.interfaces import dummy
            dummy._wrapGetUrl(dummy._recordOutput)
        elif DUMMY_READ:
            config.BLOCKCHAIN_SERVICE = 'dummy'
            from src.interfaces import dummy
            dummy._restoreOutputFromFile()
            dummy._wrapGetUrl(dummy._restoreOutput)
        global api_serv
        api_serv = api.API()
        api_serv.serve_forever(handler)
        global url
        time.sleep(.2)
        host, port= api_serv.server.socket.getsockname()
        url = 'http://' + host + ':' + str(port)

    def tearDownClass():
        api_serv.server.stop()
        handler.db.con.close()
        handler.db.con_ro.close()
        if DUMMY_RECORD:
            dummy._writeRecorderToFile()
        os.remove(os.path.join(config.DATA_DIR, "pypayd_tests.db"))

    def test0_APIExceptions(self):
        payload = {'id': 0, 'params': {"foo": "bar"}, 'jsonrpc': '2.0', 'method': 'create_order'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()

    def test1_CreateOrder(self):
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
        #print("\n", res)
        self.assertIsNotNone(res['result']['error'])
        #self.assertEqual(res['error']['data']['type'], 'ConstraintError')
        payload = {'id': 0, 'params': {'amount': 40.0, 'order_id': 'DUMMY_ORD_2', 'qr_code': True}, 'jsonrpc': '2.0', 'method': 'create_order'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(res['amount'], '0.1140003')

    def test2_GetOrder(self):
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

    def test3_OrderReceived(self):
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
        self.assertEqual(res['block_number'], 530509)
        self.assertEqual(res['receiving_address'], 'mrUedhEhZzbmdSbmd41CxoTZuTVgrwdL7p')
        self.assertEqual(res['valid'], 1)
        self.assertEqual(ast.literal_eval(res['source_address'])[0], 'mudvdSecGyVyZA6QczmdPczyFavb7rfaTi')
        self.assertEqual(ast.literal_eval(res['notes']), [])

    def test4_InvalidReceived(self):
        payload = {'id': 0, 'params': {'bindings':{'txid': 'b28c7fc0b6e710d657c7c83f0bdbb32ba494595d154e6883fecfd59691dd34ac'}}, 'jsonrpc': '2.0', 'method': 'get_payments'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['amount'], 0.0570333)
        self.assertEqual(res['special_digits'], 333)
        self.assertEqual(ast.literal_eval(res['notes'])[0], 'order not found for special digits 333')
        self.assertEqual(ast.literal_eval(res['source_address'])[0], 'n1RheG8Yx1bynzgjgHyBzobmubpRH9AM5f')
        self.assertEqual(res['valid'], 0)
        self.assertEqual(res['receiving_address'], 'mrUedhEhZzbmdSbmd41CxoTZuTVgrwdL7p')

    def test5_KeypathOverflow(self):
        payload = {'id': 0, 'params': {'amount': 20.0, 'qr_code': False}, 'jsonrpc': '2.0', 'method': 'create_order'}
        for i in range(config.MAX_LEAF_TX-2):
            res = requests.post( url, data=json.dumps(payload), headers=headers)
            time.sleep(.001)
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

    def test6_GenNewAddress(self):
        payload = {'id': 0, 'params': {'amount': 100.0, 'qr_code': False, 'gen_new': True, 'order_id': 'DUMMY_ORD_3'}, 'jsonrpc': '2.0', 'method': 'create_order'}
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

    def test7_OrderReceivedGenNew(self):
        handler.pollActiveAddresses()
        payload = {'id': 0, 'params': {'bindings':{'order_id': 'DUMMY_ORD_3'}}, 'jsonrpc': '2.0', 'method': 'get_orders'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['filled'], 'fb8c47b612edc808f532ee00f1171935b901607163b300c1283886a8448c2e83')
        self.assertEqual(res['order_id'], 'DUMMY_ORD_3')
        payload = {'id': 0, 'params': {'bindings':{'txid': 'fb8c47b612edc808f532ee00f1171935b901607163b300c1283886a8448c2e83'}}, 'jsonrpc': '2.0', 'method': 'get_payments'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['amount'], 0.286)
        self.assertEqual(res['special_digits'], -1)
        self.assertEqual(res['order_id'], 'DUMMY_ORD_3')
        self.assertEqual(res['block_number'], 530515)
        self.assertEqual(res['receiving_address'], 'miXzTXvkEsfVmkwMjLCHfXAjboodrgQQ9Z')
        self.assertEqual(res['valid'], 1)
        self.assertEqual(ast.literal_eval(res['source_address'])[0], 'mqsY54wR1Kx5ot1vA25DBi9LFJLCwrtw3k')
        self.assertEqual(ast.literal_eval(res['notes']), [])

    def test8_SpecialDigits(self): pass

    def test9_ArbitraryKeypath(self):
        handler.wallet.keypath = wallet.KeyPath('0/11/11')
        payload = {'id': 0, 'params': {'amount': 100.0, 'qr_code': False, 'gen_new': False}, 'jsonrpc': '2.0', 'method': 'create_order'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(res['receiving_address'], 'n44GYHKzs8Ytd8cCdmzaxWpVLQpW8wo1gt')
        self.assertEqual(res['amount'], '0.2860001')

    def test10_Polling(self): pass

if __name__ == '__main__':
    loader = unittest.TestLoader()
    #loader.sortTestMethodsUsing = None
    tests = loader.loadTestsFromName(__name__)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(tests)

