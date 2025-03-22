import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go

def calculate_metrics(returns):
    cumulative = (1 + returns).cumprod()
    peak = np.maximum.accumulate(cumulative)
    mdd = ((cumulative / peak) - 1).min()
    sharpe = (returns.mean() / returns.std()) * np.sqrt(24*365)  # 假设1分钟数据，年化
    return mdd, sharpe

def backtest_strategy(data):
    # 计算MA7
    data['MA7'] = data['close'].rolling(window=7).mean()
    # 计算diff（MA7的斜率变化）
    data['diff'] = data['MA7'].diff()
    # 生成信号：当diff由正转负做空，负转正做多
    data['position'] = 0
    data.loc[1:, 'position'] = np.where(
        (data['diff'].shift(1) > 0) & (data['diff'] < 0),
        -1,
        np.where(
            (data['diff'].shift(1) < 0) & (data['diff'] > 0),
            1,
            0
        )
    )

    # 计算每日收益率（假设每分钟交易）
    data['return'] = data['position'].shift(1) * (np.log(data['close']/data['close'].shift(1)))
    data['return'].iloc[0] = 0  # 第一个值设为0
    
    total_pnl = data['return'].sum()
    mdd, sharpe = calculate_metrics(data['return'])
    
    return total_pnl, mdd, sharpe

def main():
    # 连接数据库（假设SQLite）
    engine = create_engine('sqlite:///data/DOGEUSD_PERP.db')
    from sqlalchemy import text
    with engine.connect() as conn:
        data = pd.read_sql(sql=text('SELECT * FROM klines ORDER BY start_t'), con=conn)
    data.set_index('start_t', inplace=True)
    
    pnl, mdd, sharpe = backtest_strategy(data)
    print(f"Total PNL: {pnl:.4f}")
    print(f"Max Drawdown: {mdd:.4f}")
    print(f"Sharpe Ratio: {sharpe:.4f}")

    # 绘制净值曲线
    data['cumulative_return'] = (1 + data['return']).cumprod()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['cumulative_return'], name='Cumulative Return'))
    fig.update_layout(
        title='Strategy Performance',
        xaxis_title='Time',
        yaxis_title='Return',
        showlegend=True
    )
    fig.show()

    # 绘制价格与MA7的交互式图表
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=data.index, y=data['close'], name='Price'))
    fig_price.add_trace(go.Scatter(x=data.index, y=data['MA7'], name='MA7', line=dict(color='orange')))
    fig_price.update_layout(
        title='Price vs 7-Day Moving Average',
        xaxis_title='Time',
        yaxis_title='Price',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    fig_price.show()

if __name__ == "__main__":
    main()
