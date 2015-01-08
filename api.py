import os
import threading
import flask
from flask.ext.httpauth import HTTPBasicAuth
import cherrypy
from cherrypy import wsgiserver
import jsonrpc
from jsonrpc import dispatcher
import config
import json
import logging
import qr

class API(threading.Thread):
    def __init__(self): 
        threading.Thread.__init__(self)
    
    def run(self, payment_handler):
        app = flask.Flask(__name__)
        auth = HTTPBasicAuth()
        
        @dispatcher.add_method
        def is_ready(): 
            try: 
                payment_handler.checkBlockchainService() 
                payment_handler.checkPriceInfo() 
            except: return False 
            return True
            
        @dispatcher.add_method
        def create_order(amount, currency=config.DEFAULT_CURRENCY, item_number=None, order_id=None, gen_new = config.GEN_NEW, qr_code = False):
            amount, addr, order_id, timeleft, exact_amount = payment_handler.createOrder(amount, currency, item_number, order_id, gen_new)
            return {'amount': amount, 'receiving_address': addr, 'order_id': order_id, 'timeleft': timeleft, 'exact_amount': exact_amount, 'qr_image': (qr.bitcoinqr(addr) if qr_code else None)}
            
        @dispatcher.add_method
        def check_order_status(order_id=None, special_digits=None, timestamp=None, payment_address=None):  
            return payment_handler.CheckPaymentsFor(order_id=order_id, special_digits=special_digits, payment_address=payment_address, timestamp=timestamp)
        
        @dispatcher.add_method
        def get_payments(statement= "select * from payments", bindings= (),): 
            return payment_handler.db.getPayments(statement, bindings)
        @dispatcher.add_method
        def get_invalids(statement= "select * from invalid", bindings= (),): 
            return payment_handler.db.getInvalids(statement, bindings)
        @dispatcher.add_method
        def get_orders(statement= "select * from orders", bindings= (),): 
            return payment_handler.db.getOrders(statement, bindings)
        @dispatcher.add_method
        def get_active_orders(): 
            statement = "select * from orders where filled = 0 and timestamp > %s" %(time.time() - config.ORDER_LIFE)
            return payment_handler.query(statement)
        @dispatcher.add_method
        def query(statement, bindings=()):
            return payment_handler.db.rquery(statement, bindings)

        @auth.get_password
        def get_pw(username):
            if username == config.RPC_USER:
                return config.RPC_PASSWORD
            return None
        @app.route('/', methods = ["POST",])
        @app.route('/api', methods = ["POST",])
        #@auth.login_required
        def handle_post():
            # Dispatcher is dictionary {<method_name>: callable}
            try:
                request_json = flask.request.get_data().decode('utf-8')
                request_data = json.loads(request_json)
                assert('id' in request_data and request_data['jsonrpc'] == "2.0" and request_data['method'])
            except:
                obj_error = jsonrpc.exceptions.JSONRPCInvalidRequest(data="Invalid JSON-RPC 2.0 request format")
                return flask.Response(obj_error.json.encode(), 200, mimetype='application/json')
            jsonrpc_response = jsonrpc.JSONRPCResponseManager.handle(request_json, dispatcher)
            response = flask.Response(jsonrpc_response.json.encode(), 200, mimetype='application/json')
            #print(response)
            return response
        d = wsgiserver.WSGIPathInfoDispatcher({'/': app.wsgi_app})
        self.server = wsgiserver.CherryPyWSGIServer((config.RPC_HOST, config.RPC_PORT), d) 
        logging.info("API Started on %s" %(  config.RPC_HOST + ':' +  str(config.RPC_PORT)))
        self.server.start()

