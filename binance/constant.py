#!/usr/bin/env python
#-*- coding:utf-8 -*-

#-------------'_M_' means main/most---------------
# spot
_SPOT_M_VER_ = 'v3'
_SPOT_M_API_ = 'api'


# coin-m
_COIN_M_VER_ = 'v1'
_COIN_M_API_ = 'dapi'

# UniCM
_UNI_CM_VER_ = 'v1/cm'
_UNI_CM_API_ = 'papi'

# precision: 1/10^{ROUND_AT}
ROUND_AT = {
    "BNBUSD_PERP": 2,
    "BTCUSD_PERP": 1,
    "DOGEUSD_PERP": 5,
}

MIN_MOVE = {
    "BNBUSD_PERP": 0.01,
    "BTCUSD_PERP": 0.1,
    "DOGEUSD_PERP": 0.00001,
}

# Period
N_MS_PER_SEC = 1000
N_MS_PER_DAY = 24 * 3600000 
