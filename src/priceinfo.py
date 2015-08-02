from . import config
import requests
import time
import calendar
import decimal
import addict
D= decimal.Decimal

class PriceInfoError(Exception):
    pass

def bitstampTicker(currency='USD'):
    if currency != 'USD':
        raise PriceInfoError("Bitstamp Ticker does not currently support currencies other than USD")
    data = requests.get('https://www.bitstamp.net/api/ticker/').json()
    dataPrice = data['last']
    dataTime = data['timestamp']
    return dataPrice, float(dataTime)

def coindeskTicker(currency='USD'):
    data = requests.get('https://api.coindesk.com/v1/bpi/currentprice.json').json()
    dataPrice= data['bpi'][currency]['rate']
    dataTime = calendar.timegm(time.strptime(data['time']['updated'], "%b %d, %Y %H:%M:%S %Z"))
    return dataPrice, dataTime

def bitcoinaverageglobalaverageTicker(currency='USD'):
    data = request.get('https://api.bitcoinaverage.com/ticker/global/all').json()
    dataPrice = [currency]['rate']
    dataTime = calendar.timegm(time.strptime(data[currency]['timestamp'], "%a, %d %b %Y %H:%M:%S %z"))
    return dataPrice, dataTime

class Ticker(object):
    def __init__(self, default_ticker=None, default_currency=None):
        self.tickers = {'bitstamp': bitstampTicker, 'coindesk': coindeskTicker, 'btcavga': bitcoinaverageglobalaverageTicker, 'dummy': ( lambda x: (350, time.time()) ) }
        if not default_ticker:
            self.default_ticker = config.DEFAULT_TICKER
        if not default_currency:
            self.default_currency = config.DEFAULT_CURRENCY
        self.last_price = addict.Dict()
    def getPrice(self, ticker=None, currency=None):
        if not ticker:
            ticker=self.default_ticker
        if not currency:
            currency = self.default_currency
        #Use stored value if fetched within last 60 seconds
        if self.last_price[ticker][currency]:
            if self.last_price[ticker][currency][1] > time.time() - 60:
                return self.last_price[ticker][currency][0]
        btc_price, last_updated = self.tickers[ticker](currency.upper())
        if not btc_price or (time.time() - last_updated) > 300:
            raise PriceInfoError("Ticker failed to return btc price or returned out dated info")
        self.last_price[ticker][currency] = btc_price, last_updated
        return btc_price

    #For now rounding is three-points, last four are used as significant for payment records and last 1 is ignored
    def getPriceInBTC(self, amount, currency=None, ticker= None):
        btc_price = D(str(self.getPrice(currency=currency, ticker=ticker)))
        amount= D(str(amount))
        amount_in_btc = (amount/btc_price).quantize(D('.000'))
        return amount_in_btc

ticker = Ticker()
