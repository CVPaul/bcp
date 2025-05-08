import sqlite3
import pandas as pd

from datetime import datetime as dt


def get_kline(symbol, freq, start_time=None, end_time=None, set_index=True):
    if end_time:
        end_time = pd.to_datetime(str(end_time)).timestamp() * 1000
    else:
        end_time = dt.now().timestamp() * 1000
    if start_time:
        start_time = pd.to_datetime(str(start_time)).timestamp() * 1000
    else:
        start_time = 0
    conn = sqlite3.connect(f'data/{symbol}.db')
    df = pd.read_sql(
        f"SELECT * FROM klines WHERE start_t >= {start_time} "
        f"AND start_t  < {end_time} ORDER BY start_t", conn)
    if set_index:
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