import os
import sys
import glob
import pandas as pd

from strategy.data.utils import load
from strategy.common.chart import Renko
from strategy.common.constant import DATADIR
from strategy.common.constant import DAY_MS_COUNT
from strategy.indicator.common import ATR


def run(symbol):
    df = load(symbol, DATADIR)
    ratio = 0.001
    backlen = 150
    atr = ATR(backlen, df)
    chart = Renko(ratio, backlen, df)
    hist = []
    for i in range(backlen, df.shape[0]):
        # print('close', i, df.iloc[i]['close'])
        open = None
        o = df.iloc[i]['open']
        h = df.iloc[i]['high']
        l = df.iloc[i]['low']
        c = df.iloc[i]['close']
        if df.iloc[i]['start_t'] % DAY_MS_COUNT == 0:
            open = o
        count = chart.update(df.iloc[i]['close'], open)
        atr_v = atr.update(h, l, c)
        for i in range(count):
            hist.append([
                chart.hist.open[i-1], chart.hist.close[i-1],
                chart.hist.high[i-1], chart.hist.low[i-1], atr_v])
            # print(i, len(hist))
    df = pd.DataFrame(hist, columns=['open', 'close', 'high', 'low', 'atr'])
    df.to_csv(f'../data/{symbol}_renko_{ratio}.csv', index=False)


if __name__ == "__main__":
    run(sys.argv[1])