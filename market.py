import os
import websockets
import threading
import asyncio
import json
import requests
import time
from binance.client import Client as binance_client
from upbitpy import Upbitpy as upbit_client

spot_markets = ['upbit']
future_markets = ['bitmex', 'binance']

def initialize_market(symbol, spot_market, spot_api_key, future_market, future_api_key):
    if spot_market == 'upbit':
        spot_api = UpbitSpotMarket(symbol, spot_api_key)
    if future_market == 'bitmex':
        future_api = BitmexFutureMarket(symbol, future_api_key)
    elif future_market == 'binance':
        future_api = BinanceFutureMarket(symbol, future_api_key)
    return spot_api, future_api

def run_time(original_fn):
    def wrapper_fn(*args, **kwargs):
        start_time = time.time()
        result = original_fn(*args, **kwargs)
        end_time = time.time()
        print("WorkingTime[{}]: {} sec".format(original_fn.__name__, end_time-start_time))
        return result
    return wrapper_fn

class WebsocketThread (threading.Thread):
    def __init__(self,uri,sending_data=None,data_processing_func=None):
        threading.Thread.__init__(self)
        threading.Thread.daemon = True
        self.uri = uri
        self.sending_data = sending_data
        self.processer = data_processing_func
        self.reset_cycle = float('inf')
        self.received_data = []

    async def _connect(self,ontime):
        async with websockets.connect(self.uri) as websocket:
            starttime = time.time()
            if self.sending_data:
                await websocket.send(json.dumps(self.sending_data))
            while True:
                if time.time() - starttime > ontime:
                    break
                try:
                    received_data = await websocket.recv()
                except websockets.exceptions.ConnectionClosed:
                    break
                if self.processer:
                    received_data = self.processer(received_data)
                self.received_data.append(received_data)

    def set_reset_cycle(self,cycle):
        self.reset_cycle = cycle

    async def main(self):
        while True:
            await self._connect(self.reset_cycle)

    def run(self):
        asyncio.run(self.main())

    def get_data(self,only_latest=False):
        if only_latest:
            if self.received_data:
                data = self.received_data.pop()
            else:
                data = None
        else:
            data = self.received_data
        self.received_data.clear()
        return data

class UpbitSpotMarket:
    def __init__(self,symbol,api_key):
        self.fee = (0.05, 0.05)
        self.tick = 1000
        self.client = upbit_client(api_key[0], api_key[1])
        self.symbol = symbol
        self.market = 'KRW-'+symbol
        self.basefund = 0
        self.targetfund = 0
        self.orderbook = []
        self._orderbook_socket()

    def reset_market(self):
        self.cancel_every_orders()
        self.update_fund()

    def _orderbook_socket(self):
        uri = 'wss://api.upbit.com/websocket/v1'
        data = [{"ticket":"UNIQUE_TICKET"},{"type":"orderbook","codes":["KRW-BTC.10"]}]
        self.socket = WebsocketThread(uri,data)
        self.socket.set_reset_cycle(60)
        self.socket.start()

    def get_orderbook(self):
        bunch_data = self.socket.get_data(True)
        if bunch_data != None:
            orderbook = json.loads(bunch_data)['orderbook_units']
            self.orderbook = orderbook
        return self.orderbook

    def update_fund(self):
        accounts = self.client.get_accounts()
        for account in accounts:
            if account['currency'] == 'KRW':
                self.basefund = float(account['balance'])
            elif account['currency'] == self.symbol:
                self.targetfund = float(account['balance'])

    def get_open_orders(self):
        return self.client.get_orders(self.market, 'wait')

    #side = bid, ask
    def is_order_best(self, side, price):
        orderbook = self.get_orderbook()
        if side == 'BUY':
            best_price = orderbook[0]['bid_price']
            if price > best_price:
                return True
            else:
                return False
        else:
            best_price = orderbook[0]['ask_price']
            if price < best_price:
                return True
            else:
                return False

    def limit_order(self, side, price, size):
        if price*size > 1000:
            size = round(size, 6) - 0.000001
            return self.client.order(self.market, side, size, price)

    def cancel_order(self, order_UUID):
        return self.client.cancel_order(order_UUID)

    def cancel_if_retarded(self, order):
        if not self.is_order_best(order['side'], float(order['price'])):
            self.cancel_order(order['uuid'])

    def cancel_side_orders(self, side):
        # side 쪽은 모두 취소, 반대 side는 retarded만 취소
        orders = self.get_open_orders()
        if orders:
            for order in orders:
                if order['side'] == side:
                    self.cancel_order(order['uuid'])
                else:
                    self.cancel_if_retarded(order)
            self.update_fund()


    def cancel_every_orders(self):
        orders = self.get_open_orders()
        if orders:
            results = []
            for order in orders:
                result = self.cancel_order(order['uuid'])
                results.append(result)
            self.update_fund()
            return results

    def get_remaining_req(self):
        req = self.client.get_remaining_req()
        return int(req['market']['min'])

