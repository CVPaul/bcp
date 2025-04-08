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
from binance.fut.coinm import CoinM
from binance.fut.unicm import UniCM
from binance.constant import ROUND_AT
from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from binance.auth.utils import load_api_keys
from binance.tools.data.const import ORDER_KEY
from binance.tools.data.reader import TickReader

from strategy.common.utils import on_open, on_close
from strategy.indicator.common import DNN, UPP, ATR
from tools.feishu.sender import send_message
from tools.feishu.sender import send_exception


def main(args):
    # Add 30m tracking variables
    args.atr = ATR(args.atr_window)  # Reinitialize ATR with new period
    args.time = dt.now()
    if not args.debug and args.time.minute < 59:
        return
    if not args.debug and args.time.second < 57:
        time.sleep(57 - args.time.second)
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
        gdf, columns=[
            'start_t', 'open', 'high', 'low', 'close',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ]).astype(float)
    gdf['ATR'] = ATR(args.atr_window, gdf).calc(gdf)
    gdf['DIF'] = gdf.close.rolling(args.his_window).mean().diff()
    gdf['SIG'] = gdf['DIF'] / gdf['ATR']
    if args.debug:
        gdf['start_t'] = pd.to_datetime(gdf.start_t + 8 * 3600000, unit='ms')
        print(gdf.dropna())
        return
    # get positions
    positions = {}
    for pos in client.account()['positions']:
        if pos['symbol'] == args.symbol:
            positions = pos
    pos = int(positions.get('positionAmt', 0))
    # trade
    sigs = gdf.SIG.values[-3:]
    order = {"symbol":args.symbol, "quantity": 0, "type": "MARKET", "newOrderRespType": "RESULT"}
    if args.cond_type == "and":
        cond_l = (sigs[0] < 0 and sigs[1] < 0)
        cond_s = (sigs[0] > 0 and sigs[1] > 0)
    elif args.cond_type == "or":
        cond_l = (sigs[0] < 0 or sigs[1] < 0)
        cond_s = (sigs[0] > 0 or sigs[1] > 0)
    else:
        raise ValueError(f"unsupported condition type given:`{args.cond_type}`!!!")
    if sigs[1] * sigs[2] < 0:
        send_message(args.symbol, "Signal Change", f"sigs={sigs.round(4)}")
    if pos > -args.vol and cond_s and sigs[2] < -args.k:
        order["side"] = "SELL"
        order['quantity'] = args.vol + pos
    elif pos < args.vol and cond_l and sigs[2] > args.k:
        order["side"] = "BUY"
        order['quantity'] = args.vol - pos
    else:
        logging.info(f"POSITION|{positions}")
    if order['quantity'] > 0:
        res = client.new_order(**order)
        logging.info(f"ORDER|{res}")
    elif order['quantity'] < 0:
        logging.info(f"ERROR-ORDER|{order}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--his-window', type=int, default=7)
    parser.add_argument('--atr-window', type=int, default=24)
    parser.add_argument('--cond-type', type=str, required=True)
    parser.add_argument('--k', type=float, required=True, help='ATR multiplier for entry/exit')
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