#!/usr/bin/env python
#-*- coding:utf-8 -*-


import logging
import numpy as np
import pandas as pd


class Indicator:

    def __init__(self, length):
        self.cursor = 0
        self.value = None
        self.length = length
        self.hist = [] # np.array([(np.nan, np.nan)] * self.length)

    def update(self, *args, **kw):
        raise NotImplementedError('inplement it yourself!')

    def put(self, value):
        old_val = self.hist[0]
        self.hist[:-1] = self.hist[1:]
        self.hist[-1] = value
        return old_val


class MA(Indicator):

    def __init__(self, length, df=None):
        super().__init__(length)
        if df is None:
            pass
        else:
            self.init(df.start_t.values[-1], df.close.values)

    def init(self, bar_start_time, close):
        self.value = 0.0
        self.step = 0
        start_pos = len(close) - self.length
        assert start_pos >= 0, "more hist hloc data needed"
        for i in range(start_pos, len(close)):
            self.hist.append(close[i])
            self.value += close[i]
        self.value /= self.length
        self.head = self.length - 1
        self.last_update_time = bar_start_time
        return self

    def update(self, bar_start_time, close):
        if bar_start_time <= self.last_update_time:
            logging.debug(
                f'more than once update with a same bar(start_t={bar_start_time}), '
                f'while MA::last_update_time={self.last_update_time}')
            return self.value
        self.step += 1
        self.head = (self.head + 1) % self.length
        if self.step > self.length: # 避免累计误差，每length轮重新计算一次
            self.step = 0
            self.hist[self.head] = close
            self.value = np.mean(self.hist)
        else:
            self.value += (close - self.hist[self.head]) / self.length
            self.hist[self.head] = close
        return self.value

    def calc(self, df):
        return df.close.rolling(self.length).mean()


class ATR(Indicator):

    def __init__(self, length, df=None):
        super().__init__(length)
        if df is None:
            pass
        else:
            self.init(
                df.start_t.values[-1],
                df.high.values,
                df.low.values,
                df.close.values)
    
    def init(self, bar_start_time, high, low, close):
        self.value = 0.0
        self.step = 0
        start_pos = len(close) - self.length
        assert start_pos >= 1, "more hist hloc data needed"
        self.prev_close = close[start_pos - 1]
        for i in range(start_pos, len(close)):
            t1 = abs(high[i] - self.prev_close)
            t2 = abs(low[i] - self.prev_close)
            self.hist.append(max(high[i] - low[i], t1, t2))
            self.value += self.hist[-1]
            self.prev_close = close[i]
        self.value /= self.length
        self.head = self.length - 1
        self.last_update_time = bar_start_time
        return self
    
    def calc(self, df):
        lc = df.close.shift(1)
        t1 = df.high - lc
        t2 = df.low - lc
        hl = df.high - df.low
        return pd.concat([
            hl, t1.abs(), t2.abs()],
            axis=1
        ).max(axis=1).rolling(self.length).mean()
    
    def update(self, bar_start_time, high, low, close):
        if bar_start_time <= self.last_update_time:
            logging.debug(
                f'more than once update with a same bar(start_t={bar_start_time}), '
                f'while ATR::last_update_time={self.last_update_time}')
            return self.value
        t1 = abs(high - self.prev_close)
        t2 = abs(low - self.prev_close)
        v0 = max(high - low, t1, t2)
        
        self.step += 1
        self.head = (self.head + 1) % self.length
        if self.step > self.length: # 避免累计误差，每length轮重新计算一次
            self.step = 0
            self.hist[self.head] = v0
            self.value = np.mean(self.hist)
        else:
            self.value += (v0 - self.hist[self.head]) / self.length
            self.hist[self.head] = v0

        self.prev_close = close
        return self.value


