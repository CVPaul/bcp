#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import sys
import time
import sqlite3
import logging
import argparse
import pandas as pd

from binance.fut.usdm import USDM
from binance.fut.coinm import CoinM
from binance.constant import N_MS_PER_DAY

from datetime import datetime as dt
from datetime import timedelta as td

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

if __name__ == "__main__":
    print("hello world")
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str, required=True)
    parser.add_argument(
        '--type', '-t', type=str, choices=['um', 'cm'], default='cm')
    parser.add_argument('--usx', '-u', type=str, default='USDT')
    parser.add_argument('--start-time', '-st', type=str)
    parser.add_argument('--end-time', '-et', type=str)
    args = parser.parse_args()
    # Initialize client and table
    if args.type == 'cm':
        cli = CoinM()
        args.symbol = f'{args.symbol}USD_PERP'.upper()
    else:
        cli = USDM()
        args.symbol = f'{args.symbol}{args.usx}'.upper()
    # Database connection
    print(args)
    conn = sqlite3.connect(f"data/{args.symbol}.db")
    cursor = conn.cursor()
    # Determine start_time
    if not args.start_time:
        cursor.execute("SELECT MAX(start_t) FROM klines")
        last_start_t = cursor.fetchone()[0]
        if last_start_t is None:
            raise ValueError(f"No existing data found in database for {args.symbol}")
        last_dt = pd.to_datetime(last_start_t, unit='ms')
        args.start_time = last_dt + pd.Timedelta(days=1)
        logging.info(f"Inferred start_time from database: {args.start_time}")
    else:
        args.start_time = pd.to_datetime(args.start_time)
    
    start_t = int(args.start_time.timestamp() * 1000)
    if args.end_time:
        end_t = int(pd.to_datetime(args.end_time).timestamp() * 1000)
    else:
        end_t = int(dt.now().timestamp() * 1000)
        end_t -= end_t % N_MS_PER_DAY
    assert start_t <= end_t, "Invalid time range"

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS klines (
            start_t INTEGER PRIMARY KEY NOT NULL,
            open REAL, high REAL, low REAL, close REAL,
            volume REAL, end_t INTEGER, amount REAL,
            trade_cnt INTEGER, taker_vol REAL, taker_amt REAL,
            reserved TEXT
        )
    ''')
    conn.commit()
    # Data fetching loop
    while start_t < end_t:
        dat = cli.klines(
            args.symbol, '1m', endTime=start_t + N_MS_PER_DAY, limit=1441)
        if not dat:
            start_t += N_MS_PER_DAY
            continue
        day = pd.to_datetime(start_t * 1e6)
        assert dat[-1][0] == start_t + N_MS_PER_DAY, \
            f"Data mismatch: {dat[-1][0]} vs {start_t + N_MS_PER_DAY}"
        
        start_t = dat[-1][0]
        df = pd.DataFrame(dat[:-1], columns=[
            'start_t', 'open', 'high', 'low', 'close',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ])
        df.to_sql('klines', conn, if_exists='append', index=False)
        logging.info(f"{len(df)} rows inserted for {args.symbol}@{day.date()}")
        time.sleep(1/30)
    conn.close()
    logging.info("Data download completed")
