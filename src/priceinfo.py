from . import config
import requests
import time
import decimal
D= decimal.Decimal

def bitstampTicker():
    data = requests.get('https://www.bitstamp.net/api/ticker/').json()
    dataPrice = data['last']
    dataTime = data['timestamp']
    return dataPrice, dataTime
def coindeskTicker():
    data = requests.get('https://api.coindesk.com/v1/bpi/currentprice.json').json()
    dataPrice= data['bpi']['USD']['rate']
    dataTime = data['time']['updated']
    return dataPrice, dataTime
    
class tickerObj(object): 
    def __init__(self): 
        self.__dict__ = {'bitstamp': {'USD': bitstampTicker}, 'coindesk': {'USD': coindeskTicker} }
        self.default_ticker = config.DEFAULT_TICKER
        self.default_currency = config.DEFAULT_CURRENCY
    def getPrice(self, ticker=None, currency=None):
        if not ticker: ticker=self.default_ticker
        if not currency: currency = self.default_currency
        else: currency = curreny.upper()
        try: 
            price, last_updated = config.STATE[ticker][currency][price] 
            if not price or (time.time() - last_updated) > 60: raise 
        except: 
            price = self.__dict__[ticker][currency]()[0]
            config.STATE.update({ticker: {currency: {"price": (price, time.time()) }}})
        return price
    def getPrice(self):
        return 350.0
        
ticker = tickerObj() 
def getPriceInBTC(amount, currency=None, config_ticker= None):
    btc_price = D(str(ticker.getPrice()))
    amount= D(str(amount))
    amount_in_btc = (amount/btc_price).quantize(D('.000'))
    return amount_in_btc
    
    
    
