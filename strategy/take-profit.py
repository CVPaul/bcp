#!/usr/bin/env python
#-*- coding:utf-8 -*-


import json
import logging
import argparse

from binance.fut.unicm import UniCM
from binance.fut.coinm import CoinM
from binance.constant import ROUND_AT
from datetime import datetime as dt
from datetime import timedelta as td

from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from strategy.indicator.common import MA
from strategy.indicator.common import ATR
from strategy.common.utils import get_auth_keys
from strategy.common.utils import on_open, on_close


lut = 0
def on_message(self, message):
    global args, lut
    global trade_cum_period, trade_cum_count_per_1m

    message = json.loads(message)
    if trade_cum_count_per_1m > 3: # 1 分钟交易超过1次，异常直接停止策略
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
        if message['E'] - lut > 60000: # 1min
            logging.info(f'record hpp={args.hpp}, lpp={args.lpp}, step={args.step}')
            lut = message['E']
        if args.stop_ratio[0] > 1:
            cond = ask_p >= args.stop_ratio[0] * args.lpp
            acts = ('BUY', 'SHORT')
        else:
            cond = bid_p <= args.stop_ratio[0] * args.hpp
            acts = ('SELL', 'LONG')
        if args.step == 0 and cond:
            client.new_order(
                symbol=args.symbol, side=acts[0], type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.vol, positionSide=acts[1])
            logging.info(
                f'ORDER[{acts[0]}/{acts[1]}] close previous '
                f'order, stop-ratio={args.stop_ratio[0]}, pos={args.vol}, hpp={args.hpp}, lpp={args.lpp}')
            trade_cnt += 1
            args.step = 1
        
        for case_ in [1, 2]:
            if args.stop_ratio[case_] > 1:
                cond = ask_p >= args.stop_ratio[case_] * args.lpp
                acts = ('SELL', 'SHORT')
            else:
                cond = bid_p <= args.stop_ratio[case_] * args.hpp
                acts = ('BUY', 'LONG')
            if args.step == case_ and cond:
                client.new_order(
                    symbol=args.symbol, side=acts[0], type='MARKET',
                    newClientOrderId=f'{args.stgname}_{message["E"]}',
                    quantity=args.vol//2, positionSide=acts[1])
                logging.info(
                    f'ORDER[{acts[0]}/{acts[1]}] create new order, '
                    f'stop-ratio={args.stop_ratio[case_]}, pos={args.vol//2}, hpp={args.hpp}, lpp={args.lpp}')
                trade_cnt += 1
                args.step = case_ + 1
        
        n_min = message['E'] // 60000
        if trade_cum_period == n_min: #
            trade_cum_count_per_1m += trade_cnt
        else:
            trade_cum_period = n_min
            trade_cum_count_per_1m = trade_cnt

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--vol', type=int, default=0)
    parser.add_argument('--step', type=int, default=0)
    parser.add_argument('--hpp', type=float, default=0)
    parser.add_argument('--lpp', type=float, default=1e8)
    parser.add_argument('--stop-ratio', type=str, default="0.97,0.94,0.90")
    parser.add_argument('--stgname', type=str, default="hand")
    args = parser.parse_args()
    args.stop_ratio = [float(x) for x in args.stop_ratio.split(',')]
    # logging
    logging.basicConfig(
        filename=f'take-profit.{args.stgname}.log', level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    # global
    api_key, private_key = get_auth_keys()
    client = CoinM(
        api_key=api_key,
        private_key=private_key,
    )

    trade_cum_period = 0
    trade_cum_count_per_1m = 0
    # create wedsocket stream client
    wscli = CoinMWSSStreamClient(
        on_open=on_open,
        on_close=on_close,
        on_message=on_message)
    wscli.book_ticker(args.symbol)
