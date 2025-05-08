#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import sys
import time
import json
import logging
import argparse
import pandas as pd

from binance.fut.usdm import USDM
from binance.fut.coinm import CoinM
from datetime import datetime as dt
from datetime import timedelta as td

from binance.constant import ROUND_AT
from binance.auth.utils import load_api_keys
from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from strategy.indicator.common import MA
from strategy.indicator.common import ATR


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str)
    parser.add_argument(
        '--type', '-t', type=str, choices=['cm', 'um'], default='cm')
    args = parser.parse_args()
    # global
    if not args.symbol:
        args.symbol = ['SOL', 'BNB', 'ETH']
    else:
        args.symbol = args.symbol.split(',') 
    if args.type == 'cm':
        api_key, private_key = load_api_keys('li')
        cli = CoinM(api_key=api_key, private_key=private_key)
        args.symbol = [f'{x}USD_PERP' for x in args.symbol]
    else:
        api_key, private_key = load_api_keys('zhou')
        cli = USDM(api_key=api_key, private_key=private_key)
        args.symbol = [f'{x}USDT' for x in args.symbol]
    cutline_len = 145
    # 校准服务器时间和本地时间
    target_time = int(time.time())
    target_time = 1000 * (target_time - (target_time % (60 * 60)))
    for i in range(5):
        gdf = cli.klines(
            args.symbol, "1h",
            limit = (10 + 50))
        if gdf[-1][0] >= target_time: # 服务器端出现延迟的时候需要重新拉取
            print(gdf[-1][0], target_time)
            break
        print(
            args.symbol, f"test's marketinfo delay",
            f"count:{i}\ntarget_time:{target_time}\nsever_time:{gdf[-1][0]}")
        time.sleep(1)
    print("=" * cutline_len)
    print(f"market info board:")
    positions = {}
    for pos in cli.account()['positions']:
        if pos['symbol'] in args.symbol:
            positions[pos['symbol']] = int(pos['positionAmt'])
    for symbol in args.symbol:
        if symbol not in positions:
            positions[symbol] = 0
    for symbol in args.symbol:
        rsp = cli.ticker_price(symbol)
        if isinstance(rsp, list):
            rsp = rsp[0]
        print(f"    market info of {symbol}:")
        for key, value in rsp.items():
            print(f"        - {key}: {value}")
        print(f"        - position: {positions[symbol]}")
        for order in cli.get_open_orders(symbol):
            print("*" * (cutline_len // 2))
            for key in ['orderId', 'price', 'origQty']:
                print(f"*       - {key}: {order[key]}")
            print("*" * (cutline_len // 2))
    print("=" * cutline_len)
