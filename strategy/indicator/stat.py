#!/usr/bin/env python
#-*- coding:utf-8 -*-


import numpy as np

from strategy.indicator.common import Indicator


# ----------->statistic indicators<-----------


class Slope(Indicator):
    
    def __init__(self, length):
        super().__init__(length)
    
    def update(self, value):
        k = b = None
        val = self.put(value)
        if not np.isnan(val[0]):
            x = (self.hist[:, 0] - self.hist[0, 0]) / 60000 # ms -> s
            y = (self.hist[:, 1] - self.hist[0, 1]) * 100 # convert to percent
            sum_x, sum_y = x.sum(), y.sum()
            sum_xy = (x * y).sum()
            sum_x2 = (x ** 2).sum()
            # 计算斜率m和截距b
            k = (self.length * sum_xy - sum_x * sum_y) / (self.length * sum_x2 - sum_x ** 2)
            b = (sum_y - k * sum_x) / self.length
        self.value = k
        return k, b
    
