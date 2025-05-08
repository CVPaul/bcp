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

from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from strategy.common.utils import get_auth_keys
from strategy.common.utils import on_open, on_close


# global
ROUND_AT = {
    "BTCUSD_PERP": 1,
    "DOGEUSD_PERP": 5,
}


lut = 0
long_open_time = 0
short_open_time = 0
def on_message(self, message):
    global args, lut
    global long_open_time, short_open_time
    global trade_cum_period, trade_cum_count_per_1m

    message = json.loads(message)
    if trade_cum_count_per_1m > 10: # 1 分钟交易超过10次，异常直接停止策略
        event_t = message.get('E', trade_cum_period)
        if event_t - trade_cum_period > 600000: # 每10分钟打印一次：
            trade_cum_period = event_t
            logging.error('strategy error: trade exceeded 1 times per minutes!')
        return
    etype = message.get('e', '')

    if etype == 'bookTicker':
        trade_cnt = 0
        ask_p = float(message['a'])
        bid_p = float(message['b'])
        args.hpp = max(args.hpp, ask_p)
        args.lpp = min(args.lpp, bid_p)
        if abs(args.side) == 1 and message['E'] - lut > 600000: # 10min info update
            logging.info(
                f'recover with: python strategy/break.py --symbol {args.symbol} '
                f'--dnn {args.dnn} --upp={args.upp} --side {args.side} --enpp={args.enpp} '
                f'--hpp {args.hpp} --lpp={args.lpp} --vol={args.vol}')
            lut = message['E']
        # close first
        # close long position
        cond = [
            bid_p <= args.dnn,
            message["E"] - long_open_time >= args.duration,
            args.hpp >= args.enpp * 1.05 and bid_p <= 0.97 * args.hpp,
            args.hpp >= args.enpp * 1.10 and bid_p <= 0.97 * args.hpp,
        ]
        if args.side == 1 and sum(cond) > 0:
            client.new_order(
                symbol=args.symbol, side='SELL', type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.vol, positionSide='LONG')
            args.side = 0
            trade_cnt += 1
            if not cond[0]:
                args.dnn += args.hpp - args.upp
                args.upp = args.hpp
            logging.info(
                f'ORDER[SELL/LONG] order[bid_p({bid_p}], cond={cond}, dnn={args.dnn}, upp={args.upp}')
        
        # close short position
        cond = [
            ask_p >= args.upp,
            message["E"] - short_open_time >= args.duration,
            args.lpp <= args.enpp * 0.95 and ask_p >= 1.03 * args.lpp,
            args.lpp <= args.enpp * 0.90 and ask_p >= 1.03 * args.lpp,
        ]
        if args.side == -1 and sum(cond) > 0:
            client.new_order(
                symbol=args.symbol, side='BUY', type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.vol, positionSide='SHORT')
            args.side = 0 
            trade_cnt += 1
            if not cond[0]:
                args.upp -= args.dnn - args.lpp
                args.dnn = args.lpp
            logging.info(
                f'ORDER[BUY/SHORT] order[ask_p({ask_p}], cond={cond}, dnn={args.dnn}, upp={args.upp}')
        # +++++++++++++++++++++++++++open positions++++++++++++++++++++++++++
        if args.side == 0 and ask_p >= args.upp: # UP-break
            client.new_order(
                symbol=args.symbol, side='BUY', type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.vol, positionSide='LONG')
            args.side = 1
            trade_cnt += 1
            long_open_time = message["E"]
            args.hpp = args.lpp = args.enpp = ask_p
            logging.info(
                f'ORDER[BUY/LONG], ask_p={ask_p}, enpp={args.enpp}, upp={args.upp}')

        if args.side == 0 and bid_p <= args.dnn: # Down-break
            client.new_order(
                symbol=args.symbol, side='SELL', type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.vol, positionSide='SHORT')
            args.side = -1
            trade_cnt += 1
            short_open_time = message["E"]
            args.hpp = args.lpp = args.enpp = ask_p
            logging.info(
                f'ORDER[SELL/SHORT], bid_p={bid_p}, enpp={args.enpp}, dnn={args.dnn}')

        n_min = message['E'] // 60000
        if trade_cum_period == n_min: #
            trade_cum_count_per_1m += trade_cnt
        else:
            trade_cum_period = n_min
            trade_cum_count_per_1m = trade_cnt

if __name__ == "__main__":
    # 突破策略
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--upp', '-u', type=float, required=True)
    parser.add_argument('--dnn', '-d', type=float, required=True)
    parser.add_argument('--hpp', type=float, default=1e8)
    parser.add_argument('--lpp', type=float, default=0)
    parser.add_argument('--side', type=int, default=0)
    parser.add_argument('--enpp', '-e', type=float, default=0)
    parser.add_argument('--duration', type=str, default='7d')
    parser.add_argument('--stgname', type=str, default='break')
    parser.add_argument('--vol', '-p', type=int, default=5)
    args = parser.parse_args()
    # args infer
    assert args.upp > args.dnn
    args.duration = args.duration.lower()
    if args.duration[-1] == 'd':
        args.duration = int(args.duration[:-1]) * 24 * 3600000
    elif args.duration[-1] == 'h':
        args.duration = int(args.duration[:-1]) * 3600000
    elif args.duration[-1] == 'm':
        args.duration = int(args.duration[:-1]) * 60000
    elif args.duration[-1] == 's':
        args.duration = int(args.duration[:-1]) * 1000
    else:
        raise KeyError('only: d->day, h->hour, m->minute, s->second were allowed! e.g: 7d')
    # logging
    logging.basicConfig(
        filename=f'{args.stgname}.log', level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    # global
    api_key, private_key = get_auth_keys() 
    client = CoinM(
        api_key=api_key,
        private_key=private_key,
    )
    logging.info(
        f'start break strategy with[{args.symbol}]: enpp={args.enpp}, '
        f'dnn={args.dnn}, upp={args.upp}, side={args.side}, '
        f'lpp={args.lpp}, hpp={args.hpp}, vol={args.vol}')
    trade_cum_period = 0
    trade_cum_count_per_1m = 0
    # create wedsocket stream client
    wscli = CoinMWSSStreamClient(
        on_open=on_open,
        on_close=on_close,
        on_message=on_message)
    wscli.book_ticker(args.symbol)
