# WebSocket Stream Client
import sys
import time
import json
import logging

from pymongo import MongoClient
from datetime import datetime as dt
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from binance.websocket.cm_futures.websocket_client import CMFuturesWebsocketClient


# 连接到MongoDB
count = 0
tp = sys.argv[1]
mc = MongoClient('mongodb://localhost:27017/')
db = mc['ailab'][tp]

# 配置日志记录器
logging.basicConfig(
    filename=f'{dt.now().date()}.{tp}.log',  # 日志文件名
    filemode='a',            # 文件模式，'a'表示追加模式
    level=logging.INFO,      # 日志级别
    format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
)

def message_handler(_, message):
    global count
    try:
        doc = json.loads(message)
        db.insert_one(doc)
        count += 1
    except Exception as e:
        print(f"write message failed with error:{e}!")


if tp == 'um':
    client = UMFuturesWebsocketClient(
        on_message=message_handler)
    symbols = ["ETHUSDT", "ETHUSDT_250328", "ETHUSDT_250627"]
elif tp == 'cm':
    client = CMFuturesWebsocketClient(
        on_message=message_handler)
    symbols = ["DOGEUSD_PERP"] #, "ETHUSD_PERP", "BNBUSD_PERP", "BTCUSD_PERP"]
else:
    raise RuntimeError(f"unsupported type got:{tp}, only `cm`, `um` were allowed!")

# Subscribe to a single symbol stream
# client.agg_trade(symbol="ETHUSDT")

for symbol in symbols:
    client.agg_trade(symbol=symbol)
    client.book_ticker(symbol=symbol)
    client.partial_book_depth(symbol=symbol, level=20, speed=100)

while True:
    time.sleep(60) # 1min
    logging.info(f'HeartBeat|round update count={count}!')

client.stop()
logging.error("closing ws connection!")