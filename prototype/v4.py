#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on 2025-08-09
Trend following strategy V4
"""

import numba as nb
from strategy.indicator.common import ATR


def get_feat(gdf, atr_window=24, ma_window=10):
    # Multiple timeframe MA for trend direction
    gdf['MA'] = gdf.close.rolling(7).mean().diff()
    # ATR for volatility
    gdf['ATR'] = ATR(atr_window).calc(gdf)
    # ADX for trend strength
    high, low, close = gdf.high, gdf.low, gdf.close
    gdf['HL'] = high - low
    gdf['HC'] = abs(high - close.shift(1))
    gdf['LC'] = abs(low - close.shift(1))
    gdf['TR'] = gdf[['HL', 'HC', 'LC']].max(axis=1)
    return gdf


@nb.jit(nopython=True, cache=True)
def get_signal(gdf, price, k, s1, s2, clen, 
               use_atr, atr_idx, ma_idx, tr_idx, atr_loc=-1):
    """
    Enhanced signal generation with multiple confirmations
    """
    ma = gdf[-1, ma_idx]
    tr = gdf[-1, tr_idx]
    atr = gdf[atr_loc, atr_idx]
    cond_x = (tr / atr) > clen  # Trend strength condition
    # cond_l = cond_x and price > ma + k * atr
    # cond_s = cond_x and price < ma - k * atr
    cond_l = cond_x and ma / atr > k
    cond_s = cond_x and ma / atr < -k
    # Calculate entry/exit prices with adaptive sizing
    return cond_l, cond_s, *get_prices(
        cond_l, cond_s, price, s1, s2, use_atr, atr), atr


@nb.jit(nopython=True, cache=True)
def get_prices(cond_l, cond_s, price, s1, s2, use_atr, atr):
    pprice = sprice = 0
    if cond_l:
        if use_atr:
            pprice = price + s2 * atr
            sprice = price - s1 * atr
        else:
            pprice = price * (1 + s2)
            sprice = price * (1 - s1)
    elif cond_s:
        if use_atr:
            pprice = price - s2 * atr
            sprice = price + s1 * atr
        else:
            pprice = price * (1 - s2)
            sprice = price * (1 + s1) 
    return pprice, sprice


@nb.jit(nopython=True, cache=True)
def _v4_(data, k, s1, s2, clen, use_atr, close, high, low, atr_idx, ma_idx, tr_idx):
    trans = []
    start_pos = clen + 1
    mp, enpp, entt, sss, ppp = 0, 0, 0, 0, 0
    for i in range(start_pos, data.shape[0]):
        row = data[i]
        price_t = row[close]
        cond_l, cond_s, pprice, sprice, atr = get_signal(
            data[i - start_pos:i + 1], price_t, k, s1, s2, 
            clen, use_atr, atr_idx, ma_idx, tr_idx)
        # Stop loss hit
        if mp > 0 and row[low] <= sss:
            trans.append([mp, enpp, sss, entt, i, 0])
            mp = 0
        elif mp < 0 and row[high] >= sss:
            trans.append([mp, enpp, sss, entt, i, 0])
            mp = 0
        # Take profit hit
        if mp > 0 and row[high] >= ppp:
            trans.append([mp, enpp, ppp, entt, i, 1])
            mp = 0
        elif mp < 0 and row[low] <= ppp:
            trans.append([mp, enpp, ppp, entt, i, 1])
            mp = 0
        # New position entry
        if mp == 0:
            if cond_l:
                entt, enpp = i, price_t
                ppp, sss = pprice, sprice
                mp = 1
            elif cond_s:
                entt, enpp = i, price_t
                ppp, sss = pprice, sprice
                mp = -1
    return trans


def search(df, k, s1, s2, clen, use_atr=True, adx_min=25, ma_slope_min=0.5):
    """
    Enhanced strategy function with stricter parameters
    Parameters:
    - k: ATR multiplier for entry
    - s1: Initial stop loss ATR multiplier
    - s2: Take profit ATR multiplier
    - clen: Look back period
    - use_atr: Whether to use ATR for price levels (default True)
    - adx_min: Minimum ADX value to confirm trend (default 25)
    - ma_slope_min: Minimum MA slope to confirm trend direction (default 0.5)
    """
    columns = df.columns.to_list()
    data = df.values
    close = columns.index('close')
    high = columns.index('high')
    low = columns.index('low')
    ma_idx = columns.index('MA')
    tr_idx = columns.index('TR')
    atr_idx = columns.index('ATR')
    return _v4_(data, k, s1, s2, clen, use_atr,
               close, high, low, atr_idx, ma_idx, tr_idx)