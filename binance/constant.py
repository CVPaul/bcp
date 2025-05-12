#!/usr/bin/env python
#-*- coding:utf-8 -*-

#-------------'_M_' means main/most---------------
# spot
_SPOT_M_VER_ = 'v3'
_SPOT_M_API_ = 'api'


# coin-m
_COIN_M_VER_ = 'v1'
_COIN_M_API_ = 'dapi'

# usds-m
_USD_M_VER_ = 'v1'
_USD_M_API_ = 'fapi'

# UniCM
_UNI_CM_VER_ = 'v1/cm'
_UNI_CM_API_ = 'papi'

# precision: 1/10^{ROUND_AT}
ROUND_AT = {
    "BNB": 2,
    "BTC": 1,
    "DOGE": 5,
    "SOL": 2,
    "ETH": 2,
    "SUI": 4,
    "TRUMP": 3,
}

LOT_ROUND_AT = {
    'BTC': 3,
    'ETH': 3,
    'BNB': 2,
    'DOGE': 0,
    'SOL': 2,
    'SUI': 1,
    'TRUMP': 2,
}
# Period
N_MS_PER_SEC = 1000
N_MS_PER_DAY = 24 * 3600000 
