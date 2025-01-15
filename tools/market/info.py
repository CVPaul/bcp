#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import sys
import time
import json
import logging
import argparse
import pandas as pd

from binance.fut.unicm import CoinM
from datetime import datetime as dt
from datetime import timedelta as td

from binance.constant import ROUND_AT
from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from strategy.indicator.common import MA
from strategy.indicator.common import ATR

from strategy.common.utils import get_auth_keys
from strategy.common.utils import on_open, on_close



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str)
    args = parser.parse_args()
    # global
    if not args.symbol:
        args.symbol = [f"{x}USD_PERP" for x in ['DOGE', 'BTC', 'BNB']]
    else:
        args.symbol = args.symbol.split(',') 
    api_key, private_key = get_auth_keys()
    client = CoinM(
        api_key=api_key,
        private_key=private_key)
    cutline_len = 145
    print("=" * cutline_len)
    print(f"market info board:")
    for symbol in args.symbol:
        rsp = client.ticker_price(symbol)
        print(f"    market info of {symbol}:")
        for key, value in rsp[0].items():
            print(f"        - {key}: {value}")
    print("=" * cutline_len)
