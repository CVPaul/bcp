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

from strategy.common.utils import get_auth_keys
from strategy.common.utils import on_open, on_close
from strategy.indicator.common import DNN, UPP
from pymongo import MongoClient, DESCENDING, ReplaceOne


class FakeClient:

    def __init__(self):
        self.orderid = 0
        self.orders = []
        self.datetime = None

    def new_order(self, *args, **kw):
        self.orderid += 1
        kw['datetime'] = self.datetime
        self.orders.append(kw)
        return {"orderId": self.orderid}
    
    def profit(self):
        df = pd.DataFrame(self.orders)
        df['direction'] = 2 * (df['side'] == 'BUY') - 1
        df['pos'] = df['direction'].cumsum()
        df['profit'] = (df.pos * df.price.diff().shift(-1)).cumsum()
        df['mdd'] = df.profit.expanding().max() - df.profit
        return df


def load_api_keys():
    path = f'{os.getenv("HOME")}/.vntrader/connect_unifycm.json'
    with open(path, 'r') as f:
        config = json.load(f)
        api_key = config['API Key']
        private_key = config['API Secret']
        if os.path.exists(private_key):
            with open(private_key, 'r') as f:
                private_key = f.read().strip()
    return api_key, private_key


def on_tick(args, bid_p, ask_p):
    actions = []
    if not args.enpp:
        args.enpp = ask_p
    if bid_p <= (1.0 - args.k1) * args.enpp:
        args.enpp = bid_p
        actions.append({'side':'BUY', 'newClientId':'add','type':'MARKET'})
    return actions


def trade(cli, args, actions, T):
    cid = '%s_{}_{}_{}'%(args.stgname)
    for action in actions:
        action['newClientId'] = cid.format(
                action['side'].lower(), action['newClientId'], T)
        action['quantity'] = args.vol
        action['symbol'] = args.symbol
        cli.new_order(**action)
        actions['enpp'] = args.enpp
        logging.info(f'ORDER|{action}')
         

# def on_message(cli, args, message):
def on_message(self, message):
    message = json.loads(message)
    etype = message.get('e', '')
    if etype == 'bookTicker':
        ask_p = float(message['a'])
        bid_p = float(message['b'])
        actions = on_tick(args, ask_p, bid_p)
        trade(client, args, actions, message['E'])

if __name__ == "__main__":
    # 网格策略
    parser = argparse.ArgumentParser()
    parser.add_argument('--stgname', type=str, default='backtest')
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--enpp', type=float, default=None)
    parser.add_argument('--vol', '-v', type=int, default=1)
    parser.add_argument('--k1', type=float, default=0.3)
    args = parser.parse_args()
    # args infer
    assert '_' not in args.stgname, '"_" is not allowed to include in the stgname'
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
    # init session params
    logging.info(f'strategy `{args.stgname}` start with k1={args.k1}')
    # send request by period client
    wscli = CoinMWSSStreamClient(
        on_open=on_open,
        on_close=on_close,
        on_message=on_message)
    wscli.book_ticker(args.symbol)
