#!/usr/bin/env python
#-*- coding:utf-8 -*-


import sys
import time
import argparse
import requests
import pandas as pd

from urllib.parse import urlencode
from datetime import datetime as dt
from binance.auth.utils import load_api_keys
from binance.lib.authentication import ed25519_signature


BASE_URL = 'https://fapi.binance.com'


def get_order_history(symbol, start_time, end_time):
    endpoint = '/fapi/v1/income'
    params = {
        'symbol': symbol,
        'incomeType': 'REALIZED_PNL',
        'startTime': start_time,
        'endTime': end_time,
        'limit': 1000,
        'timestamp': int(time.time() * 1000),
    }

    query_string = urlencode(params)
    signature = ed25519_signature(PRIVATE_KEY, query_string)
    params['signature'] = signature
    headers = {'X-MBX-APIKEY': API_KEY}

    resp = requests.get(BASE_URL + endpoint, params=params, headers=headers)
    data = resp.json()
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', '-s', type=str)
    parser.add_argument('--account', '-a', type=str, default='zhou')
    parser.add_argument('--start-time', '-st', type=str, default='20250401')
    parser.add_argument('--end-time', '-et', type=str, default=str(dt.now()))
    parser.add_argument('--usd', '-u', type=str, default='C')
    args = parser.parse_args()

    args.symbol = f'{args.symbol}USD{args.usd}'
    args.start_time = int(pd.to_datetime(args.start_time).timestamp() * 1000)
    args.end_time = int(pd.to_datetime(args.end_time).timestamp() * 1000)
    API_KEY, PRIVATE_KEY = load_api_keys(args.account)
    orders = pd.DataFrame(get_order_history(args.symbol, args.start_time, args.end_time))
    orders.time = pd.to_datetime(orders.time, unit='ms')

    print(orders, "\n>>> total pnl:", orders.income.astype(float).sum())