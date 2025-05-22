import pandas as pd


def search(df, k, s1, s2, s3=None, cond_len=2, use_atr=False, follow_trend=False):
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
            trans.append([mp, enpp, sss])
            mp = 0
        if mp < 0 and row[high] >= sss:
            trans.append([mp, enpp, sss])
            mp = 0
        # profit
        if mp > 0 and row[high] >= ppp:
            trans.append([mp, enpp, ppp])
            mp = 0
        if mp < 0 and row[low] <= ppp:
            trans.append([mp, enpp, ppp])
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
        if follow_trend:
            cond_l, cond_s = (cond_s and (row[m4] > k)), (cond_l and (row[m4] < -k))
        else:
            cond_l = cond_l and (row[m4] > k)
            cond_s = cond_s and (row[m4] < -k)
        if s3 is not None:
            # last_return = row[close] / row[open_] - 1.0
            # cond_l = cond_l and last_return > s3
            # cond_s = cond_s and last_return < -s3
            atr_range = row[m5] / row[close]
            cond_l = cond_l and atr_range < s3
            cond_s = cond_s and atr_range < s3
        # sell
        if mp >= 0 and cond_s:
            if mp != 0:
                trans.append([mp, enpp, row[price_t]])
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
                trans.append([mp, enpp, row[price_t]])
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


def search2(df, k, s1, s2, s3=None, cond_len=2, use_atr=False, follow_trend=False):
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
            trans.append([mp, enpp, sss])
            mp = 0
        if mp < 0 and row[high] >= sss:
            trans.append([mp, enpp, sss])
            mp = 0
        # profit
        if mp > 0 and row[high] >= ppp:
            trans.append([mp, enpp, ppp])
            mp = -1
            enpp = ppp
            if use_atr:
                ppp = enpp - s1 * row[m5]
                sss = enpp + s2 * row[m5]
            else:
                ppp = enpp * (1 - s1)
                sss = enpp * (1 + s2)
        if mp < 0 and row[low] <= ppp:
            trans.append([mp, enpp, ppp])
            mp = 1
            enpp = ppp
            if use_atr:
                ppp = enpp + s1 * row[m5]
                sss = enpp - s2 * row[m5]
            else:
                ppp = enpp * (1 + s1)
                sss = enpp * (1 - s2)
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
        if s3 is not None:
            # last_return = row[close] / row[open_] - 1.0
            # cond_l = cond_l and last_return > s3
            # cond_s = cond_s and last_return < -s3
            atr_range = row[m5] / row[close]
            cond_l = cond_l and atr_range < s3
            cond_s = cond_s and atr_range < s3
        # sell
        if mp >= 0 and cond_s:
            if mp != 0:
                trans.append([mp, enpp, row[price_t]])
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
                trans.append([mp, enpp, row[price_t]])
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