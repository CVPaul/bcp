#!/usr/bin/env python
#-*- coding:utf-8 -*-


import json
import logging
import argparse

from binance.fut.unicm import CoinM
from binance.constant import ROUND_AT
from strategy.common.utils import get_auth_keys
from strategy.common.utils import on_open, on_close
from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient


class KLineRobinQueue:
    def __init__(self, interval, maxlen): # ms
        self.maxlen = maxlen
        self.interval = interval
        self.pos = 0
        self.last_pos = 0
        # start_t, open, high, low, close
        self.queue = [[0, 0, 0, 0, 0]] * self.maxlen
    
    def update(self, timestamp, price):
        st = timestamp // self.interval
        kl = self.queue[self.pos]
        is_new = False
        if st == kl[0]:
            if kl[2] < price:
                kl[2] = price
            if kl[3] > price:
                kl[3] = price
            kl[4] = price # latest price
        else:
            self.pos = (self.pos + 1) % self.maxlen
            self.queue[self.pos] = [
                st, price, price, price, price]
            is_new = True
        return is_new
    
    def ready(self):
        return self.queue[0][4] != 0
    
    def gap(self):
        lpp, hpp = 1e8, 0
        for kline in self.queue:
            if kline[2] > hpp:
                hpp = kline[2]
            if kline[3] < lpp:
                lpp = kline[3]
        return hpp, lpp


class FakeClient:

    def __init__(self, *args, **kw):
        logging.info(f'create fake cli with: args={args}, kw={kw}')

    def new_order(self, *args, **kw):
        logging.info(f'fake cli new order with: args={args}, kw={kw}')


lut = 0
last_long_open_time = 0
last_short_open_time = 0

