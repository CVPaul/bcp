#!/usr/bin/env python
#-*- coding:utf-8 -*-


# 说明：已经尝试过wss订阅kline,但是延迟不是一般的高，根本不是250ms,所以考虑for循环


import time
import copy
import logging
import argparse
import pandas as pd

from datetime import datetime as dt
from datetime import timedelta as td
from binance.fut.usdm import USDM
from binance.fut.coinm import CoinM

from binance.auth.utils import load_api_keys
from binance.tools.trade.position import PositionManager

from strategy.common.utils import round_at, lot_round_at
from strategy.common.utils import cancel_all, round_it
from strategy.common.utils import upated_after_closed
from strategy.indicator.common import ATR
from tools.feishu.sender import send_message
from tools.feishu.sender import send_exception


def main(args):
    # args infer
    assert '_' not in args.stgname, '"_" is not allowed to include in the stgname'
    api_key, private_key = load_api_keys(args.account)
    if args.is_um:
        cli = USDM(api_key=api_key, private_key=private_key)
    else:
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
                args.symbol, f"{args.stgname} update pos after closed({status=})", str(pm.load()))
        pos = float(position['pos'])
        # is trading time
        if args.trade_price <= 1e-8 and dt.now().minute != 0:
            pm.save(position)
            return
    gdf = get_data(args, cli)
    enpp = gdf.close.iloc[-1]
    cond_l, cond_s, atr = get_signal(args, cli)
    orders, trade_info = get_orders(
        args, cli, atr, pos, cond_l, cond_s, enpp) 
    execute(args, cli, orders, trade_info)


def get_data(args, cli):
    # init
    target_time = int(time.time())
    target_time = (target_time - (target_time %  3600)) * 1000
    for i in range(10):
        gdf = cli.klines(args.symbol, "1h", limit = args.atr_window + 50)
        if gdf[-1][0] >= target_time: # 服务器端出现延迟的时候需要重新拉取
            break
        if i > 7:
            send_message(
                args.symbol, f"{args.stgname}'s marketinfo delay",
                f"count:{i},close-price:{gdf[-1][4]}", )
        time.sleep(1)
    return pd.DataFrame(
        gdf[:-1], columns=[ # drop the last gdf[-1]
            'start_t', 'open', 'high', 'low', 'close',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ]).astype(float) 


def get_signal(args, gdf):
    # init
    atr = ATR(args.atr_window, gdf).calc(gdf).iloc[-2] # atr shift 1
    gdf['MA7'] = gdf.close.rolling(args.his_window).mean()
    gdf['DIF'] = gdf.MA7.diff()
    gdf['SIG'] = gdf['DIF'] / atr
    # trade
    maxlen = max(7, args.cond_len + 1)
    sigs = gdf.SIG.values[-maxlen:]
    go_up = go_down = True
    for i in range(args.cond_len):
        go_up = go_up and (sigs[-2 - i] > 0)
        go_down = go_down and (sigs[-2 - i] < 0)
    final_up = sigs[-1] > args.k
    final_down = sigs[-1] < -args.k
    if args.follow_trend:
        cond_l = go_up and final_up
        cond_s = go_down and final_down
    else:
        cond_l = go_down and final_up
        cond_s = go_up and final_down
    return cond_l, cond_s, atr


def get_orders(args, atr, pos, cond_l, cond_s, enpp):
    orders = {}
    order = {"symbol":args.symbol, "quantity": 0, "type": "LIMIT", "timeInForce": "GTC"}
    if pos >= 0 and cond_s:
        order["side"] = "SELL"
        order['quantity'] = args.vol + pos
        order["price"] = round_it(enpp * (1 + args.profit), round_at(args.symbol))
    elif pos <= 0 and cond_l:
        order["side"] = "BUY"
        order['quantity'] = args.vol - pos
        order["price"] = round_it(enpp * (1 - args.profit), round_at(args.symbol))
    else:
        logging.info(f"POSITION|{pos}")
    if order['quantity'] > 1e-8:
        if args.is_um:
            order['quantity'] = round_it(
                order['quantity'], lot_round_at(args.symbol))
        orders['eOrderId'] = copy.deepcopy(order)
        qty = float(order['quantity'])
        trade_info = {'pos':qty if order['side'] == 'BUY' else -qty, 'enpp': enpp}
        order['type'] = 'LIMIT' # 止盈单
        if order['side'] == 'BUY':
            order['side'] = 'SELL'
            if args.use_atr:
                pprice = enpp + args.s1 * atr
            else:
                pprice = enpp * (1 + args.s1)
            order['price'] = round_it(pprice, round_at(args.symbol))
        else:
            order['side'] = 'BUY'
            if args.use_atr:
                pprice = enpp - args.s1 * atr
            else:
                pprice = enpp * (1 - args.s1)
            order['price'] = round_it(pprice, round_at(args.symbol))
        orders['pOrderId'] = copy.deepcopy(order)
        trade_info['pprice'] = order['price']
        # ----------------------------------------------------------------------------
        order['type'] = 'STOP_MARKET' # 止损单
        if order['side'] == 'SELL': # side已经在上面修改过了
            if args.use_atr:
                sprice = enpp - args.s2 * atr
            else:
                sprice = enpp * (1 - args.s2)
            if order['type'] == 'STOP_MARKET' and 'price' in order:
                order.pop('price')
            else:
                order['price'] = round_it(sprice, round_at(args.symbol))
            order['stopPrice'] = round_it(sprice * (1 + args.profit), round_at(args.symbol))
        else:
            if args.use_atr:
                sprice = enpp + args.s2 * atr
            else:
                sprice = enpp * (1 + args.s2)
            if order['type'] == 'STOP_MARKET' and 'price' in order:
                order.pop('price')
            else:
                order['price'] = round_it(sprice, round_at(args.symbol))
            order['stopPrice'] = round_it(sprice * (1 - args.profit), round_at(args.symbol))
        orders['sOrderId'] = copy.deepcopy(order)
        trade_info['sprice'] = order['stopPrice']
    return orders, trade_info


def execute(args, cli, orders, trade_info):
    for key, order in orders.items():
        res = cli.order(**order)
        trade_info[key] = res['orderId']
    pm = PositionManager(args.stgname)
    pm.save(trade_info)
    return res


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
        parser.add_argument('--close-only', action='store_true')
        parser.add_argument('--follow-trend', action='store_true')
        parser.add_argument('--usd', '-u', type=float, default=100)
        parser.add_argument('--vol', '-v', type=float, default=1)
        parser.add_argument('--profit', '-p', type=float, default=1e-4)
        parser.add_argument('--account', '-a', type=str, default='zhou')
        parser.add_argument('--trade-price', '-tp', type=float, default=0)
        parser.add_argument('--trade-side', '-ts', type=str, choices=['BUY', 'SELL'])
        parser.add_argument('--stgname', type=str, default='backtest')
        args = parser.parse_args()
        if not args.use_atr:
            assert args.s1 < 1 and args.s2 < 1, f'{args.s1=} and {args.s2=} is reqired to less than 1.0 without atr use'
        args.is_um = not args.symbol.endswith('_PERP')
        if args.trade_price > 1e-8:
            assert args.trade_side, f'--trade-side is require(`BUY` or `SELL`) when trade_price > 0'
        main(args)
    except Exception as e:
        # send_exception(args.symbol)
        if dt.now().minute != 0 and hasattr(e, 'error_code') and e.error_code == -1021: # 已经止损失·
            logging.warning(f"{args.stgname} is timeout")
        else:
            send_exception(args.symbol)
