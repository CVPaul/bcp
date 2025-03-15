import sqlite3
import pandas as pd

def aggregate_klines():
    conn = sqlite3.connect('data/DOGEUSD_PERP.db')
    
    # 读取原始1分钟K线数据
    df = pd.read_sql("SELECT * FROM klines ORDER BY start_t", conn)
    
    # 转换时间戳为datetime并创建小时分组
    df['start_dt'] = pd.to_datetime(df['start_t'], unit='ms')
    df['hour'] = df['start_dt'].dt.floor('H')
    
    # 定义聚合规则
    agg_funcs = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'amount': 'sum',
        'trade_cnt': 'sum',
        'taker_vol': 'sum',
        'taker_amt': 'sum',
        'end_t': 'max'
    }
    
    # 执行聚合
    hourly_df = df.groupby('hour').agg(agg_funcs)
    
    # 转换小时开始时间到Unix时间戳
    hourly_df['start_t'] = (hourly_df['hour'].astype(int) // 10**9).astype('int64')
    
    # 选择输出字段并调整顺序
    output_cols = ['start_t', 'open', 'high', 'low', 'close', 'volume', 'end_t', 
                  'amount', 'trade_cnt', 'taker_vol', 'taker_amt']
    result_df = hourly_df[output_cols].reset_index(drop=True)
    
    # 保存到新表
    result_df.to_sql('hourly_klines', conn, if_exists='replace', index=False)
    conn.close()
    
if __name__ == '__main__':
    aggregate_klines()
