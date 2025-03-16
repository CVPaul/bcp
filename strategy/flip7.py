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

from strategy.common.utils import load_api_keys
from strategy.common.utils import on_open, on_close
from strategy.indicator.common import DNN, UPP, ATR
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
        df['profit'] = (df.pos * df.price.diff().shift(-1))
        df['gross'] = df.profit.cumsum()
        df['commis'] = (df.direction.abs() * df.price * 2e-4)
        df['net'] = df.gross - df.commis.cumsum()
        df['mdd'] = df.net.expanding().max() - df.profit
        print(f'win:loss=', (df.profit > 1e-9).sum(), (df.profit < -1e-9).sum())
        return df


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
    no = args.kline[1]
    nh = args.kline[2]
    nl = args.kline[3]
    nc = args.kline[4]
    if args.kline[0] != args.last_kline[0]:
        # update upp/dnn
        args.upp.update(args.kline[0],args.last_kline[2])
        args.dnn.update(args.kline[0],args.last_kline[3])
        # update session kline and atr
        start_t = args.kline[0] // args.session_interval
        if start_t != args.start_t:
            args.atr.update(args.kline[0], args.high, args.low, args.close)
            logging.info(
                f"SESSION[UPDATE]|st={args.start_t},open={args.open},"
                f"high={args.high},low={args.low},close={args.close},atr={args.atr.value:.6f}")
            args.open = no
            args.high = nh
            args.low = nl
            args.close = nc
            args.start_t = start_t
        else:
            args.low = min(args.low, nl)
            args.high = max(args.high, nh)
            args.close = nc
    # New entry/exit logic based on 30m high/low and ATR
    current_price = no
    atr_value = args.atr.value
    buy_condition = (current_price >= (args.low_30m + args.k * atr_value))
    sell_condition = (current_price <= (args.high_30m - args.k * atr_value))
    # Reset high/low every session
    if start_t != args.start_t:
        args.high_30m = mprice
        args.low_30m = mprice
        args.start_t = start_t
    # Update ATR with latest data
    args.atr.update(T, high=args.high_30m, low=args.low_30m, close=current_price)
    # Entry execution
    if args.mp == 0:
        if buy_condition:
            actions.append({
                'side':'BUY', 'price':current_price, 
                'newClientId':'entry_buy',
                'type':'LIMIT', 'timeInForce':'GTC'})
            args.mp = 1
            args.entry_price = current_price
            args.entry_time = T
        elif sell_condition:
            actions.append({
                'side':'SELL', 'price':current_price, 
                'newClientId':'entry_sell',
                'type':'LIMIT', 'timeInForce':'GTC'})
            args.mp = -1
            args.entry_price = current_price
            args.entry_time = T
    # calculate the market-position
    if args.mp != 0:
        stop_loss_price = args.entry_price - (args.k * atr_value) if args.mp == 1 else args.entry_price + (args.k * atr_value)
        take_profit_price = args.entry_price + (2 * args.k * atr_value) if args.mp == 1 else args.entry_price - (2 * args.k * atr_value)
        # Stop loss
        if (args.mp == 1 and current_price <= stop_loss_price) or (args.mp == -1 and current_price >= stop_loss_price):
            actions.append({
                'side': 'SELL' if args.mp == 1 else 'BUY',
                'price': stop_loss_price,
                'newClientId': 'stop_loss',
                'type': 'LIMIT',
                'timeInForce': 'GTC'
            })
            args.mp = 0
        # Take profit
        if (args.mp == 1 and current_price >= take_profit_price) or (args.mp == -1 and current_price <= take_profit_price):
            actions.append({
                'side': 'SELL' if args.mp == 1 else 'BUY',
                'price': take_profit_price,
                'newClientId': 'take_profit',
                'type': 'LIMIT',
                'timeInForce': 'GTC'
            })
            args.mp = 0
    return actions


