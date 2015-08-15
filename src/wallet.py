from pycoin.key.BIP32Node import *
from . import config
from .interfaces.counterwalletseed import mnemonicToEntropy
import time
import json
import os

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
    def _get_netcode(cls):
        return NETCODES['testnet' if config.TESTNET else 'mainnet']

    @classmethod
    def from_entropy(cls, seed, netcode=None):
        if not netcode:
            netcode = cls._get_netcode()
        return BIP32Node.from_master_secret(seed, netcode)

    @classmethod
    def from_mnemonic(cls, mnemonic, mnemonic_type = None, netcode=None):
        if not netcode:
            netcode = cls._get_netcode()
        if not mnemonic_type:
            mnemonic_type = config.DEFAULT_MNEMONIC_TYPE
        exec("from .interfaces.%s import mnemonicToEntropy" %mnemonic_type)
        seed = mnemonicToEntropy(mnemonic)
        return BIP32Node.from_master_secret(seed, netcode=netcode)

    @classmethod
    def from_file(cls, password=None, file_dir=None, file_name=None, netcode=None):
        if file_dir is None:
            file_dir = config.DATA_DIR
        if file_name is None:
            file_name = config.DEFAULT_WALLET_FILE
        if netcode is None:
            netcode = cls._get_netcode()
        with open(os.path.join(file_dir, file_name), 'rb') as rfile:
            data = rfile.read()
        if password:
            data = cls._decrypt_file(password, data)
        wallet = json.loads(data)
        return cls.from_hwif((wallet.get('privkey') or wallet.get('pubkey')), keypath=wallet.get('keypath'), netcode=netcode)

    @classmethod
    def _decrypt_file(cls, password, data):
        import simplecrypt
        return simplecrypt.decrypt(password, data).decode('utf-8')

    @classmethod
    def from_hwif(cls, b58_str, keypath=None, netcode = None):
         node = BIP32Node.from_hwif(b58_str)
         return cls.from_BIP32_node(node, keypath, netcode)

    #Go figure why BIP32Node won't instantiate from an instance of itself...
    @classmethod
    def from_BIP32_node(cls, W, keypath=None, netcode = None):
        secret_exponent = (W._secret_exponent or None)
        public_pair = (W._public_pair if not W._secret_exponent else None)
        if not netcode:
            netcode = cls._get_netcode() or W._netcode
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

    def _to_file(self, data, file_dir = None, file_name =None, force = False ):
        if file_dir is None:
            file_dir = config.DATA_DIR
        if file_name is None:
            file_name = config.DEFAULT_WALLET_FILE
        target = os.path.join(file_dir, file_name)
        if os.path.isfile(target) and not force:
            raise PyPayWalletError("Could not save to file because file already exists and force=True was not specified")
        with open(target, 'wb') as wfile:
            result = wfile.write(data)
            assert(len(data) == result)
        return result

    def json_for_wallet(self, store_private=False):
        return json.dumps({
        "keypath": self.keypath,
        "pubkey": self.hwif(),
        "privkey": (self.hwif(True) if (self.is_private() and store_private ) else None)
        })

    def to_file(self, **kwargs):
        self._to_file(json_for_wallet(), args, kwargs)

    def to_encrypted_file(self, password, store_private=False, **kwargs):
        import simplecrypt
        data = simplecrypt.encrypt(password, json_for_wallet(store_private))
        self._to_file(data, kwargs)

    def get_current_address(self):
        '''return the public address for the current path'''
        return self.subkey_for_path(str(self.keypath)).address()

    def get_new_address(self):
        '''return public address after incrementing path by 1'''
        self.keypath.incr()
        return self.get_current_address()

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
    W = PyPayWallet.fromEncryptedFile("foobar")


