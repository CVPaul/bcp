import plotly.io as pio
import plotly.graph_objects as go


def analysis(df):
    # Create figure
    fig = go.Figure(data=[
        go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='DOGE/USD'
        ),
        go.Scatter(
            x=df['timestamp'],
            y=df['M1'],
            line=dict(color='orange', width=0.5),
            name='M1'
        ),
        go.Scatter(
            x=df['timestamp'],
            y=df['M2'],
            line=dict(color='blue', width=0.5),
            name='M2'
        ),
        go.Scatter(
            x=df['timestamp'],
            y=df['M3'],
            line=dict(color='purple', width=1, dash='dot'),
            name='M3'
        ),
        go.Scatter(
            x=df[df['buy']]['timestamp'],
            y=df[df['buy']]['close'],
            mode='markers',
            marker_symbol='triangle-up',
            marker_color='lime',
            marker_size=11,
            name='Buy Signal'
        ),
        go.Scatter(
            x=df[df['sell']]['timestamp'],
            y=df[df['sell']]['close'],
            mode='markers',
            marker_symbol='triangle-down',
            marker_color='red',
            marker_size=11,
            name='Sell Signal'
        )
    ])
    
    fig.update_layout(
        title=f'Technical Analysis',
        xaxis_rangeslider_visible=False,
        yaxis_title='Price (USD)',
        hovermode='x unified',
        showlegend=True
    )
    return fig