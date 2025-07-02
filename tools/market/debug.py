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
from prototype.v3 import get_feat, get_signal


def get_data(args, cli, start_time): # no try needed
    start_time = pd.to_datetime(str(start_time))
    start_time = start_time.timestamp() * 1000
    data = cli.klines(args.symbol, "1h", startTime=int(start_time))
    return pd.DataFrame(
        data, columns=[ # drop the last data[-1]
            'start_t', 'open', 'high', 'low', 'close',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ]).astype(float) 


def main(args):
    # args infer
    api_key, private_key = load_api_keys(args.account)
    if args.is_um:
        cli = USDM(api_key=api_key, private_key=private_key)
    else:
        cli = CoinM(api_key=api_key, private_key=private_key)
    # trade logic
    data = get_data(args, cli, args.start_time)
    start_pos = max(args.atr_window + 1, args.his_window) + args.shift - 1
    assert start_pos <= data.shape[0]
    data = get_feat(data, args.atr_window, args.his_window)
    if args.shift:
        data['ATR'] = data['ATR'].shift(1)
    data['side'] = 0
    atr_idx = data.columns.get_loc('ATR')
    sig_idx = data.columns.get_loc('SIG')
    for i in range(start_pos, data.shape[0]):
        price = data.iloc[i].close.item()
        cond_l, cond_s, pprice, sprice, atr = get_signal(
            data.iloc[i-7:i+1].values, price, args.k, args.s1, args.s2,
            args.cond_len, args.use_atr, args.follow_trend, atr_idx, sig_idx)
        data.loc[i, 'side'] = cond_l - cond_s
    data['D/H'] = pd.to_datetime(data.start_t + 8 * 36e5, unit='ms').dt.strftime('%d/%H')
    print(data[['D/H', 'close', 'ATR', 'DIF', 'SIG', 'side']].dropna())
        


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--shift', type=int, default=0)
    parser.add_argument('--his-window', type=int, default=7)
    parser.add_argument('--atr-window', type=int, default=24)
    parser.add_argument('--cond-len', type=int, default=2)
    parser.add_argument('--k', type=float, required=True, help='ATR multiplier for entry/exit')
    parser.add_argument('--s1', type=float, required=False, help='take profit ratio', default=0.01)
    parser.add_argument('--s2', type=float, required=False, help='get loss ratio', default=0.01)
    parser.add_argument('--use-atr', action='store_true')
    parser.add_argument('--follow-trend', action='store_true')
    parser.add_argument('--start-time', type=str)
    parser.add_argument('--account', '-a', type=str, default='zhou')
    args = parser.parse_args()
    if not args.use_atr:
        assert args.s1 < 1 and args.s2 < 1, f'{args.s1=} and {args.s2=} is reqired to less than 1.0 without atr use'
    args.symbol = args.symbol.upper()
    if 'USD' not in args.symbol:
        args.symbol += 'USDC'
    args.is_um = not args.symbol.endswith('_PERP')
    if not args.start_time:
        args.start_time = dt.now() - pd.Timedelta(days=2)
    main(args)
