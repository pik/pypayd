pypayd
===============

Pypayd is a small daemon (<1000 lines) for accepting bitcoin payments with light-weight dependencies. This is meant to be a good alternative if you do not want setup an account with a third-party payment processor.
Pypayd provides an API for creating orders and automatically records order fulfillment (payment received) as well as invalid payments.

Pypayd automatically creates receiving addresses from it's own wallet, a wrapper around the pycoin implementation of BIP32. The wallet (can generate addresses from a public or private master-key (note that there is no need to store the private key on the server). It also supports loading keys from mnemonic, byte-string, or encrypted file. 

installation
---------------------
For now the recomended installation method is to use ```git clone https://github.com/pik/pypayd.git``` following that ```cd``` into the pypayd directory and execute ```pip install -r pip-requirements.txt```, with this you should be good to go (one thing to note is that in some cases APSW may require manual installation).

example usage
-----------------
Obtain an encrypted-file with a publickey on an offline server from a mnemonic:

```python pypayd.py wallet --from-mnemonic "like just love know never want time out there make look eye" --mnemonic-type="electrum" --to-file="payment_wallet.txt" --encrypt-pw="foobar" ```

This will generate a BIP32 wallet from the mnemonic and save only the master public key to an encrypted file. CP the file to your online server. Then run pypayd:

```python pypayd.py --server wallet --from-file="payment_wallet.txt" --encrypt-pw="foobar" ```

Then from your webserver (i.e. to create an order for a payment of 20 usd): 
```
import requests
import json
url = "http://127.0.0.1:3080"
headers = {'content-type': 'application/json'}
payload = {
    "method": "create_order",
    "params": {"amount": 20.0, "qr_code": True},
    "jsonrpc": "2.0",
    "id": 0,
}
response = requests.post( url, data=json.dumps(payload), headers=headers).json()
```

This will return an automatically created order_id, a price converted to Bitcoin from the ``DEFAULT_CURRENCY`` by the ``DEFAULT_TICKER``, a receiving address, as well as a time left on the transaction (note that the timeleft on the transaction is the time-lapse after which a payment received for the order will not be considered valid; it may be preferable to set a longer ``TX_LIFE`` then the one displayed to the customer). The full argument list for ``create_order`` as follows: 

    * amount     
    * currency      takes a string such as 'USD', config.DEFAULT_CURRENCY if none
    * item_number       specify an item-number to associate  with the order in the database
    * order_id        specify an order-id, if one is not given an order-id will be created by hashing other order attributes
    * gen_new         generate a new address for the order if True, otherwise uses config settings
    * qr_code         generate a qr_code for the corresponding receiving address if True

dependencies
----------------------
See ```pip-requirements.txt```

to do
---------------------------
See the ```TODO``` list. 

interfaces 
---------------------------
Pypayd supports insight-api (run locally or hosted: https://insight.bitpay.com/) and blockr (https://blockr.io/). I'll probably add support for jmcorgan's fork of bitcoin-core with address indexing in the near future. To configure set ```BLOCKCHAIN_SERVICE``` to the interface Pypayd should load ("insight" or "blockr") and ```BLOCKCHAIN_CONNECT``` to the complete url in the ```pypayd.conf``` file. 
