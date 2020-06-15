from market import WebsocketThread
from time import sleep

uri = 'wss://api.upbit.com/websocket/v1'
data = [{"ticket":"UNIQUE_TICKET"},{"type":"orderbook","codes":["KRW-BTC.10"]}]

socket = WebsocketThread(uri,data)
socket.set_reset_cycle(60)
socket.start()

while True:
    sleep(1)
    print(socket.get_data(True))
