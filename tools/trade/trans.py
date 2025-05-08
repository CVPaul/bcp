#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import argparse
import pandas as pd

from binance.fut.unicm import CoinM
from datetime import datetime as dt
from datetime import timedelta as td

from strategy.common.utils import get_auth_keys


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str)
    parser.add_argument('--raw', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--start-time', type=str)
    parser.add_argument('--end-time', type=str)
    parser.add_argument(
        '--stgname', type=str,
        help='only recall the orders whose ClientOrderId start with given stgname!')
    args = parser.parse_args()
    if not args.symbol:
        if 'doge' in args.stgname.lower():
            args.symbol = 'DOGEUSD_PERP'
        elif 'btc' in args.stgname.lower():
            args.symbol = 'BTCUSD_PERP'
        else:
            raise RuntimeError(
                f'can not infer symbol from stgname, please specify with --symbol')
    if args.stgname:
        args.stgname += '_' # add the end mark '_' to it
    # create the API client first
    api_key, private_key = get_auth_keys()
    cli = CoinM(
        api_key=api_key,
        private_key=private_key,
    )
    cut_line_len = 96
    # get commisionRate
    rsp = cli.commission_rate(args.symbol)
    commission_rate = float(rsp['takerCommissionRate'])
    print("=" * cut_line_len)
    print(f"{args.symbol}'s basic info:")
    for k, v in rsp.items():
        if 'Rate' not in k:
            continue
        print(f"    - {k}:{v}")
    for k, v in cli.ticker_price(args.symbol)[0].items():
        if k not in ['price', 'time']:
            continue
        print(f"    - {k}:{v}")
    print("=" * cut_line_len)
    orders = cli.get_orders(
        symbol=args.symbol, limit=100)
    if args.end_time:
        args.end_time = pd.to_datetime(args.end_time).timestamp() * 1000
    else:
        args.end_time = orders[0]['time']
    if args.start_time:
        args.start_time = pd.to_datetime(args.start_time).timestamp() * 1000
    else:
        assert args.limit, "you should specify at least one of --limit/--start-time"
    while args.end_time >= args.start_time:
        if args.limit > 0 and len(orders) >= args.limit:
            break 
        order_t = cli.get_orders(
            symbol=args.symbol, limit=100, endTime=args.end_time)
        if len(order_t) == 1: # not more orders any more
            break
        args.end_time = order_t[0]['time']
        orders = order_t[:-1] + orders
    # stat
    trans, long_open, short_open = [], [], []
    order_ids, start_t, end_t = set(), 0, 0
    fields =  ["avgPrice", "executedQty", "side", "positionSide", "time"]
    for o in orders:
        if o['orderId'] in order_ids: # check if duplicated
            continue
        order_ids.add(o['orderId'])
        if args.stgname and not o['clientOrderId'].startswith(args.stgname):
            continue
        if o['status'] != 'FILLED' and not args.raw:
            continue
        #if args.start_time and o['time'] < args.start_time:
        #    continue
        #if args.end_time and o['time'] > args.end_time:
        #    continue
        if args.raw:
            long_open.append(o)
            continue
        if o['side'] == 'BUY' and o['positionSide'] == 'LONG': # long open
            long_open.append(o)
        elif o['side'] == 'SELL' and o['positionSide'] == 'SHORT': # short open
            short_open.append(o)
        else: # close order
            if o['side'] == 'SELL': # long close
                if long_open:
                    # ord = long_open.pop()
                    oid = int(o['clientOrderId'].split('_')[-1])
                    ord = None
                    for i in range(len(long_open)):
                        if long_open[i]['orderId'] == oid:
                            ord = long_open[i]
                            long_open = long_open[:i] + long_open[i+1:]
                            break
                    if not ord:
                        continue
                    assert o['executedQty'] == ord['executedQty']
                    trans.append([
                        1, o['executedQty'], ord['time'], ord['avgPrice'],
                        o['time'], o['avgPrice']])
                else:
                    print('can not match long close order:')
                    df = pd.DataFrame([o])[fields]
                    df.time = pd.to_datetime(df.time*1e6).dt.strftime("%Y%m%d %H:%M:%S")
                    print(df)
            else:
                if short_open:
                    # ord = short_open.pop()
                    oid = int(o['clientOrderId'].split('_')[-1])
                    ord = None
                    for i in range(len(short_open)):
                        if short_open[i]['orderId'] == oid:
                            ord = short_open[i]
                            short_open = short_open[:i] + short_open[i+1:]
                            break
                    if not ord:
                        continue
                    assert o['executedQty'] == ord['executedQty']
                    trans.append([
                        -1, o['executedQty'], ord['time'], ord['avgPrice'],
                        o['time'], o['avgPrice']])
                else:
                    print('can not match short close order:')
                    df = pd.DataFrame([o])[fields]
                    df.time = pd.to_datetime(df.time*1e6).dt.strftime("%Y%m%d %H:%M:%S")
                    print(df)
    if trans:
        trans = pd.DataFrame(
            trans, columns=[
                'side', 'pos', 'open_time', 'open', 'close_time', 'close']).astype(float)
        trans.open_time = pd.to_datetime(trans.open_time * 1e6).dt.strftime('%Y%m%d %H:%M:%S')
        trans.close_time = pd.to_datetime(trans.close_time * 1e6).dt.strftime('%Y%m%d %H:%M:%S')
        trans['step'] = (trans.close - trans.open) * trans.side
        trans['percent'] = trans.close / trans.open - 1.0
        trans['gross'] = trans.side * trans.pos * (trans.close - trans.open)
        trans['comms'] = trans.pos * (trans.close + trans.open) * commission_rate
        print(trans)
        print('=' * cut_line_len)
        print(f'statistic result of {args.symbol}：')
        print(f'    - time range:{trans.open_time[0]} '
              f'~ {trans.close_time.iloc[-1]}')
        print(f'    - gross profit: {trans.gross.sum():.5f}')
        print(f'    - gross profit per trade: {trans.gross.mean():.5f}')
        print(f'    - commission: {trans.comms.sum():.5f}')
        print(f'    - commission per trade: {trans.comms.mean():.5f}')
        print('=' * cut_line_len)
    if long_open:
        print(f'still open long orders:')
        df = pd.DataFrame(long_open)[fields]
        df.time = pd.to_datetime(df.time*1e6).dt.strftime("%Y%m%d %H:%M:%S")
        print(df)
        print('=' * cut_line_len)
    if short_open:
        print(f'still open short orders:')
        df = pd.DataFrame(short_open)[fields]
        df.time = pd.to_datetime(df.time*1e6).dt.strftime("%Y%m%d %H:%M:%S")
        print(df)
        print('=' * cut_line_len)
