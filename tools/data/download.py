#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import sys
import time
import logging
import argparse
import pandas as pd

from binance.fut.coinm import CoinM
from binance.constant import N_MS_PER_DAY

from datetime import datetime as dt
from datetime import timedelta as td

# logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument('--start-time', type=str)
    parser.add_argument('--end-time', type=str)
    parser.add_argument(
        '--type', '-t', type=str, required=True,
        choices=['kline', 'tick'])
    args = parser.parse_args()
    args.datadir = f'data/{args.symbol}/'
    os.makedirs(args.datadir, exist_ok=True)
    # args convert
    if not args.start_time:
        files = os.listdir(args.datadir)
        for file in files:
            if file[-4:] != '.csv':
                continue
            date = file.split('.')[-2]
            if not args.start_time or args.start_time < date:
                args.start_time = date
        assert args.start_time, f'no data found in {args.datadir}, cannot infer the --start-time!'
        args.start_time = pd.to_datetime(args.start_time) + td(days=1)
        logging.info(f'infer start-date for datadir got: {args.start_time}')
    start_t = int(pd.to_datetime(args.start_time).timestamp() * 1000)
    if args.end_time:
        end_t = int(pd.to_datetime(args.end_time).timestamp() * 1000)
    else:
        end_t = int(dt.now().timestamp() * 1000)
        end_t -= (end_t % N_MS_PER_DAY)
    assert start_t <= end_t
    # create client
    cli = CoinM()
    # start pull data
    data = []
    while start_t < end_t:
        if args.type == 'kline':
            dat = cli.klines(
                args.symbol, '1m', endTime=start_t + N_MS_PER_DAY, limit=1441)
            day = pd.to_datetime(start_t * 1e6)
            assert dat[-1][0] == start_t + N_MS_PER_DAY, \
                f'dat[-1][0]={dat[-1][0]}, start_t + N_MS_PER_DAY={start_t} + {N_MS_PER_DAY}=' \
                f'{start_t + N_MS_PER_DAY}'
            start_t = dat[-1][0]
            dat = pd.DataFrame(dat[:-1], columns=[
                'start_t', 'open', 'high', 'low', 'close',
                'volume', 'end_t', 'amount', 'trade_cnt',
                'taker_vol', 'taker_amt', 'reserved'
            ])
            dat.to_csv(f'{args.datadir}/{day.date()}.csv', index=False)
            logging.info(
                f'{dat.shape[0]} 1m klines of {args.symbol}@'
                f'{day.date()} had been save to data dir!')
            time.sleep(1/40)
        else:
            raise KeyError(f'unsupported type:{args.type}!')
    logging.info('endtime reached!')