class TR(Indicator):

    def __init__(self, length, df=None):
        super().__init__(length)
        if df is None:
            return
        self.init(
            df.start_t.values[-1], 
            df.high.values,
            df.low.values,
            df.close.values)
    
    def init(self, bar_start_time, high, low, close):
        self.value = 0.0
        start_pos = len(close) - self.length
        assert start_pos >= 1, "more hist hloc data needed"
        self.prev_close = close[start_pos - 1]
        for i in range(start_pos, len(close)):
            t1 = abs(high[i] - self.prev_close)
            t2 = abs(low[i] - self.prev_close)
            self.hist.append(max(high[i] - low[i], t1, t2))
            self.prev_close = close[i]
        self.value = self.hist[-1]
        self.head = self.length - 1
        self.last_update_time = bar_start_time
        return self.value
    
    def calc(self, df):
        lc = df.close.shift(1)
        t1 = df.high - lc
        t2 = df.low - lc
        hl = df.high - df.low
        return pd.concat([
            hl, t1.abs(), t2.abs()],
            axis=1
        ).max(axis=1)
    
    def update(self, bar_start_time, high, low, close):
        if bar_start_time <= self.last_update_time:
            logging.debug(
                f'more than once update with a same bar(start_t={bar_start_time}), '
                f'while TR::last_update_time={self.last_update_time}')
            return self.value
        t1 = abs(high - self.prev_close)
        t2 = abs(low - self.prev_close)
        v0 = max(high - low, t1, t2)
        
        self.head = (self.head + 1) % self.length
        self.value = v0
        self.hist[self.head] = v0

        self.prev_close = close
        return self.value


class UPP(Indicator):

    def __init__(self, length, df=None, which='high'):
        super().__init__(length)
        if df is None:
            return
        self.init(
            df.start_t.values[-1], 
            df[which].values)
    
    def init(self, bar_start_time, values):
        self.value = 0.0
        start_pos = len(values) - self.length
        assert start_pos >= 0, "more hist hloc data needed"
        for i in range(start_pos, len(values)):
            self.hist.append(values[i])
            self.value = max(self.value, self.hist[-1])
        self.head = self.length - 1
        self.last_update_time = bar_start_time
        return self
    
    def calc(self, df, which='high'):
        return df[which].rolling(self.length).max()
    
    def update(self, bar_start_time, value):
        if bar_start_time <= self.last_update_time:
            logging.debug(
                f'more than once update with a same bar(start_t={bar_start_time}), '
                f'while UPP::last_update_time={self.last_update_time}')
            return self.value
        self.head = (self.head + 1) % self.length
        if value >= self.value:
            self.value = value
        elif self.hist[self.head] >= self.value:
            self.hist[self.head] = value
            self.value = max(self.hist)
        else:
            pass # do nothing
        self.hist[self.head] = value
        return self.value


class DNN(Indicator):

    def __init__(self, length, df=None, which='low'):
        super().__init__(length)
        if df is None:
            return
        self.init(
            df.start_t.values[-1], 
            df[which].values)
    
    def init(self, bar_start_time, values):
        self.value = 1e9
        start_pos = len(values) - self.length
        assert start_pos >= 0, "more hist hloc data needed"
        for i in range(start_pos, len(values)):
            self.hist.append(values[i])
            self.value = min(self.value, self.hist[-1])
        self.head = self.length - 1
        self.last_update_time = bar_start_time
        return self
    
    def calc(self, df, which='high'):
        return df[which].rolling(self.length).min()
    
    def update(self, bar_start_time, value):
        if bar_start_time <= self.last_update_time:
            logging.debug(
                f'more than once update with a same bar(start_t={bar_start_time}), '
                f'while DNN::last_update_time={self.last_update_time}')
            return self.value
        self.head = (self.head + 1) % self.length
        if value <= self.value:
            self.value = value
        elif self.hist[self.head] <= self.value:
            self.hist[self.head] = value
            self.value = min(self.hist)
        else:
            pass # do nothing
        self.hist[self.head] = value
        return self.value
