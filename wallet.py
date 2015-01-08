from pycoin.key.BIP32Node import *
import config
from simplecrypt import encrypt, decrypt 
from interfaces.counterwalletseed import mnemonicToEntropy
import time 
import json
import os
"""
Wallet wrapper around the Pycoin implementation. (Pycoin is a little heavier of a dependency than we need, but it already supports python3 and keypath-address handling). 
The savePrivate() and savePublic() methods will save the public and/or private keys available to this wallet in an encrypted file using simplecrypt. Note: You do not need to have the privatekeys to generate new addresses.
The MasterKey or the PublicKey for the branch specified in the configfile must be loaded at startup, branches take default numbers. Currently hardened branch's are incremented to none-hardened ones (since hardened branches require a privatekey, which you hopefully aren't loading). 
"""
NETCODES = {"mainnet": "BTC", "testnet": "XTN"}

#To Do: enable autosweep, privkey_mode only
#sweep address function
#sweep branch function
    
class PyPayWallet(BIP32Node):
    @classmethod
    def fromEntropy(cls, seed): 
        return cls.from_master_secret(seed)
    
    @classmethod
    def fromMnemonic(cls, mnemonic, mnemonic_type = "electrumseed"):
        exec("from interfaces.{0} import mnemonicToEntropy".format(mnemonic_type))
        seed = mnemonicToEntropy(mnemonic) 
        return cls.from_master_secret(seed)
        
    def toEncryptedFile(self, password, file_dir=config.DATA_DIR, file_name=config.DEFAULT_WALLET_FILE, store_private=False, force=False): 
        wallet = json.dumps({ "keypath": self.keypath, "pubkey": self.hwif(), "privkey": (self.hwif(True) if (self.is_private() and store_private ) else None) })
        data = encrypt(password, wallet)
        target = os.path.join(file_dir, file_name)
        if os.path.isfile(target) and not force: return False
        try:
            with open(target, 'wb') as wfile: 
                result = wfile.write(data)
                assert(len(data) == result)
        except: return False
        return result
        
    @classmethod
    def fromEncryptedFile(cls, password, file_dir=config.DATA_DIR, file_name=config.DEFAULT_WALLET_FILE): 
        try:
            with open(os.path.join(file_dir, file_name), 'rb') as rfile: 
                data = rfile.read() #read with os?
            wallet = json.loads(decrypt(password, data).decode('utf-8'))
        except: return False
        return cls.from_hwif((wallet.get('privkey') or wallet.get('pubkey')), keypath=wallet.get('keypath'))
        
    @classmethod
    def from_hwif(cls, b58_str, keypath=None): 
         node = BIP32Node.from_hwif(b58_str)
         return cls.fromBIP32Node(node, keypath)
         
    #Go figure why BIP32Node won't instantiate from an instance of itself...
    @classmethod
    def fromBIP32Node(cls, W, keypath=None):
        secret_exponent = (W._secret_exponent or None)
        public_pair = (W._public_pair if not W._secret_exponent else None)
        netcode = NETCODES.get(("mainnet" if not config.TESTNET else "testnet"))
        return PyPayWallet((netcode or W._netcode), W._chain_code, W._depth, W._parent_fingerprint, W._child_index, secret_exponent=secret_exponent, public_pair=public_pair, keypath= (keypath or W.__dict__.get('keypath')))

    def __init__(self, *args, keypath=None, testnet=config.TESTNET,**kwargs): 
        if not keypath:
            keypath = config.KEYPATH or config.DEFAULT_KEYPATH
        self.keypath = KeyPath(keypath)
        BIP32Node.__init__(self, *args, **kwargs)
        
    #return the public address for the current path
    def getCurrentAddress(self): 
        return self.subkey_for_path(str(self.keypath)).address()
    #return public address after incrementing path by 1
    def getNewAddress(self):
        self.keypath.incr() 
        return self.getCurrentAddress() 

class KeyPath(list): 
    """An address keypath object with an increment function"""
    def __init__(self, l, *args):
        if type(l) is str: l = l.split('/')
        elif not l: l =[]
        list.__init__(self, l,*args)
    #keeping __repr__ as a list for now
    def __str__(self): 
        return str('/'.join([str(i) for i in self]))
    def incr(self, x=1, pos=-1):
        self[pos] = ''.join([l for l in str(self[pos]) if l.isdigit()])
        self[pos] = int(self[pos]) + x if int(self[pos]) >= 0 else int(self[pos]) - x
    
#test
if __name__ == '__main__': 
    def dmc(x, y): 
        x.__dict__[y.__name__] = y.__get__(x, x.__class__)

    W = PyPayWallet.fromEncryptedFile("foobar")
    s = KeyPath('0H/22/3902HASDAS2')
    

