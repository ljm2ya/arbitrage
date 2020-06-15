import datetime
import threading
import math
import time
from forex_python.converter import CurrencyRates
from market import UpbitSpotMarket,BinanceTicker,BinanceLiquidationSocket
from private import upbit_key

SPOT_ENTER_GAP = 0.3
SPOT_ESCAPE_GAP = 0
SPOT_ESCAPE_EXCCES_PROFIT = 0.2
SPOT_ESCAPE_FUTURE_LIQUID_INTENSITY = -0.1

class Trader:
    def __init__(self):
        self.spot_api = UpbitSpotMarket('BTC', upbit_key)
        self.future_api = BinanceTicker('BTC')
        self.future_liquidation_socket = BinanceLiquidationSocket()
        self.c = CurrencyRates()
        self.fee = self.spot_api.fee[0]*2

    def initialize(self, cycle, spread_len, liquidation_len):
        print("Starting futures tracking arbitrage bot..")
        self.spot_api.reset_market()
        self.future_liquidation_socket.connect()
        self.start_time = time.time()
        print("Spot Fund:", self.spot_api.basefund, "원")
        self.dollor_rate = self.c.get_rates('USD')['KRW']
        self.data = {'spread':[], 'liquidations':[]}
        self.cycle = cycle
        self.spread_list_size = spread_len / self.cycle
        self.liquidation_list_size = liquidation_len / self.cycle

    def _new_data(self, spread, liquidations):
        self.data['spread'].append(spread)
        self.data['liquidations'].append(liquidations)
        #if len(self.data['spread']) >= self.spread_list_size and len(self.data['liquidations']) >= self.liquidation_list_size:
        if len(self.data['liquidations']) >= self.liquidation_list_size:
            if len(self.data['spread']) >= self.spread_list_size:
                self.data['spread'].pop(0)
            self.data['liquidations'].pop(0)
            return True
        else:
            return False

    def trading(self):
        currenttime = time.time()
        spot_book = self.spot_api.get_orderbook()
        future_best_ask = self.future_api.get_best_ask()

        def get_spread(spot_book, order):
            spot_price = spot_book[order]['ask_price']
            return (future_best_ask - (spot_price / self.dollor_rate)) / (spot_price / self.dollor_rate) * 100

        spread_best = get_spread(spot_book, 0)
        liquidation_size = self.future_liquidation_socket.get_data()

        if self._new_data(spread_best, liquidation_size):
            spread_avg = sum(self.data['spread']) / len(self.data['spread'])
            liquidation_per_second = sum(self.data['liquidations']) / (self.liquidation_list_size * self.cycle)

            price = 0
            for i in range(10):
                spread_best = get_spread(spot_book, i)
                if self.spot_enter(spread_best, spread_avg):
                    price = spot_book[i]['ask_price']
                else:
                    break
            if price != 0:
                self.spot_api.cancel_side_orders('ask')
                available = self.spot_api.basefund / price * 0.999
                print('Spot enter: ', available, 'BTC')
                print('Spot Premium average:', -spread_avg)
                print('Current Premium:', -spread_best)
                print('Liquidations:', liquidation_per_second)
                result = self.spot_api.limit_order('bid', price, available)
                self.spot_api.update_fund()
                enter_price = price

            try:
                current_profit = (spot_book[0]['bid_price'] - enter_price) / enter_price * 100 - fee
            except:
                current_profit = 0

            if self.spot_escape(spread_best, spread_avg, current_profit, liquidation_per_second):
                self.spot_api.cancel_side_orders('bid')
                if self.spot_api.targetfund > 0.001:
                    print('Spot Escape')
                    print('Profit:', current_profit)
                    spot_book = self.spot_api.get_orderbook()
                    self.spot_api.limit_order('ask', spot_book[0]['ask_price']-self.spot_api.tick, self.spot_api.targetfund*0.999)
                    self.spot_api.update_fund()

        endtime = time.time()
        elapsetime = endtime - currenttime
        if elapsetime < self.cycle:
            time.sleep(self.cycle-elapsetime)

    def start_trading(self):
        while True:
            self.trading()

    def spot_enter(self, spread, spread_average):
        if spread - spread_average >= SPOT_ENTER_GAP:
            return True
        else:
            return False

    def spot_escape(self, spread, spread_average, current_profit, liquid_intensity):
        if spread - spread_average <= SPOT_ESCAPE_GAP:
            return True
        elif current_profit >= SPOT_ESCAPE_EXCCES_PROFIT:
            return True
        elif liquid_intensity <= SPOT_ESCAPE_FUTURE_LIQUID_INTENSITY:
            return True
        else:
            return False

def run_time(original_fn):
    def wrapper_fn(*args, **kwargs):
        start_time = time.time()
        result = original_fn(*args, **kwargs)
        end_time = time.time()
        print("WorkingTime[{}]: {} sec".format(original_fn.__name__, end_time-start_time))
        return result
    return wrapper_fn

if __name__ == "__main__":
    #startAlgo('BTC', 'upbit', upbit_key, 'binance', binance_key)
    trader = Trader()
    trader.initialize(0.5, 600, 10)
    trader.start_trading()
