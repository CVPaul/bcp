#!/usr/bin/env python
#-*- coding:utf-8 -*-


import requests
import traceback

from .const import HOOK_PREFIX
from datetime import datetime as dt
from datetime import timedelta as td


NOTICE_ID = "50827e6ac3d3ed1a6cdd31ab04964346"


def send_message(symbol, title, message):
    url = f"{HOOK_PREFIX}/{NOTICE_ID}"
    info = {
        "symbol": symbol,
        "datetime": str(dt.now() + td(hours=8)),
        "title": title,
        "message":  message
    }
    return requests.post(url, json=info)


def send_exception(symbol):
    return send_message(
        symbol,
        f"Trader Exception({symbol})",
        traceback.format_exc())