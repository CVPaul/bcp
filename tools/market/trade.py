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
from binance.fut.unicm import UniCM
from datetime import datetime as dt
from datetime import timedelta as td

from binance.constant import ROUND_AT
from binance.auth.utils import load_api_keys2
from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from strategy.indicator.common import MA
from strategy.indicator.common import ATR


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str)
    parser.add_argument(
        '--type', '-t', choices=['um', 'cm'], type=str, default='cm')
    args = parser.parse_args()

    if args.type == 'cm':
        api_key, private_key = load_api_keys2('li')
        client = UniCM(api_key=api_key, private_key=private_key)
        args.symbol = f"{args.symbol.upper()}USD_PERP"
    else:
        api_key, private_key = load_api_keys2('zhou')
        print(api_key)
        print(private_key)
        client = USDM(api_key=api_key, private_key=private_key)
        args.symbol = f"{args.symbol.upper()}USDT"
    cutline_len = 145
    order = {
        "side": "BUY",
        "symbol": args.symbol,
        "quantity": 1, "type": "LIMIT",
        "timeInForce": "GTC", "price": 540.48,
    }
    res = client.new_order(**order)
    print(res)
    print("=" * cutline_len)
