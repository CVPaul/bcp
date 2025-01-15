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


# logging
logging.basicConfig(
    filename='trend.log', level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
# global
ROUND_AT = {
    "DOGEUSD_PERP": 5,
}

# strategy construct
k = 1.0
length = 150
interval = 300000 # 300000 # 5m


def on_message(self, message):
    pos = 1 # 每次开/平仓的数量
    global B, last_trade_action
    global side, dnn, upp, hpp, lpp, last_kline
    global trade_cum_period, trade_cum_count_per_1m

    message = json.loads(message)
    if trade_cum_count_per_1m > 10: # 1 分钟交易超过10次，异常直接停止策略
        event_t = message.get('E', trade_cum_period)
        if event_t - trade_cum_period > 600000: # 每10分钟打印一次：
            trade_cum_period = event_t
            logging.error('strategy error: trade exceeded 10 time per minutes!')
        return
    etype = message.get('e', '')
    # if message.get('E', listen_time) - listen_time >= 50 * 300000: # 50min
    #     rsp = client.renew_listen_key(listen_key)
    #     logging.info(f'renew listenKey with rsp={rsp}')

    if etype == 'bookTicker':
        trade_cnt = 0
        ask_p = float(message['a'])
        bid_p = float(message['b'])
        hpp = max(hpp, ask_p)
        lpp = min(lpp, bid_p)
        # 先平仓，这样可以处理开仓的时候需要反手的问题
        spp = max(hpp * (1 - B), dnn) # 先达到哪个就止损那个，如果是dnn就是反手
        if side > 0 and bid_p <= spp:
            rsp = client.new_order(
                symbol=symbol, side='SELL', type='MARKET',
                quantity=pos, positionSide='LONG')
            logging.info(
                f'ORDER[SELL/CLOSE] close previous '
                f'order[side({side}:bid_p({ask_p} <= spp({spp})|dnn({dnn})] with rsp={rsp}')
            side = 0
            trade_cnt += 1
            last_trade_action = 1
        spp = min(lpp * (1 + B), upp) # 先达到哪个就止损那个，如果是upp就是反手
        if side < 0 and ask_p >= spp:
            rsp = client.new_order(
                symbol=symbol, side='BUY', type='MARKET',
                quantity=pos, positionSide='SHORT')
            logging.info(
                f'ORDER[BUY/CLOSE] close previoud '
                f'order[side({side}):ask_p({ask_p} >= spp({spp})|upp({upp})] with rsp={rsp}')
            side = 0
            trade_cnt += 1
            last_trade_action = -1

        if last_trade_action == 1 and bid_p <= atr.value:
            last_trade_action = 0
        if last_trade_action == -1 and ask_p >= atr.value:
            last_trade_action = 0
        # 开仓 
        if last_trade_action != 1 and side <= 0 and ask_p >= upp:
            rsp = client.new_order(
                symbol=symbol, side='BUY', type='MARKET',
                quantity=(1 - side)*pos, positionSide='LONG')
            logging.info(
                f'ORDER[BUY/OPEN] create new order[ask_p({ask_p}) >= upp({upp})] '
                f'with side({side}->0) and rsp={rsp}')
            side = 1
            trade_cnt += 1
            hpp = lpp = ask_p
        if last_trade_action != -1 and side >= 0 and bid_p <= dnn:
            rsp = client.new_order(
                symbol=symbol, side='SELL', type='MARKET',
                quantity=(1 + side)*pos, positionSide='SHORT')
            logging.info(
                f'ORDER[SELL/OPEN] create new order[bid_p({bid_p} <= dnn({dnn})] '
                f'with side({side}->0) and rsp={rsp}')
            side = -1
            trade_cnt += 1
            hpp = lpp = bid_p
        n_min = message['E'] // 60000
        if trade_cum_period == n_min: #
            trade_cum_count_per_1m += trade_cnt
        else:
            trade_cum_period = n_min 
            trade_cum_count_per_1m = trade_cnt
        
    if etype == 'kline':
        kline = message['k']
        if kline['t'] < last_kline['t']:
            return # recived the old message
        if kline['t'] != last_kline['t']:
            t = last_kline['t']
            o = float(last_kline['o'])
            h = float(last_kline['h'])
            l = float(last_kline['l'])
            c = float(last_kline['c'])
            s = ma.update(c)
            a = atr.update(h, l, c)
            B = a / c
            upp = round(s + k * a, ROUND_AT[symbol])
            dnn = round(s - k * a, ROUND_AT[symbol])
            logging.info(
                f'UPDATE,t={t},o={o},h={h},l={l},c={c},ma={s},atr={a},upp={upp},dnn={dnn}')
        last_kline = kline # 这里必须是if etype == 'kline'之外


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument(
        '--last-trade-action', '-a', type=int, default=0,
        help='0: 追高/低，1: 不追高，-1: 不追低')
    args = parser.parse_args()
    # global
    symbol = args.symbol # 'DOGEUSD_PERP'
    api_key, private_key = get_auth_keys()
    client = CoinM(
        api_key=api_key,
        private_key=private_key,
    )

    # 如果距离下一根k线不足5s的话，就等到下一根k线过后至少5秒
    if interval - client.time()['serverTime'] % interval <= 5000: 
        logging.warning('>>> 距离下一根k线不足5s, 需等待10s...')
        time.sleep(10)
        logging.warning('>>> 等待结束!')
    
    df = client.klines(symbol, f'{interval // 60000}m', limit = length + 2)
    last_kline = {'t': df[-1][0], 'c': df[-1][4]}
    df = df[:-1] # 最后一根kline是不完整的
    df = pd.DataFrame(
        df, columns=[
            'start_t', 'open', 'high', 'low', 'close',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ]).astype(float)
    ma = MA(args.length, df)
    atr = ATR(args.length, df)

    s = ma.value
    a = atr.value
    B = a / float(last_kline['c'])
    last_trade_action = args.last_trade_action

    trade_cum_period = 0
    trade_cum_count_per_1m = 0

    side, hpp, lpp = 0, 0, 1e8
    upp = round(s + k * a, ROUND_AT[symbol])
    dnn = round(s - k * a, ROUND_AT[symbol])

    # subscribe streams before any order send 
    # listen_key = client.new_listen_key()['listenKey']
    # listen_time = client.time()['serverTime']
    # create wedsocket stream client
    wscli = CoinMWSSStreamClient(
        on_open=on_open,
        on_close=on_close,
        on_message=on_message)
    wscli.kline(symbol, f'{interval // 60000}m')
    wscli.book_ticker(symbol)
    # wscli.user_data(listen_key)
