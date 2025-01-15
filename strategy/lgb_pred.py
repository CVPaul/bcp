#!/usr/bin/env python
#-*- coding:utf-8 -*-


# 说明：已经尝试过wss订阅kline,但是延迟不是一般的高，根本不是250ms,所以考虑for循环


import os
import time
import json
import argparse
import numpy as np
import pandas as pd
import lightgbm as lgb

from binance.fut.coinm import CoinM
from binance.fut.unicm import UniCM
from binance.constant import ROUND_AT


def rolling_slope_vectorized(data, window):
    """
    向量化计算滚动窗口的斜率
    """
    x = np.arange(window)
    x_mean = np.mean(x)
    denominator = np.sum((x - x_mean)**2)

    # 滑动窗口计算每个窗口的均值
    y_cumsum = np.cumsum(data).values
    y_cumsum = np.concatenate(([0], y_cumsum))  # 防止索引越界
    y_mean = (y_cumsum[window:] - y_cumsum[:-window]) / window

    # 滑动窗口计算 Σ(y_i * x_i) 和 Σ(y_i)
    xy_cumsum = np.cumsum(data * np.tile(x, len(data) // len(x) + 1)[:len(data)]).values
    xy_cumsum = np.concatenate(([0], xy_cumsum))  # 防止索引越界
    xy_mean = (xy_cumsum[window:] - xy_cumsum[:-window]) / window

    # 计算斜率
    slopes = (xy_mean - x_mean * y_mean) / denominator
    return np.concatenate([[np.nan] * (window - 1), slopes])


def feature_engine(df_1m, df_8h):
    day_period = '8h'
    origin_colums = set(df_1m.columns) | set(['date'])
    # ATR
    df_8h['prev_close_price'] = df_8h.close_price.shift(1)
    df_8h['HL'] = df_8h.high_price - df_8h.low_price
    df_8h['HC'] = (df_8h.high_price - df_8h.prev_close_price).abs()
    df_8h['LC'] = (df_8h.low_price - df_8h.prev_close_price).abs()
    df_8h['TR'] = pd.concat([df_8h.HL, df_8h.HC, df_8h.LC], axis=1).max(axis=1)
    df_8h['ATR'] = df_8h.TR.rolling(20).mean().dropna().shift(1)
    # for p in [30, 60]:
    #     df_1m[f"upp-{p}"] = df_1m.high_price.rolling(p).max().shift(1)
    #     df_1m[f"dnn-{p}"] = df_1m.low_price.rolling(p).min().shift(1)
    #     df_1m[f"rng-{p}"] = df_1m[f"upp-{p}"] - df_1m[f"dnn-{p}"]
    # join
    df_1m['date'] = df_1m.index.floor(day_period)
    df = df_1m.join(df_8h, on='date', rsuffix=f'_{day_period}')
    # # break
    # for i, v in enumerate([0.1, 0.3, 0.9, 2.0, 3.0]):
    #     df[f'long-break{i}'] = df.open_price >= df.MA + v * df.ATR
    #     df[f'short-break{i}'] = df.open_price <= df.MA - v * df.ATR
    # # flip
    # for i, v in enumerate([0.1, 0.3, 0.9, 2.0, 3.0]):
    #     for p in [30, 60]:
    #         df[f'long-flip{i}/{p}'] = df.open_price <= df[f'upp-{p}'] - v * df.ATR
    #         df[f'short-flip{i}/{p}'] = df.open_price >= df[f'dnn-{p}'] + v * df.ATR
    # slope
    df[f'slope-30'] = rolling_slope_vectorized(df.close_price, 30)
    df[f'slope-30'] = df[f'slope-30'].shift(1)
    for i in range(2): # add more weight to slope-30
        df[f'slope-30.{i}'] = df[f'slope-30']
    # return
    for w in [1, 2, 3, 5, 15, 30, 60, 120, 240]:
        df[f'his-ret-{w}'] = df.close_price.pct_change(w).shift(1)
    # labels
    for w in [1, 2, 3, 5, 15, 30, 60, 120, 240]:
        df[f'label-ret-{w}'] = df.close_price.pct_change(w).shift(-w)
    # prices after labels
    base = df.pop(f'open_price_{day_period}')
    for c in df.columns:
        if 'price' in c:
            df[f'r_{c}'] = df.pop(c).shift(1) / base - 1.0
    # =====================================================================
    label_cols = [c for c in df.columns if c.startswith('label')]
    feat_cols = [c for c in df.columns if c not in origin_colums and c not in label_cols]
    return df, feat_cols, label_cols


def load_api_keys():
    path = f'{os.getenv("HOME")}/.vntrader/connect_unifycm.json'
    with open(path, 'r') as f:
        config = json.load(f)
        api_key = config['API Key']
        private_key = config['API Secret']
        if os.path.exists(private_key):
            with open(private_key, 'r') as f:
                private_key = f.read().strip()
    return api_key, private_key


def load_bar(cli, symbol, period, length, endTime=None): # online required endtime=None
    df = cli.klines(
        symbol, period, endTtime=endTime, limit = length)
    df = pd.DataFrame(
        df, columns=[
            'start_t', 'open_price', 'high_price', 'low_price', 'close_price',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ]).astype(float)
    df['datetime'] = pd.to_datetime(df.start_t, unit='ms')
    return df.set_index('datetime')


def load_model():
    with open('lgb_config.json', 'r') as fp:
        config = json.load(fp)
        model = lgb.Booster(model_file=config['path'])
    return model, config


if __name__ == "__main__":
    # 网格策略
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--length-1m', '-l1', type=int, default=240)
    parser.add_argument('--length-8h', '-l8', type=int, default=20)
    args = parser.parse_args()
    # global
    api_key, private_key = load_api_keys()
    client = UniCM(
        api_key=api_key,
        private_key=private_key,
    )
    mdcli = CoinM(
        api_key=api_key,
        private_key=private_key,
    )
    # init session params
    df_8h = load_bar(mdcli, args.symbol, '8h', args.length_8h + 2)
    # init bar params
    df_1m = load_bar(mdcli, args.symbol, '1m', args.length_1m + 2)
    # feature engineering
    df, _, _ = feature_engine(df_1m, df_8h.shift(1))
    # load model
    model, config = load_model()
    df_8h.to_csv('8h.csv')
    df_1m.to_csv('1m.csv')
    # predict
    df['pred'] = model.predict(df[config['features']])
    df.to_csv('feature.csv')
    print('result saved to feature.csv')
