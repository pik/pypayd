import json
from . import db, config, wallet, priceinfo
import decimal
import time
import threading
import logging
import imp
import os
from .db import qNum

D = decimal.Decimal
def normalizeAmount(amount): 
    return D(str(amount)).quantize(D('.0000000'))

def extractSpecialDigits(amount): 
    if type(amount) is not decimal.Decimal:
        amount = D(str(amount)).quantize(D('.0000000'))
    return int(str(amount)[-4:])
    
class PaymentHandler(object):
    def __init__(self, database, wallet, bitcoin_interface_name=config.BLOCKCHAIN_SERVICE): 
        self.locks = {'run': threading.Lock(), 'order': threading.Lock() }
        self.active_addresses = []
        self.db = database
        self.wallet = wallet
        self.bitcoin_interface_name = bitcoin_interface_name
        exec("from .interfaces import %s" %bitcoin_interface_name)
        global bitcoin_interface
        bitcoin_interface = eval(bitcoin_interface_name)
        #bitcoin_interface = imp.load_module(bitcoin_interface_name, f, fl, dsc)
        
    def checkPriceInfo(self):
        return priceinfo.ticker.getPrice()
        
    #fix blockchain service imports
    def checkBlockchainService(self):
        return bitcoin_interface.check()
    #Runs address polling for new payments
    def run(self):
        with self.locks['run']:
            self.poller_thread = threading.Thread(target=self._run)
            self.poller_thread.start()
    def stop(self): 
        try: self.poller_thread._stop()
        except: pass
    
    def _run(self, polling_delay=config.POLLING_DELAY):
        while True:
            t = time.time()
            self.pollActiveAddresses()
            time.sleep((config.POLLING_DELAY - (time.time() - t)))
    
    #add an include Invalids flag
    def getPayments(self, bindings):  
        payments = self.db.getPayments(bindings)
        return payments
        
    #add an include Invalids flag
    def pollPayments(self, bindings): 
        if not bindings.get('receiving_address'): 
            orders = self.db.getOrders(bindings)
        lock = self.locks
        bindings['receiving_address'] = orders[0]['receiving_address']
        pollAddress(orders[0]['receiving_address'])
        time.sleep(.5)
        return getPayments(bindings)
        
    def getActiveAddresses(self): 
        #todo add last updated var in db, then if addreses haven't been added, we can keep polling the old ones
        #if config self.db last updated >self.lastActiveAddressGrab #else return self.active_addresses
        return self.db.getAddresses({}) #getActiveAddresses

    def pollAddress(self, addr):
        logging.info('calling %s api for address info %s' %(self.bitcoin_interface_name, addr ) )
        unspent_tx = bitcoin_interface.getUtxo(addr)
        if unspent_tx: logging.debug("Found %i utxo for address %s processing..." %(len(unspent_tx), addr))
        for tx in unspent_tx:
            print(tx)
            #use yield instead?
            self.processTxIn(addr, tx)
            
    def pollActiveAddresses(self):
        self.current_block = bitcoin_interface.getInfo()['info']['blocks']
        self.active_addresses = [i['receiving_address'] for i in self.getActiveAddresses()]
        logging.info("Current block is %s polling %i active addresses" %(self.current_block, len(self.active_addresses) ))
        #No locks here, since _run() is locked atm.. We could thread this but it doesn't seem important.  
        for addr in self.active_addresses: 
            self.pollAddress(addr)
        
    def processTxIn(self, receiving_address, tx): 
        notes = []
        valid = True
        order = None
        #timestamp = time.time()
        tx_full = bitcoin_interface.getTxInfo(tx['txid'])
        #only one order per address, so just look up by address
        if config.GEN_NEW:
            try: 
                order = self.db.getOrders({'receiving_address': receiving_address})
                tx_special_digits= 0
                if len(order > 1): raise #config.GEN_NEW was changed at somepoint recently and the order is not unique to the address
            except: pass
        #otherwise extract digits 4-7
        if order is None: 
            amount = normalizeAmount(tx['amount'])
            tx_special_digits = extractSpecialDigits(amount)
            order = self.db.getOrders({'special_digits': tx_special_digits, 'receiving_address': receiving_address})
        try: 
            order = order[0]
            order_id=order['order_id']
        except:
            order_id=None
            valid = False
            notes.append("order not found for special digits %i" %tx_special_digits)
        else:
            if not amount >=  D(order['btc_price']):
                valid = False
                notes.append("amount received is less than btc_price required for order_id %s" %order_id)
            elif amount > D(order['btc_price']) + D('.0000001'):
                notes.append("transaction with order_id %s overpaid amount by %s" %(order_id, str(amount - D(order['btc_price'])))) #Negligible overpay
             #processing as config.ORDER_LIFE allows some control (i.e. if there was a server shutdown and we want to process old orders) blockchain timestamps are unfortunatly not very accurate
            if not float(order['creation_time']) > timestamp - config.ORDER_LIFE:
                valid = False 
                notes.append("transaction received after expiration time for order_id %s" %order_id)
            if order['filled'] != 0 and order['filled'] != tx['txid']:
                valid = False
                notes.append("payment for order_id %s has already been received with txid %s" %(order_id, self.db.getPayments({'order_id': order_id})[0]['txid']))
        logging.debug("Results ", valid, " ", str(notes))
        sources = str(self.sourceAddressesFromTX(tx_full)) 
        bindings = {'receiving_address': receiving_address, 'txid': tx['txid'], 'source_address': sources, 'confirmations': (tx.get('confirmations') or 0), 'block_number': (self.current_block - (tx.get('confirmations')) or 0), 'notes': str(notes), 'tx_special_digits':tx_special_digits, 'order_id': order_id, 'amount': float(amount)} 
        if valid: 
            #fix timestamping on updates, don't update confirmation list at all maybe?
            #anyways insert or replace will work for now but it's more writing than we need to be doing
            self.db.addPayment(bindings)
            if order['filled'] == 0:
                self.db.updateOrder({'order_id': order_id, 'filled': tx['txid']})
            logging.debug("Recorded payment for receiving address etc")
        else: 
            self.db.addInvalid(bindings)
            logging.debug("Recorded invalid for receiving address etc")
        return True
            
    def sourceAddressesFromTX(self, tx_full): 
        return [i['addr'] for i in tx_full['vin']]

    def createOrder(self, amount, currency=config.DEFAULT_CURRENCY, item_number=None, order_id=None, gen_new = False):
        #timestamp = time.time()
        try: 
            btc_price = priceinfo.getPriceInBTC(amount, currency=currency).__str__()
        except: 
            return "error stuff failed to connect to price server"
        #special_digits are 0 on gen_new, we add them to the db but ignore them for the order, and return exact_amount: False
        with self.locks['order']: 
            receiving_address, special_digits = self.getPaymentAddress(gen_new)
        if not receiving_address: 
            return "failed to obtain payment address stuff"
        if not gen_new: 
            btc_price = btc_price.__str__() + ('0000' + str(special_digits))[-4:]
        #add timestamp to hash? 
        #change hash to hex
        if not order_id: 
            order_id = hash(json.dumps({'price': str(btc_price), 'address': str(receiving_address), 'special_digits': str(special_digits)}))
        timeleft = config.ORDER_LIFE
        self.db.addOrder({'order_id': order_id, 'native_price': amount, 'native_currency': currency, 'btc_price': btc_price, 'special_digits':special_digits,
        'keypath': str(self.wallet.keypath), 'item_number': item_number, 'receiving_address':receiving_address, 'max_life': config.ORDER_LIFE}) 
        return btc_price, receiving_address, order_id, timeleft, not gen_new

    def getNewAddress(self): 
        #Temporary - This won't work properly if the wallet is loaded from a child key on the same branch as a previously used master
        #But it will find the first unused value even if the wallet has been loaded at different ranges
        used= self.db.rquery("select keypath from addresses")
        while( list(filter(lambda x: x['keypath'] == str(self.wallet.keypath), used))):
            self.wallet.keypath.incr()
        logging.debug("generated new address at %s" %str(self.wallet.keypath))
        new_addr = self.wallet.getCurrentAddress()
        self.addAddress(new_addr)
        return new_addr
        
    #move this to DB
    def addAddress(self, new_addr):
        statement = "insert into addresses(receiving_address, keypath, max_tx, max_life, special_digits) VALUES(%s)" %qNum(5)
        bindings = (new_addr, str(self.wallet.keypath), config.MAX_LEAF_TX, config.MAX_LEAF_LIFE, 0 if config.GEN_NEW else 1)
        self.db.wquery(statement, bindings)

    def getPaymentAddress(self, gen_new): 
        current_address = self.wallet.getCurrentAddress()
        try:
            result = self.db.rquery("select * from addresses where (receiving_address = %s)" %current_address) 
        #If table is empty
        except: result = None
        if not result: 
             self.addAddress(current_address)
             return current_address, 0 if config.GEN_NEW else 1
        else: 
            receiving_address= result[0]
        #Check if we hit a condition to generate a new address (note that atm, max_tx are hard-capped at 9999, independent of config settings)
        if ( (time.time() - float(receiving_address['max_life'])) > float(receiving_address['creation_time']) ) or (receiving_address['special_digits'] >= receiving_address['max_tx']) or (receiving_address['special_digits'] >= 9999) or gen_new: 
            return self.getNewAddress(), 0 if config.GEN_NEW else 1
        else: 
            #increment digits on old address and updated last_used time
            self.db.wquery("update addresses set special_digits = special_digits +1, last_used = strftime('%s', 'now') where receiving_address = ?", (receiving_address['receiving_address'], )) 
            return receiving_address['receiving_address'], receiving_address['special_digits'] + 1 
            
#tests 
if __name__ == '__main__':
    wallet = wallet.PyPayWallet.fromEncryptedFile("foobar")
    database = db.PyPayDB("pypay_testnet.db")
    P = PaymentHandler(database=database, wallet=wallet)
"""
def ex(s): 
    cur=con.cursor()
    res = list(cur.execute(s))
    cur.close()
    return res
 """