#class BitmexFutureMarket(FutureMarket):
#    def __init__(self, market, api_key):
#        restapi =

class BinanceTicker:
    def __init__(self, symbol):
        self.client = binance_client()
        self.market = symbol+'USDT'

    def get_best_ask(self):
        ticker = self.client.futures_orderbook_ticker(symbol=self.market)
        best_ask = float(ticker['askPrice'])
        return best_ask

class BinanceLiquidationSocket:
    def __init__(self):
        uri = "wss://fstream.binance.com/ws/btcusdt@forceOrder"
        self.socket = WebsocketThread(uri)

    def connect(self):
        self.socket.set_reset_cycle(60)
        self.socket.start()

    def get_data(self):
        trades = self.socket.get_data()
        size = 0
        if trades != None:
            for trade in trades:
                if trade['o']['S'] == 'BUY':
                    size += float(trade['o']['q'])
                else:
                    size -= float(trade['o']['q'])
        return size

class BinanceUserDataStream:
    def __init__(self, client):
        self.client = client
        self.balances = []
        self.positions = []
        self.ws = websocket.WebSocket()
        self.start_stream()
        t = threading.Thread(target=self.on_event)
        t.start()

    def start_stream(self):
        self.base_time = time.time()
        listenKey = self.client._request_futures_api('post', 'listenKey', True, data={})
        self.ws.connect('wss://fstream.binance.com/ws/'+listenKey['listenKey'])

    def keepalive_stream(self):
        self.client._request_futures_api('put', 'listenKey', True, data={})

    def close_stream(self):
        self.client._request_futures_api('delete', 'listenKey', True, data={})

    def on_event(self):
        while True:
            current_time = time.time()
            if current_time - self.base_time > 3500:
                self.keepalive_stream()
                self.base_time = current_time

            message = json.loads(self.ws.recv())
            if message['e'] == 'ACCOUNT_UPDATE':
                self.balances = message['a']['B']
                self.positions = message['a']['P']

    def __del__(self):
        self.close_stream()


