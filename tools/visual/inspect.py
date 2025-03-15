import plotly.io as pio
import plotly.graph_objects as go

def analysis(df):
    fig = go.Figure()

    # Add candlestick
    fig.add_trace(
        go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='DOGE/USD'
        )
    )

    # Add M1 with thicker line
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['M1'],
            line=dict(color='orange', width=1),
            name='M1'
        )
    )

    # Add M2 with thicker line
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['M2'],
            line=dict(color='blue', width=1, dash='dot'),
            name='M2'
        )
    )

    # Add M3 with thicker line
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['M3'],
            line=dict(color='purple', width=1),
            name='M3'
        )
    )

    # Add Buy/Sell signals
    fig.add_trace(
        go.Scatter(
            x=df[df['buy'] > 0]['timestamp'],
            y=df[df['buy'] > 0]['close'],
            mode='markers',
            marker_symbol='triangle-up',
            marker_color='lime',
            marker_size=11,
            name='Buy Signal'
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df[df['sell'] > 0]['timestamp'],
            y=df[df['sell'] > 0]['close'],
            mode='markers',
        marker_symbol='triangle-down',
        marker_color='blue',
        marker_size=11,
            name='Sell Signal'
        )
    )

    # Add M4 bar on secondary y-axis
    fig.add_trace(
        go.Bar(
            x=df['timestamp'],
            y=df['M4'],
            name='M4',
            yaxis='y2',  # Assign to secondary y-axis
            marker_color='gray',
            opacity=0.6
        )
    )

    # Configure dual y-axes layout
    fig.update_layout(
        title='Technical Analysis',
        xaxis_rangeslider_visible=False,
        yaxis=dict(
            title='Price (USD)',
            side='left',
            showgrid=True
        ),
        yaxis2=dict(
            title='M4 Value',
            side='right',
            overlaying='y',
            showgrid=False
        ),
        height=1600,
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    return fig
