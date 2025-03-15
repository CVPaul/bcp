# WebSocket Stream Client
import sys
import time
import json
import logging
sys.path.append('/home/ubuntu')

from pymongo import MongoClient
from datetime import datetime as dt

from bcp.strategy.common.utils import HeartBeatThread
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from binance.websocket.cm_futures.websocket_client import CMFuturesWebsocketClient

from websocket import WebSocketConnectionClosedException


# 连接到MongoDB
count = 0
last_update_time = 0
tp = sys.argv[1]
mc = MongoClient('mongodb://localhost:27017/')
db = mc['ailab'][tp]

# init the heart beat thread
heart_beat = HeartBeatThread(f'dumper.{tp}.{sys.argv[2]}')
heart_beat.start()

# 配置日志记录器
logging.basicConfig(
    filename=f'{dt.now().date()}.{tp}.{sys.argv[2]}.log',  # 日志文件名
    filemode='a',            # 文件模式，'a'表示追加模式
    level=logging.INFO,      # 日志级别
    format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
)

connected = False

def on_open(self):
    global connected
    connected = True
    logging.info(f"web socket of {tp}.{sys.argv[2]} opened!")

 
def on_error(self, e):
    global connected
    if isinstance(e, WebSocketConnectionClosedException):
        connected = False
        logging.error(f"found that websocket loss it's connection!")

def message_handler(_, message):
    global count
    try:
        doc = json.loads(message)
        db.insert_one(doc)
        if 'E' in doc:
            last_update_time = doc['E']
            heart_beat.keep_alive(last_update_time)
        count += 1
    except Exception as e:
        print(f"write message failed with error:{e}!")


symbols = sys.argv[2].split('|')
def listen(tp, symbols):
    if tp == 'um':
        client = UMFuturesWebsocketClient(
            on_open=on_open,
            on_error=on_error,
            on_message=message_handler)
        # symbols = ["ETHUSDT", "ETHUSDT_250328", "ETHUSDT_250627"]
    elif tp == 'cm':
        client = CMFuturesWebsocketClient(
            on_open=on_open,
            on_error=on_error,
            on_message=message_handler)
        # symbols = ["DOGEUSD_PERP"] #, "ETHUSD_PERP", "BNBUSD_PERP", "BTCUSD_PERP"]
    else:
        raise RuntimeError(f"unsupported type got:{tp}, only `cm`, `um` were allowed!")

    # Subscribe to a single symbol stream
    # client.agg_trade(symbol="ETHUSDT")

    for symbol in symbols:
        # client.agg_trade(symbol=symbol)
        client.book_ticker(symbol=symbol)
        client.partial_book_depth(symbol=symbol, level=20, speed=100)
    return client

last_check_time = 0
while True:
    cli = listen(tp, symbols)
    while True:
        time.sleep(1)
        if connected == False:
            cli.stop()
            logging.info("websocket thread stopped succeeded!")
            break
        if time.time() - last_check_time > 60: # 1min
            logging.info(f'HeartBeat|round update count={count}!')
            last_check_time = time.time()
        
