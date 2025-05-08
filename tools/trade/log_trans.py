#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import sys
import ast
import json
import pandas as pd


def parse_orders(records):
    orders = []
    is_open = False
    mismatch_orders = []
    last_is_close = True 
    win_cnt, loss_cnt = 0, 0
    for line in records:
        order = ast.literal_eval(line.split('ORDER|')[-1])
        if '_open_' in order['newClientId']:
            is_open = True
        else:
            is_open = False
            if '_win_' in order['newClientId']:
                win_cnt += 1
            else:
                loss_cnt += 1 
        order['datetime'] = pd.to_datetime(
            line[:23], format="%Y-%m-%d %H:%M:%S,%f")
        if last_is_close:
            if is_open:
                last_is_close = False
            else:
                mismatch_orders.append(order)
                continue
        else:
            if is_open:
                mismatch_orders.append(order)
                continue
            else:
                last_is_close = True
        orders.append(order)
    print(f'>>>[win:loss]{win_cnt=}/{loss_cnt=}')
    return pd.DataFrame(orders), pd.DataFrame(mismatch_orders)


def get_log_trans(fname):
    with open(fname) as fp:
        records = [line for line in fp if 'ORDER|' in line]
    trans, missing_trans = parse_orders(records)
    trans = trans.set_index('datetime')
    trans['direction'] = trans.side.apply(
        lambda x: 1 if x == 'BUY' else -1)
    trans['vol'] = trans.quantity * trans.direction
    trans['pos'] = trans.vol.cumsum()
    trans['gross-profit'] = (trans.pos * trans.price.diff().shift(-1)).cumsum()
    trans['commis'] = (trans.quantity * trans.price * 2e-4).cumsum()
    trans['net'] = trans['gross-profit'] - trans.commis
    # missing ones
    missing_trans = missing_trans.set_index('datetime')
    missing_trans['commis'] = (missing_trans.quantity * missing_trans.price * 2e-4).cumsum()
    return trans, missing_trans


if __name__ == "__main__":
    trans, missing_trans = get_log_trans(sys.argv[1])
    for c in ['type', 'timeInForce', 'symbol']:
        trans.pop(c)
        missing_trans.pop(c)
    print(missing_trans)
    print("=" * 108)
    print(trans)