#!/usr/bin/env python
#-*- coding:utf-8 -*-


class HistStore:

    def __init__(self, length):
        self.open = []
        self.high = []
        self.low = []
        self.close = []
        self.length = length
        self.maxlen = max(2 * self.length, 1000000)
    
    def append(self, o, c, h, l):
        self.open.append(o)
        self.high.append(h)
        self.low.append(l)
        self.close.append(c)
        if len(self.high) > self.maxlen:
            del self.open[-self.length:]
            del self.high[-self.length:]
            del self.low[-self.length:]
            del self.close[-self.length:]
    
    def __len__(self):
        return len(self.high)

    def empty(self):
        return len(self.high) == 0


class Chart:
    # base class of chart

    def __init__(self, length):
        # 注意这里的length是bar的长度不是产生的brick的个数，这样是为了和其他kline的indicator对齐
        self.length = length
        self.hist = HistStore(length)

    def update(self, price):
        raise NotImplementedError('you should implement it by yourself!')
    

class Renko(Chart):
    # renko chart

    def __init__(self, ratio, length, df):
        super().__init__(length)
        self.ratio = ratio
        # open, close, high, low
        self.init(
            df.close.values,
            df.open.values[0]
        )
        # 注意此时len(self.hist)基本上不等于length，极端情况可能会是0，
        # 需要特殊处理，e.g先init再update
    
    def init(self, close, o): # o means open/start price
        # init the first brick
        i, count = 0, 0
        self.span = o * self.ratio
        while close[i] < o + self.span and \
            close[i] > o - self.span:
            i += 1
        while i < self.length:
            while close[i] >= o + self.span:
                self.hist.append(o, o + self.span, o + self.span, o)
                o += self.span
                count += 1
            while close[i] <= o - self.span:
                self.hist.append(o, o - self.span, o, o - self.span)
                o -= self.span
                count += 1
            i += 1
        return count
    
    def update(self, price, open):
        count = 0
        if open:
            self.span = self.ratio * open
            last_close = self.hist.close[-1]
            if  last_close != open:
                self.hist.append( # 前一天的最后一个brick
                    last_close, open,
                    max(last_close, open),
                    min(last_close, open))
            count += 1
        # if last brick is positive
        h, l = self.hist.high[-1], self.hist.low[-1]
        while price >= h + self.span:
            self.hist.append(h, h + self.span, h + self.span, h)
            h += self.span
            count += 1
        while price <= l - self.span:
            self.hist.append(l, l - self.span, l, l - self.span)
            l -= self.span
            count += 1
        return count





