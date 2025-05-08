#!/usr/bin/env python
#-*- coding:utf-8 -*-


import numpy as np
import pandas as pd


def ma_atr(df, k, s1, s2, cond_len=2, use_atr=False):
    mp, enpp = 0, 0
    trans, conds = [], []
    for i in range(df.shape[0]):
        row = df.iloc[i]
        atr, sig = row['atr'], row['sig']
        h, l, c = row['high'], row['low'], row['close']
        conds.append(sig)
        if len(conds) <= cond_len:
            continue
        cond_l = conds[-1] > k
        cond_s = conds[-1] < -k
        for i in range(cond_len):
            cond_l = cond_l and conds[-2 - i] < 0
            cond_s = cond_s and conds[-2 - i] > 0
        # stop price
        if use_atr:
            lpp = enpp + s1 * atr
            spp = enpp - s1 * atr
            lss = enpp - s2 * atr
            sss = enpp + s2 * atr
        else:
            lpp = enpp * (1 + s1) 
            spp = enpp * (1 - s1) 
            lss = enpp * (1 - s2)
            sss = enpp * (1 + s2)
        # ----------------loss---------------
        if mp > 0 and l <= lss:
            mp = 0
            trans.append([mp, lss, 3])
        # short loss
        if mp < 0 and h >= sss:
            mp = 0
            trans.append([mp, sss, -3])
        # ----------------win---------------
        if mp > 0 and h >= lpp:
            mp = 0
            trans.append([mp, lpp, 2])
        # short win
        if mp < 0 and l <= spp:
            mp = 0
            trans.append([mp, lpp, -2])
        # ----------------open---------------
        if mp <= 0 and cond_l:
            mp = 1
            enpp = c
            trans.append([mp, c, 1])
        if mp >= 0 and cond_s:
            mp = -1
            enpp = c
            trans.append([mp, c, -1])
    return trans