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
from binance.fut.usdm import USDM
from binance.fut.coinm import CoinM
from binance.constant import ROUND_AT, LOT_ROUND_AT

from binance.auth.utils import load_api_keys
from binance.tools.data.const import ORDER_KEY
from binance.tools.data.reader import TickReader
from binance.tools.trade.position import PositionManager

from strategy.common.utils import cancel_all, round_it
from strategy.common.utils import upated_after_closed
from strategy.indicator.common import DNN, UPP, ATR
from tools.feishu.sender import send_message
from tools.feishu.sender import send_exception


def main(args):
    # args infer
    assert '_' not in args.stgname, '"_" is not allowed to include in the stgname'
    if args.is_um:
        api_key, private_key = load_api_keys('zhou')
        cli = USDM(api_key=api_key, private_key=private_key)
    else:
        api_key, private_key = load_api_keys('li')
        cli = CoinM(api_key=api_key, private_key=private_key)
    logging.basicConfig(
        filename=f'{args.stgname}.log', level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    if not args.debug:
        # get trade-info
        pm = PositionManager(args.stgname)
        position, status = upated_after_closed(args, cli, pm.load())
        if status != 0:
            send_message(
                args.symbol, f"update pos after closed({status=})", str(pm.load()))
        pos = float(position['pos'])
        # is trading time
        if dt.now().minute != 0:
            pm.save(position)
            return
    # init
    target_time = int(time.time())
    target_time = (target_time - (target_time %  3600)) * 1000
    if args.debug:
        gdf = cli.klines(args.symbol, "1h", limit = args.atr_window + 50)
    else:
        for i in range(10):
            gdf = cli.klines(args.symbol, "1h", limit = args.atr_window + 50)
            if gdf[-1][0] >= target_time: # 服务器端出现延迟的时候需要重新拉取
                break
            if i > 2:
                send_message(
                    args.symbol, f"{args.stgname}'s marketinfo delay",
                    f"count:{i},close-price:{gdf[-1][4]}", )
            time.sleep(1)
    gdf = pd.DataFrame(
        gdf[:-1], columns=[ # drop the last gdf[-1]
            'start_t', 'open', 'high', 'low', 'close',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ]).astype(float)
    enpp = gdf.close.iloc[-1]
    if args.is_um:
        args.vol = args.usd / enpp
    gdf['ATR'] = ATR(args.atr_window, gdf).calc(gdf)
    gdf['DIF'] = gdf.close.rolling(args.his_window).mean().diff()
    gdf['SIG'] = gdf['DIF'] / gdf['ATR']
    if args.debug:
        gdf = gdf[['start_t','open', 'high', 'low', 'close', 'ATR', 'DIF', 'SIG']]
        gdf['buy'] =  gdf.SIG > args.k
        gdf['sell'] = gdf.SIG < -args.k
        for i in range(args.cond_len):
            gdf['buy'] = gdf['buy'] & (gdf.SIG.shift(i + 1) < 0)
            gdf['sell'] = gdf['sell'] & (gdf.SIG.shift(i + 1) > 0)
        gdf['start_t'] = pd.to_datetime(gdf['start_t'], unit='ms') + td(hours=8)
        print(gdf.dropna())
        return
    # trade
    maxlen = max(7, args.cond_len + 1)
    sigs = gdf.SIG.values[-maxlen:]
    order = {
        "symbol":args.symbol, "quantity": 0, "type": "LIMIT",
        "timeInForce": "GTC", "price": round_it(enpp, ROUND_AT[args.symbol])}
    cond_l = sigs[-1] > args.k
    cond_s = sigs[-1] < -args.k
    for i in range(args.cond_len):
        cond_l = cond_l and (sigs[-2 - i] < 0)
        cond_s = cond_s and (sigs[-2 - i] > 0)
    if pos >= 0 and cond_s:
        order["side"] = "SELL"
        order['quantity'] = args.vol + pos
    elif pos <= 0 and cond_l:
        order["side"] = "BUY"
        order['quantity'] = args.vol - pos
    else:
        logging.info(f"POSITION|{pos}")
    if order['quantity'] > 1e-8:
        if args.is_um:
            order['quantity'] = round_it(
                order['quantity'], LOT_ROUND_AT[args.symbol])
        cancel_all(args, cli, position) # cancel all before new open
        logging.info(f"ORDER|{order}")
        res = cli.new_order(**order)
        qty = float(order['quantity'])
        trade_info = {
            'pos':qty if order['side'] == 'BUY' else -qty,
            'enpp': enpp, 'eOrderId': res['orderId']
        }
        order['quantity'] = args.vol
        if args.is_um:
            order['quantity'] = round_it(
                args.vol, LOT_ROUND_AT[args.symbol])
        atr = gdf.ATR.values[-1]
        title = f"{args.stgname} {order['side']}@{order['price']}|{atr=:.6f}"
        # ----------------------------------------------------------------------------
        order['type'] = 'LIMIT' # 止盈单
        if order['side'] == 'BUY':
            order['side'] = 'SELL'
            if args.use_atr:
                pprice = enpp + args.s1 * atr
            else:
                pprice = enpp * (1 + args.s1)
            order['price'] = round_it(pprice, ROUND_AT[args.symbol])
        else:
            order['side'] = 'BUY'
            if args.use_atr:
                pprice = enpp - args.s1 * atr
            else:
                pprice = enpp * (1 - args.s1)
            order['price'] = round_it(pprice, ROUND_AT[args.symbol])
        logging.info(f"TAKE-PROFIT|{order}")
        res = cli.new_order(**order)
        trade_info['pprice'] = order['price']
        trade_info['pOrderId'] = res['orderId']
        # ----------------------------------------------------------------------------
        order['type'] = 'STOP' # 止损单
        if order['side'] == 'SELL': # 止盈单, side已经在上面修改过了
            if args.use_atr:
                sprice = enpp - args.s2 * atr
            else:
                sprice = enpp * (1 - args.s2)
            order['price'] = round_it(sprice, ROUND_AT[args.symbol])
        else:
            if args.use_atr:
                sprice = enpp + args.s2 * atr
            else:
                sprice = enpp * (1 + args.s2)
            order['price'] = round_it(sprice, ROUND_AT[args.symbol])
        order['stopPrice'] = order['price']
        logging.info(f"STOP|{order}")
        res = cli.new_order(**order)
        trade_info['sprice'] = order['price']
        trade_info['sOrderId'] = res['orderId']
        send_message(args.symbol, title, str(trade_info))
        # ----------------------------------------------------------------------------
        pm.save(trade_info)
    elif order['quantity'] < 0:
        logging.info(f"ERROR-ORDER|{order}")


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--symbol', '-s', type=str, required=True)
        parser.add_argument('--his-window', type=int, default=7)
        parser.add_argument('--atr-window', type=int, default=24)
        parser.add_argument('--cond-len', type=int, default=2)
        parser.add_argument('--k', type=float, required=True, help='ATR multiplier for entry/exit')
        parser.add_argument('--s1', type=float, required=True, help='take profit ratio')
        parser.add_argument('--s2', type=float, required=True, help='get loss ratio')
        parser.add_argument('--mp', type=int, default=0)
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--use-atr', action='store_true')
        parser.add_argument('--usd', '-u', type=float, default=100)
        parser.add_argument('--vol', '-v', type=float, default=1)
        parser.add_argument('--stgname', type=str, default='backtest')
        args = parser.parse_args()
        args.is_um = not args.symbol.endswith('_PERP')
        main(args)
    except Exception as e:
        if e.error_code == -1021: # 已经止损失·
            logging.warning(f"{args.stgname} is timeout")
        else:
            send_exception(args.symbol)
