import json
from . import db, config, wallet
from .priceinfo import ticker
import decimal
import time
import threading
import logging
import imp
import os
from hashlib import sha1
from pycoin.encoding import b2a_base58
from .db import qNum

D = decimal.Decimal
def normalizeAmount(amount):
    return D(str(amount)).quantize(D('.0000000'))

def ensureList(l):
        return l if isinstance(l, list) else [l]

def extractSpecialDigits(amount):
    if type(amount) is not decimal.Decimal:
        amount = D(str(amount)).quantize(D('.0000000'))
    return int(str(amount)[-4:])

class ProcessingError(Exception):
    pass

class PaymentHandler(object):
    """The Payment Handler class - this basically handles all the payment logic connecting all the other interfaces (wallet, db, api, message_feed, blockchain_interface)
    """
    #One particular aspect of current transaction handling is that order's are not given a block_number; on creation, for an order to be filled #a payment must be received within a certain time - in otherwords Pypay does not check if the payment was made prior to order creation - #this may be convenient in certain cases (i.e. resubmitting an order to validate an invalid payment), the major drawback is that addresses #that are used for other functions should NOT be used as payment addresses
    #Todo - Add a configureable flag to disable this behaviour
    def __init__(self, database, wallet, bitcoin_interface_name= None):
        self.locks = {'order': threading.Lock(), 'polling':threading.Lock()}
        self.polling = {'addresses': [], 'last_updated': 0}
        self.db = database
        self.wallet = wallet
        if not bitcoin_interface_name:
            bitcoin_interface_name = config.BLOCKCHAIN_SERVICE
        self.bitcoin_interface_name = bitcoin_interface_name
        exec("from .interfaces import %s" %bitcoin_interface_name) #instead of 6 lines of importlib
        global bitcoin_interface
        bitcoin_interface = eval(bitcoin_interface_name)
        bitcoin_interface.setHost()

    def checkPriceInfo(self):
        return ticker.getPrice()

    #fix blockchain service imports
    def checkBlockchainService(self):
        return bitcoin_interface.check()

    #Runs address polling for new payments
    def run(self):
        self.poller_thread = threading.Thread(target=self._run, daemon=True)
        self.poller_thread.start()
        return self.poller_thread.is_alive(), self.poller_thread.ident

    def _run(self, polling_delay=config.POLLING_DELAY):
        while True:
            t = time.time()
            self.pollActiveAddresses()
            time.sleep((config.POLLING_DELAY - (time.time() - t)))

    def getPayments(self, bindings):
        payments = self.db.getPayments(bindings)
        return payments

    def pollPayments(self, bindings):
        if not bindings.get('receiving_address'):
            orders = self.db.getOrders(bindings)
        bindings['receiving_address'] = orders[0]['receiving_address']
        pollAddress(orders[0]['receiving_address'])
        time.sleep(.5)
        return getPayments(bindings)

    def updateActiveAddresses(self):
        '''If the database has been updated, refresh the list of active addresses'''
        if self.db.last_updated['addresses'] >= self.polling['last_updated'] or time.time() - 600 > self.polling['last_updated']:
            #Get all addresses that have not been stale for longer than leaf poll life
            addresses = self.db.rquery("select * from addresses where last_used > %s" %(time.time() - config.LEAF_POLL_LIFE))
            self.polling['addresses'] = [i['receiving_address'] for i in addresses]
            self.polling['last_updated'] = time.time()

    def pollAddress(self, addr):
        logging.info('calling %s api for address info %s' %(self.bitcoin_interface_name, addr ) )
        unspent_tx = bitcoin_interface.getUtxo(addr)
        if unspent_tx: logging.debug("Found %i utxo for address %s processing..." %(len(unspent_tx), addr))
        for tx in unspent_tx:
            logging.debug(("tx: ", tx))
            self.processTxIn(addr, tx)

    #Add socketio listener option for locally hosted insight-api
    def pollActiveAddresses(self):
        '''Polling for inbound transactions to acvie address'''
        with self.locks['polling']:
            self.current_block = bitcoin_interface.getInfo()['info']['blocks']
            self.updateActiveAddresses()
            logging.info("Current block is %s polling %i active addresses" %(self.current_block, len(self.polling['addresses']) ))
            #No locks here, since _run() is locked atm.. We could thread this but it doesn't seem important.
            for addr in self.polling['addresses']:
                self.pollAddress(addr)

    def processTxIn(self, receiving_address, tx):
        '''This method handles transactions inbound to active addresses '''
        #Add USD value at time of receipt to database?
        notes = []
        valid = True
        order = None
        order_id = None
        timestamp = time.time()
        tx_full = bitcoin_interface.getTxInfo(tx['txid'])
        tx_record = self.db.getPayments({"txid": tx['txid']})
        amount = normalizeAmount(tx['amount'])
        if tx_record:
            tx_record = tx_record[0]
            availableCheckPoints = lambda conf: len([i for i in ensureList(config.UPDATE_ON_CONFIRM) if i > conf])
            #If a payment exists but has been recorded with less confirmations then a possible checkpoint, update the confirmation number
            if availableCheckPoints(tx_record['confirmations']) > availableCheckPoints(tx.get('confirmations', 0)):
                self.db.updatePayment({"txid": tx["txid"], "confirmations": tx['confirmations']})
                #Publish checkpoint update info
                #feed.publishMessage()
            else:
                logging.debug("tx_record for txid %s exists, no updates to record" %tx_record['txid'])
            return True
        # Look for an order by special_digits
        tx_special_digits = extractSpecialDigits(amount)
        orders = self.db.getOrders({'special_digits': tx_special_digits, 'receiving_address': receiving_address})
        # If Orders not found by special_digits see if it's singular
        try:
            if not orders:
                orders = self.db.getOrders({'receiving_address': receiving_address})
                # If the order is not gen_new and this should fail
                assert(len(orders) == 1)
                assert(orders[0]['special_digits'] == -1)
                tx_special_digits = -1
            order = orders[0]
            order_id = order['order_id']
        except AssertionError:
            valid = False
            order = {}
            order_id = None
            notes.append("order not found for special digits %i" %tx_special_digits)
        if valid:
            #A matching order has been found - verify other validity parameters
            if not amount >=  D(order['btc_price']):
                valid = False
                notes.append("amount received is less than btc_price required for order_id %s" %order_id)
            elif amount > D(order['btc_price']) + D('.00001'):
                notes.append("transaction with order_id %s overpaid amount by %s" %(order_id, str(amount - D(order['btc_price']))))
             #processing as config.ORDER_LIFE allows some control (i.e. if there was a server shutdown and we want to process old orders) blockchain timestamps are unfortunatly not very accurate
            if not order['creation_time'] > timestamp - config.ORDER_LIFE:
                valid = False
                notes.append("transaction received after expiration time for order_id %s" %order_id)
            if order['filled'] != 0 and order['filled'] != tx['txid']:
                valid = False
                notes.append("payment for order_id %s has already been received with txid %s" %(order_id, order['filled']))
        logging.debug(("txid: ", tx['txid'], "Result: ", valid, "      Notes ", str(notes)))
        sources = str(bitcoin_interface.sourceAddressesFromTX(tx_full))
        #payment record
        bindings = {'receiving_address': receiving_address, 'txid': tx['txid'], 'source_address': sources, 'confirmations': tx.get('confirmations', 0) , 'block_number': (self.current_block -tx.get('confirmations', 0)), 'notes': str(notes), 'special_digits':tx_special_digits, 'order_id': order_id, 'amount': float(amount), "valid": valid }
        self.db.addPayment(bindings)
        #update order
        if order.get('filled') == 0 and valid == True:
            self.db.updateOrder({'order_id': order_id, 'filled': tx['txid']})
        #Send event to socketio / ZMQ feed
        #There should either be a dummy feed class or a self method which will do nothing if config.ZMQ_FEED = False
        #feed.publishMessage("payments", "new", str(bindings))
        return True

    def createOrder(self, amount, currency=config.DEFAULT_CURRENCY, item_number=None, order_id=None, gen_new = None):
        '''The main order creation method to which the api call is routed'''
        if gen_new is None:
            gen_new = config.GEN_NEW
        #timestamp = time.time()
        #Try ret
        btc_price = str(ticker.getPriceInBTC(amount, currency=currency))
        #if error: return error
        #special_digits are 0 on gen_new, we add them to the db but ignore them for the order, and return exact_amount: False
        with self.locks['order']:
            receiving_address, special_digits = self.getPaymentAddress(gen_new)
        if not receiving_address:
            return "failed to obtain payment address stuff"
        if not gen_new:
            btc_price = btc_price.__str__() + ('0000' + str(special_digits))[-4:]
        #Hash an order_id as base58 - because if someone needs to reference it the bitcoin standard is the most readable
        #Note that the pycoin to_long method reads bytes as big endian.
        if not order_id:
            order_id = b2a_base58(sha1(json.dumps({'price': str(btc_price), 'address': str(receiving_address), 'special_digits': str(special_digits)}).encode('utf-8')).digest())
        timeleft = config.ORDER_LIFE
        err= self.db.addOrder({'order_id': order_id, 'native_price': amount, 'native_currency': currency, 'btc_price': btc_price, 'special_digits':special_digits,
        'keypath': str(self.wallet.keypath), 'item_number': item_number, 'receiving_address':receiving_address, 'max_life': config.ORDER_LIFE})
        if err:
            return {'error': str(err)}
        return {'amount': btc_price, 'receiving_address': receiving_address, 'order_id': order_id, 'timeleft': timeleft, 'exact_amount': not gen_new}

    def getNewAddress(self, special_digits=None):
        ''' Obtain a new payment address from the wallet'''
        #Change this later - This won't work properly if the wallet is loaded from a child key on the same branch as a previously used master
        #But it will find the first unused value even if the wallet has been loaded at different ranges
        used= self.db.rquery("select keypath from addresses")
        while( list(filter(lambda x: x['keypath'] == str(self.wallet.keypath), used))):
            self.wallet.keypath.incr()
        logging.debug("generated new address at %s" %str(self.wallet.keypath))
        new_addr = self.wallet.getCurrentAddress()
        self.addAddress(new_addr, special_digits)
        return new_addr

    #move this to DB
    def addAddress(self, new_addr, special_digits=None):
        ''' Add address to database '''
        if not special_digits:
            special_digits = -1 if config.GEN_NEW else 1
        statement = "insert into addresses(receiving_address, keypath, max_tx, max_life, special_digits) VALUES(%s)" %qNum(5)
        bindings = (new_addr, str(self.wallet.keypath), config.MAX_LEAF_TX, config.MAX_LEAF_LIFE, special_digits)
        self.db.wquery(statement, bindings)
        self.db.last_updated['addresses'] = time.time()

    def getPaymentAddress(self, gen_new):
        '''
        Obtain a payment address
           Set gen_new=True to create a new address irrespective of config settings
           Note that max_tx is set form config an addresses max_tx is set from config.MAX_LEAF_TX at creation time -
           a lower config.MAX_LEAF_TX value, will force gen_new - but a higher one will ignored if max_tx is already added to an entry.
        '''
        #Currently a requested address or special digit will be marked as used independent of further errors with the order
        #This can be made atomic later, so i.e. a duplicate order_id won't increment special digits
        current_address = self.wallet.getCurrentAddress()
        try:
            result = self.db.rquery("select * from addresses where (receiving_address = '%s')" %current_address)
        #If table is empty
        except:
            result = []
        if not result:
             self.addAddress(current_address, -1 if gen_new else 1)
             return current_address, -1 if gen_new else 1
        else:
            receiving_address= result[0]
        #Check if we hit a condition to generate a new address (note that atm, max_tx are hard-capped at 9999, independent of config settings)
        if ( (time.time() - float(receiving_address['max_life'])) > float(receiving_address['creation_time']) ) or (receiving_address['special_digits'] >= (config.MAX_LEAF_TX if receiving_address['max_tx'] > config.MAX_LEAF_TX else receiving_address['max_tx'])) or (receiving_address['special_digits'] >= 9999) or gen_new or (receiving_address['special_digits'] == -1):
            return self.getNewAddress(-1 if gen_new else 1), -1 if gen_new else 1
        else:
            #increment digits on old address and update last_used time
            self.db.wquery("update addresses set special_digits = special_digits +1, last_used = strftime('%s', 'now') where receiving_address = ?", (receiving_address['receiving_address'], ))
            return receiving_address['receiving_address'], receiving_address['special_digits'] + 1

if __name__ == '__main__':
    wallet = wallet.PyPayWallet.fromEncryptedFile("foobar")
    database = db.PyPayDB("pypay_testnet.db")
    handler = PaymentHandler(database=database, wallet=wallet)

