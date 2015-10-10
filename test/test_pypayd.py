import os
import unittest
import time
import requests
import json
import ast
from pypayd import wallet, db, api, config, payments
from .fixtures import *

DUMMY_RECORD = False
DUMMY_READ = False
PAYLOAD = lambda : {
        'id': 0,
        'params': {},
        'jsonrpc': '2.0',
        }

headers = {'content-type': 'application/json'}

def setConfigOverrides():
    config.TESTNET = True
    config.AUTH_REQUIRED = False
    config.GEN_NEW = False
    config.KEYPATH = '0/0/1'
    config.DEFAULT_CURRENCY = 'USD'
    config.MAX_LEAF_TX = 999
    config.DEFAULT_TICKER = 'dummy'
    config.POLLING_DELAY = 30
    config.DB = "tests_pypayd.db"
    config.DATA_DIR = "test"
    config.RPC_PORT = 3434
    config.BLOCKCHAIN_SERVICE = "blockr"

def setupTestLogger():
    import logging
    logger = logging.getLogger()
    logger.setLevel(logging.WARN)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('\n%(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    logging.getLogger("requests").setLevel(logging.WARN)

def setupMockTesting():
    global dummy
    if DUMMY_RECORD:
        config.BLOCKCHAIN_SERVICE = 'dummy'
        from pypayd.interfaces import dummy
        dummy._wrapGetUrl(dummy._recordOutput)
    elif DUMMY_READ:
        config.BLOCKCHAIN_SERVICE = 'dummy'
        from pypayd.interfaces import dummy
        dummy._restoreOutputFromFile()
        dummy._wrapGetUrl(dummy._restoreOutput)

class PyPayState(unittest.TestCase):

    def setUpClass():
        #logging
        setupTestLogger()
        #config
        setConfigOverrides()
        #setup
        pypay_wallet = wallet.PyPayWallet.fromHwif(pub_hwif_test)
        database = db.PyPayDB(os.path.join(config.DATA_DIR, "pypayd_tests.db"))
        database._dropAllTables()
        database._initTables()
        global handler
        handler = payments.PaymentHandler(database=database, wallet=pypay_wallet)
        #dummy recorder
        setupMockTesting()
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
        payload = {
            'id': 0,
            'params': {"foo": "bar"},
            'jsonrpc': '2.0',
            'method': 'create_order'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()

    def test11_CreateOrder(self):
        payload = {
            'id': 0,
            'params': {'amount': 20.0, 'order_id': 'DUMMY_ORD_1', 'qr_code': True},
            'jsonrpc': '2.0',
            'method': 'create_order'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(res['order_id'], payload['params']['order_id'])
        self.assertEqual(res['amount'], '0.0570001')
        self.assertEqual(res['timeleft'], config.ORDER_LIFE)
        self.assertEqual(res['receiving_address'], 'mrUedhEhZzbmdSbmd41CxoTZuTVgrwdL7p')
        self.assertTrue(res['exact_amount'])
        self.assertIsNotNone(res['qr_image'])

    def test12_CreateOrder(self):
        #return error on creating the same order_id twice
        #check this since failed creations are skipping special digits atm
        payload = {
            'id': 0,
            'params': {'amount': 40.0, 'order_id': 'DUMMY_ORD_1', 'qr_code': False},
            'jsonrpc': '2.0',
            'method': 'create_order'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()
        self.assertIsNotNone(res['result']['error'])
        #self.assertEqual(res['error']['data']['type'], 'ConstraintError')

    def test13_CreateOrder(self):
        payload = {
            'id': 0,
            'params': {'amount': 40.0, 'order_id': 'DUMMY_ORD_2', 'qr_code': True},
            'jsonrpc': '2.0',
            'method': 'create_order'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(res['amount'], '0.1140003')

    def test2_GetOrder(self):
        payload = {
            'id': 0,
            'params': {'bindings' : {'order_id': 'DUMMY_ORD_1' }},
            'jsonrpc': '2.0',
            'method': 'get_orders'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['rowid'], 1)
        self.assertEqual(res['order_id'], 'DUMMY_ORD_1')
        self.assertEqual(res['native_price'], 20)
        self.assertEqual(res['native_currency'], config.DEFAULT_CURRENCY)
        self.assertIsNone(res['item_number'])
        self.assertFalse(res['filled'])
        self.assertEqual(res['special_digits'], 1)
        self.assertEqual(res['keypath'], config.KEYPATH)
        self.assertTrue((time.time() - res['created_at'] < 60))
        self.assertEqual(res['max_life'], config.ORDER_LIFE)

    def test3_OrderReceived(self):
        handler.pollActiveAddresses()
        payload = {
            'id': 0, 'params': {'bindings':{'order_id': 'DUMMY_ORD_2'}},
            'jsonrpc': '2.0',
            'method': 'get_orders'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['filled'], 'c90c454b38fb6d449d52a0cb724a847e1b0210ecea796722c1fe798780eacd6b')
        self.assertEqual(res['order_id'], 'DUMMY_ORD_2')

    def test4_PaymentFilled(self):
        payload = {
            'id': 0,
            'params': {'bindings':{'txid': 'c90c454b38fb6d449d52a0cb724a847e1b0210ecea796722c1fe798780eacd6b'}},
            'jsonrpc': '2.0',
            'method': 'get_payments'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['amount'], 0.1140003)
        self.assertEqual(res['special_digits'], 3)
        self.assertEqual(res['order_id'], 'DUMMY_ORD_2')
        #self.assertEqual(res['block_number'], 530509)
        self.assertEqual(res['receiving_address'], 'mrUedhEhZzbmdSbmd41CxoTZuTVgrwdL7p')
        self.assertEqual(res['valid'], 1)
        self.assertEqual(ast.literal_eval(res['source_address'])[0], 'mudvdSecGyVyZA6QczmdPczyFavb7rfaTi')
        self.assertEqual(ast.literal_eval(res['notes']), [])

    def test5_InvalidReceived(self):
        payload = {'id': 0,
            'params': {'bindings':{'txid': 'b28c7fc0b6e710d657c7c83f0bdbb32ba494595d154e6883fecfd59691dd34ac'}},
            'jsonrpc': '2.0',
            'method': 'get_payments'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()
        res = res['result'][0]
        self.assertEqual(res['amount'], 0.0570333)
        self.assertEqual(res['special_digits'], 333)
        self.assertEqual(ast.literal_eval(res['notes'])[0], 'order not found for special digits 333')
        self.assertEqual(ast.literal_eval(res['source_address'])[0], 'n1RheG8Yx1bynzgjgHyBzobmubpRH9AM5f')
        self.assertEqual(res['valid'], 0)
        self.assertEqual(res['receiving_address'], 'mrUedhEhZzbmdSbmd41CxoTZuTVgrwdL7p')

    def test6_KeypathOverflow(self):
        payload = {
            'id': 0,
            'params': {'amount': 20.0, 'qr_code': False},
            'jsonrpc': '2.0',
            'method': 'create_order'
            }
        for i in range(config.MAX_LEAF_TX-2):
            res = requests.post( url, data=json.dumps(payload), headers=headers)
            #I forgot what the point of a delay was now
            #time.sleep(.0001)
        res = res.json()['result']
        self.assertEqual(res['receiving_address'], 'mg5C6ibPHeGh6goEXEMq1pwtSTowkHS8td')
        self.assertEqual(res['amount'], '0.0570001')
        order_id = res['order_id']
        handler.pollActiveAddresses()
        payload = {'id': 0, 'params': {'bindings':{'order_id': order_id}}, 'jsonrpc': '2.0', 'method': 'get_orders'}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['keypath'], '0/0/2')
        self.assertEqual(res['filled'], '86f1f6bf74612d3c31652d3834bf7359c169c8b60ada8f960d22c7dd568f84b9')
        payload = {'id': 0,
            'params': {'bindings':{'order_id': 'U94KHGMvAyRkR4enrs6Lpx9ey4M'}},
            'jsonrpc': '2.0',
            'method': 'get_payments'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        for tx in res:
            self.assertEqual(tx['special_digits'], 1)
            self.assertEqual(tx['order_id'], order_id)

    def test81_GenNewAddress(self):
        """Creates a new address for a single order"""
        payload = {
            'id': 0,
            'params': {'amount': 100.0, 'qr_code': False, 'gen_new': True, 'order_id': 'DUMMY_ORD_3'},
            'jsonrpc': '2.0',
            'method': 'create_order'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(res['amount'], '0.286')
        self.assertEqual(res['exact_amount'], False)
        self.assertEqual(res['receiving_address'], 'miXzTXvkEsfVmkwMjLCHfXAjboodrgQQ9Z')

    def test82_GenNewAddress(self):
        """Creates a new incremental address if previous address was gen_new"""
        payload = {
            'id': 0,
            'params': {'amount': 100.0, 'qr_code': False, 'gen_new': False},
            'jsonrpc': '2.0',
            'method': 'create_order'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(res['receiving_address'], 'mjPS9N4T6cjcWLvdkv4jtCrzNA6C6qm8uv')
        self.assertEqual(res['amount'], '0.2860001')
        self.assertTrue(res['exact_amount'])
        order_id = res['order_id']
        payload = {
            'id': 0, 'params': {'bindings':{'receiving_address': 'mjPS9N4T6cjcWLvdkv4jtCrzNA6C6qm8uv'}},
            'jsonrpc': '2.0',
            'method': 'get_address'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['keypath'], '0/0/4')
        self.assertEqual(res['max_tx'], config.MAX_LEAF_TX)
        self.assertTrue(res['special_digits'] > 0)

    def test83_OrderReceivedGenNew(self):
        handler.pollActiveAddresses()
        payload = {
            'id': 0,
            'params': {'bindings':{'order_id': 'DUMMY_ORD_3'}},
            'jsonrpc': '2.0',
            'method': 'get_orders'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['filled'], 'fb8c47b612edc808f532ee00f1171935b901607163b300c1283886a8448c2e83')
        self.assertEqual(res['order_id'], 'DUMMY_ORD_3')
        payload = {
            'id': 0,
            'params': {'bindings':{'txid': 'fb8c47b612edc808f532ee00f1171935b901607163b300c1283886a8448c2e83'}},
            'jsonrpc': '2.0',
            'method': 'get_payments'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result'][0]
        self.assertEqual(res['amount'], 0.286)
        self.assertEqual(res['special_digits'], -1)
        self.assertEqual(res['order_id'], 'DUMMY_ORD_3')
        #self.assertEqual(res['block_number'], 530515)
        self.assertEqual(res['receiving_address'], 'miXzTXvkEsfVmkwMjLCHfXAjboodrgQQ9Z')
        self.assertEqual(res['valid'], 1)
        self.assertEqual(ast.literal_eval(res['source_address'])[0], 'mqsY54wR1Kx5ot1vA25DBi9LFJLCwrtw3k')
        self.assertEqual(ast.literal_eval(res['notes']), [])

    def test8_SpecialDigits(self): pass

    def test8_ArbitraryKeypath(self):
        handler.wallet.keypath = wallet.KeyPath('0/11/11')
        payload = {
            'id': 0,
            'params': {'amount': 100.0, 'qr_code': False, 'gen_new': False},
            'jsonrpc': '2.0',
            'method': 'create_order'
            }
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(res['receiving_address'], 'n44GYHKzs8Ytd8cCdmzaxWpVLQpW8wo1gt')
        self.assertEqual(res['amount'], '0.2860001')

    def test91_GetFilledOrders(self):
        """API call returns only fulfilled orders since specified time period
        or all fulfilled orders if no period is specified"""
        payload = PAYLOAD()
        payload['method'] = 'get_filled_orders'
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]['receiving_address'], 'mrUedhEhZzbmdSbmd41CxoTZuTVgrwdL7p')
        self.assertEqual(res[0]['order_id'], 'DUMMY_ORD_2')
        sorted(res, key = lambda x: x['created_at'])
        payload['params']['timestamp'] = res[0]['created_at'] + 1
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(len(res), 2)

    def test91_GetUnfilledOrders(self):
        """API call returns only unfulfilled orders since specified time period
        or all unfulfilled orders if no period is specified"""
        payload = PAYLOAD()
        payload['method'] = 'get_unfilled_orders'
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(len(res), 999)
        sorted(res, key = lambda x: x['created_at'])
        payload['params']['timestamp'] = res[-2]['created_at'] + 1
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(len(res), 1)

    def test92_GetPayments(self):
        payload = PAYLOAD()
        payload['method'] = 'get_payments'
        payload['params']['bindings'] = {}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(len(res), 7)
        payload['params']['bindings']['valid'] = False
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(len(res), 4)
        payload['params']['bindings']['valid'] = True
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(len(res), 3)

    def test93_GetOrders(self):
        payload = PAYLOAD()
        payload['method'] = 'get_orders'
        payload['params']['bindings'] ={}
        res = requests.post( url, data=json.dumps(payload), headers=headers).json()['result']
        self.assertEqual(len(res), 1002)

    def test99_Polling(self): pass

if __name__ == '__main__':
    unittest.main()

