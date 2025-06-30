#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Created on Thu Aug  3 16:01:04 2023
"""


import numba as nb
from strategy.indicator.common import ATR


def get_feat(gdf, atr_window=24, his_window=7):
    # init
    gdf['ATR'] = ATR(atr_window, gdf).calc(gdf)  # atr shift 1
    gdf['MA7'] = gdf.close.rolling(his_window).mean()
    gdf['DIF'] = gdf.MA7.diff()
    gdf['SIG'] = gdf['DIF'] / gdf['ATR']
    return gdf


@nb.jit(nopython=True, cache=True)
def get_signal(gdf, price, k, s1, s2, clen, use_atr, follow_trend, atr_idx, sig_idx, atr_loc=-1):
    # trade
    atr = gdf[atr_loc, atr_idx] # 对于V9这里的atr_loc=-2是为了保持开仓的时候是上一个ATR, 但是status=1|2的时候则不需
    sigs = gdf[-clen - 1:, sig_idx]
    go_up = go_down = True
    for i in range(clen):
        go_up = go_up and (sigs[-2 - i] > 0)
        go_down = go_down and (sigs[-2 - i] < 0)
    final_up = sigs[-1] > k
    final_down = sigs[-1] < -k
    if follow_trend:
        cond_l = go_up and final_up
        cond_s = go_down and final_down
    else:
        cond_l = go_down and final_up
        cond_s = go_up and final_down
    return cond_l, cond_s, *get_prices(cond_l, cond_s, price, s1, s2, use_atr, atr)


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
    return pprice, sprice, atr


@nb.jit(nopython=True, cache=True)
def _v1_(data, k, s1, s2, clen, use_atr, follow_trend, close, high, low, atr_idx, sig_idx):
    trans = []
    # main logical
    start_pos = clen + 1
    mp, enpp, entt, sss, ppp = 0, 0, 0, 0, 0
    for i in range(start_pos, data.shape[0]):
        row = data[i]
        price_t = row[close]
        cond_l, cond_s, pprice, sprice, _ = get_signal(
            data[i - start_pos:i + 1], price_t, k, s1, s2, clen,
            use_atr, follow_trend, atr_idx, sig_idx)
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
def _v2_(data, k, s1, s2, clen, use_atr, follow_trend, close, high, low, atr_idx, sig_idx):
    trans = []
    # main logical
    start_pos = clen + 1
    mp, enpp, entt, sss, ppp = 0, 0, 0, 0, 0
    for i in range(start_pos, data.shape[0]):
        row = data[i]
        price_t = row[close]
        cond_l, cond_s, pprice, sprice, atr = get_signal(
            data[i - start_pos:i + 1], price_t, k, s1, s2, clen,
            use_atr, follow_trend, atr_idx, sig_idx)
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


def search(df, k, s1, s2, clen, use_atr=False, follow_trend=False, version=1):
    # k, s1, s2 = 0.08, 10e-2, 1e-2
    columns = df.columns.to_list()
    data = df.values
    close = columns.index('close')
    high = columns.index('high')
    low = columns.index('low')
    atr_idx = columns.index('ATR')
    sig_idx = columns.index('SIG')
    if version == 1:
        return _v1_(data, k, s1, s2, clen, use_atr, follow_trend,
            close, high, low, atr_idx, sig_idx)
    elif version == 2:
        return _v2_(data, k, s1, s2, clen, use_atr, follow_trend,
            close, high, low, atr_idx, sig_idx)
    else:
        raise ValueError("Currently, version only support 1 or 2")


def search2(df, k, s1, s2, clen, use_atr=False, follow_trend=False):
    return search(df, k, s1, s2, clen, use_atr, follow_trend, version=2)
