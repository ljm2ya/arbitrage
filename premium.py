import requests
import time
import json
import threading
import configparser
from upbitpy import Upbitpy
from binance.client import Client

class Arbitrader:
    def __init__(self):
        if self.__initial_load():
            #self.__check_fund()
            self.__start_monitor()

    def __initial_load(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.upbit_api = (config['UPBIT_API_KEY'], config['UPBIT_API_SECRET'])
        self.binance_api = (config['BINANCE_API_KEY'], config['BINANCE_API_SECRET'])
        self.hedge_lev = config['HEDGE_LEVERAGE']
        self.max_fund = config['MAX_FUND']

        try:
            self.upbit = Upbitpy(self.upbit_api[0], self.upbit_api[1])
            self.binance = Client(self.binance_api[0], self.binance_api[1])
        except Exception as ex:
            print("api connection error", ex)
            return 0
        else:
            return 1
            '''
            if self.__check_connection():
                return 1
            else:
                print("api is alright, but server connection error")
                return 0
            '''

   '''
    def __check_fund(self):
        upbitFund =
        if self.__hedging_fund_lack(self)
'''

    def __start_monitor(self):
        while True:
            time.sleep(5)
            if
    def __binance_transfer(self, origin, target, amount):

    def _make_transfer(self, toTether, propotion, crypto):



class Sender (threading.Thread):
    def __init__(self, toTether, propotion, crypto):
        if toTether:
            self.origin_market = 'upbit'
            self.target_market = 'binance'
        else:
            self.origin_market = 'binance'
            self.target_market = 'upbit'

        self.propotion = propotion
        self.pair_upbit = 'KRW-'+crypto
        self.pair_binance = crypto+'USDT'


    def __is_arrived(self):


    def run(self):
        self.__buy_coin()
        self.__send()
        while True:
            time.sleep(5)
            if self.__is_arrived():
                break




if __name__ == "__main__":
    print("Welcome to Crypto Arbitrader")
    bot = Arbitrader()
