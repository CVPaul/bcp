#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import sys
import time
import json
import logging
import argparse
import pandas as pd

from binance.fut.coinm import CoinM
from binance.fut.unicm import UniCM
from datetime import datetime as dt
from datetime import timedelta as td

from binance.constant import ROUND_AT
from binance.auth.utils import load_api_keys
from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from strategy.indicator.common import MA
from strategy.indicator.common import ATR


if __name__ == "__main__":
    api_key, private_key = load_api_keys()
    client = UniCM(
        api_key=api_key,
        private_key=private_key,
    )
    mdcli = CoinM(
        api_key=api_key,
        private_key=private_key)
    cutline_len = 145
    symbol = "BNB"
    order = {
        "side": "BUY",
        "symbol":f"{symbol}USD_PERP",
        "quantity": 10, "type": "LIMIT",
        "timeInForce": "GTC", "price": 540.48,
    }
    res = client.new_order(**order)
    print(res)
    print("=" * cutline_len)
