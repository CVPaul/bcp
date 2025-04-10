#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import sys
import time
import json
import logging
import argparse
import pandas as pd

from binance.fut.coinm import CoinM
from binance.fut.unicm import UniCM
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
    args = parser.parse_args()
    # global
    if not args.symbol:
        args.symbol = [f"{x}USD_PERP" for x in ['DOGE', 'BNB', 'ETH']]
    else:
        args.symbol = args.symbol.split(',') 
    api_key, private_key = load_api_keys()
    mdcli = CoinM(
        api_key=api_key,
        private_key=private_key)
    client = UniCM(
        api_key=api_key,
        private_key=private_key,
    )
    cutline_len = 145
    print("=" * cutline_len)
    print(f"market info board:")
    positions = {}
    for pos in client.account()['positions']:
        if pos['symbol'] in args.symbol:
            positions[pos['symbol']] = int(pos['positionAmt'])
    for symbol in args.symbol:
        rsp = mdcli.ticker_price(symbol)
        print(f"    market info of {symbol}:")
        for key, value in rsp[0].items():
            print(f"        - {key}: {value}")
        print(f"        - position: {positions[symbol]}")
        for order in client.get_open_orders(symbol):
            print(">" * cutline_len)
            for key in ['orderId', 'price', 'origQty']:
                print(f"        - {key}: {order[key]}")
            print("<" * cutline_len)
    print("=" * cutline_len)
