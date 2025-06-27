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

from binance.auth.utils import load_api_keys
from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from strategy.common.utils import round_at, round_it


def to_datetime(ts, offset=28800000):
    return pd.to_datetime(ts + offset, unit='ms')


def rename_symbol(df):
    if 'symbol' in df:
        df['symbol'] = df['symbol'].apply(
            lambda s: s.split('USD')[0].split('1000')[-1])
    return df


def get_asset(accinfo, usdx={'USDC':0.0, 'USDT':0.0}):
    for asset in accinfo['assets']:
        symbol = asset['asset']
        if symbol in usdx:
            usdx[symbol] += float(asset['walletBalance'])
    total = 0.0
    for _, amount in usdx.items():
        total += amount
    usdx['total'] = total
    return rename_symbol(pd.DataFrame([usdx]))


def get_positions(accinfo, mds):
    price_map = mds[['symbol', 'price']].set_index('symbol').astype(float).to_dict()['price']
    positions = pd.DataFrame(accinfo['positions'])
    if positions.empty:
        return "No position data!"
    positions = positions[[
        'symbol', "positionAmt", "unrealizedProfit", "updateTime"]].rename(
        columns={
            'unrealizedProfit': 'pnl', 'positionAmt': 'pos'})
    positions['pnl'] = positions.pnl.astype(float).round(2)
    positions['pos'] = positions.pos.astype(float)
    positions = positions[positions.pos != 0]
    positions['price'] = positions.apply(
        lambda r: 
            round_it(price_map[r['symbol']] - r['pnl'] / r['pos'], round_at(r['symbol'])), axis=1)
    positions['updateTime'] = to_datetime(
        positions.pop('updateTime')).dt.strftime(args.time_format)
    return rename_symbol(positions)


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
        args.symbol = ['ETH', 'BNB', 'DOGE', '1000PEPE']
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
    mds = []
    for symbol in args.symbol:
        rsp = cli.ticker_price(symbol)
        if isinstance(rsp, list):
            rsp = rsp[0]
        mds.append(rsp)
    mds = pd.DataFrame(mds)
    mds.time = to_datetime(mds.time)
    print(mark * headlen, accstr, mark * headlen)
    accinfo = cli.account()
    print(f"Asset info:")
    print(get_asset(accinfo))
    print(mark * cutline_len)
    print(f"Positions info:")
    print(get_positions(accinfo, mds))
    print(mark * cutline_len)
    orders = []
    for symbol in args.symbol:
        orders.extend(cli.get_open_orders(symbol))
    if orders:
        orders = rename_symbol(pd.DataFrame(orders)[[
            'symbol', 'price', 'origQty', 'side', 'updateTime']].rename(
                columns={'origQty': 'qty'}))
        orders.updateTime = to_datetime(
            orders.updateTime).dt.strftime(args.time_format)
        print(f"Orders info {args.account}:")
        print(orders)
    else:
        print("No open orders.")
    print(mark * cutline_len)
    print(f"Market info:")
    print(rename_symbol(mds))
    print(mark * cutline_len)
