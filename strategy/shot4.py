#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import sys
import time
import json
import logging
import argparse
import numpy as np
import pandas as pd

from binance.fut.unicm import CoinM
from datetime import datetime as dt
from datetime import timedelta as td

from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from strategy.indicator.common import MA
from strategy.indicator.common import ATR
from strategy.common.utils import get_auth_keys
from strategy.common.utils import on_open, on_close

# global
ROUND_AT = {
    "BTCUSD_PERP": 1,
    "DOGEUSD_PERP": 5,
}


lut = 0
trade_cum_period = 0
trade_cum_count_per_1m = 0
def on_message(self, message):
    global args, lut
    global trade_cum_period, trade_cum_count_per_1m

    message = json.loads(message)
    if trade_cum_count_per_1m > 3: # 1 分钟交易超过10次，异常直接停止策略
        event_t = message.get('E', trade_cum_period)
        if event_t - trade_cum_period > 600000: # 每10分钟打印一次：
            trade_cum_period = event_t
            logging.error('strategy error: trade exceeded 10 times per minutes!')
        return
    etype = message.get('e', '')

    if etype == 'ORDER_TRADE_UPDATE':
        trade_cnt = 0
        order = message['o']
        if order['X'] != 'FILLED':
            return # do nothing
        toks = order['c'].split('_')
        if toks[0] != args.stgname:
            return # not the order of this stg
        slot = int(toks[-2])
        args.orders[slot] = 0 # delete the traded order
        if slot < args.grids and args.orders[slot + 1] == 0:
            trade_cnt += 1
            pSide = 'SHORT' if slot + 1 > args.entry_slot else 'LONG'
            args.orders[slot + 1] = client.new_order(
                symbol=args.symbol, side='SELL', type='LIMIT',
                price=args.slots[slot + 1], timeInForce='GTC',
                newClientOrderId=f'{args.stgname}_{slot + 1}_{message["E"]}',
                quantity=args.vol, positionSide=pSide)['orderId']
            logging.info(
                f'put limit ORDER[SELL/{pSide}] at slot={slot}, price={args.slots[slot + 1]} and '
                f'--entry-slot={args.entry_slot},--orders={str(args.orders)[1:-1].replace(" ", "")} ')
        if slot > 0 and args.orders[slot - 1] == 0:
            trade_cnt += 1
            pSide = 'LONG' if slot - 1 < args.entry_slot else 'SHORT'
            args.orders[slot - 1] = client.new_order(
                symbol=args.symbol, side='BUY', type='LIMIT',
                price=args.slots[slot - 1], timeInForce='GTC',
                newClientOrderId=f'{args.stgname}_{slot - 1}_{message["E"]}',
                quantity=args.vol, positionSide=pSide)['orderId']
            logging.info(
                f'put limit ORDER[BUY/{pSide}] at slot={slot}, price={args.slots[slot - 1]} and '
                f'--entry-slot={args.entry_slot},--orders={str(args.orders)[1:-1].replace(" ", "")} ')
        
        n_min = message['E'] // 60000
        if trade_cum_period == n_min: #
            trade_cum_count_per_1m += trade_cnt
        else:
            trade_cum_period = n_min
            trade_cum_count_per_1m = trade_cnt

def init(cli, args):
    hist = cli.klines(
        args.symbol, f'{args.interval // 60000}m',
        limit = args.length + 1)
    assert len(hist) ==  args.length + 1
    df = pd.DataFrame(
        hist[:-1], columns=[
            'start_t', 'open', 'high', 'low', 'close',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ]).astype(float)
    args.last = {'t': hist[-1][0], 'c': hist[-1][4]}
    args.lows = df['low'].values
    args.highs = df['high'].values
    args.tail = args.length - 1
    args.upp = args.highs.max()
    args.dnn = args.lows.min()
    args.lpp = round(args.upp * (1 - args.stop_ratio), ROUND_AT[args.symbol])
    args.spp = round(args.dnn * (1 + args.stop_ratio), ROUND_AT[args.symbol])
    if args.lpp < args.last['c'] < args.spp: # 还在区间内，可以挂单
        args.lopen_order = client.new_order( # open long
                symbol=args.symbol, side='BUY', type='LIMIT',
                price=args.lpp, timeInForce='GTC',
                newClientOrderId=f'{args.stgname}_{hist[-1][6]}',
                quantity=args.vol, positionSide='LONG')['orderId']
        spp = round(args.lpp * (1 - ))
        args.lloss_order = client.new_order(
                symbol=args.symbol, side='SELL', type='STOP',
                price=args., timeInForce='GTC',
                newClientOrderId=f'{args.stgname}_{slot + 1}_{message["E"]}',
                quantity=args.vol, positionSide=pSide)['orderId']


if __name__ == "__main__":
    # 网格策略
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--length', type=int, default=30)
    parser.add_argument('--threshold', type=float, default=0.011)
    parser.add_argument('--stop-ratio', type=float, default=0.01)
    parser.add_argument('--vol', '-v', type=int, default=1)
    parser.add_argument('--stgname', type=str, default='shot4')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    # args infer
    assert '_' not in args.stgname, '"_" is not allowed to include in the stgname'
    # logging
    logging.basicConfig(
        filename=f'{args.stgname}.log', level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    # dry-run
    strategy_info = (
        f'{args.stgname} start with: --symbol {args.symbol} --threshold={args.threshold} '
        f'--stop-ratio={args.stop_ratio} --vol={args.vol} ')
    if args.dry_run:
        print('>>>', strategy_info)
        sys.exit(0)
    else:
        logging.info(strategy_info)
    # global
    api_key, private_key = get_auth_keys()
    client = CoinM(
        api_key=api_key,
        private_key=private_key,
    )
    # create wedsocket stream client
    wscli = CoinMWSSStreamClient(
        on_open=on_open,
        on_close=on_close,
        on_message=on_message)
    # wscli.book_ticker(args.symbol)
    # 需要在挂单前注册on_message
    listen_key = client.new_listen_key()['listenKey']
    wscli.user_data(listen_key)
    # stg main
    if args.entry_slot < 0:
        rsp = client.ticker_price(args.symbol)[0]
        last_p = float(rsp['price'])
        for i in range(1, len(args.slots)):
            if args.slots[i] > last_p:
                args.entry_slot = i - 1
                break
        assert args.entry_slot >= 0
        on_message( # directly using the on_message to init the position
            wscli, json.dumps({
                'e':'ORDER_TRADE_UPDATE', 'E':rsp['time'],
                'o':{'X':'FILLED', 'c':f'{args.stgname}_{args.entry_slot}_{rsp["time"]}'}}))
    # update the listenKey
    while True:
        time.sleep(3599)
        client.renew_listen_key(listen_key)
