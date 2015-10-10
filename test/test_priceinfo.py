import time
import unittest
import decimal
from pypayd import priceinfo

class PriceInfoTests(unittest.TestCase):

    def testDummyTicker(self):
        self.assertEqual(priceinfo.ticker.getPrice(ticker="dummy"), 350)
        self.assertEqual(priceinfo.ticker.getPriceInBTC(ticker="dummy", amount=175.0), 0.5)

    def testBitstampTicker(self):
        btc_price, last_updated = priceinfo.bitstampTicker()
        self.assertTrue((time.time() - float(last_updated) < priceinfo.MAX_TICKER_INTERVAL))
        self.assertTrue(float(btc_price) > 0)

    def testCoindeskTicker(self):
        btc_price, last_updated = priceinfo.coindeskTicker()
        self.assertTrue((time.time() - float(last_updated) < priceinfo.MAX_TICKER_INTERVAL))
        self.assertTrue(float(btc_price) > 0)

    def testBitcoinaverageglobalaverageTicker(self):
        btc_price, last_updated = priceinfo.bitcoinaverageglobalaverageTicker()
        self.assertTrue((time.time() - float(last_updated) < priceinfo.MAX_TICKER_INTERVAL))
        self.assertTrue(float(btc_price) > 0)

    def testTicker(self):
        ticker = priceinfo.Ticker(default_currency='EUR', default_ticker='coindesk')
        price = ticker.getPriceInBTC(amount=100)
        # ticker returns a Decimal
        self.assertTrue(isinstance(price, decimal.Decimal))
        # ticker retruns a Decimal quantized to SIGNIFICANT_DIGITS
        self.assertTrue(len(str(price).split('.')[1]) == abs(priceinfo.SIGNIFICANT_DIGITS.adjusted()))

if __name__ == '__main__':
    unittest.main()
