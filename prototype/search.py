#!/usr/bin/env python
#-*- coding:utf-8 -*-


import numpy as np
import pandas as pd

from prototype.tend import ma_atr
from tools.data.store import get_kline
from strategy.indicator.common import ATR


def load_data(symbol):
    df = get_kline(symbol, 60)
    df['ma7'] = df['close'].rolling(7).mean()
    df['atr'] = ATR(24).calc(df) 
    df['sig'] = df['ma7'] / df['atr']
    return df


def calc(trans):
    gross = trans.pos * trans.price.diff().shift(1)
    commi = trans.pos.diff().abs() * trans.price * 5e-4
    netvl = (gross - commi).fillna(0).cumsum()
    net = netvl.iloc[-1]
    mdd = (netvl.expanding().max() - mdd).max()
    win_ratio = (netvl > 0).sum() / netvl.shape[0]
    return net, mdd, win_ratio


def main(symbol, cond_len, use_atr):
    last = 0
    df = load_data(symbol)
    for k in np.arange(0.01, 0.2, 0.01):
        for s1 in np.arange(0.01, 0.2, 0.01):
            for s2 in np.arange(0.01, 0.2, 0.01):
                trans = ma_atr(df, k, s1, s2, cond_len, use_atr)
                pnl, mdd, win = calc(
                    pd.DataFrame(trans, columns=['pos', 'price', 'type']))
                if pnl > last:
                    last = pnl
                    records = np.array([k, s1, s2, pnl, mdd, win])
                    print(records.round(4))


if __name__ == "__main__":
    main('ETHUSDT', 2, True)
