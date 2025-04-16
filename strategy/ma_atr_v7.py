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
from binance.constant import ROUND_AT, LOT_SIZE

from binance.auth.utils import load_api_keys
from binance.tools.data.const import ORDER_KEY
from binance.tools.data.reader import TickReader
from binance.tools.trade.position import PositionManager

from strategy.common.utils import on_open, on_close
from strategy.indicator.common import DNN, UPP, ATR
from tools.feishu.sender import send_message
from tools.feishu.sender import send_exception


def upated_after_closed(args, cli, position):
    pOrderId = position.get('pOrderId', 0)
    sOrderId = position.get('sOrderId', 0)
    if pOrderId:
        try:
            cli.get_order(args.symbol, orderId=pOrderId)
        except Exception as e:
            if e.error_code == -2013: # 已经止盈
                send_message(args.symbol, "cancle after closed(win)", str(position))
                position['pOrderId'] = 0
                if sOrderId:
                    try:
                        cli.cancel_order(args.symbol, orderId=sOrderId)
                    except:
                        pass # 无论是否撤成功都行
                sOrderId = 0
                position['sOrderId'] = 0
                position['pos'] = 0
            else:
                raise e
    if sOrderId: 
        try:
            cli.get_order(args.symbol, orderId=sOrderId)
        except Exception as e:
            if e.error_code == -2013: # 已经止盈
                send_message(args.symbol, "cancle after closed(loss)", str(position))
                position['sOrderId'] = 0
                if pOrderId:
                    try:
                        cli.cancel_order(args.symbol, orderId=pOrderId)
                    except:
                        pass # 无论是否撤成功都行
                pOrderId = 0
                position['pOrderId'] = 0
                position['pos'] = 0
    return position


def cancel_all(args, cli, position):
    pOrderId = position.get('pOrderId', 0)
    sOrderId = position.get('sOrderId', 0)
    if pOrderId:
        try:
            cli.cancel_order(args.symbol, orderId=pOrderId)
        except:
            pass # no matter is it succeeded
    if sOrderId:
        try:
            cli.cancel_order(args.symbol, orderId=sOrderId)
        except:
            pass # no matter is it succeeded
    send_message(args.symbol, "cancle before open", str(position))


def calc_vol(usd, price, minmove):
    return round(usd / price / minmove) * minmove


