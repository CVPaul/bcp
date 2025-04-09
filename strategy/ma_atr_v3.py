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

from datetime import datetime as dt
from datetime import timedelta as td
from binance.fut.coinm import CoinM
from binance.fut.unicm import UniCM
from binance.constant import ROUND_AT
from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from binance.auth.utils import load_api_keys
from binance.tools.data.const import ORDER_KEY
from binance.tools.data.reader import TickReader
from binance.tools.trade.position import PositionManager

from strategy.common.utils import on_open, on_close
from strategy.indicator.common import DNN, UPP, ATR
from tools.feishu.sender import send_message
from tools.feishu.sender import send_exception


def main(args):
    # Add 30m tracking variables
    args.atr = ATR(args.atr_window)  # Reinitialize ATR with new period
    args.time = dt.now() + td(hours=8)
    if not args.debug and args.time.minute < 59:
        return
    if not args.debug and args.time.second < 59:
        time.sleep(59 - args.time.second)
    # args infer
    assert '_' not in args.stgname, '"_" is not allowed to include in the stgname'
    api_key, private_key = load_api_keys()
    client = UniCM(
        api_key=api_key,
        private_key=private_key,
    )
    mdcli = CoinM(
        api_key=api_key,
        private_key=private_key,
    )
    logging.basicConfig(
        filename=f'{args.stgname}.log', level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    # init
    gdf = mdcli.klines(args.symbol, args.period, limit = args.atr_window + 50)
    gdf = pd.DataFrame(
        gdf[:-1], columns=[
            'start_t', 'open', 'high', 'low', 'close',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ]).astype(float)
    gdf['ATR'] = ATR(args.atr_window, gdf).calc(gdf)
    gdf['DIF'] = gdf.close.rolling(args.his_window).mean().diff()
    gdf['SIG'] = gdf['DIF'] / gdf['ATR']
    pm = PositionManager(args.stgname)
    position = pm.load()
    pos = position['pos']
    orderId = position.get('orderId', 0)
    if args.debug:
        gdf['start_t'] = pd.to_datetime(gdf.start_t + 8 * 3600000, unit='ms')
        print(gdf.dropna())
        return
    # get positions
    # positions = {}
    # for pos in client.account()['positions']:
    #     if pos['symbol'] == args.symbol:
    #         positions = pos
    # pos = int(positions.get('positionAmt', 0))
    # trade
    sigs = gdf.SIG.values[-7:]
    order = {"symbol":args.symbol, "quantity": 0, "type": "MARKET", "newOrderRespType": "RESULT"}
    cond_l = (sigs[-4] < 0 and sigs[-3] < 0 and sigs[-2] < 0)
    cond_s = (sigs[-4] > 0 and sigs[-3] > 0 and sigs[-2] > 0)
    send_message(args.symbol, "Signal(V3)", f"sigs:{sigs.round(4)}")
    if pos > -args.vol and cond_s and sigs[-1] < -args.k:
        order["side"] = "SELL"
        order['quantity'] = args.vol + pos
    elif pos < args.vol and cond_l and sigs[-1] > args.k:
        order["side"] = "BUY"
        order['quantity'] = args.vol - pos
    else:
        logging.info(f"POSITION|{pos}")
    if order['quantity'] > 0:
        try:
            client.cancel_order(args.symbol, orderId=orderId)
        except Exception as e:
            if e.error_code == -2011: # 'Unknown order sent.'
                order['quantity'] = args.vol # already take profit traded
        client.cancel_open_orders(args.symbol) # cancel all orders first
        res = client.new_order(**order)
        logging.info(f"ORDER|{res}")
        send_message(args.symbol, "open", str(order))
        order['type'] = 'LIMIT'
        order['quantity'] = args.vol
        order['newOrderRespType'] = "ACK"
        order['timeInForce'] = 'GTC'
        if order['side'] == 'BUY': # 止盈单
            order['side'] = 'SELL'
            pprice = float(res['avgPrice']) * (1 + args.s1)
            order['price'] = round(pprice, ROUND_AT[args.symbol])
        else:
            order['side'] = 'BUY'
            pprice = float(res['avgPrice']) * (1 - args.s1)
            order['price'] = round(pprice, ROUND_AT[args.symbol])
        res = client.new_order(**order)
        pm.save({ # 这里的order是止盈，所以和原始order是反的
            'pos':args.vol if order['side'] == 'SELL' else -args.vol,
            'orderId': int(res['OrderId'])
        })
        logging.info(f"TAKE-PROFIT|{order}")
        send_message(args.symbol, "take-profit", str(order))
    elif order['quantity'] < 0:
        logging.info(f"ERROR-ORDER|{order}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--his-window', type=int, default=7)
    parser.add_argument('--atr-window', type=int, default=24)
    parser.add_argument('--k', type=float, required=True, help='ATR multiplier for entry/exit')
    parser.add_argument('--s1', type=float, required=True, help='take profit ratio')
    parser.add_argument('--mp', type=int, default=0)
    parser.add_argument('--period', type=str, default='1h')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--vol', '-v', type=int, default=1)
    parser.add_argument('--stgname', type=str, default='backtest')
    args = parser.parse_args()
    try:
        main(args)
    except:
        send_exception(args.symbol)