def trade(cli, args, actions, T):
    cid = '%s_{}_{}_{}'%(args.stgname)
    for action in actions:
        action['newClientId'] = cid.format(
                action['side'].lower(), action['newClientId'], T)
        if action['side'] == 'BUY':
            action['price'] *= 0.9998
        else:
            action['price'] *= 1.0002
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
        
        mprice = round(0.5 * (ask_p + bid_p), ROUND_AT[args.symbol])
        start_t = message['E'] - message['E'] % 60000
        if start_t != args.kline[0]:
            args.mps.append(mprice)
            # Update 30m high/low tracking
            if mprice > args.high_30m:
                args.high_30m = mprice
            if mprice < args.low_30m:
                args.low_30m = mprice
            args.kline = [start_t, mprice, mprice, mprice, mprice]
        else:
            args.kline[2] = max(args.kline[2], mprice)
            args.kline[3] = min(args.kline[3], mprice)
            args.kline[4] = mprice
        T = message['E']
        actions = on_tick(args, bid_p, ask_p, T)
        trade(client, args, actions, T)
        args.last_kline = args.kline

def tick2msg(tick):
    # return {
    #     'e': 'bookTicker',
    #     'a': tick['ask_price_1'],
    #     'b': tick['bid_price_1'],
    #     'E': int(tick['datetime'].timestamp() * 1000)
    # }
    return tick

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
    parser.add_argument('--k', type=float, default=1.5, help='ATR multiplier for entry/exit')
    parser.add_argument('--mp', type=int, default=0)
    parser.add_argument('--backtest', action='store_true')
    parser.add_argument('--start-time', type=str, default=None)
    parser.add_argument('--end-time', type=str, default=None)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument(
        '--session-period', type=str, default='30m',
        help="Time window for tracking high/low and ATR calculation")
    parser.add_argument('--vol', '-v', type=int, default=1)
    parser.add_argument('--stgname', type=str, default='backtest')
    args = parser.parse_args()
    # Add 30m tracking variables
    args.high_30m = 0.0
    args.low_30m = float('inf')
    args.atr_window = 20  # ATR period
    args.atr = ATR(args.atr_window)  # Reinitialize ATR with new period
    # args infer
    assert '_' not in args.stgname, '"_" is not allowed to include in the stgname'
    args.session_interval = period2milli_second(args.session_period)
    args.cond_l = args.cond_s = False
    args.hpp = args.lpp = 0
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
    if args.backtest:
        endTime = int(pd.to_datetime(args.start_time).timestamp() * 1000)
    # init session params
    gdf = mdcli.klines(
        args.symbol, args.session_period,
        endTime=endTime, limit = args.atr_window + 2)
    kline = gdf[-1] # 最后一根kline是不完整的
    args.start_t = kline[0] // args.session_interval
    args.open = float(kline[1])
    args.high = float(kline[2])
    args.low = float(kline[3])
    args.close = float(kline[4])
    gdf = pd.DataFrame(
        gdf[:-1], columns=[
            'start_t', 'open', 'high', 'low', 'close',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ]).astype(float)
    args.atr = ATR(args.atr_window, gdf)
    # init bar params
    df = mdcli.klines(
        args.symbol, '1m', endTime=endTime, limit = args.his_window + 2)
    args.last_kline = df[-1] # 最后一根kline是不完整的
    args.mps = [float(x[1]) for x in df]
    df = pd.DataFrame(
        df[:-1], columns=[
            'start_t', 'open', 'high', 'low', 'close',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ]).astype(float)
    args.upp = UPP(args.his_window, df)
    args.dnn = DNN(args.his_window, df)
    logging.info(
        f'strategy `{args.stgname}` start with his_window={args.his_window}, atr_window={args.atr_window}, '
        f'k1={args.k1}, s1={args.s1}, s2={args.s2}, k={args.k}, '
        f'upp={args.upp.value}, dnn={args.dnn.value}, '
        f'atr={args.atr.value:.6f}, start_t={args.last_kline[0]}'
    )
    # send request by period client
    args.last_kline = [
        args.last_kline[0], float(args.last_kline[1]),
        float(args.last_kline[2]), float(args.last_kline[3]),
        float(args.last_kline[4])]
    args.kline = args.last_kline
    if args.backtest:
        client = FakeClient()
        from quark.db.ailab import Client
        reader = Client().read2([args.symbol], 'PK', args.start_time, args.end_time, kind='cm', return_df=False)
        for tick in reader:
            client.datetime = tick['E']
            on_message(None, json.dumps(tick2msg(tick)))
        print(client.profit())
    else:
        wscli = CoinMWSSStreamClient(
            on_open=on_open,
            on_close=on_close,
            on_message=on_message)
        wscli.book_ticker(args.symbol)
