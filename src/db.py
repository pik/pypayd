import time
from . import config
import json
import apsw
import logging

def qNum(num_items):
        return ','.join('?' for i in range(num_items))
def dName(s):
    return ','.join([(lambda x: ' :' + x[1:] if x[0] == ' ' else ':' + x)(i) for i in s.split(',')])
def rowtracer(cursor, sql):
    dictionary = {}
    for index, (name, type_) in enumerate(cursor.getdescription()):
        dictionary[name] = sql[index]
    return dictionary
    
class PyPayDB(object): 
    """Database object using apsw (I got some mixed info regarding pysqlite threading support: there seems to be a flag to enable it (sqlite3 does support threading) but I saw more than a few error reports as well) - therefore switching to APSW seemed like the safer bet.
    """
    def __init__(self, db_name):
        #con and con_ro, are write and read_only connections respectively 
        self.con = apsw.Connection(db_name)
        self.con_ro = apsw.Connection(db_name, flags=0x00000001)
        #set rowtacer for con_ro, so we don't have to do it for each cursor object
        self.con_ro.setrowtrace(rowtracer)
        self._initTables()
        #keep time-record of last update to tables
        self.last_updated = {"addresses": 0, "orders": 0, "payments": 0}
                
    def rquery(self, statement, bindings=()):
        ''' execute read '''
        cur = self.con_ro.cursor() 
        results = list(cur.execute(statement, bindings))
        cur.close()
        return results
        
    def wquery(self, statement, bindings = ()):
        ''' execute write '''
        cur = self.con.cursor() 
        #print(statement, "\n", bindings)
        logging.debug((statement, bindings))
        cur.execute(statement, bindings)
        cur.close()
        
    def _dropAllTables(self):
        ''' drop all tables in database '''
        cur = self.con.cursor()
        tables =list(cur.execute("select name from sqlite_master where type is 'table'"))
        cur.execute("begin; " + ';'.join(["drop table if exists %s" %i for i in tables]) + "; commit")
        cur.close()
        
    def _initTables(self): 
        ''' create pypayd tables '''
        self._initAddresses()
        self._initOrders()
        self._initPayments()

    def _initOrders(self): 
        ''' create order table '''
        statement = """create table if not exists orders (rowid INTEGER PRIMARY KEY, order_id UNIQUE NOT NULL, native_price, native_currency, btc_price, item_number, receiving_address, special_digits, keypath, creation_time INTEGER DEFAULT(strftime('%s', 'now')), max_life, filled DEFAULT 0)"""
        self.wquery(statement)
    def _initAddresses(self):
        ''' create address table '''
        statement= """create table if not exists addresses (rowid INTEGER PRIMARY KEY, receiving_address UNIQUE NOT NULL, keypath, max_tx, max_life, special_digits, creation_time INTEGER DEFAULT(strftime('%s', 'now')), last_used INTEGER DEFAULT(strftime('%s', 'now')))"""
        self.wquery(statement)
    def _initPayments(self):
        ''' create payment table '''
        statement= """create table if not exists payments (rowid INTEGER PRIMARY KEY, receiving_address, source_address, amount, txid UNIQUE NOT NULL, order_id, timestamp INTEGER DEFAULT(strftime('%s', 'now')), block_number, special_digits, confirmations, valid BOOL DEFAULT TRUE, notes)"""
        self.wquery(statement)
        
    #payments and invalid are insert or replace, since confirmations are updated.
    #TODO remove confirmations as table updating, and simply introduce a check to make sure the transaction has not been reversed (confirmations can simply be calculated after a querys as current_block - tx_block). 
    def addPayment(self, bindings): 
        s= "receiving_address, source_address, amount, txid, order_id, block_number, special_digits, confirmations, notes, valid"
        s2= dName(s)
        statement= ("insert or replace into payments(rowid, %s) VALUES((select rowid from payments where txid = :txid), %s )" %(s,s2))
        self.wquery(statement, bindings)
        self.last_updated['payments'] = time.time() 
        
    def addOrder(self, bindings):
        s = "order_id, native_price, native_currency, btc_price, item_number, receiving_address, special_digits, keypath, max_life"
        s2 = dName(s)
        statement = "insert into orders(%s) VALUES(%s)" %(s,s2)
        try: 
            self.wquery(statement, bindings)
            self.last_updated['orders'] = time.time() 
        except apsw.ConstraintError as e:
            logging.warn(e)
            return e
        return None
    
    def updateOrder(self, bindings): 
        self.updateInTable('orders', bindings)
    
    def updatePayment(self, bindings): 
        self.updateInTable('payments', bindings)
        
    def updateInTable(self, table, bindings): 
        ''' update fields in a single row for a table '''
        k = [i for i in list(bindings.keys()) if i not in (['txid', 'rowid' ] if table == 'payments' else ['order_id', 'rowid']) ]
        assert k and ('txid' in bindings.keys() or 'rowid' in bindings.keys() or 'order_id' in bindings.keys())
        statement = "update %s" %table
        for i in range(len(k)): 
            statement += ' AND' if i > 0 else ' SET' +' %s = :%s' %(k[i],k[i]) 
        statement += " where {0} = :{0}".format([i for i in bindings if i in ['rowid', 'txid', 'order_id']][0])
        self.wquery(statement, bindings)
        self.last_updated[table] = time.time() 
        
    def getFromTable(self, table, bindings):
        """Turn a list of bindings into a get query for the appropriate table, uses 'and' & '=', I don't think we need comprehensive dynamic querying for 3 tables, just write an sqlite statement for anything more specific."""
        k = list(bindings.keys())
        statement = "select * from %s" %table
        for i in range(len(k)):
            statement += (' AND' if i >0 else ' WHERE') + ' (%s = :%s)' %(k[i], k[i]) 
        return self.rquery(statement, bindings)
        
    def getPayments(self, bindings): 
        return self.getFromTable(table='payments', bindings=bindings) 
           
    def getOrders(self, bindings):
        return self.getFromTable(table='orders', bindings=bindings)
        
    def getAddresses(self, bindings):
        #statement = ("select * from addresses where timestamp > %s and in_use > %i " %((time.time() - order_life), 0))
        #config.POLL_LIFE, ~like about 24 hours
        return self.getFromTable(table='addresses', bindings= bindings)
