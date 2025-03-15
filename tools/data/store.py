import sqlite3
import pandas as pd


def get_kline(symbol, freq):
    conn = sqlite3.connect(f'data/{symbol}.db')
    df = pd.read_sql("SELECT * FROM klines ORDER BY start_t", conn)
    df.index = pd.to_datetime(df['start_t'], unit='ms')
    conn.close()
    if freq == 1:
        return df
    # 转换时间戳为datetime并创建小时分组
    # 定义聚合规则
    agg_funcs = {
        'start_t': 'min', 'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum', 'amount': 'sum', 'trade_cnt': 'sum',
        'taker_vol': 'sum', 'taker_amt': 'sum', 'end_t': 'max'
    }
    # 执行聚合
    df = df.resample(f'{freq}min').agg(agg_funcs)
    return df