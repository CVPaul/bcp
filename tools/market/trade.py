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

from binance.constant import LOT_ROUND_AT
from binance.auth.utils import load_api_keys
from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from strategy.indicator.common import MA
from strategy.indicator.common import ATR


def get_lot_size(exchange_info):
    result = {}
    symbols = {f'{s}USDT' for s in ['BNB', 'SOL', 'DOGE', 'ETH', 'BTC', 'TRUMP', 'SUI']}
    for info in exchange_info['symbols']:
        if info['symbol'] not in symbols:
            continue
        for flt in info['filters']:
            if flt['filterType'] == 'LOT_SIZE':
                result[info['symbol']] = float(flt['minQty'])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str)
    parser.add_argument(
        '--type', '-t', choices=['um', 'cm'], type=str, default='cm')
    args = parser.parse_args()

    if args.type == 'cm':
        api_key, private_key = load_api_keys('li')
        client = CoinM(api_key=api_key, private_key=private_key)
        args.symbol = f"{args.symbol.upper()}USD_PERP"
    else:
        api_key, private_key = load_api_keys('zhou')
        client = USDM(api_key=api_key, private_key=private_key)
        args.symbol = f"{args.symbol.upper()}USDT"
    cutline_len = 145
    # qty = 4.6012345
    # order = {
    #     "side": "SELL",
    #     "symbol": args.symbol,
    #     "quantity": f'{qty:.{LOT_ROUND_AT[args.symbol]}f}', "type": "LIMIT",
    #     "timeInForce": "GTC", "price": '12.791',
    # }
    # res = client.new_order(**order)
    # res = client.get_order(args.symbol, orderId=69332236674)
    res = client.exchange_info()
    print(get_lot_size(res))
    print("=" * cutline_len)
