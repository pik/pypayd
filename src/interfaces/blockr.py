"""
blockr.io
"""
import logging
import requests
from .. import config
from binascii import hexlify, unhexlify
import hashlib
from hashlib import sha256

def getUrl(request_string):
    return requests.get(request_string).json()
    
def setHost():
    config.BLOCKCHAIN_CONNECT = ('http://tbtc.blockr.io' if config.TESTNET else 'http://btc.blockr.io')

#And fix this
def check():
    return getInfo() 
    
def getInfo():
    result = getUrl(config.BLOCKCHAIN_CONNECT + '/api/v1/coin/info', )
    if 'status' in result and result['status'] == 'success':
        return {
            "info": {
                "blocks": result['data']['last_block']['nb']
            }
        }
    return result

def getUtxo(address):
    result = getUrl(config.BLOCKCHAIN_CONNECT + '/api/v1/address/unspent/{}/'.format(address))
    if 'status' in result and result['status'] == 'success':
        utxo = []
        for txo in result['data']['unspent']:
            newtxo = {
                'address': address,
                'txid': txo['tx'],
                'vout': txo['n'],
                'ts': 0,
                'scriptPubKey': txo['script'],
                'amount': float(txo['amount']),
                'confirmations': txo['confirmations'],
                'confirmationsFromCache': False
            }
            utxo.append(newtxo)
        return utxo
    return None

def getAddressInfo(address):
    infos = getUrl(config.BLOCKCHAIN_CONNECT + '/api/v1/address/info/{}'.format(address), )
    if 'status' in infos and infos['status'] == 'success':
        txs = getUrl(config.BLOCKCHAIN_CONNECT + '/api/v1/address/txs/{}'.format(address), )
        if 'status' in txs and txs['status'] == 'success':
            transactions = []
            for tx in txs['data']['txs']:
                transactions.append(tx['tx'])
            return {
                'addrStr': address,
                'balance': infos['data']['balance'],
                'balanceSat': infos['data']['balance'] * config.UNIT,
                'totalReceived': infos['data']['totalreceived'],
                'totalReceivedSat': infos['data']['totalreceived'] * config.UNIT,
                'unconfirmedBalance': 0,
                'unconfirmedBalanceSat': 0,
                'unconfirmedTxApperances': 0,
                'txApperances': txs['data']['nb_txs'],
                'transactions': transactions
            }
    return None

def getTxInfo(tx_hash):
    tx = getUrl(config.BLOCKCHAIN_CONNECT + '/api/v1/tx/raw/{}'.format(tx_hash))
    if tx.get('status') == 'success':
        valueOut = 0
        for vout in tx['data']['tx']['vout']:
            valueOut += vout['value']
        return {
            'txid': tx_hash,
            'version': tx['data']['tx']['version'],
            'locktime': tx['data']['tx']['locktime'],
            'blockhash': tx['data']['tx'].get('blockhash', None), 
            'confirmations': tx['data']['tx'].get('confirmations', None),
            'time': tx['data']['tx'].get('time', None),
            'blocktime': tx['data']['tx'].get('blocktime', None),
            'valueOut': valueOut,
            'vin': tx['data']['tx']['vin'],
            'vout': tx['data']['tx']['vout']
        }
    return None

def sourceAddressesFromTX(self, tx_full): 
    '''Return source (outbound) addresses for a bitcoin tx'''
    return [addressForPubKey(i['scriptSig']['asm'].split(" ")[1]) for i in tx_full['vin']]
    
#This can be replaced with the pycoin function 
def addressForPubKey(pubkey_hex, testnet=None): 
    if testnet is None: 
        testnet = config.TESTNET
    ripehash = hashlib.new('ripemd160')
    step1 = unhexlify(pubkey_hex)
    step2 = sha256(step1).digest()
    ripehash.update(step2)
    if testnet:
        step4 = b'\x6F' + ripehash.digest()
    else:
        step4 = b'\x00' + ripehash.digest()
    step5 = sha256(step4).digest()
    step6 = sha256(step5).digest()
    chksum = step6[:4]
    address = step4 + chksum
    addr_58 = encodeBase58(address)
    return addr_58

def encodeBase58(v):
    long_value = int.from_bytes(v, 'big') 
    result = ''
    while long_value >= 58:
        div, mod = divmod(long_value, 58)
        result = _b58chars[mod] + result
        long_value = div
    result = _b58chars[long_value] + result
    nPad = 0
    for c in v:
        if c == ord(b'\0'): nPad += 1
        else: break
    return (_b58chars[0]*nPad) + result