def main(args):
    # args infer
    assert '_' not in args.stgname, '"_" is not allowed to include in the stgname'
    api_key, private_key = load_api_keys('zhou')
    cli = USDM(api_key=api_key, private_key=private_key)
    logging.basicConfig(
        filename=f'{args.stgname}.log', level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    if not args.debug:
        # get trade-info
        pm = PositionManager(args.stgname)
        position = upated_after_closed(args, cli, pm.load())
        pos = position['pos']
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
        for i in range(5):
            gdf = cli.klines(args.symbol, "1h", limit = args.atr_window + 50)
            if gdf[-1][0] >= target_time: # 服务器端出现延迟的时候需要重新拉取
                break
            if i > 1:
                send_message(
                    args.symbol, f"{args.stgname}'s marketinfo delay",
                    f"count:{i},target_time:{target_time},sever_time:{gdf[-1][0]}", )
            time.sleep(1)
    gdf = pd.DataFrame(
        gdf[:-1], columns=[ # drop the last gdf[-1]
            'start_t', 'open', 'high', 'low', 'close',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ]).astype(float)
    enpp = gdf.close.iloc[-1]
    args.vol = calc_vol(args.usd, enpp, LOT_SIZE[args.symbol])
    gdf['ATR'] = ATR(args.atr_window, gdf).calc(gdf)
    gdf['DIF'] = gdf.close.rolling(args.his_window).mean().diff()
    gdf['SIG'] = gdf['DIF'] / gdf['ATR']
    if args.debug:
        gdf = gdf[['start_t','open', 'high', 'low', 'close', 'ATR', 'DIF', 'SIG']]
        gdf['buy'] = (gdf.SIG.shift(2) < 0) & (gdf.SIG.shift(1) < 0) & (gdf.SIG > args.k)
        gdf['sell'] = (gdf.SIG.shift(2) > 0) & (gdf.SIG.shift(1) > 0) & (gdf.SIG < -args.k)
        gdf['start_t'] = pd.to_datetime(gdf['start_t'], unit='ms')
        print(gdf.dropna())
        return
    # trade
    sigs = gdf.SIG.values[-7:]
    order = {
        "symbol":args.symbol, "quantity": 0, "type": "LIMIT",
        "timeInForce": "GTC", "price": enpp}
    cond_l = (sigs[-3] < 0 and sigs[-2] < 0)
    cond_s = (sigs[-3] > 0 and sigs[-2] > 0)
    # send_message(args.symbol, f"Signal(V2)[{args.stgname}]", f"sigs:{sigs.round(4)}")
    if pos > -args.vol and cond_s and sigs[-1] < -args.k:
        order["side"] = "SELL"
        order['quantity'] = args.vol + pos
    elif pos < args.vol and cond_l and sigs[-1] > args.k:
        order["side"] = "BUY"
        order['quantity'] = args.vol - pos
    else:
        logging.info(f"POSITION|{pos}")
    if order['quantity'] > 0:
        cancel_all(args, cli, position) # cancel all before new open
        res = cli.new_order(**order)
        logging.info(f"ORDER|{res}")
        trade_info = {
            'pos':args.vol if order['side'] == 'BUY' else -args.vol,
            'enpp': enpp, 'eOrderId': res['orderId']
        }
        send_message(
            args.symbol, f"{args.stgname} {order['side']} {args.symbol}", str(order))
        order['quantity'] = args.vol
        # ----------------------------------------------------------------------------
        order['type'] = 'STOP' # 止损单
        if order['side'] == 'BUY':
            order['side'] = 'SELL'
            sprice = enpp * (1 - args.s2)
            order['price'] = round(sprice, ROUND_AT[args.symbol])
            order['stopPrice'] = order['price']
        else:
            order['side'] = 'BUY'
            sprice = enpp * (1 + args.s2)
            order['price'] = round(sprice, ROUND_AT[args.symbol])
            order['stopPrice'] = order['price']
        res = cli.new_order(**order)
        trade_info['sprice'] = order['price']
        trade_info['sOrderId'] = res['orderId']
        logging.info(f"STOP|{order}|{res}")
        send_message(args.symbol, f"{args.stgname} stop-order", str(order))
        # ----------------------------------------------------------------------------
        if order['side'] == 'SELL': # 止盈单, side已经再上面修改过了
            pprice = enpp * (1 + args.s1)
            order['price'] = round(pprice, ROUND_AT[args.symbol])
        else:
            pprice = enpp * (1 - args.s1)
            order['price'] = round(pprice, ROUND_AT[args.symbol])
        res = cli.new_order(**order)
        trade_info['pprice'] = order['price']
        trade_info['pOrderId'] = res['orderId']
        logging.info(f"TAKE-PROFIT|{order}|{res}")
        send_message(args.symbol, f"{args.stgname} take-profit", str(order))
        # ----------------------------------------------------------------------------

    elif order['quantity'] < 0:
        logging.info(f"ERROR-ORDER|{order}")


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--symbol', '-s', type=str, required=True)
        parser.add_argument('--his-window', type=int, default=7)
        parser.add_argument('--atr-window', type=int, default=24)
        parser.add_argument('--k', type=float, required=True, help='ATR multiplier for entry/exit')
        parser.add_argument('--s1', type=float, required=True, help='take profit ratio')
        parser.add_argument('--s2', type=float, required=True, help='get loss ratio')
        parser.add_argument('--mp', type=int, default=0)
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--usd', '-u', type=float, default=100)
        parser.add_argument('--stgname', type=str, default='backtest')
        args = parser.parse_args()
        main(args)
    except:
        send_exception(args.symbol)
