import numba

# 固定百分比，止盈
@numba.jit(nopython=True)
def break_fix(data, length, k1, s1, direct):
    trans, mp = [], 0
    for i in range(length, data.shape[0] - 1):
        t, o, h, l, c, upp, dnn = data[i,0], data[i,1], data[i,2], data[i,3], \
            data[i,4], data[i,5], data[i,6]
        pos = i + 1
        nt, no, nh, nl, nc, nu, nd = data[pos,0], data[pos,1], data[pos,2], data[pos,3], \
            data[pos,4], data[pos,5], data[pos,6]
        if mp == 0 and upp / no > (1 + k1):
            price = no
            mp = direct
            entt = nt
            enpp = hpp = lpp = price
        if mp == 0 and dnn / no < (1 - k1):
            price = no
            mp = -direct
            entt = nt
            enpp = hpp = lpp = price
        if mp != 0:
            # hpp = max(hpp, nh)
            # lpp = min(lpp, nl)
            # long 
            spp = round(enpp * (1 - s1), 5)
            if mp > 0 and nl <= spp: # 止损
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0
            spp = round(enpp * (1 + s1), 5)
            if mp > 0 and nh >= spp: # 止盈
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0
            spp = round(enpp * (1 + s1), 5)
            # short
            if mp < 0 and nh >= spp: # 止损
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0
            spp = round(enpp * (1 - s1), 5)
            if mp < 0 and nl <= spp: # 止盈
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0
    return trans

@numba.jit(nopython=True)
def break_float(data, length, k1, s1, s2, direct):
    trans, mp, mp_t = [], 0, 0
    for i in range(length, data.shape[0] - 1):
        t, o, h, l, c, upp, dnn = data[i,0], data[i,1], data[i,2], data[i,3], \
            data[i,4], data[i,5], data[i,6]
        pos = i + 1
        nt, no, nh, nl, nc, nu, nd = data[pos,0], data[pos,1], data[pos,2], data[pos,3], \
            data[pos,4], data[pos,5], data[pos,6]
        if mp == 0 and upp / no > (1 + k1):
            price = no
            mp = direct
            entt = nt
            enpp = hpp = lpp = price
        if mp == 0 and dnn / no < (1 - k1):
            price = no
            mp = -direct
            entt = nt
            enpp = hpp = lpp = price
        if mp != 0:
            hpp = max(hpp, nh)
            lpp = min(lpp, nl)
            # long 
            spp = round(hpp * (1 - s1), 5)
            if mp > 0 and nl <= spp: # 止损
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0
            spp = round(hpp * (1 - s1), 5)
            if mp > 0 and nl <= spp: # 止盈
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0
            # short
            spp = round(lpp * (1 + s1), 5)
            if mp < 0 and nh >= spp: # 止损
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0
            spp = round(lpp * (1 + s1), 5)
            if mp < 0 and nh >= spp: # 止盈
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0
        mp_t = mp
    return trans


# 固定百分比，止盈/止损 with ATR
@numba.jit(nopython=True)
def break_atr(data, length, k1, s1, s2, direct):
    trans, mp = [], 0
    for i in range(length, data.shape[0] - 1):
        t, o, h, l, c, upp, dnn, atr = data[i,0], data[i,1], data[i,2], data[i,3], \
            data[i,4], data[i,5], data[i,6], data[i,7]
        pos = i + 1
        nt, no, nh, nl, nc, nu, nd, natr = data[pos,0], data[pos,1], data[pos,2], data[pos,3], \
            data[pos,4], data[pos,5], data[pos,6], data[i, 7]
        if mp == 0 and upp - no > (k1 * atr):
            price = no
            mp = direct
            entt = nt
            enpp = price
        if mp == 0 and no - dnn > (k1 * atr):
            price = no
            mp = -direct
            entt = nt
            enpp = price
        if mp != 0:
            # long 
            spp = round(enpp - s1 * atr, 5)
            if mp > 0 and nl <= spp: # 止损
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0
            spp = round(enpp + s2 * atr, 5)
            if mp > 0 and nh >= spp: # 止盈
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0
            spp = round(enpp + s1 * atr, 5)
            # short
            if mp < 0 and nh >= spp: # 止损
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0
            spp = round(enpp - s2 * atr, 5)
            if mp < 0 and nl <= spp: # 止盈
                price = spp
                trans.append([mp, enpp, price, entt, nt])
                mp = 0
    return trans