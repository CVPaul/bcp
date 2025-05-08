import sqlite3
import pandas as pd
import talib

def load_data():
    conn = sqlite3.connect('data/DOGEUSD_PERP.db')
    query = "SELECT * FROM klines ORDER BY start_t"
    df = pd.read_sql(query, conn)
    return df

def calculate_atr(df, period=14):
    df['TR'] = talib.TRANGE(df['high'], df['low'], df['close'])
    df['ATR'] = talib.SMA(df['TR'], timeperiod=period)
    return df

def backtest(k=1.5, atr_period=14, stop_loss=0.02, take_profit=0.05):
    df = load_data()
    df = calculate_atr(df, atr_period)
    df['high_30m'] = df['high'].rolling(30).max()
    df['low_30m'] = df['low'].rolling(30).min()
    
    balance = 10000
    position = None
    entry_price = 0
    trades = []
    
    for _, row in df.iterrows():
        if position is None:
            # 开多仓条件：价格从30分钟低点回升超过k*ATR
            if row['close'] > row['high_30m'] - k * row['ATR']:
                position = 'long'
                entry_price = row['close']
                stop = entry_price * (1 - stop_loss)
                take = entry_price * (1 + take_profit)
            # 开空仓条件：价格从30分钟高点回落超过k*ATR
            elif row['close'] < row['low_30m'] + k * row['ATR']:
                position = 'short'
                entry_price = row['close']
                stop = entry_price * (1 + stop_loss)
                take = entry_price * (1 - take_profit)
        else:
            if position == 'long':
                # 平多仓条件：价格从高点回落超过k*ATR 或 触及止损/止盈
                if row['close'] <= row['high_30m'] - k * row['ATR']:
                    profit = (row['close'] - entry_price) / entry_price
                    balance *= (1 + profit)
                    trades.append({'entry': entry_price, 'exit': row['close'], 'profit': profit})
                    position = None
                elif row['close'] <= stop or row['close'] >= take:
                    if row['close'] <= stop:
                        profit = (row['close'] - entry_price) / entry_price
                    else:
                        profit = (row['close'] - entry_price) / entry_price
                    balance *= (1 + profit)
                    trades.append({
                        'entry': entry_price,
                        'exit': row['close'],
                        'profit': profit
                    })
                    position = None
            elif position == 'short':
                # 平空仓条件：价格从低点回升超过k*ATR 或 触及止损/止盈
                if row['close'] >= row['low_30m'] + k * row['ATR']:
                    profit = (entry_price - row['close']) / entry_price
                    balance *= (1 + profit)
                    trades.append({
                        'entry': entry_price,
                        'exit': row['close'],
                        'profit': profit
                    })
                    position = None
                elif row['close'] >= stop or row['close'] <= take:
                    if row['close'] >= stop:
                        profit = (entry_price - row['close']) / entry_price
                    else:
                        profit = (entry_price - row['close']) / entry_price
                    balance *= (1 + profit)
                    trades.append({
                        'entry': entry_price,
                        'exit': row['close'],
                        'profit': profit
                    })
                    position = None
    
    return balance, trades

import numpy as np

if __name__ == '__main__':
    final_balance, trades = backtest()
    pd.DataFrame(trades).to_csv("trades.csv")
    print(f"Final balance: {final_balance}")
    print(f"Number of trades: {len(trades)}")
    
    # 计算夏普率
    if len(trades) == 0:
        sharpe_ratio = 0.0
    else:
        returns = [t['profit'] for t in trades]
        avg_return = np.mean(returns)
        risk_free = 0.0  # 假设无风险利率为0
        std_dev = np.std(returns)
        sharpe_ratio = (avg_return - risk_free) / std_dev if std_dev != 0 else 0.0
    print(f"夏普率: {sharpe_ratio:.4f}")
