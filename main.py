#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import sys
import time
import json
import logging
import pandas as pd

from binance.spot import Spot
from binance.fut.unicm import CoinM
from datetime import datetime as dt
from datetime import timedelta as td
# from strategy.common.utils import get_auth_keys
from binance.auth.utils import get_auth_keys

from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s-%(message)s')

def on_message(self, message):
    message = json.loads(message)
    e = message.get('e', '')
    print(json.dumps(message, indent=4))

from scapy.all import sniff, IP
from threading import Thread

# 定义一个函数来处理捕获的包
def packet_handler(packet):
    if packet.haslayer(IP):
        print(f"捕获到的IP包，源地址：{packet[IP].src}，目的地址：{packet[IP].dst}")

# 定义一个函数来启动 Scapy 抓包
def start_sniffing():
    sniff(filter="ip", prn=packet_handler, store=0)

# 你的主程序逻辑
def main():
    # 启动 Scapy 抓包的线程
    sniff_thread = Thread(target=start_sniffing)
    sniff_thread.start()

    # 这里可以放置你的其他主程序逻辑
    # ...


if __name__ == "__main__":
    main()

    api_key, private_key = get_auth_keys()
    print(api_key)
    print(private_key)

    client = CoinM(
        api_key=api_key,
        # private_key=private_key,
        api_secret=private_key,
    )
    # logging.info(pd.to_datetime(client.time()['serverTime'] * 1e6))
    rsp = client.new_order(
       symbol='DOGEUSD_PERP', side='BUY', type='MARKET', quantity=1)
    #rsp = client.new_order(
    #   symbol='DOGEUSD_PERP', side='BUY', type='MARKET',
    #   price=0.1768, # timeInForce='GTC',
    #   timeInForce='GTC', quantity=1, positionSide='LONG')
    #rsp = client.klines('DOGEUSD_PERP', '8h', limit=135)
    #df = pd.DataFrame(
    #    rsp, columns=[
    #        'start_t', 'open', 'high', 'low', 'close',
    #        'volume', 'end_t', 'amount', 'trade_cnt',
    #        'taker_vol', 'taker_amt', 'reserved'
    #    ])
    #df.start_t = pd.to_datetime(df.start_t * 1e6)
    print(df)

    # print(rsp)
    # acc = client.exchange_info(symbol)
    # with open(f'{symbol}.json', 'w') as fp:
    #     json.dump(acc, fp, indent=4)
    # print(client.user_trades(symbol))
    #for i in range(10):
    #    line = client.klines(symbol, '5m', limit=1)
    #    print(i, client.time(), line)
    #    time.sleep(5)
    #print(client.time())
    #
    #rsp = client.new_listen_key()
    #print(rsp)
    # create wedsocket stream client
    # wscli = CoinMWSSStreamClient(
    #     # stream_url=wss_test_url,
    #     on_message=on_message)
    # wscli.book_ticker(symbol)
    ## wscli.kline(symbol, '1m')
    #wscli.user_data(rsp['listenKey'])
    # wscli.agg_trade(symbol)
    # enable it by endpoint POST /dapi/v1/positionSide/dual, setting the parameter dualSidePosition = true
    # Open position:
    #   - Long : positionSide=LONG, side=BUY
    #   - Short: positionSide=SHORT, side=SELL
    # Close position:
    #   - Close long position: positionSide=LONG, side=SELL
    #   - Close short position: positionSide=SHORT, side=BUY
    #order = {
    #    'symbol': 'DOGEUSD_PERP',
    #    'side': 'BUY',
    #    'type': 'LIMIT',
    #    'timeInForce': 'GTC',
    #    'quantity': 1,
    #    'price': 0.1608,
    #    'positionSide': 'SHORT'
    #}
    #print(client.new_order(**order))
    # ords = client.get_orders(symbol, limit=20)
    # print(json.dumps(ords, indent=4))
    # 10303866131
    # print(client.cancel_order(symbol, origClientOrderId='KEpBHANuPJCQlGZOgjAkdI'))
    print('send order finished!')
    # print(pd.DataFrame(kline_store)[['E', 't', 'T', 'o', 'h', 'l', 'c']])



