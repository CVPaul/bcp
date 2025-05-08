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
    "BNBUSDT": 2,
    "BTCUSDT": 1,
    "DOGEUSDT": 5,
    "SOLUSDT": 2,
    "ETHUSDT": 2,
    "SUIUSDT": 4,
    "TRUMPUSDT": 3,
    "BNBUSD_PERP": 2,
    "BTCUSD_PERP": 1,
    "DOGEUSD_PERP": 5,
    "SOLUSD_PERP": 2,
    "ETHUSD_PERP": 2,
    "TRUMPUSD_PERP": 3,
}

MIN_MOVE = {
    "BNBUSD_PERP": 0.01,
    "BTCUSD_PERP": 0.1,
    "DOGEUSD_PERP": 0.00001,
}

LOT_SIZE = {
    'BTCUSDT': 0.001,
    'ETHUSDT': 0.001,
    'BNBUSDT': 0.01,
    'DOGEUSDT': 1.0,
    'SOLUSDT': 0.01,
    'SUIUSDT': 0.1,
    'TRUMPUSDT': 0.01,
}

LOT_ROUND_AT = {
    'BTCUSDT': 3,
    'ETHUSDT': 3,
    'BNBUSDT': 2,
    'DOGEUSDT': 0,
    'SOLUSDT': 2,
    'SUIUSDT': 1,
    'TRUMPUSDT': 2,
}
# Period
N_MS_PER_SEC = 1000
N_MS_PER_DAY = 24 * 3600000 
