"""
blockr.io
"""
import logging
import requests
from . import config, util, util_bitcoin

def getUrl(request_string):
    return requests.get(request_string).json()
    
def setHost():
    if config.BLOCKCHAIN_CONNECT: pass
    else: 
        config.BLOCKCHAIN_CONNECT = ('http://tbtc.blockr.io' if config.TESTNET else 'http://btc.blockr.io')
        
def check():
    pass

def getInfo():
    result = getUrl(config.BLOCKCHAIN_CONNECT + '/api/v1/coin/info', )
    if 'status' in result and result['status'] == 'success':
        return {
            "info": {
                "blocks": result['data']['last_block']['nb']
            }
        }
    return None

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
    if 'status' in tx and tx['status'] == 'success':
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


