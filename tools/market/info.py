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


def get_asset(accinfo, usdx={'USDC':0.0, 'USDT':0.0}):
    for asset in accinfo['assets']:
        symbol = asset['asset']
        if symbol in usdx:
            usdx[symbol] += float(asset['walletBalance'])
    total = 0.0
    for _, amount in usdx.items():
        total += amount
    usdx['total'] = total
    return pd.DataFrame([usdx])


def get_positions(accinfo):
    positions = pd.DataFrame(accinfo['positions'])[[
        'symbol', "positionAmt", "notional", "updateTime"]]
    positions.updateTime = pd.to_datetime(
        positions.updateTime, unit='ms').dt.strftime(args.time_format)
    positions.positionAmt = positions.positionAmt.astype(float)
    positions.notional = positions.notional.astype(float)
    positions = positions[positions.positionAmt != 0]
    return positions


if __name__ == "__main__":
    mark, cutline_len = '-', 50
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str)
    parser.add_argument('--account', '-a', type=str, default='zhou')
    parser.add_argument('--time-format', '-tf', type=str, default='%d/%H:%M:%S')
    parser.add_argument(
        '--type', '-t', type=str, choices=['cm', 'um'], default='um')
    args = parser.parse_args()
    # global
    if not args.symbol:
        args.symbol = ['ETH', 'BNB', 'DOGE']
    else:
        args.symbol = args.symbol.split(',') 
    if args.type == 'cm':
        api_key, private_key = load_api_keys('li')
        cli = CoinM(api_key=api_key, private_key=private_key)
        args.symbol = [f'{x}USD_PERP' for x in args.symbol]
    else:
        api_key, private_key = load_api_keys(args.account)
        cli = USDM(api_key=api_key, private_key=private_key)
        args.symbol = [f'{x}USDC' for x in args.symbol]
    accstr = f"Account:{args.account}"
    headlen = (cutline_len - len(accstr)) // 2 - 1
    print(mark * headlen, accstr, mark * headlen)
    accinfo = cli.account()
    print(f"Asset info:")
    print(get_asset(accinfo))
    print(mark * cutline_len)
    print(f"Positions info:")
    print(get_positions(accinfo))
    print(mark * cutline_len)
    orders = []
    for symbol in args.symbol:
        orders.extend(cli.get_open_orders(symbol))
    if orders:
        orders = pd.DataFrame(orders)[[
            'symbol', 'price', 'origQty', 'side', 'updateTime']]
        orders.updateTime = pd.to_datetime(
            orders.updateTime, unit='ms').dt.strftime(args.time_format)
        print(f"Orders info {args.account}:")
        print(orders)
    else:
        print("No open orders.")
    print(mark * cutline_len)
    print(f"Market info:")
    mds = []
    for symbol in args.symbol:
        rsp = cli.ticker_price(symbol)
        if isinstance(rsp, list):
            rsp = rsp[0]
        mds.append(rsp)
    mds = pd.DataFrame(mds)
    mds.time = pd.to_datetime(mds.time, unit='ms')
    print(mds)
    print(mark * cutline_len)
