#!/usr/bin/env python
#-*- coding:utf-8 -*-


import requests
import traceback

from .const import HOOK_PREFIX
from datetime import datetime as dt


def send_exception(symbol):
    url = f"{HOOK_PREFIX}/50827e6ac3d3ed1a6cdd31ab04964346"
    info = {
        "symbol": symbol,
        "datetime": str(dt.now()),
        "message":  traceback.format_exc()
    }
    rsp = requests.post(url, json=info)
    print(rsp.status_code, rsp.text)