from . import config
from errors import PriceInfoError
import time
import decimal
D= decimal.Decimal

class Ticker(object):
    def init_tickers(self):
        import ast
        import os
        tickers = os.listdir("tickers")
        for file_name in tickers:
            ticker_name = file_name.replace('.py', '')
            exec("from tickers import %s" %ticker_name)
            self.tickers[ticker_name] = ast.literal_eval("ticker_name.ticker")

    def __init__(self, default_ticker=None, default_currency=None, tickers={}):
        if not default_ticker:
            self.default_ticker = config.DEFAULT_TICKER
        if not default_currency:
            self.default_currency = config.DEFAULT_CURRENCY
        self.tickers = tickers
        if not self.tickers:
            init_tickers()
        self.recorded_prices = {}

    def get_price(self, ticker=None, currency=None):
        if not ticker:
            ticker=self.default_ticker
        if not currency:
            currency = self.default_currency
        #Use stored value if fetched within last 60 seconds
        last_price = self.recorded_prices.get(ticker, {}).get(currency, {})
        if last_price and last_price[1] > (time.time() - 60):
            return last_price[0]
        btc_price, last_updated = self.tickers[ticker](currency.upper())
        if not btc_price or (time.time() - last_updated) > config.MAX_PRICE_TIME_GAP:
            raise PriceInfoError("Ticker failed to return btc price or returned out dated info")
        if not self.recorded_prices.get(ticker):
            self.recorded_prices[ticker] = {}
        self.recorded_prices[ticker][currency] = btc_price, last_updated
        return btc_price

    #For now rounding is three-points, last four are used as significant for payment records and last 1 is ignored
    def get_price_in_btc(self, amount, currency=None, ticker= None):
        btc_price = D(str(self.get_price(currency=currency, ticker=ticker)))
        amount= D(str(amount))
        amount_in_btc = (amount/btc_price).quantize(D('.000'))
        return amount_in_btc

ticker = Ticker()
