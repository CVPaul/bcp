import numpy as np
import pandas as pd
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import logging
import time

def main():
    start_time = time.time()
    conn = sqlite3.connect('data/DOGEUSD_PERP.db')
    df = pd.read_sql("SELECT * FROM klines ORDER BY start_t", conn)
    logging.info(f"Data loaded in {time.time()-start_time:.2f}s - {len(df)} rows")
    
    # 计算MA7
    df['ma7'] = df['close'].rolling(window=7).mean()
    logging.info(f"MA7 calculation completed at {time.time()-start_time:.2f}s")
    
    # 更高效的斜率计算
    slope_start = time.time()
    logging.info("Calculating MA7 slope using vectorized approach")
    df['ma7_slope'] = df['ma7'].diff()
    logging.info(f"Slope calculation took {time.time()-slope_start:.2f}s ({time.time()-start_time:.2f}s total)")

    # 检测斜率方向变化
    df['slope_sign'] = np.sign(df['ma7_slope'])
    df['slope_sign_prev'] = df['slope_sign'].shift(1)
    df['slope_change'] = (df['slope_sign'] != df['slope_sign_prev']) & df['slope_sign'].notnull()

    # 特征工程
    df['price_ma_diff'] = df['close'] - df['ma7']
    df['volatility'] = df['high'].rolling(7).max() - df['low'].rolling(7).min()
    df['slope_abs'] = np.abs(df['ma7_slope'])
    
    # 生成信号
    df['signal'] = 0
    df.loc[df['slope_change'] & (df['slope_sign'] > 0), 'signal'] = 1  # 做多
    df.loc[df['slope_change'] & (df['slope_sign'] < 0), 'signal'] = -1  # 做空
    
    # 模型过滤
    np.random.seed(42)
    df['label'] = np.random.choice([0, 1], size=len(df), p=[0.4, 0.6])  # 需替换为真实标签

    X = df[['price_ma_diff', 'volatility', 'slope_abs']].dropna()
    y = df.loc[X.index, 'label']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    train_start = time.time()
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    logging.info(f"Model training took {time.time()-train_start:.2f}s ({time.time()-start_time:.2f}s total)")

    # 预测并应用过滤
    features = df[['price_ma_diff', 'volatility', 'slope_abs']]  # 保留列名
    df['valid'] = model.predict(features)
    df['final_signal'] = df['signal'] * df['valid']
    
    # 回测计算
    backtest_start = time.time()
    logging.info("Starting backtesting process")

    # 计算持仓和收益
    df['position'] = df['final_signal'].shift(1).fillna(0)
    
    # 下一周期收盘价
    df['next_close'] = df['close'].shift(-1)
    df['daily_pnl'] = df['position'] * (df['next_close'] - df['close'])
    df = df.iloc[:-1]  # 移除最后缺失行
    
    # 累计收益和指标
    df['cumulative_pnl'] = df['daily_pnl'].cumsum()
    total_pnl = df['cumulative_pnl'].iloc[-1]

    # 最大回撤计算
    peak = df['cumulative_pnl'].expanding().max()
    peak = peak.mask(peak == 0, 1e-10)  # 避免除以零
    dd = (df['cumulative_pnl'] - peak) / peak
    mdd = dd.min()

    # 夏普比率
    epsilon = 1e-10
    daily_returns = df['daily_pnl']
    std = daily_returns.std()
    sharpe_ratio = (daily_returns.mean() / (std + epsilon)) * np.sqrt(252) if std > epsilon else 0

    # 结构化输出结果
    logging.info("Backtest Results:")
    logging.info(f"Total PNL: ${total_pnl:.2f}")
    logging.info(f"Max Drawdown: {mdd:.2%}")
    logging.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    logging.info(f"Processed {len(df)} rows of data")

    # 计算总耗时
    total_time = time.time() - start_time
    logging.info(f"Total execution time: {total_time:.2f}s")

    # 保存结果到文件
    with open("backtest_metrics.txt", "w") as f:
        f.write(f"Total PNL: ${total_pnl:.2f}\n")
        f.write(f"Max Drawdown: {mdd:.2%}\n")
        f.write(f"Sharpe Ratio: {sharpe_ratio:.2f}\n")
        
    
if __name__ == '__main__':
    logging.info("Starting strategy execution")
    main()
    logging.info("Strategy execution completed")
