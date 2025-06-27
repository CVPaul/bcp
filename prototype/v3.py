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
def get_signal(gdf, price, k, s1, s2, cond_len, use_atr, follow_trend, atr_idx, sig_idx):
    # trade
    atr = gdf[-1, atr_idx]
    sigs = gdf[-cond_len - 1:, sig_idx]
    go_up = go_down = True
    for i in range(cond_len):
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
    return pprice, sprice


@nb.jit(nopython=True, cache=True)
def _v1_(data, k, s1, s2, cond_len, use_atr, follow_trend, close, high, low, atr_idx, sig_idx):
    trans = []
    # main logical
    start_pos = cond_len + 1
    mp, enpp, entt, sss, ppp = 0, 0, 0, 0, 0
    for i in range(start_pos, data.shape[0]):
        row = data[i]
        price_t = row[close]
        cond_l, cond_s, pprice, sprice = get_signal(
            data[i - start_pos:i + 1], price_t, k, s1, s2, cond_len,
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


def _v2_(data, k, s1, s2, cond_len, use_atr, follow_trend, close, high, low, atr_idx, sig_idx):
    trans = []
    # main logical
    start_pos = cond_len + 1
    mp, enpp, entt, sss, ppp = 0, 0, 0, 0, 0
    for i in range(start_pos, data.shape[0]):
        row = data[i]
        price_t = row[close]
        cond_l, cond_s, pprice, sprice, atr = get_signal(
            data[i - start_pos:i + 1], price_t, k, s1, s2, cond_len,
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


def search(df, k, s1, s2, cond_len=2, use_atr=False, follow_trend=False, atr_window=24, his_window=7):
    # k, s1, s2 = 0.08, 10e-2, 1e-2
    data = get_feat(df, atr_window, his_window)
    columns = data.columns.to_list()
    data = data.values
    close = columns.index('close')
    high = columns.index('high')
    low = columns.index('low')
    atr_idx = columns.index('ATR')
    sig_idx = columns.index('SIG')
    return _v1_(data, k, s1, s2, cond_len, use_atr, follow_trend,
           close, high, low, atr_idx, sig_idx)


def search2(df, k, s1, s2, cond_len=2, use_atr=False, follow_trend=False, reverse=False):
    # main logical
    data = df.values
    columns = df.columns.to_list()
    m4 = columns.index('M4')
    m5 = columns.index('M5')
    high = columns.index('high')
    low = columns.index('low')
    close = columns.index('close')
    price_t = close

    trans = []
    # k, s1, s2 = 0.08, 10e-2, 1e-2
    mp, enpp, entt, sss, ppp = 0, 0, 0, 0, 0
    last_1_m4, last_2_m4, last_3_m4, last_4_m4 = 0, 0, 0, 0
    for i in range(1, df.shape[0]):
        row = data[i]
        # loss
        if mp > 0 and row[low] <= sss:
            trans.append([mp, enpp, sss, entt, i])
            enpp = sss
            ppp = enpp - s1 * row[m5]
            sss = enpp + s2 * row[m5]
            mp = -mp
        if mp < 0 and row[high] >= sss:
            trans.append([mp, enpp, sss, entt, i])
            enpp = sss
            ppp = enpp + s1 * row[m5]
            sss = enpp - s2 * row[m5]
            mp = -mp
        # profit
        if mp > 0 and row[high] >= ppp:
            trans.append([mp, enpp, ppp, entt, i])
            enpp = ppp
            ppp = enpp - s1 * row[m5]
            sss = enpp + s2 * row[m5]
            mp = -mp
        if mp < 0 and row[low] <= ppp:
            trans.append([mp, enpp, ppp, entt, i])
            enpp = ppp
            ppp = enpp + s1 * row[m5]
            sss = enpp - s2 * row[m5]
            mp = -mp
        if cond_len == 0:
            cond_l = True
            cond_s = True
        elif cond_len == 1:
            cond_l = last_1_m4 < 0
            cond_s = last_1_m4 > 0
        elif cond_len == 2:
            cond_l = (last_1_m4 < 0 and last_2_m4 < 0)
            cond_s = (last_1_m4 > 0 and last_2_m4 > 0)
        elif cond_len == 3:
            cond_l = (last_1_m4 < 0 and last_2_m4 < 0 and last_3_m4 < 0)
            cond_s = (last_1_m4 > 0 and last_2_m4 > 0 and last_3_m4 > 0)
        elif cond_len == 4:
            cond_l = (last_1_m4 < 0 and last_2_m4 < 0 and last_3_m4 < 0 and last_4_m4 < 0)
            cond_s = (last_1_m4 > 0 and last_2_m4 > 0 and last_3_m4 > 0 and last_4_m4 > 0)
        else:
            raise ValueError(f'invalid {cond_len=}')
        if follow_trend:
            cond_l, cond_s = (cond_s and (row[m4] > k)), (cond_l and (row[m4] < -k))
        else:
            cond_l = cond_l and (row[m4] > k)
            cond_s = cond_s and (row[m4] < -k)
        if reverse:
            cond_l, cond_s = cond_s, cond_l
        # sell
        if mp >= 0 and cond_s:
            if mp != 0:
                trans.append([mp, enpp, row[price_t], entt, i])
            entt = i
            enpp = row[price_t]
            if use_atr:
                ppp = enpp - s1 * row[m5]
                sss = enpp + s2 * row[m5]
            else:
                ppp = enpp * (1 - s1)
                sss = enpp * (1 + s2)
            mp = -1 
        # buy
        if mp <= 0 and cond_l:
            if mp != 0:
                trans.append([mp, enpp, row[price_t], entt, i])
            entt = i
            enpp = row[price_t]
            if use_atr:
                ppp = enpp + s1 * row[m5]
                sss = enpp - s2 * row[m5]
            else:
                ppp = enpp * (1 + s1)
                sss = enpp * (1 - s2)
            mp = 1
        last_4_m4 = last_3_m4
        last_3_m4 = last_2_m4
        last_2_m4 = last_1_m4
        last_1_m4 = row[m4]
    return trans