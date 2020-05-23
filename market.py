import os
import websocket
import threading

spot_markets = ['upbit']
future_markets = ['bitmex', 'binance']

def initialize_market(spot_market, spot_api_key, future_market, future_api_key):
    if spot_market == 'upbit':
        spot_api = UpbitSpotMarket(market, spot_api_key)
    if future_market == 'bitmex':
        future_api = BitmexFutureMarket(market, future_api_key)
    elif future_market == 'binance':
        future_api = BinanceFutureMarket(market, future_api_key)

    return spot_api, future_api

class SpotMarket:
    def limit_order(self, side, price, size):
    def market_order(self, side, size):
    def cancel_order(self, ordernum):

    def get_position(self):
    def get_orders(self):
    def get_rate_limit(self):

class FutureMarket:
    def __init__(self, market, leverage):

    def limit_order(self, side, price, size):
    def market_order(self, side, size):
    def cancel_order(self, ordernum):
    def liquidate_position(self):
    def get_position(self):
    def get_orders(self):
    def get_rate_limit(self):
    def get_liquidations(self):


class UpbitSpotMarket(SpotMarket):


class BitmexFutureMarket(FutureMarket):
    def __init__(self, market, api_key):
        ws = WebSocket(bitmex_websocket_make_endpoint, market, 'quote', 'liquidation')
        restapi =




class BinanceFutureMarket(FutureMarket):

class WebSocket (threading.Thread):
    def __init__(self, convert_to_endpoint_func, market, *streams):
        self._reset()
        endpoint = convert_to_endpoint_func(market, map(str, streams))
        threading.Thread.__init__(self)
        self._init_websocket(endpoint)

    def _init_websocket(self, endpoint):
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(endpoint,on_open = self._on_open,on_message = self._on_message,
                                         on_error = self._on_error,on_close = self._on_close)

    def _on_open(self, ws):
        pass

    def _on_message(self, ws, message):
        message = json.loads(message)
        self.data.append(message)

    def _on_error(self, ws, error):
        print(error)
        self._on_close(ws)

    def _on_close(self, ws):
        self.ws.close()

    def _reset(self):
        self.data = []

    def _check_data(self):
        return True if self.data else False

    def run(self):
        self.ws.run_forever()

    def get_data(self):
        if self._check_data():
            data = self.data
            self._reset()
            return data

def bitmex_websocket_make_endpoint(symbol, streams):
    if symbol == 'BTC':
        symbol = 'XBT'
    market = symbol + 'USD'
    stream_string = ','.join(map(lambda x:x+market, streams))
    endpoint = 'wss://www.bitmex.com/realtime?subscribe='+ stream_string
    return endpoint

def binance_websocket_make_endpoint(symbol, streams):
    symbol = symbol.lower()
    market = symbol + 'usdt'
    if len(streams) == 1:
        endpoint = 'wss://fstream.binance.com/ws/'+market+'@'+streams
    else:
        stream_string = '/'.join(map(lambda x:market+'@'+x, streams))
        endpoint = 'wss://fstream.binance.com/'+ stream_string
    return endpoint

def upbit_websocket_make_endpoint(symbol, streams):
    return endpoint
