
#Defaults - overridable via. pypayd.conf or command-line arguments
DEFAULT_KEYPATH = '0/0/1'
DEFAULT_TICKER = 'dummy'
DEFAULT_CURRENCY = 'USD'
DEFAULT_WALLET_FILE = 'wallet.txt'
DEFAULT_WALLET_PASSWORD = "foobar"
DB = None
DEFAULT_DB = "pypayd.db"
DEFAULT_TESTNET_DB = "paypayd_testnet.db"
#Pypay server settings
RPC_HOST ='127.0.0.1'
RPC_PORT = 3080
VERSION = 0.1
AUTH_REQUIRED = False
#Blockchain
TESTNET = True
BLOCKCHAIN_CONNECT = 'http://localhost:3001' #'https://test-insight.bitpay.com' #None
LOCAL_BLOCKCHAIN = True
BLOCKCHAIN_SERVICE = 'insight'
#generate a new address for every order if gen_new == True
GEN_NEW = False
#delay between requests to the blockchain service for new transactions
POLLING_DELAY = 30
#maximum time a leaf (address) is used to process orders before a new one is generated
MAX_LEAF_LIFE = 604800
#maximum number of transactions per address before a new one is generated
MAX_LEAF_TX = 9999
#maximum amount of time an order received for generated amount will be considered valid
ORDER_LIFE = 86400
#time from last order creation, after which an adress is considered stale and no longer polled
LEAF_POLL_LIFE = ORDER_LIFE*2

#log file settings
LOG = None
MAX_LOG_SIZE = 16*1024*1024

UPDATE_ON_CONFIRM = 6 #can also take a list, such as [6, 20, 100]
STATE = {"last_order_updates": {"order_id":None, "timestamp": None}}
DATA_DIR = ""
DB = None
KEYPATH = None
LAST_USED_KEYPATH = None
ZMQ_BIND = None
ZMQ_FEED = False
SOCKETIO_BIND = None
SOCKETIO_FEED = False
RPC_USER = 'user'
RPC_PASSWORD= 'password'

