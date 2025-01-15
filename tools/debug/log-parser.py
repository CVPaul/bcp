import os
import io
import sys

import pandas as pd


def line2dic(line):
    res = {}
    toks = line.split(',')
    for tk in toks:
        kv = tk.split('=')
        res[kv[0].strip()] = kv[1].strip()
    return res


if __name__ == "__main__":
    content = []
    with open(sys.argv[1]) as fp:
        for line in fp:
            if "/WIN" in line or "/LOSS" in line:
                direct = 'LONG' if 'LONG' in line else 'SHORT'
                action = 'OPEN' if 'OPEN' in line else 'CLOSE'
                line = f'direct={direct},action={action},' + line.split("|")[1]
                content.append(line2dic(line))
    df = pd.DataFrame(content)
    df['open'] = df.enpp
    if 'price' in df.columns:
        df['close'] = df.price.fillna(df.spp)
    else:
        df['close'] = df.spp
    df.open = df.open.astype(float)
    df.close = df.close.astype(float)
    df['side'] = df.direct.apply(lambda x: 1 if x == 'LONG' else -1)
    df['gross'] = df.side * (df.close - df.open)
    df['commis'] = (df.close + df.open) * 0.0005
    df.index = pd.to_datetime(df.pop('st').astype(float) * 1e6)
    print('=' * 20, 'Trade History', '=' * 20)
    if df.shape[0] > 60:
        print(">>> head-30:")
        print(df.head(30))
        print(">>> tail-30:")
        print(df.tail(30))
    else:
        print(df)
    trade_days = (df.index[-1] - df.index[0]).days
    print('=' * 20, 'Trade Summary', '=' * 20)
    print('    - start-time: %s'%df.index[0])
    print('    - stop-time: %s'%df.index[-1])
    print('    - trade-days: %d'%trade_days)
    print('    - trade-cnt: %s'%df.shape[0])
    print('    - trade-cnt/day: %.2f'%(df.shape[0] / trade_days))
    print('    - gross:%.6f'%df.gross.sum())
    print('    - commis:%.6f'%df.commis.sum())
    print('    - net-value:%.6f'%(df.gross - df.commis).sum())
    print('=' * 20, 'End of Summary', '=' * 20)
