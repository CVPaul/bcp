#!/usr/bin/env python
#-*- coding:utf-8 -*-


# 说明：已经尝试过wss订阅kline,但是延迟不是一般的高，根本不是250ms,所以考虑for循环


import os
import sys
import time
import json
import glob
import logging
import argparse
import numpy as np
import pandas as pd

from binance.fut.coinm import CoinM
from binance.fut.unicm import UniCM
from binance.constant import ROUND_AT
from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from binance.tools.data.const import ORDER_KEY
from binance.tools.data.reader import TickReader

from strategy.indicator.stat import Slope
from strategy.common.utils import FakeClient
from strategy.common.utils import load_api_keys
from strategy.common.utils import on_open, on_close


def on_tick(args, bid_p, ask_p):
    actions = []
    if args.timestamp - args.last_time < 60000: # sample price with 60s
        return actions
    args.tick_cnt += 1
    k, b = slope_.update((args.timestamp, (bid_p + ask_p) / 2))
    if args.tick_cnt % slope_.length != 0 or k is None:
        return actions
    args.cond_l = k > args.k1
    args.cond_s = k < -args.k1
    # long
    if args.mp == 0 and args.cond_l:
        actions.append({
            'side':'BUY', 'price':ask_p, 'newClientId':'open',
            'type':'LIMIT', 'timeInForce':'GTC'})
        args.mp = 1
        args.enpp = ask_p
    # short
    if args.mp == 0 and args.cond_s:
        actions.append({
            'side':'SELL', 'price':bid_p, 'newClientId':'open',
            'type':'LIMIT', 'timeInForce':'GTC'})
        args.mp = -1
        args.enpp = bid_p
    # calculate the market-position
    if args.mp != 0:
        spp = (1 - args.s1) * args.enpp
        if args.mp > 0 and bid_p <= spp and not args.cond_l: # 止损
            args.mp = 0
            actions.append({
                'side':'SELL', 'price':bid_p, 'newClientId':'loss',
                'type':'LIMIT', 'timeInForce':'GTC'})
        ppp = (1 + args.s2) * args.enpp
        if args.mp > 0 and ask_p >= ppp and not args.cond_l: # 止盈
            args.mp = 0
            actions.append({
                'side':'SELL', 'price':ask_p, 'newClientId':'win',
                'type':'LIMIT', 'timeInForce':'GTC'})
        # short
        spp = (1 + args.s1) * args.enpp
        if args.mp < 0 and ask_p >= spp and not args.cond_s: # 止损
            args.mp = 0
            actions.append({
                'side':'BUY', 'price':ask_p, 'newClientId':'loss',
                'type':'LIMIT', 'timeInForce':'GTC'})
        ppp = (1 - args.s2) * args.enpp
        if args.mp < 0 and bid_p <= ppp and not args.cond_s: # 止盈
            args.mp = 0
            actions.append({
                'side':'BUY', 'price':bid_p, 'newClientId':'win',
                'type':'LIMIT', 'timeInForce':'GTC'})
    return actions


def trade(cli, args, actions):
    cid = '%s_{}_{}_{}'%(args.stgname)
    for action in actions:
        action['newClientId'] = cid.format(
                action['side'].lower(), action['newClientId'], args.timestamp)
        action['price'] = round(action['price'], ROUND_AT[args.symbol])
        action['quantity'] = args.vol
        action['symbol'] = args.symbol
        cli.new_order(**action)
        logging.info(f'ORDER|{action}')
         

# def on_message(cli, args, message):
def on_message(self, message):
    message = json.loads(message)
    etype = message.get('e', '')
    if etype == 'bookTicker':
        ask_p = float(message['a'])
        bid_p = float(message['b'])
        args.timestamp = message['E'] 
        actions = on_tick(args, bid_p, ask_p)
        trade(client, args, actions)

def tick2msg(tick):
    return {
        'e': 'bookTicker',
        'a': tick['ask_price_1'],
        'b': tick['bid_price_1'],
        'E': int(tick['datetime'].timestamp() * 1000)
    }

def period2milli_second(period):
    cnt = int(period[:-1])
    if period[-1] == 'm':
        return cnt * 60000
    if period[-1] == 'h':
        return cnt * 3600000
    if period[-1] == 'd':
        return cnt * 86400000
    raise ValueError(f'unsupport period:{period}')


if __name__ == "__main__":
    # 网格策略
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--his-window', type=int, default=30)
    parser.add_argument('--atr-window', type=int, default=20)
    parser.add_argument('--k1', type=float, default=0.3)
    parser.add_argument('--s1', type=float, default=0.9)
    parser.add_argument('--s2', type=float, default=2.1)
    parser.add_argument('--mp', type=int, default=0)
    parser.add_argument('--backtest', action='store_true')
    parser.add_argument('--start-time', type=str, default=None)
    parser.add_argument('--end-time', type=str, default=None)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument(
        '--session-period', type=str, default='8h',
        help="该参数描述的是大周期长度，本策略中主要用于计算ATR(8h)")
    parser.add_argument('--vol', '-v', type=int, default=1)
    parser.add_argument('--stgname', type=str, default='backtest')
    args = parser.parse_args()
    # args infer
    assert '_' not in args.stgname, '"_" is not allowed to include in the stgname'
    args.session_interval = period2milli_second(args.session_period)
    args.cond_l = args.cond_s = False
    args.tick_cnt = 0
    args.last_time = 0
    # global
    api_key, private_key = load_api_keys()
    client = UniCM(
        api_key=api_key,
        private_key=private_key,
    )
    mdcli = CoinM(
        api_key=api_key,
        private_key=private_key,
    )
    # logging
    logging.basicConfig(
        filename=f'{args.stgname}.log', level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    # init
    endTime = None
    slope_ = Slope(args.his_window)
    # init session params
    logging.info(
        f'strategy `{args.stgname}` start with his_window={args.his_window}, '
        f'k1={args.k1}, s1={args.s1}, s2={args.s2}, '
    )
    if args.backtest:
        client = FakeClient()
        from quark.db.ailab import Client
        reader = Client().read2(
            args.symbol, 'PK', args.start_time, args.end_time, return_df=False, kind='cm')
        for tick in reader:
            client.datetime = tick['E']
            on_message(None, json.dumps(tick))
        print(client.profit())
    else:
        wscli = CoinMWSSStreamClient(
            on_open=on_open,
            on_close=on_close,
            on_message=on_message)
        wscli.book_ticker(args.symbol)
