#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import sys
import json
import gzip
import struct
import argparse
import pandas as pd

from state import generate
from state import TickReader
from binance.constant import ROUND_AT
from tools.data.constant import ORDER_BIN, ORDER_KEY, ORDER_VAL


class Order:

    def __init__(self, side, price, dnn, upp):
        self.price = price
        self.dnn = dnn
        self.upp = upp
        self.side = side
        self.status = 0

    def update(self, ask, bid):
        if self.status != 0:
            return False
        if (self.side == 1 and ask >= self.upp) or \
                (self.side == -1 and bid <= self.dnn):
            self.status = 1 # profit
            return True
        if (self.side == 1 and bid <= self.dnn) or \
                (self.side == -1 and ask >= self.upp):
            self.status = -1 # loss
            return True
        return False


class OrderManager:

    def __init__(self):
        self.orders = []
        self.new_orders = set()
        self.trd_orders = set()

    def new_order(self, side, price, dnn, upp):
        self.new_orders.add(len(self.orders))
        self.orders.append(Order(side, price, dnn, upp))
    
    def update(self, last_mprice, ask, bid):
        trd_orders = set()
        for i in self.new_orders:
            if self.orders[i].update(ask, bid):
                trd_orders.add(i)
        self.new_orders -= trd_orders
        self.trd_orders |= trd_orders
        if len(trd_orders) > 0:
            self.summary()
        reward = 0
        for i in trd_orders:
            o = self.orders[i]
            if o.status == 1:
                gain = o.upp - o.price if o.side == 1 else o.price - o.dnn
                comm = o.upp + o.price if o.side == 1 else o.price + o.dnn
            elif o.status == -1:
                gain = o.dnn - o.price if o.side == 1 else o.price - o.upp
                comm = o.dnn + o.price if o.side == 1 else o.price + o.upp
            else:
                print(f"BUG: traded order's status is not [-1, 1] but {o.status}")
            reward += (gain - comm * 0.0005)
        return reward

    def summary(self):
        res = {}
        res["n_open"] = len(self.new_orders)
        res["n_trade"] = len(self.trd_orders)
        res["n_win"] = sum([self.orders[i].status == 1 for i in self.trd_orders])
        res["n_loss"] = res['n_trade'] - res['n_win']
        res["profit"] = sum([self.orders[i].status * 0.01 for i in self.trd_orders])
        res['win-ratio'] = f"{res['n_win'] * 100 / res['n_trade']:.2f}%"
        print(res)

    def position(self):
        pos = 0
        for i in self.new_orders:
            pos += self.orders[i].side
        return pos


class TradeEnv:

    def __init__(self, symbol, files, gap, threshold, histlen):
        self.sequence = generate(files, gap) 
        print('sequence length:', len(self.sequence))
        self.threshold = threshold
        self.round_at = ROUND_AT[symbol]
        self.histlen = histlen

    def reset(self):
        # self.data = TickReader(files) 
        # self.om = OrderManager()
        self.pos = self.histlen
        self.position = 0
        next_market = [self.sequence[i][0] for i in range(self.pos - self.histlen, self.pos)]
        next_status = next_market + [next_market[i] - next_market[i-1] for i in range(1, len(next_market))]
        next_status.append(self.position)
        return next_status


    def step(self, action):
        self.pos += 1
        next_market = [self.sequence[i][0] for i in range(self.pos - self.histlen, self.pos)]
        # next hold
        # if self.last_message and action:
        #     price = self.last_message['a'] if action == 1 else self.last_message['b'] 
        #     self.om.new_order(
        #         action, price, round(price * (1 - self.threshold), self.round_at),
        #         round(price * (1 + self.threshold), self.round_at))
        pos_diff = action - self.position
        self.position = action
        #for tick in self.data:
        #    message = dict(zip(ORDER_KEY, tick))
        #    # reward += self.om.update(message['a'], message['b'])
        #    if message["u"] == self.sequence[self.pos][1]:
        #        self.last_message = message
        #        break
        #midprice = 0.5 * (message['a'] + message['b'])
        gross = self.position * (self.sequence[self.pos][2] - self.sequence[self.pos-1][2])
        fee = abs(pos_diff) * 0.0005 * (self.sequence[self.pos][2] + self.sequence[self.pos-1][2])
        # print(action, gross, fee)
        next_status = next_market + [next_market[i] - next_market[i-1] for i in range(1, len(next_market))]
        next_status.append(self.position)
        return next_status, gross - fee, self.pos >= len(self.sequence) - 1

