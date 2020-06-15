import datetime
import threading
import math
import time
from forex_python.converter import CurrencyRates
from market import initialize_market

SPOT_ENTER_GAP = 0.2
SPOT_ESCAPE_GAP = -0.1
SPOT_ESCAPE_EXCCES_PROFIT = 0.3
SPOT_ESCAPE_FUTURE_LIQUID_INTENSITY = -0.1
FUTURE_ENTER_LIQUID_INTENSITY = 0.1
FUTURE_ESCAPE_LIQUID_INTENSITY = 1
FUTURE_ESCAPE_LIQUID_RISK = 0.5
FUTURE_IMMEDIATE_ESCAPE_LIQUID_RISK = 0.8
FUTURE_HOLD_REVERSE_LIQUID_INTENSITY = -0.1

c = CurrencyRates()

upbit_key = ('FkuPBspgFDkzTYx2cFy8uXU7xuJPvVoa0SCx9YRZ', 'HH4ThxiRxBHf1zKJxAwEgsydUx00hTmWUCVPPvn5')
binance_key = ('mAvvEtWAonCZegyPrXxU2CHxpkDCwZA9kRqzylRfOzDFp81G4wgjPk2kzcXB2tD3', '2WWqoTczKwuEfCiuXNO1HP4e476x0ivQm1FN0neD5YeX3zGD09i35L5Qpi7LcsjB')

def run_time(original_fn):
    def wrapper_fn(*args, **kwargs):
        start_time = time.time()
        result = original_fn(*args, **kwargs)
        end_time = time.time()
        print("WorkingTime[{}]: {} sec".format(original_fn.__name__, end_time-start_time))
        return result
    return wrapper_fn

