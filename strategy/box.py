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


def on_tick(args, bid_p, ask_p):
    actions = []
    # highest price section
    if not args.hpp:
        args.hpp = ask_p
        logging.info(f"init the hpp={args.hpp}")
    if ask_p > args.hpp:
        args.hpp = ask_p
        logging.info(f"update hpp to {args.hpp}")
    if bid_p <= (1.0 - args.k1) * args.hpp:
        args.hpp = bid_p
        actions.append({'side':'BUY', 'newClientOrderId':'bottom', 'type':'MARKET'})
    # lowest price section
    if not args.lpp:
        args.lpp = bid_p
        logging.info(f"init the lpp={args.lpp}")
    if bid_p < args.lpp:
        args.lpp = bid_p
        logging.info(f"update lpp to {args.lpp}")
    if ask_p >= (1.0 + args.k1) * args.lpp:
        args.lpp = ask_p
        actions.append({'side':'SELL', 'newClientOrderId':'peak', 'type':'MARKET'})
    return actions


def trade(cli, args, actions, T):
    cid = '%s_{}_{}_{}'%(args.stgname)
    for action in actions:
        action['newClientOrderId'] = cid.format(
                action['side'].lower(), action['newClientOrderId'], T)
        action['quantity'] = args.vol
        action['symbol'] = args.symbol
        action['newOrderRespType'] = 'RESULT'
        order = cli.new_order(**action)
        logging.info(f'ORDER|{order}')
         

# def on_message(cli, args, message):
def on_message(self, message):
    global last_check_time
    message = json.loads(message)
    etype = message.get('e', '')
    if etype == 'bookTicker':
        bid_p = float(message['b'])
        ask_p = float(message['a'])
        actions = on_tick(args, bid_p, ask_p)
        trade(client, args, actions, message['E'])
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
            


if __name__ == "__main__":
    # 网格策略
    parser = argparse.ArgumentParser()
    parser.add_argument('--stgname', type=str, required=True)
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--kind', type=str, default='cm')
    parser.add_argument('--hpp', type=float, default=None)
    parser.add_argument('--lpp', type=float, default=None)
    parser.add_argument('--vol', '-v', type=int, default=1)
    parser.add_argument('--k1', type=float, default=0.3)
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
    # logging
    logging.basicConfig(
        filename=f'{args.stgname}.log', level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    # init session params
    logging.info(f'strategy `{args.stgname}` start with k1={args.k1}')
    # start the market data server forever
    forever(args)