def on_message(self, message):
    global krq, args, lut
    global trade_cum_period, trade_cum_count_per_1m
    global last_long_open_time, last_short_open_time

    message = json.loads(message)
    if trade_cum_count_per_1m > 10: # 1 分钟交易超过10次，异常直接停止策略
        event_t = message.get('E', trade_cum_period)
        if event_t - trade_cum_period > 600000: # 每10分钟打印一次：
            trade_cum_period = event_t
            logging.error('strategy error: trade exceeded 10 times per minutes!')
        return
    etype = message.get('e', '')

    if etype == 'bookTicker':
        trade_cnt = 0
        ask_p = float(message['a'])
        bid_p = float(message['b'])
        args.hpp = max(args.hpp, ask_p)
        args.lpp = min(args.lpp, bid_p)
        mid_p = 0.5 * (bid_p + ask_p) # round可能会导致bid_p < mid_p < ask_p不成立
        krq.update(message['E'], mid_p)
        # strategy::main
        # close postion first
        if args.stopi < len(args.stop_ratio) - 1 and args.side != 0:
            profit_S = args.stop_ratio[args.stopi + 1] - args.stop_ratio[1] 
            if args.side == 1 and ask_p >= args.enpp * (1 + profit_S):
                args.stopi += 1
            if args.side == -1 and bid_p <= args.enpp * (1 - profit_S):
                args.stopi += 1
        S = args.stop_ratio[args.stopi] - args.stop_ratio[args.stopi - 1]
        if args.side == 1 and bid_p <= args.hpp * (1 - S):
            client.new_order(
                symbol=args.symbol, side='SELL', type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.vol, positionSide='LONG')
            args.side = 0
            args.stopi = 1 # notation, this is start with 1
            trade_cnt += 1
            logging.info(
                f'ORDER[SELL/LONG] close position, enpp={args.enpp}, '
                f'pos={args.vol}, close={bid_p}, args.hpp={args.hpp}')  
        if args.side == -1 and ask_p >= args.lpp * (1 + S):
            client.new_order(
                symbol=args.symbol, side='BUY', type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.vol, positionSide='SHORT')
            args.side = 0
            args.stopi = 1 # notation, this is start with 1
            trade_cnt += 1
            logging.info(
                f'ORDER[BUY/SHORT] close postions, enpp={args.enpp}, '
                f'pos={args.vol}, close={bid_p}, args.lpp={args.lpp}')
        # open positions 
        if args.side == 0 and not krq.ready():
            return # not ready: do nothing and return
        hpp, lpp = krq.gap()
        cond = [
            message["E"] >= last_long_open_time + args.interval,
            ask_p >= hpp and (ask_p - lpp) / lpp > args.break_ratio,
        ]
        if args.side == 0 and cond[0] and cond[1]: # 区间内上涨 
            client.new_order(
                symbol=args.symbol, side='BUY', type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.vol, positionSide='LONG')
            args.side = 1
            trade_cnt += 1
            last_long_open_time = message["E"]
            args.enpp = args.hpp = args.lpp = ask_p
            logging.info(
                f'ORDER[BUY/LONG] create new order, enpp={args.enpp}, '
                f'lpp={lpp:.5f}, hpp={hpp:.5f}')
        cond = [
            message["E"] >= last_short_open_time + args.interval,
            bid_p <= lpp and (hpp - bid_p) / hpp > args.break_ratio,
        ]
        if args.side == 0 and cond[0] and cond[1]: # 区间内下跌
            client.new_order(
                symbol=args.symbol, side='SELL', type='MARKET',
                newClientOrderId=f'{args.stgname}_{message["E"]}',
                quantity=args.vol, positionSide='SHORT')
            args.side = -1
            trade_cnt += 1
            last_short_open_time = message["E"]
            args.enpp = args.hpp = args.lpp = bid_p
            logging.info(
                f'ORDER[SELL/SHORT] create new order, enpp={args.enpp}, '
                f'lpp={lpp:.5f}, hpp={hpp:.5f}') 
        # print somte regular info
        if message['E'] - lut > 60000: # 1min
            logging.info(
                f'ragular info(1m): hpp={hpp} lpp={lpp} mid_p={mid_p} --enpp {args.enpp} '
                f'--side={args.side} --hpp={args.hpp} --lpp={args.lpp} --stopi {args.stopi} ')
            lut = message['E']
        
        n_min = message['E'] // 60000
        if trade_cum_period == n_min: #
            trade_cum_count_per_1m += trade_cnt
        else:
            trade_cum_period = n_min
            trade_cum_count_per_1m = trade_cnt

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--hpp', type=float, default=1e8)
    parser.add_argument('--lpp', type=float, default=0)
    parser.add_argument('--enpp', type=float, default=0)
    parser.add_argument('--vol', type=int, default=1)
    parser.add_argument('--side', type=int, default=0)
    parser.add_argument('--stopi', type=int, default=1)
    parser.add_argument('--break-ratio', '-B', type=float, default=0.01)
    parser.add_argument('--stop-ratio', '-S', type=str, default='0.01')
    parser.add_argument('--length', '-l', type=int, default=60)
    parser.add_argument('--interval', '-i', type=int, default=1000) # ms
    parser.add_argument('--stgname', type=str, default='shot')
    # args parser
    args = parser.parse_args()
    vals = [0]
    for tok in args.stop_ratio.split(','):
        vals.append(vals[-1] + float(tok))
    args.stop_ratio = vals
    # logging
    logging.basicConfig(
        filename=f'shot.{args.stgname}.log', level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    # build chart
    krq = KLineRobinQueue(args.interval, args.length + 1)
    # global
    api_key, private_key = get_auth_keys()
    # client = FakeClient(
    client = CoinM(
        api_key=api_key,
        private_key=private_key,
    )
    logging.info(
        f'start shot strategy: --symbol={args.symbol} --hpp={args.hpp} --lpp={args.lpp} '
        f'--enpp={args.enpp} --vol={args.vol} --side={args.side} -B {args.break_ratio} '
        f'-S={args.stop_ratio} --l={args.length}, -i={args.interval}, --stgname={args.stgname}')
    trade_cum_period = 0
    trade_cum_count_per_1m = 0
    # create wedsocket stream client
    wscli = CoinMWSSStreamClient(
        on_open=on_open,
        on_close=on_close,
        on_message=on_message)
    wscli.book_ticker(args.symbol)
