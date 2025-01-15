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

from strategy.indicator.common import MA
from strategy.indicator.common import ATR
from strategy.common.utils import get_auth_keys
from strategy.common.utils import on_open, on_close


# global
lut = 0
ROUND_AT = {
    "BTCUSD_PERP": 1,
    "DOGEUSD_PERP": 5,
}


def on_message(self, message):
    global args, lut
    global trade_cum_period, trade_cum_count_per_1m

    message = json.loads(message)
    if trade_cum_count_per_1m > 20: # 1 分钟交易超过20次，异常直接停止策略
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
        if abs(args.side) == 1 and message['E'] - lut > 60000: # 1min info update
            logging.info(
                f'recover with: python strategy/break.py --symbol {args.symbol} '
                f'--dnn {args.dnn} --upp={args.upp} --side {args.side} --enpp={args.enpp} '
                f'--hpp {args.hpp} --lpp={args.lpp} --pos={args.pos}')
            lut = message['E']
        # close first
        # close long position
        cond = [False] * 4
        cond[0] = (args.hpp > args.enpp * 1.01 and bid_p <= 0.97 * args.hpp)
        cond[1] = (args.hpp > args.enpp * 1.03 and bid_p <= 0.97 * args.hpp)
        cond[2] = (args.hpp > args.enpp * 1.05 and bid_p <= 0.98 * args.hpp)
        cond[3] = (args.hpp > args.enpp * 1.10 and bid_p <= 0.99 * args.hpp)
        if args.side == 1 and sum(cond) > 0:
            rsp = client.new_order(
                symbol=args.symbol, side='SELL', type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.pos, positionSide='LONG')
            args.side = 2 # 机会只有一次
            trade_cnt += 1
            logging.info(
                f'ORDER[SELL/LONG/{args.symbol}] order[bid_p({bid_p}], cond={cond}, rsp={rsp}')
        
        # close short position
        cond = [False] * 4
        cond[0] = (args.lpp < args.enpp * 0.99 and ask_p >= 1.03 * args.lpp)
        cond[1] = (args.lpp < args.enpp * 0.97 and ask_p >= 1.03 * args.lpp)
        cond[2] = (args.lpp < args.enpp * 0.95 and ask_p >= 1.02 * args.lpp)
        cond[3] = (args.lpp < args.enpp * 0.90 and ask_p >= 1.01 * args.lpp)
        if args.side == -1 and sum(cond) > 0:
            rsp = client.new_order(
                symbol=args.symbol, side='BUY', type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.pos, positionSide='SHORT')
            args.side = -2 # 机会只有一次
            trade_cnt += 1
            logging.info(
                f'ORDER[BUY/SHORT/{args.symbol}] order[ask_p({ask_p}], cond={cond}, rsp={rsp}')
        # +++++++++++++++++++++++++++open positions++++++++++++++++++++++++++
        if args.side == 0 and ask_p >= args.upp: # UP-break
            rsp = client.new_order(
                symbol=args.symbol, side='BUY', type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.pos, positionSide='LONG')
            args.side = 1
            trade_cnt += 1
            args.hpp = args.lpp = args.enpp = ask_p
            logging.info(
                f'ORDER[BUY/LONG/{args.symbol}], ask_p={ask_p}, enpp={args.enpp}, rsp={rsp}')

        if args.side == 0 and bid_p <= args.dnn: # UP-break
            rsp = client.new_order(
                symbol=args.symbol, side='SELL', type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.pos, positionSide='SHORT')
            args.side = -1
            trade_cnt += 1
            args.hpp = args.lpp = args.enpp = ask_p
            logging.info(
                f'ORDER[SELL/SHORT/{args.symbol}], bid_p={bid_p}, enpp={args.enpp}, rsp={rsp}')

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
    parser.add_argument('--stgname', type=str, default='break')
    parser.add_argument('--pos', '-p', type=int, default=5)
    args = parser.parse_args()
    # args infer
    assert args.upp > args.dnn
    # logging
    logging.basicConfig(
        filename=f'break.{args.stgname}.log', level=logging.INFO,
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
        f'lpp={args.lpp}, hpp={args.hpp}, pos={args.pos}')
    trade_cum_period = 0
    trade_cum_count_per_1m = 0
    # create wedsocket stream client
    wscli = CoinMWSSStreamClient(
        on_open=on_open,
        on_close=on_close,
        on_message=on_message)
    wscli.book_ticker(args.symbol)
