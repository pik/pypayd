from pycoin.key.BIP32Node import *
from . import config
from .interfaces.counterwalletseed import mnemonicToEntropy
import time
import json
import os
from .errors import PyPayWalletError

NETCODES = {"mainnet": "BTC", "testnet": "XTN"}
#To Do: enable autosweep, privkey_mode only
#sweep address function
#sweep branch function

class PyPayWallet(BIP32Node):
    """
    Wallet wrapper around the Pycoin implementation. (Pycoin is a little heavier of a dependency than we need, but it already supports python3 and keypath-address handling).
    The savePrivate() and savePublic() methods will save the public and/or private keys available to this wallet in an encrypted file using simplecrypt. Note: You do not need to have the privatekeys to generate new addresses.
    The MasterKey or the PublicKey for the branch specified in the configfile must be loaded at startup, branches take default numbers. Currently hardened branch's are not supported (since hardened branches require the root-key to be a private-key which should not be used).
    """

    @classmethod
    def _getNetcode(cls):
        return NETCODES['testnet' if config.TESTNET else 'mainnet']

    @classmethod
    def fromEntropy(cls, seed, netcode=None):
        if not netcode:
            netcode = cls._getNetcode()
        return BIP32Node.from_master_secret(seed, netcode)

    @classmethod
    def fromMnemonic(cls, mnemonic, mnemonic_type = None, netcode=None):
        if not netcode:
            netcode = cls._getNetcode()
        if not mnemonic_type:
            mnemonic_type = config.DEFAULT_MNEMONIC_TYPE
        exec("from .interfaces.%s import mnemonicToEntropy" %mnemonic_type)
        seed = mnemonicToEntropy(mnemonic)
        return cls.from_master_secret(seed, netcode=netcode)

    @classmethod
    def fromFile(cls, password=None, file_dir=None, file_name=None, netcode=None):
        if file_dir is None:
            file_dir = config.DATA_DIR
        if file_name is None:
            file_name = config.DEFAULT_WALLET_FILE
        if netcode is None:
            netcode = cls._getNetcode()
        with open(os.path.join(file_dir, file_name), 'rb') as rfile:
            data = rfile.read()
        if password:
            data = cls._decryptFile(password, data)
        wallet = json.loads(data)
        return cls.fromHwif((wallet.get('privkey') or wallet.get('pubkey')), keypath=wallet.get('keypath'), netcode=netcode)

    fromEncryptedFile = fromFile

    @classmethod
    def _decryptFile(cls, password, data):
        import simplecrypt
        return simplecrypt.decrypt(password, data).decode('utf-8')

    @classmethod
    def fromHwif(cls, b58_str, keypath=None, netcode = None):
         node = BIP32Node.from_hwif(b58_str)
         return cls.fromBIP32Node(node, keypath, netcode)

    #Go figure why BIP32Node won't instantiate from an instance of itself...
    @classmethod
    def fromBIP32Node(cls, W, keypath=None, netcode = None):
        secret_exponent = (W._secret_exponent or None)
        public_pair = (W._public_pair if not W._secret_exponent else None)
        if not netcode:
            netcode = cls._getNetcode() or W._netcode
        return PyPayWallet(
        netcode,
        W._chain_code,
        W._depth,
        W._parent_fingerprint,
        W._child_index,
        secret_exponent=secret_exponent,
        public_pair=public_pair,
        keypath= (keypath or W.__dict__.get('keypath'))
        )

    def _toFile(self, data, file_dir = None, file_name =None, force = False ):
        if file_dir is None:
            file_dir = config.DATA_DIR
        if file_name is None:
            file_name = config.DEFAULT_WALLET_FILE
        print(file_dir, file_name)
        target = os.path.join(file_dir, file_name)
        if os.path.isfile(target) and not force:
            raise PyPayWalletError("Could not save to file because file already exists and force=True was not specified")
        with open(target, 'wb') as wfile:
            result = wfile.write(data)
            assert(len(data) == result)
        return result

    def jsonForWallet(self, store_private=False):
        return json.dumps({
        "keypath": self.keypath,
        "pubkey": self.hwif(),
        "privkey": (self.hwif(True) if (self.is_private() and store_private ) else None)
        }).encode('utf-8')

    def toFile(self, password=None, store_private=False, **kwargs):
        payload = self.jsonForWallet(store_private)
        if password:
            import simplecrypt
            payload = simplecrypt.encrypt(password, payload)
        self._toFile(payload, **kwargs)

    def toEncryptedFile(self, password=None, store_private=False, **kwargs):
        self.toFile(password, store_private, **kwargs)

    def getCurrentAddress(self):
        '''return the public address for the current path'''
        return self.subkey_for_path(str(self.keypath)).address()

    def getNewAddress(self):
        '''return public address after incrementing path by 1'''
        self.keypath.incr()
        return self.getCurrentAddress()

    def __init__(self, *args, keypath=None, **kwargs):
        if not keypath:
            keypath = config.KEYPATH or config.DEFAULT_KEYPATH
        self.keypath = KeyPath(keypath)
        BIP32Node.__init__(self, *args, **kwargs)

class KeyPath(list):
    """An address keypath object with an increment function"""
    def __init__(self, l, *args):
        if type(l) is str:
            l = (int(i) for i in l.split('/'))
        elif not l:
            l =[]
        list.__init__(self, l,*args)

    def __repr__(self):
        return "KeyPath('%s')" %self

    def __str__(self):
        return str('/'.join([str(i) for i in self]))

    def incr(self, x=1, pos=-1):
        '''When called with no arguments increments the right-most path by one'''
        self[pos] += (x if self[pos] >= 0 else -x)

    def set_pos(self, x, pos):
        self[pos] = int(x)


if __name__ == '__main__':
    def dmc(x, y):
        x.__dict__[y.__name__] = y.__get__(x, x.__class__)
    W = PyPayWallet.fromEncryptedFile(password="foobar")


