import pandas as pd


def search(df, k, s1, s2, s3=None, cond_len=2, use_atr=False, k_use_atr=False):
    # reset to 0 before trading
    df['buy'] = 0 # (df.M4.shift(1) < 0) & (df.M4 > 0)
    df['sell'] = 0 # (df.M4.shift(1) > 0) & (df.M4 < 0)
    df['price'] = df.close
    df['pos'] = 0
    # main logical
    data = df.values
    columns = df.columns.to_list()
    m4 = columns.index('M4')
    m5 = columns.index('M5')
    buy = columns.index('buy')
    sell = columns.index('sell')
    high = columns.index('high')
    low = columns.index('low')
    price = columns.index('price')
    open_ = columns.index('open')
    close = columns.index('close')
    pos = columns.index('pos')

    price_t = close
    # k, s1, s2 = 0.08, 10e-2, 1e-2
    mp, enpp, sss, ppp = 0, 0, 0, 0
    last_1_m4, last_2_m4, last_3_m4, last_4_m4 = 0, 0, 0, 0
    for i in range(1, df.shape[0]):
        row = data[i]
        # loss
        if mp > 0 and row[low] <= sss:
            row[sell] = mp
            row[price] = sss
            mp = 0
        if mp < 0 and row[high] >= sss:
            row[buy] = mp
            row[price] = sss
            mp = 0
        # profit
        if mp > 0 and row[high] >= ppp:
            row[sell] = mp
            row[price] = ppp
            mp = 0
        if mp < 0 and row[low] <= ppp:
            row[buy] = mp
            row[price] = ppp
            mp = 0
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
        threshold = k * row[m5] / row[price_t] if k_use_atr else k
        cond_l = cond_l and (row[m4] > threshold)
        cond_s = cond_s and (row[m4] < -threshold)
        if s3 is not None:
            # last_return = row[close] / row[open_] - 1.0
            # cond_l = cond_l and last_return > s3
            # cond_s = cond_s and last_return < -s3
            atr_range = row[m5] / row[close]
            cond_l = cond_l and atr_range > s3
            cond_s = cond_s and atr_range > s3
        # sell
        if cond_s:
            row[sell] = mp + 1
            enpp = row[price_t]
            if use_atr:
                ppp = enpp - s1 * row[m5]
                sss = enpp + s2 * row[m5]
            else:
                ppp = enpp * (1 - s1)
                sss = enpp * (1 + s2)
            row[price] = enpp
            mp = -1
        
        # buy
        if cond_l:
            row[buy] = 1 - mp
            enpp = row[price_t]
            if use_atr:
                ppp = enpp + s1 * row[m5]
                sss = enpp - s2 * row[m5]
            else:
                ppp = enpp * (1 + s1)
                sss = enpp * (1 - s2)
            row[price] = enpp
            mp = 1
        last_4_m4 = last_3_m4
        last_3_m4 = last_2_m4
        last_2_m4 = last_1_m4
        last_1_m4 = row[m4]
        row[pos] = mp
    return pd.DataFrame(data, columns=columns)