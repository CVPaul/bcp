#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Created on Thu Aug  3 16:01:04 2023
"""


import numba as nb
import numpy as np
import prototype.v3 as v3

from strategy.indicator.common import ATR


def get_feat(gdf, atr_window=24, clen=2):
    # init
    gdf['ATR'] = ATR(atr_window).calc(gdf)
    lwin = gdf.low.rolling(atr_window)
    hwin = gdf.high.rolling(atr_window)
    gdf['DNN'] = lwin.min()
    gdf['UPP'] = hwin.max()
    gdf['UPI'] = lwin.apply(lambda x: x.argmax(), raw=True)
    gdf['DNI'] = hwin.apply(lambda x: x.argmin(), raw=True)
    gdf['DIF'] = gdf.close.diff()
    def _cal_sig_(row):
        rng = row['UPP'] - row['DNN']
        if row['UPI'] == row['DNI']:
            sig = row['close'] > row['open']
        else:
            sig = row['UPI'] > row['DNI']
        if sig:
            return rng / row['DNN']
        else:
            return -rng / row['UPP']
    if clen < 1:
        gdf['SIG'] = gdf.apply(_cal_sig_, axis=1)
    return gdf


@nb.jit(nopython=True, cache=True)
def get_signal(gdf, price, k, clen, dnn_idx, upp_idx, atr_idx, sig_idx, dif_idx, lloc=-1):
    # trade
    atr = gdf[lloc, atr_idx]
    dnn = gdf[lloc, dnn_idx]
    upp = gdf[lloc, upp_idx]
    if clen < 1:
        sig = gdf[lloc, sig_idx]
        cond_l = sig < -k # and (price - dnn) / dnn > clen
        cond_s = sig > k # and (upp - price) / upp > clen
        go_up = go_down = True
        difs = gdf[-clen:, dif_idx]
        for i in range(2):
            go_up = go_up and (difs[-1 - i] > 0)
            go_down = go_down and (difs[-1 - i] < 0)
        cond_l = cond_l and go_up
        cond_s = cond_s and go_down
    else:
        difs = gdf[-clen:, dif_idx]
        cond_s = (price - dnn) / dnn > k
        cond_l = (upp - price) / upp > k
        go_up = go_down = True
        for i in range(clen):
            go_up = go_up and (difs[-1 - i] > 0)
            go_down = go_down and (difs[-1 - i] < 0)
        cond_l = cond_l and go_up
        cond_s = cond_s and go_down
    return cond_l, cond_s, atr


@nb.jit(nopython=True, cache=True)
def get_prices(cond_l, cond_s, price, s1, s2, use_atr, atr):
    pprice = sprice = 0
    if cond_l:
        if use_atr:
            pprice = price + s1 * atr
            sprice = price - s2 * atr
        else:
            pprice = price * (1 + s1)
            sprice = price * (1 - s2)
    if cond_s:
        if use_atr:
            pprice = price - s1 * atr
            sprice = price + s2 * atr
        else:
            pprice = price * (1 - s1)
            sprice = price * (1 + s2)
    return pprice, sprice


@nb.jit(nopython=True, cache=True)
def _v1_(data, k, s1, s2, clen, use_atr, dnn_idx, upp_idx, close, high, low, atr_idx, sig_idx, dif_idx):
    trans = []
    # main logical
    start_pos = max(clen + 1, 3)
    mp, enpp, entt, sss, ppp = 0, 0, 0, 0, 0
    for i in range(start_pos, data.shape[0]):
        row = data[i]
        price_t = row[close]
        cond_l, cond_s, atr = get_signal(
            data[i - start_pos:i + 1], price_t, k, clen,
            dnn_idx, upp_idx, atr_idx, sig_idx, dif_idx)
        pprice, sprice = get_prices(cond_l, cond_s, price_t, s1, s2, use_atr, atr)
        # loss
        if mp > 0 and row[low] <= sss:
            trans.append([mp, enpp, sss, entt, i])
            mp = 0
        if mp < 0 and row[high] >= sss:
            trans.append([mp, enpp, sss, entt, i])
            mp = 0
        # profit
        if mp > 0 and row[high] >= ppp:
            trans.append([mp, enpp, ppp, entt, i])
            mp = 0
        if mp < 0 and row[low] <= ppp:
            trans.append([mp, enpp, ppp, entt, i])
            mp = 0
        # sell
        if mp >= 0 and cond_s:
            if mp != 0:
                trans.append([mp, enpp, price_t, entt, i])
            entt = i
            enpp, ppp, sss = price_t, pprice, sprice
            mp = -1 
        # buy
        if mp <= 0 and cond_l:
            if mp != 0:
                trans.append([mp, enpp, price_t, entt, i])
            entt = i
            enpp, ppp, sss = price_t, pprice, sprice
            mp = 1
    return trans


@nb.jit(nopython=True, cache=True)
def _v2_(data, k, s1, s2, clen, use_atr, dnn_idx, upp_idx, close, high, low, atr_idx, sig_idx, dif_idx):
    trans = []
    # main logical
    start_pos = max(int(clen + 1), 3)
    mp, enpp, entt, sss, ppp = 0, 0, 0, 0, 0
    for i in range(start_pos, data.shape[0]):
        row = data[i]
        price_t = row[close]
        cond_l, cond_s, atr = get_signal(
            data[i - start_pos:i + 1], price_t, k, clen,
            dnn_idx, upp_idx, atr_idx, sig_idx, dif_idx)
        pprice, sprice = get_prices(cond_l, cond_s, price_t, s1, s2, use_atr, atr)
        # loss
        if mp > 0:
            if row[low] <= sss:
                trans.append([mp, enpp, sss, entt, i, 0])
                entt, enpp = i, sss
                ppp, sss, _ = get_prices(False, True, enpp, s1, s2, use_atr, atr)
                mp = -mp
            elif ppp > 1e-8 and row[high] >= ppp:
                trans.append([mp, enpp, ppp, entt, i, 1])
                entt, enpp = i, ppp
                ppp, sss, _ = get_prices(False, True, enpp, s1, s2, use_atr, atr)
                mp = -mp
        elif mp < 0:
            if sss > 1e-8 and row[high] >= sss:
                trans.append([mp, enpp, sss, entt, i, 2])
                entt, enpp = i, sss
                ppp, sss, _ = get_prices(True, False, enpp, s1, s2, use_atr, atr)
                mp = -mp
            elif row[low] <= ppp:
                trans.append([mp, enpp, ppp, entt, i, 3])
                entt, enpp = i, ppp
                ppp, sss, _ = get_prices(True, False, enpp, s1, s2, use_atr, atr)
                mp = -mp
        # sell
        if mp >= 0 and cond_s:
            if mp != 0:
                trans.append([mp, enpp, price_t, entt, i, 4])
            entt, enpp = i, price_t
            ppp, sss = pprice, sprice
            mp = -1 
        # buy
        if mp <= 0 and cond_l:
            if mp != 0:
                trans.append([mp, enpp, price_t, entt, i, 5])
            entt, enpp = i, price_t
            ppp, sss = pprice, sprice
            mp = 1
    return trans


def search(df, k, s1, s2, clen, use_atr=False, version=1):
    # k, s1, s2 = 0.08, 10e-2, 1e-2
    columns = df.columns.to_list()
    data = df.values
    close = columns.index('close')
    high = columns.index('high')
    low = columns.index('low')
    atr_idx = columns.index('ATR')
    dnn_idx = columns.index('DNN')
    upp_idx = columns.index('UPP')
    dif_idx = columns.index('DIF')
    if clen < 1:
        sig_idx = columns.index('SIG')
    else:
        sig_idx = 10086
    if version == 1:
        return _v1_(data, k, s1, s2, clen, use_atr, dnn_idx, upp_idx, close, high, low, atr_idx, sig_idx, dif_idx)
    elif version == 2:
        return _v2_(data, k, s1, s2, clen, use_atr, dnn_idx, upp_idx, close, high, low, atr_idx, sig_idx, dif_idx)
    else:
        raise ValueError("Currently, version only support 1 or 2")


def search2(df, k, s1, s2, clen, use_atr=False):
    return search(df, k, s1, s2, clen, use_atr)