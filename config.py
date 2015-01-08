
#Defaults - overridable via. pypayd.conf or command-line arguments
DEFAULT_KEYPATH = '0/0/2'
DEFAULT_TICKER = 'coindesk'
DEFAULT_CURRENCY = 'USD'
DEFAULT_WALLET_FILE = 'wallet.txt'
DEFAULT_WALLET_PASSWORD = "foobar"
DEFAULT_DB = "pypayd.db"
DEFAULT_TESTNET_DB = "pypayd_testnet.db"
#Pypay server settings
RPC_HOST ='127.0.0.1'
RPC_PORT = 3080
VERSION = 0.1
#Blockchain
TESTNET = True
BLOCKCHAIN_CONNECT = 'http://localhost:3001' #'https://test-insight.bitpay.com' #None
LOCAL_BLOCKCHAIN = True
BLOCKCHAIN_SERVICE = 'insight'
#generate a new address for every order if gen_new == True
GEN_NEW = False
#delay between requests to the blockchain service for new transactions
POLLING_DELAY = 60
#maximum time a leaf (address) is used to process orders before a new one is generated
MAX_LEAF_LIFE = 604800
#maximum number of transactions per address before a new one is generated
MAX_LEAF_TX = 9999
#maximum amount of time an order received for generated amount will be considered valid
ORDER_LIFE = 86400

#log file settings
LOG = None
MAX_LOG_SIZE = 16*1024*1024

STATE = {"last_order_updates": {"order_id":None, "timestamp": None}}
DATA_DIR = None 
DB = None
KEYPATH = None
LAST_USED_KEYPATH = None
