import numpy as np

from collections import deque
from datetime import datetime

class PriceChannelStrategy:
    def __init__(self, window_size=20):
        self.window_size = window_size  # 通道周期
        self.position = 0  # 当前持仓 (-1:空, 0:平, 1:多)
        self.entry_price = 0  # 入场价格
        
        # 价格通道数据
        self.high_prices = deque(maxlen=window_size)
        self.low_prices = deque(maxlen=window_size)
        self.close_prices = deque(maxlen=window_size)
        
        # 通道参数
        self.channel_multiplier = 1.0  # 通道宽度倍数
        self.entry_threshold = 0.3  # 入场阈值（通道宽度的百分比）
        self.exit_threshold = 0.5   # 出场阈值
        
        # 风控参数
        self.stop_loss = 0.02  # 止损比例
        self.take_profit = 0.03  # 止盈比例
        
        # 通道价格
        self.upper_channel = None
        self.lower_channel = None
        self.middle_channel = None
        
        # 统计数据
        self.last_trade_price = None
        self.trades_count = 0
        self.winning_trades = 0
        
    def calculate_channels(self):
        """计算价格通道"""
        if len(self.high_prices) < self.window_size:
            return False
            
        # 计算基础通道
        self.upper_channel = max(self.high_prices)
        self.lower_channel = min(self.low_prices)
        self.middle_channel = (self.upper_channel + self.lower_channel) / 2
        
        # 调整通道宽度
        channel_width = self.upper_channel - self.lower_channel
        self.upper_channel += channel_width * (self.channel_multiplier - 1)
        self.lower_channel -= channel_width * (self.channel_multiplier - 1)
        
        return True
        
    def get_channel_position(self, price):
        """计算价格在通道中的相对位置"""
        if not all([self.upper_channel, self.lower_channel]):
            return 0
            
        channel_width = self.upper_channel - self.lower_channel
        if channel_width == 0:
            return 0
            
        relative_position = (price - self.lower_channel) / channel_width
        return relative_position
        
    def check_risk_management(self, current_price):
        """检查止盈止损"""
        if self.position == 0 or not self.entry_price:
            return None
            
        profit_pct = (current_price - self.entry_price) / self.entry_price
        if self.position == -1:
            profit_pct = -profit_pct
            
        if profit_pct <= -self.stop_loss:
            return "STOP_LOSS"
        elif profit_pct >= self.take_profit:
            return "TAKE_PROFIT"
            
        return None
        
    def is_trend_confirmed(self, price):
        """确认趋势方向"""
        if len(self.close_prices) < 3:
            return False
            
        # 使用简单的移动平均判断趋势
        ma_short = np.mean(list(self.close_prices)[-3:])
        ma_long = np.mean(list(self.close_prices))
        
        if price > ma_short > ma_long:
            return 1  # 上涨趋势
        elif price < ma_short < ma_long:
            return -1  # 下跌趋势
            
        return 0
        
    def update(self, price, high=None, low=None):
        """
        更新策略状态并返回交易信号
        price: 当前价格
        high: 当前K线最高价（如果是K线数据）
        low: 当前K线最低价（如果是K线数据）
        """
        # 如果没有提供high和low，使用当前价格
        high = high if high is not None else price
        low = low if low is not None else price
        
        # 更新价格数据
        self.high_prices.append(high)
        self.low_prices.append(low)
        self.close_prices.append(price)
        
        # 检查数据是否足够
        if not self.calculate_channels():
            return None
            
        # 检查止盈止损
        risk_signal = self.check_risk_management(price)
        if risk_signal:
            self.position = 0
            return "CLOSE"
            
        # 计算价格在通道中的位置
        channel_position = self.get_channel_position(price)
        trend = self.is_trend_confirmed(price)
        
        # 交易信号逻辑
        signal = None
        
        if self.position == 0:  # 无持仓
            if channel_position < self.entry_threshold and trend > 0:
                # 价格接近下轨且趋势向上时做多
                signal = "BUY"
                self.position = 1
                self.entry_price = price
                
            elif channel_position > (1 - self.entry_threshold) and trend < 0:
                # 价格接近上轨且趋势向下时做空
                signal = "SELL"
                self.position = -1
                self.entry_price = price
                
        elif self.position == 1:  # 持有多仓
            if channel_position > (1 - self.exit_threshold) or trend < 0:
                # 价格接近上轨或趋势转向时平仓
                signal = "CLOSE"
                self.position = 0
                
        elif self.position == -1:  # 持有空仓
            if channel_position < self.exit_threshold or trend > 0:
                # 价格接近下轨或趋势转向时平仓
                signal = "CLOSE"
                self.position = 0
                
        # 更新交易统计
        if signal and signal != "CLOSE":
            self.last_trade_price = price
            self.trades_count += 1
            
        return signal
        
    def get_channel_info(self):
        """获取通道信息"""
        return {
            'upper': self.upper_channel,
            'middle': self.middle_channel,
            'lower': self.lower_channel,
            'width': self.upper_channel - self.lower_channel if self.upper_channel else 0
        }
