import requests
import json
import pprint
from upbitpy import Upbitpy
from binance.client import Client

binance = Client()
binance_candle = binance.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1MINUTE, "1 Jan, 2019", "31 Dec, 2019")

upbit = Upbitpy()
upbit_candle = upbit.get_minutes_candles(1, 'KRW-BTC')

pprint.pprint(binance_candle)