class BinanceFutureMarket:
    def __init__(self, symbol, api_key):
        self.fee = (0.02, 0.04)
        self.tick = 0.01
        self.precision = 3
        self.client = binance_client(api_key[0], api_key[1])
        self.symbol = symbol
        self.market = symbol+'USDT'
        self.fund = 0
        self.position = 0
        self.user_stream = BinanceUserDataStream(self.client)
        self.ticker = {}
        self.liquids = []
        self._sockets()


    def _sockets(self):
        self.tickerws = websocket.WebSocket()
        self.liquidws = websocket.WebSocket()
        t = threading.Thread(target=self._start_sockets)
        t.daemon = True
        t.start()
        threading.Timer(120, self._sockets).start()

    def _start_sockets(self):
        self.tickerws.connect("wss://fstream.binance.com/ws/btcusdt@bookTicker")
        self.liquidws.connect("wss://fstream.binance.com/ws/btcusdt@forceOrder")
        while True:
            ticker = self.tickerws.recv()
            self.ticker = json.loads(ticker)
            liquid = self.liquidws.recv()
            self.liquids.append(json.loads(liquid))

    def correct_decimal(self, num):
        rounded = round(num, self.precision)
        if rounded > num:
            return rounded - (1/10**self.precision)
        else:
            return rounded

    def reset_market(self):
        self.cancel_all_orders()
        self.update_fund()

    def update_fund(self):
        balances = self.user_stream.balances
        for balance in balances:
            if balance['a'] == 'USDT':
                self.fund = float(balance['cw'])

        positions = self.user_stream.positions
        for position in positions:
            if position['s'] == self.market:
                self.position = float(position['pa'])

    def change_leverage(self, leverage):
        return self.client.futures_change_leverage(symbol=self.market, leverage=leverage)

    #[{'symbol': 'BTCUSDT', 'positionAmt': '0.016', 'entryPrice': '8938.00000', 'markPrice': '8940.56275786', 'unRealizedProfit': '0.04100413', 'liquidationPrice': '7158.33', 'leverage': '20', 'maxNotionalValue': '5000000', 'marginType': 'cross', 'isolatedMargin': '0.00000000', 'isAutoAddMargin': 'false', 'positionSide': 'BOTH'}]
    def get_position(self):
        return self.client.futures_position_information()

    #{'u': 33393280994, 's': 'BTCUSDT', 'b': '8826.38', 'B': '0.262', 'a': '8826.40', 'A': '0.504', 'T': 1590397546495, 'E': 1590397546499}
    def get_ticker(self):
        return self.ticker


    # {"e":"forceOrder","E":1590400691564,
    # "o":{"s":"BTCUSDT","S":"BUY","o":"LIMIT","f":"IOC","q":"0.197","p":"8794.59","ap":"8755.50","X":"FILLED","l":"0.197","z":"0.197","T":1590400691561}}'
    def get_liquidations(self):
        trades = self.liquids
        size = 0
        if trades:
            for trade in trades:
                if trade['o']['S'] == 'BUY':
                    size += float(trade['o']['q'])
                else:
                    size -= float(trade['o']['q'])
        self.liquids.clear()
        return size

    def get_open_orders(self):
        return self.client.futures_get_open_orders(symbol=self.market)

    #{'orderId': 4398189118, 'symbol': 'BTCUSDT', 'status': 'NEW', 'clientOrderId': 't6pVZoXVFRQ2Wp4G755pJG', 'price': '8800', 'avgPrice': '0.00000', 'origQty': '0.001', 'executedQty': '0', 'cumQty': '0', 'cumQuote': '0', 'timeInForce': 'GTC', 'type': 'LIMIT', 'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'origType': 'LIMIT', 'updateTime': 1590478180027}
    def limit_order(self, side, price, size, reduceOnly=False):
        size = self.correct_decimal(size)
        result = self.client.futures_create_order(symbol=self.market, side=side, type='LIMIT', timeInForce='GTC', quantity=size, price=price, reduceOnly=reduceOnly)
        return result

    def market_order(self, side, size, reduceOnly=False):
        size = self.correct_decimal(size)
        result = self.client.futures_create_order(symbol=self.market, side=side, type='MARKET', quantity=size, reduceOnly=reduceOnly)
        return result

    def immediate_liquidate_position(self):
        positions = self.get_position()
        for position in positions:
            if position['symbol'] == self.market:
                amount = float(position['positionAmt'])
                if amount >= 0:
                    self.market_order('SELL', amount)
                else:
                    self.market_order('BUY', abs(amount))
        self.update_fund()

    def cancel_if_retarded(self, order):
        price = float(order['price'])
        if order['side'] == 'BUY':
            if price <= float(self.ticker['b']):
                return self.cancel_order(order['orderId'])
            else:
                return []
        else:
            if price >= float(self.ticker['a']):
                return self.cancel_order(order['orderId'])
            else:
                return []

    def cancel_side_orders(self, side):
        orders = self.get_open_orders()
        if orders:
            for order in orders:
                if order['side'] == side:
                    self.cancel_order(order['orderId'])
                else:
                    self.cancel_if_retarded(order)
            self.update_fund()

    def cancel_order(self, order_id):
        return self.client.futures_cancel_order(symbol=self.market, orderId=order_id)

    def cancel_all_orders(self):
        return self.client.futures_cancel_all_open_orders(symbol=self.market)

'''
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
'''
