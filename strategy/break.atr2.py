#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import sys
import time
import json
import logging
import argparse
import pandas as pd

from binance.fut.unicm import CoinM
from datetime import datetime as dt
from datetime import timedelta as td

from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from strategy.indicator.common import MA
from strategy.indicator.common import ATR
from strategy.common.utils import get_auth_keys
from strategy.common.utils import on_open, on_close

# global
ROUND_AT = {
    "BTCUSD_PERP": 1,
    "DOGEUSD_PERP": 5,
}


lut = 0
trade_cum_period = 0
trade_cum_count_per_1m = 0
def on_message(self, message):
    global args, lut
    global trade_cum_period, trade_cum_count_per_1m

    message = json.loads(message)
    if trade_cum_count_per_1m > 3: # 1 分钟交易超过10次，异常直接停止策略
        event_t = message.get('E', trade_cum_period)
        if event_t - trade_cum_period > 600000: # 每10分钟打印一次：
            trade_cum_period = event_t
            logging.error('strategy error: trade exceeded 10 times per minutes!')
        return
    trade_cnt = 0
    etype = message.get('e', '')
    if etype == 'kline':
        kline = message['k']
        if kline['t'] != args.last_kline['t']:
            # update upp/dnn
            args.upp.update(float(args.last_kline['h']))
            args.dnn.update(float(args.last_kline['l']))
            # update session kline and atr
            session_n = kline['t'] // args.minutes_per_session
            o = float(kline['o'])
            h = float(kline['h'])
            l = float(kline['l'])
            c = float(kline['c'])
            if session_n != args.session_n:
                args.atr.update(args.high, args.low, args.close)
                args.open = o
                args.high = h
                args.low = l
                args.close = c
            else:
                args.high = max(args.high, h)
                args.low = min(args.low, l)
                args.close = c
        no = float(kline['o'])
        # trade
        range_t = args.k1 * args.atr.value
        # long
        pSide = 'LONG'
        if args.mp == 0 and args.upp.value - no > range_t:
            trade_cnt += 1
            args.long_id = client.new_order( # close position
                symbol=args.symbol, side='BUY', type='MARKET',
                newClientOrderId=f'{args.stgname}_long_open_{message["E"]}',
                quantity=args.vol, positionSide=pSide)['orderId']
            args.enpp = no
            # loss
            spp = args.enpp - args.s1 * args.atr.value
            spp = round(spp, ROUND_AT[args.symbol])
            rsp = client.new_order( # close position
                symbol=args.symbol, side='SELL', type='STOP',
                price=spp, stopPrice=spp,
                newClientOrderId=f'{args.stgname}_long_loss_{args.long_id}',
                quantity=args.vol, positionSide=pSide)
            # win
            spp = args.enpp + args.s2 * args.atr
            spp = round(spp, ROUND_AT[args.symbol])
            rsp = client.new_order( # close position
                symbol=args.symbol, side='SELL', type='LIMIT', price=spp,
                newClientOrderId=f'{args.stgname}_long_win_{args.long_id}',
                quantity=args.vol, positionSide=pSide)
            args.mp = 1
        # short
        pSide = 'SHORT'
        if args.mp == 0 and no - args.dnn.value > range_t:
            trade_cnt += 1
            args.short_id = client.new_order( # close position
                symbol=args.symbol, side='SELL', type='MARKET',
                newClientOrderId=f'{args.stgname}_short_open_{message["E"]}',
                quantity=args.vol, positionSide=pSide)['orderId']
            args.enpp = no
            # loss
            spp = args.enpp + args.s1 * args.atr.value
            spp = round(spp, ROUND_AT[args.symbol])
            rsp = client.new_order( # close position
                symbol=args.symbol, side='BUY', type='STOP',
                price=spp, stopPrice=spp,
                newClientOrderId=f'{args.stgname}_short_loss_{args.short_id}',
                quantity=args.vol, positionSide=pSide)
            # win
            spp = args.enpp - args.s2 * args.atr
            spp = round(spp, ROUND_AT[args.symbol])
            rsp = client.new_order( # close position
                symbol=args.symbol, side='SELL', type='LIMIT', price=spp,
                newClientOrderId=f'{args.stgname}_close_win_{args.long_id}',
                quantity=args.vol, positionSide=pSide)
            args.mp = -1
        # calculate the market-position
        if args.mp != 0:
            # long 
            nl = float(kline['l'])
            nh = float(kline['h'])
            spp = args.enpp - args.s1 * args.atr.value
            spp = round(spp, ROUND_AT[args.symbol])
            if args.mp > 0 and nl <= spp: # 止损
                mp = 0
            spp = args.enpp + args.s2 * args.atr.value
            spp = round(spp, ROUND_AT[args.symbol])
            if args.mp > 0 and nh >= spp: # 止盈
                mp = 0
            # short
            spp = args.enpp + args.s1 * args.atr.value
            spp = round(spp, ROUND_AT[args.symbol])
            if mp < 0 and nh >= spp: # 止损
                mp = 0
            spp = args.enpp - args.s2 * args.atr.value
            spp = round(spp, ROUND_AT[args.symbol])
            if mp < 0 and nl <= spp: # 止盈
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0

    if etype == 'ORDER_TRADE_UPDATE':
        order = message['o']
        if order['i'] == args.long_id and order['l'] != '0':
            trade_cnt += 1
            vol = int(order['l'])
            # loss
            spp = float(order['p']) - args.s1 * args.atr
            spp = round(spp, ROUND_AT[args.symbol])
            rsp = client.new_order( # close position
                symbol=args.symbol, side='SELL', type='STOP',
                price=spp, price=spp,
                newClientOrderId=f'{args.stgname}_loss_{args.long_id}_{len(args.long_loss)}',
                quantity=vol, positionSide='LONG')
            args.long_loss[rsp['orderId']] = vol
            # win
            spp = float(order['p']) + args.s2 * args.atr
            spp = round(spp, ROUND_AT[args.symbol])
            rsp = client.new_order( # close position
                symbol=args.symbol, side='SELL', type='LIMIT', price=spp,
                newClientOrderId=f'{args.stgname}_win_{args.long_id}_{len(args.long_win)}',
                quantity=vol, positionSide='LONG')
            args.long_win[rsp['orderId']] = vol
        if order['i'] == args.short_id and order['l'] != '0':
            vol = int(order['l'])
            # loss
            spp = float(order['p']) + args.s1 * args.atr
            spp = round(spp, ROUND_AT[args.symbol])
            rsp = client.new_order( # close position
                symbol=args.symbol, side='BUY', type='STOP',
                price=spp, stopPrice=spp,
                newClientOrderId=f'{args.stgname}_loss_{args.short_id}_{len(args.long_loss)}',
                quantity=vol, positionSide='SHORT')
            args.short_loss[rsp['orderId']] = vol
            # win
            spp = float(order['p']) - args.s2 * args.atr
            spp = round(spp, ROUND_AT[args.symbol])
            rsp = client.new_order( # close position
                symbol=args.symbol, side='BUY', type='STOP', price=spp,
                newClientOrderId=f'{args.stgname}_win_{args.long_id}_{len(args.long_win)}',
                quantity=vol, positionSide='SHORT')
            args.short_win[rsp['orderId']] = vol


if __name__ == "__main__":
    # 网格策略
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--', '-u', type=float, required=True)
    parser.add_argument('--vol', '-v', type=int, default=1)
    parser.add_argument('--stgname', type=str, default='grid')
    args = parser.parse_args()
    # args infer
    assert '_' not in args.stgname, '"_" is not allowed to include in the stgname'
    # global
    api_key, private_key = get_auth_keys()
    client = CoinM(
        api_key=api_key,
        private_key=private_key,
    )
    # create wedsocket stream client
    wscli = CoinMWSSStreamClient(
        on_open=on_open,
        on_close=on_close,
        on_message=on_message)
    # wscli.book_ticker(args.symbol)
    # 需要在挂单前注册on_message
    listen_key = client.new_listen_key()['listenKey']
    wscli.user_data(listen_key)
    wscli.kline(args.symbol, interval='1m')
    # update the listenKey
    while True:
        time.sleep(3599)
        client.renew_listen_key(listen_key)