def startAlgo(symbol, spot_market, spot_api_key, future_market, future_api_key):
    print("Starting Bot..", spot_market, "and", future_market)
    spot_api, future_api = initialize_market(symbol, spot_market, spot_api_key, future_market, future_api_key)
    # for initial update user data stream
    try:
        future_api.client.futures_change_margin_type(symbol='XMRUSDT', marginType='ISOLATED')
    except:
        future_api.client.futures_change_margin_type(symbol='XMRUSDT', marginType='CROSSED')
        future_api.client.futures_change_margin_type(symbol='XMRUSDT', marginType='ISOLATED')

    time.sleep(1)

    spot_api.reset_market()
    future_api.reset_market()
    start_time = time.time()
    print("Spot Fund:", spot_api.basefund, "원")
    print("Future Fund:", future_api.fund, "$")
    dollor_rate = get_dollor_rate()
    cycle = 0.5
    spreads = []
    spread_recording_seconds = 600
    spread_max_len = spread_recording_seconds / cycle
    liquidations = []
    liquidation_recording_seconds = 5
    liquidation_max_len = liquidation_recording_seconds / cycle
    fee = spot_api.fee[0]*2 + future_api.fee[0]*2

    def trading():
        currenttime = time.time()
        spot_book = spot_api.get_orderbook()
        future_ticker = future_api.get_ticker()
        future_best_ask = float(future_ticker['a'])
        future_best_bid = float(future_ticker['b'])
        future_api.update_fund()

        def get_spread(spot_book, order):
            spot_price = spot_book[order]['ask_price']
            return (future_best_ask - (spot_price / dollor_rate)) / (spot_price / dollor_rate) * 100

        liquid_size = future_api.get_liquidations()
        spread_best = get_spread(spot_book, 0)
        spreads.append(spread_best)
        liquidations.append(liquid_size)

        #if len(spreads) >= spread_max_len and len(liquidations) >= liquidation_max_len:
        if len(liquidations) >= liquidation_max_len:
            if len(spreads) > spread_max_len:
                spreads.pop(0)
            if len(liquidations) > liquidation_max_len:
                liquidations.pop(0)
            spread_avg = sum(spreads) / len(spreads)
            liquidation_per_second = sum(liquidations) / liquidation_recording_seconds

            #롱포지션 존재시 청산
            if future_api.position > 0:
                future_api.limit_order('SELL', future_best_ask, future_api.position)

            print('김프', len(spreads)*cycle, '초 평균:', -spread_avg)
            print('현재 김프', -spread_best)
            print('초당 청산수:', liquidation_per_second)

            price = 0
            spot_book = spot_api.get_orderbook()
            for i in range(10):
                spread_best = get_spread(spot_book, i)
                if spot_enter(spread_best, spread_avg):
                    price = spot_book[i]['ask_price']
                else:
                    break
            if price is not 0:
                spot_api.cancel_side_orders('ask')
                available = spot_api.basefund / price * 0.999
                print('Spot 진입: ', available, 'BTC')
                result = spot_api.limit_order('bid', price, available)
                enter_price = price

            try:
                current_profit = (spot_book[0]['bid_price'] - enter_price) / enter_price * 100 - fee
            except:
                current_profit = 0

            if spot_escape(spread_best, spread_avg, current_profit, liquidation_per_second):
                spot_api.cancel_side_orders('bid')
                if spot_api.targetfund > 0.001:
                    print('Spot 탈출')
                    print('Profit: ', current_profit)
                    spot_book = spot_api.get_orderbook()
                    spot_api.limit_order('ask', spot_book[0]['ask_price']-spot_api.tick, spot_api.targetfund*0.999)

            spot_api.update_fund()
            if spot_api.targetfund > 0.001:
                spot_on = True
            else:
                spot_on = False

            if future_enter(spot_on, liquidation_per_second):
                future_api.cancel_side_orders('BUY')
                quantity = spot_api.targetfund + future_api.position
                if quantity >= 0.001:
                    print('Futures 진입:', quantity)
                    try:
                        future_api.limit_order('SELL', future_best_ask, quantity)
                    except:
                        pass

            # position risk 임시로 0으로 설정
            if future_escape(spot_on, liquidation_per_second, 0):
                future_api.cancel_side_orders('SELL')
                quantity = abs(future_api.position)
                if quantity >= 0.001:
                    print('Futures 탈출:', quantity)
                    try:
                        future_api.limit_order('BUY', future_best_bid, quantity)
                    except:
                        pass
        else:
            print("데이터 수집 중..", len(spreads), '/', spread_max_len)
        endtime = time.time()
        elapsetime = endtime - currenttime
        if elapsetime < cycle:
            time.sleep(cycle-elapsetime)

    while True:
        trading()

def get_dollor_rate():
    return c.get_rates('USD')['KRW']

def spot_enter(spread, spread_average):
    if spread - spread_average >= SPOT_ENTER_GAP:
        return True
    else:
        return False

def spot_escape(spread, spread_average, current_profit, liquid_intensity):
    if spread - spread_average <= SPOT_ESCAPE_GAP:
        return True
    elif current_profit >= SPOT_ESCAPE_EXCCES_PROFIT:
        return True
    elif liquid_intensity <= SPOT_ESCAPE_FUTURE_LIQUID_INTENSITY:
        return True
    else:
        return False

def future_enter(spot_on, liquid_intensity):
    if spot_on:
        if liquid_intensity <= FUTURE_ENTER_LIQUID_INTENSITY:
            return True
        else:
            return False
    else:
        return False

def future_escape(spot_on, liquid_intensity, position_risk):
    if spot_on:
        if position_risk >= FUTURE_ESCAPE_LIQUID_RISK:
            return True
        elif liquid_intensity >= FUTURE_ESCAPE_LIQUID_INTENSITY:
            return True
        else:
            return False
    else:
        if liquid_intensity <= FUTURE_HOLD_REVERSE_LIQUID_INTENSITY:
            return False
        else:
            return True

if __name__ == "__main__":
    startAlgo('BTC', 'upbit', upbit_key, 'binance', binance_key)
