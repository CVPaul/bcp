#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import sys
import json
import gzip
import struct
import argparse
import pandas as pd

from binance.constant import ROUND_AT
from tools.data.constant import ORDER_BIN, ORDER_KEY, ORDER_VAL


class Reader(object):

    def __init__(self):
        pass

    def read(self, filename):
        raise NotImplementedError("implement your own read here!")


class TickReader(object):

    def __init__(self, files):
        super().__init__()
        self.files = files
        self.data_size = struct.calcsize(ORDER_BIN)

    def __iter__(self):
        for filename in self.files:
            with gzip.open(filename, 'rb') as fp:
                yield from struct.iter_unpack(ORDER_BIN, fp.read())


class Recorder:

    def __init__(self, symbol, gap):
        self.symbol = symbol
        self.round_at = ROUND_AT[symbol]
        self.last_close = 0
        self.last_open = 0
        self.last_side = 0
        self.gap = gap
    
    def step(self, a, b):
        m = 0.5 * (a + b)
        if self.last_open == 0:
            self.last_open = m
        if self.last_close == 0:
            self.last_close = m
        span = self.last_close * self.gap
        action, price = 0, m
        if self.last_side == 1:
            if a >= self.last_close + span:
                action = 1
                self.last_open = self.last_close
                self.last_close += span
            if b <= self.last_open - span:
                action = -1
                self.last_side = -1
                self.last_close = self.last_open - span
        elif self.last_side == -1:
            if b <= self.last_close - span:
                action = -1
                self.last_open = self.last_close
                self.last_close -= span
            if a >= self.last_open + span:
                action = 1
                self.last_side = 1
                self.last_close = self.last_open + span
        else: # side = 0
            if a >= self.last_close + span:
                action = 1
                self.last_side = 1
                self.last_close += span
            if b <= self.last_close - span:
                action = -1
                self.last_side = -1
                self.last_close -= span
        self.last_open = round(self.last_open, self.round_at)
        self.last_close = round(self.last_close, self.round_at)
        return action


def generate(files, gap):
    symbol = files[0].split('.')[1]
    rcd = Recorder(symbol, gap)
    # load data
    sequence, ids = [], set()
    for tick in TickReader(files):
        message = dict(zip(ORDER_KEY, tick))
        assert message['u'] not in ids, 'unique check failed!'
        ids.add(message['u'])
        action = rcd.step(message['a'], message['b'])
        if action:
            m = 0.5 * (message['a'] + message['b'])
            sequence.append([action, message['u'], m])
    return sequence


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-files', nargs='+', type=str, required=True)
    parser.add_argument('--gap', type=float, default=0.005)
    # args parser
    args = parser.parse_args()
    # symbol
    print(len(generate(args.data_files, args.gap)))

