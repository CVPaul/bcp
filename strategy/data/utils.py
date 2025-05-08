#!/usr/bin/env python
#-*- coding:utf-8 -*-


import glob

import pandas as pd


def load(symbol, datadir):
    dfs = []
    lis = sorted(glob.glob(f'{datadir}/{symbol}/*.csv'))
    for file in lis: 
        dfs.append(pd.read_csv(file))
    return pd.concat(dfs).drop_duplicates('start_t')