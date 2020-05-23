import configparser
from market import initialize_market

config = configparser.ConfigParser()
config.read('config.ini')

SPOT_ENTER_GAP = 0.3
SPOT_ESCAPE_GAP = 0
SPOT_ESCAPE_EXCCES_PROFIT = 0.3
SPOT_ESCAPE_FUTURE_LIQUID_INTENSITY = -0.1
FUTURE_ENTER_LIQUID_INTENSITY = 0.1
FUTURE_ESCAPE_LIQUID_INTENSITY = 0.3
FUTURE_ESCAPE_LIQUID_RISK = 0.5
FUTURE_IMMEDIATE_ESCAPE_LIQUID_RISK = 0.8
FUTURE_HOLD_REVERSE_LIQUID_INTENSITY = -0.1

def startAlgo(spot_market, future_market):
    spot_api, future_api = initialize_market(spot_market, spot_api_key, future_market, future_api_key)
    dollor_rate = get_dollor_rate()
    spreads = []
    spot_api_limit = spot_api['limit']
    future_api_limit = future_api['limit']
    spot_api_call = 0
    future_api_call = 0

    while True:
        spot_orders = spot_api.get_orders()
        future_orders = spot_api.get_orders()
        if spot_orders:
            for order in spot_orders:
                if spot_api.is_order_top(order):
                    spot_api.cancel(order['num'])
        if future_orders:
            for order in future_orders:
                if future_api.is_order_top(order):
                    future_api.cancel(order['num'])

        leverage = spot_api['fund'] / future_api['fund']
        spot_OB = spot_api.get_orderBook()
        future_OB = future_api.get_orderBook()
        liquid_intensity = calc_liquid_intensity(future_api.get_liquids())

        spot_position = spot_api.get_position()
        future_position = future_api.get_position()
        if spot_position and future_position:

def get_dollor_rate():
    return dollor_rate

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
