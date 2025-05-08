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
import pandas as pd

from binance.fut.coinm import CoinM
from binance.fut.unicm import UniCM
from binance.constant import ROUND_AT
from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from binance.tools.data.const import ORDER_KEY
from binance.tools.data.reader import TickReader
from websocket import WebSocketConnectionClosedException

from strategy.common.utils import load_api_keys
from strategy.common.utils import HeartBeatThread


# global vars
connected = False
last_check_time = 0

def on_open(self):
    global connected
    connected = True
    logging.info(f"web socket of {sys.argv[2]} opened!")

 
def on_error(self, e):
    global connected
    if isinstance(e, WebSocketConnectionClosedException):
        connected = False
        logging.error(f"found that websocket loss it's connection!")


def on_tick(args, bid_p, ask_p, T):
    actions = []
    if T - args.last_update_time < args.interval:
        return actions
    args.last_update_time = T
    # highest price section
    mprice = 0.5 * (bid_p + ask_p)
    args.cq.update(mprice)
    if not args.cq.is_full():
        return actions
    diff = mprice / args.cq.old_val - 1.0
    print(diff, mprice, args.cq.old_val)
    orderbook = []
    for o in args.orderbook: # close
        price = float(o['avgPrice'])
        win_l = o['side'] == 'BUY' and bid_p >= 1.002 * price
        win_s = o['side'] == 'SELL' and ask_p <= 0.998 * price
        t_out = T - o['updateTime'] > 600000
        if win_l or win_s or t_out:
            actions.append({
                'side': 'SELL' if o['side'] == 'BUY' else 'BUY',
                'newClientOrderId': 'close', 'type': 'MARKET'
            })
        else:
            orderbook.append(o)
    args.orderbook = orderbook
    action = None
    if diff > args.k1 and args.mp != 1: 
        action = {
            'side':'BUY', 'newClientOrderId':'open', 'type':'MARKET',
            'quantity': args.vol if args.mp == 0 else 2 * args.vol}
        args.mp = 1
    elif diff < -args.k1 and args.mp != -1:
        action = {
            'side':'SELL', 'newClientOrderId':'open', 'type':'MARKET',
            'quantity': args.vol if args.mp == 0 else 2 * args.vol}
        args.mp = -1
    if action:
        actions.append(action)
    return actions


def trade(cli, args, actions, T):
    cid = '%s_{}_{}_{}'%(args.stgname)
    for action in actions:
        action['newClientOrderId'] = cid.format(
                action['side'].lower(), action['newClientOrderId'], T)
        action['symbol'] = args.symbol
        action['newOrderRespType'] = 'RESULT'
        if action['type'] == 'MARKET':
            order = cli.new_order(**action)
            logging.info(f'ORDER|{order}')
            args.orderbook.append(order)
        else:
            cli.new_order(**action)
            action['enpp'] = args.enpp
            logging.info(f'ORDER|{action}')
         

# def on_message(cli, args, message):
def on_message(self, message):
    global last_check_time
    message = json.loads(message)
    etype = message.get('e', '')
    if etype == 'bookTicker':
        T = message['E']
        bid_p = float(message['b'])
        ask_p = float(message['a'])
        actions = on_tick(args, bid_p, ask_p, T)
        trade(client, args, actions, T)
    if message.get('E', last_check_time) - last_check_time >= 60000: # 60s
        logging.info(f'HeartBeat|stg={args.stgname}!')
        last_check_time = message['E']


def listen(args):
    wscli = CoinMWSSStreamClient(
        on_open=on_open,
        on_error=on_error,
        on_message=on_message)
    wscli.book_ticker(args.symbol)
    return wscli


def forever(args):
    while True:
        cli = listen(args)
        while True:
            time.sleep(1)
            if connected == False:
                cli.stop()
                logging.info("websocket thread stopped succeeded!")
                break
            
class CQueue:

    def __init__(self, maxlen):
        self.maxlen = maxlen
        self.queue = [0] * self.maxlen
        self.steps = -1
        self.old_val = 0
        # user diff metric
        self.value = 0
        self.head = 0

    def update(self, value):
        self.steps += 1
        self.head = self.steps % self.maxlen
        self.old_val = self.queue[self.head]
        self.queue[self.head] = value
        self.diff = value - self.old_val

    def is_full(self):
        return self.steps >= self.maxlen


if __name__ == "__main__":
    # 网格策略
    parser = argparse.ArgumentParser()
    parser.add_argument('--stgname', type=str, required=True)
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--kind', type=str, default='cm')
    parser.add_argument('--interval', type=int, default=500)
    parser.add_argument('--vol', type=int, default=1)
    parser.add_argument('--k1', type=float, default=0.004)
    parser.add_argument('--mp', type=int, default=0)
    args = parser.parse_args()
    # args infer
    assert '_' not in args.stgname, '"_" is not allowed to include in the stgname'
    # global
    api_key, private_key = load_api_keys()
    if args.kind == 'cm':
        client = UniCM(api_key=api_key, private_key=private_key)
    elif args.kind == 'um':
        client = UniUM(api_key=api_key, private_key=private_key)
    else:
        raise RuntimeError(f"unsupported kind: {args.kind}!")
    # mdcli
    mdcli = CoinM()
    klines = mdcli.klines(args.symbol, interval='1m', limit=2)
    args.last_mprices = [float(klines[0][1]), float(klines[1][1])]
    args.last_update_time = klines[1][6]
    args.cq = CQueue(117000 // args.interval + 1)
    args.orderbook = []
    # logging
    logging.basicConfig(
        filename=f'{args.stgname}.log', level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    # init session params
    logging.info(f'strategy start with {args=}')
    # start the market data server forever
    forever(args)
