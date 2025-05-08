#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import ast
import sys
import glob
import numba
import numpy as np
import pandas as pd

from strategy.data.utils import load
from strategy.indicator.common import ATR, MA, UPP, DNN
from strategy.strategy.store import(
    break_atr, break_atr3, break_fix, break_float)


def data_process(raw, period = 8 * 3600000, length=20):
    # 8 hours # DAY_MS_COUNT
    df = raw#.iloc[-1440*90:].copy()
    df = df.reset_index(drop=True)
    df['gid'] = df.start_t // period
    gdf = df.groupby('gid').agg({
        'gid': 'first',
        'open':'first', 'high':'max', 'low':'min', 'close':'last'})
    atr = ATR(length).calc(gdf).to_frame('atr').shift(1)
    atr['gid'] = gdf.gid
    # atr['ma'] = MA(short).calc(gdf)
    # df = df.join(tr, on='gid', rsuffix='_x')
    df = df.join(atr, on='gid', rsuffix='_x')
    # df['upp'] = round(df.ma + k * df.atr, 5)
    # df['dnn'] = round(df.ma - k * df.atr, 5)
    # df = df.dropna()
    print('valid data shape:', df.shape)
    return df


def trans2pnl(trans, param, fee):
    if len(trans[0]) == 5:
        columns = ['pos', 'open', 'close', 'entt', 'close_t']
    elif len(trans[0]) == 7:
        columns = ['pos', 'open', 'close', 'entt', 'close_t', 'hpp', 'lpp']
    else:
        raise ValueError('trans.shape[1] not in (5,7)')
    rcd = pd.DataFrame(trans, columns=columns)
    profit = rcd.pos * (rcd.close - rcd.open)
    commis = rcd.pos.abs() * (rcd.close + rcd.open) * fee
    res = (profit - commis) / rcd.open
    pnl = res.sum()
    s = 1 + res.cumsum()
    u = s.expanding(min_periods=1).max()
    win = (res > 0).sum()
    mdd = ((u - s) / u).max()
    if param:
        res.cumsum().plot(title=f"param:{param}, pnl={pnl:.4f})")
        res.index = rcd.entt
        return res, rcd, win / res.shape[0], res.shape[0]
    return pnl, mdd, win / res.shape[0], res.shape[0]


def buy_and_hold(df):
    open_p = df.open[0]
    close_p = df.close.values[-1]
    open_t = pd.to_datetime(df.start_t[0] * 1e6)
    close_t = pd.to_datetime(df.start_t.values[-1] * 1e6)
    pnl = close_p / open_p - 1.0
    mdd = df.high.expanding(min_periods=1).max()
    hpp = mdd.max()
    mdd = ((mdd - df.low) / mdd).max()
    print(
        f'baseline(buy&hold): pnl={pnl:.4f}, mdd={mdd:.6f}, open={open_p}@{open_t.date()}, '
        f'close={close_p}@{close_t.date()}, hpp={hpp}')


def main(len_idx):
    filename = sys.argv[1]
    with open(filename) as fp:
        content = fp.readlines()
    basename = os.path.basename(filename)
    tokens = basename.split('.')
    # infer symbol
    symbol = tokens[0].upper()
    symbol = f'{symbol}USD_PERP'
    # infer strategy
    if tokens[1].startswith('stable'):
        stg = break_atr3
    elif tokens[1] == 'fix':
        stg = break_fix
    elif tokens[1] == 'float':
        stg = break_float
    raw = load(symbol, 'data')
    df = data_process(raw)
    buy_and_hold(df)
    tag = 'best:'
    for line in content:
        if not line.startswith(tag):
            continue
        param = ast.literal_eval(line.split(tag)[1].strip())
        df['upp'] = df.high.rolling(param[len_idx]).max()
        df['dnn'] = df.low.rolling(param[len_idx]).min()
        trans = stg(df[[
                "start_t", "open", "high",
                "low", "close", "upp", "dnn", "atr"]].values, *param[len_idx:])
        pnl, mdd, win, count = trans2pnl(trans, param, 0.0002)
        print(
            f'pnl={pnl.sum()}, win={win}, trade_cnt={count}, '
            f'long_cnt={(mdd.pos > 0).sum()}, short_cnt={(mdd.pos < 0).sum()}')
    # print(pnl.cumsum().tolist())
    # mdd.entt =  pd.to_datetime(mdd.entt * 1e6)
    # mdd.close_t =  pd.to_datetime(mdd.close_t * 1e6)
    # print(mdd.head(60))



if __name__ == "__main__":
    main(int(sys.argv[2]))

