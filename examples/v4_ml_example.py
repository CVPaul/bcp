#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt

from tools.visual.inspect import plot_df
from prototype import v4

def calculate_features(df):
    """创建技术指标特征"""
    # 基础价格特征
    df['returns'] = df['close'].pct_change()
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    df['high_low_ratio'] = df['high'] / df['low']
    df['close_open_ratio'] = df['close'] / df['open']
    
    # 波动率特征
    for window in [5, 10, 20, 30]:
        # 移动平均
        df[f'ma_{window}'] = df['close'].rolling(window=window).mean()
        # 标准差
        df[f'std_{window}'] = df['close'].rolling(window=window).std()
        # 收益率统计
        df[f'returns_{window}'] = df['returns'].rolling(window=window).mean()
        df[f'returns_std_{window}'] = df['returns'].rolling(window=window).std()
        # 价格与移动平均的距离
        df[f'ma_dist_{window}'] = (df['close'] - df[f'ma_{window}']) / df[f'ma_{window}']
    
    # 成交量特征
    df['volume_ma5'] = df['volume'].rolling(window=5).mean()
    df['volume_ma20'] = df['volume'].rolling(window=20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma20']
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    df['macd'] = macd
    df['macd_signal'] = signal
    df['macd_hist'] = macd - signal
    
    # ATR相关特征
    df['atr_ratio'] = df['ATR'] / df['close']
    df['hl_range'] = (df['high'] - df['low']) / df['close']
    
    # 趋势特征
    df['trend_5'] = df['close'].rolling(5).apply(lambda x: 1 if x.iloc[-1] > x.iloc[0] else -1)
    df['trend_20'] = df['close'].rolling(20).apply(lambda x: 1 if x.iloc[-1] > x.iloc[0] else -1)
    
    # 信号特征
    df['signal_ma5'] = df['signal'].rolling(5).mean()
    df['signal_std5'] = df['signal'].rolling(5).std()
    df['signal_change'] = df['signal'].diff()
    
    # 删除包含NaN的行
    df = df.dropna()
    
    return df

def create_features(df):
    """特征工程主函数"""
    # 创建技术指标特征
    df = calculate_features(df)
    
    # 创建目标变量：下一个K线的收益是否与信号方向一致
    df['next_return'] = df['returns'].shift(-1)
    df['success'] = ((df['signal'] * df['next_return']) > 0).astype(int)
    
    # 删除包含NaN的行
    df = df[df['signal'] != 0]  # 只保留有信号的行
    df = df.dropna()
    return df

def calculate_returns(df, signal_col='signal'):
    """计算策略收益"""
    df['position'] = df[signal_col].shift(1).fillna(0)
    df['strategy_returns'] = df['position'] * df['returns']
    df['cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
    
    # 计算统计指标
    total_return = df['cumulative_returns'].iloc[-1] - 1
    daily_returns = df['strategy_returns']
    sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std()
    max_drawdown = (df['cumulative_returns'] / df['cumulative_returns'].cummax() - 1).min()
    
    return {
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'cumulative_returns': df['cumulative_returns']
    }

def plot_results(original_results, filtered_results):
    """绘制结果对比图"""
    plt.figure(figsize=(12, 6))
    plt.plot(original_results['cumulative_returns'], label='原始信号')
    plt.plot(filtered_results['cumulative_returns'], label='过滤后信号')
    plt.title('收益曲线对比')
    plt.xlabel('时间')
    plt.ylabel('累计收益')
    plt.legend()
    plt.grid(True)
    plt.show()

def train_and_evaluate_model(X_train, X_test, y_train, y_test):
    """训练和评估模型"""
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_split=20,
        min_samples_leaf=10,
        max_features='sqrt',
        random_state=42,
        n_jobs=-1
    )

    # 训练模型
    model.fit(X_train, y_train)

    # 评估模型
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)

    # 打印分类报告
    print('\n分类报告:')
    print(classification_report(y_test, y_pred))

    # 计算和打印特征重要性
    feature_importance = pd.DataFrame({
        'feature': X_train.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print('\n前10个最重要的特征:')
    print(feature_importance.head(10))

    return model, feature_importance

def main():
    # 1. 加载数据
    print("加载数据...")
    df = pd.read_csv('v4_results.csv')
    print('数据形状:', df.shape)
    print('数据列:', df.columns.tolist())

    # 2. 特征工程
    print("\n创建特征...")
    df_features = create_features(df)
    print('特征创建后的数据形状:', df_features.shape)

    # 3. 准备训练数据
    feature_columns = [col for col in df_features.columns if col not in [
        'start_t', 'end_t', 'open', 'high', 'low', 'close', 'volume', 
        'amount', 'trade_cnt', 'taker_vol', 'taker_amt', 'signal', 
        'success', 'filtered_signal', 'next_return'
    ]]

    # 分割数据集
    train_size = int(len(df_features) * 0.8)
    X_train = df_features[feature_columns][:train_size]
    y_train = df_features['success'][:train_size]
    X_test = df_features[feature_columns][train_size:]
    y_test = df_features['success'][train_size:]

    # 标准化特征
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 转换回DataFrame以保持列名
    X_train_scaled = pd.DataFrame(X_train_scaled, columns=X_train.columns)
    X_test_scaled = pd.DataFrame(X_test_scaled, columns=X_test.columns)

    print('\n训练集大小:', X_train.shape)
    print('测试集大小:', X_test.shape)

    # 4. 训练模型
    print("\n训练模型...")
    model, feature_importance = train_and_evaluate_model(
        X_train_scaled, X_test_scaled, y_train, y_test
    )

    # 5. 使用模型过滤信号
    print("\n过滤信号...")
    # 准备所有数据的特征
    X_all = df_features[feature_columns]
    X_all_scaled = pd.DataFrame(
        scaler.transform(X_all),
        columns=X_all.columns
    )
    
    # 获取预测概率
    prediction_proba = model.predict_proba(X_all_scaled)
    
    # 设置不同的概率阈值来筛选信号
    thresholds = [0, 0.6, 0.65, 0.7, 0.75]
    best_threshold = None
    best_sharpe = float('-inf')
    best_filtered_signal = None
    
    print("\n测试不同的概率阈值:")
    
    for threshold in thresholds:
        # 创建过滤后的信号
        filtered_signal = np.zeros(len(df_features))
        high_prob_mask = prediction_proba[:, 1] >= threshold
        filtered_signal[high_prob_mask] = df_features.loc[high_prob_mask, 'signal']
        
        # 计算该阈值下的表现
        df_features['test_signal'] = filtered_signal
        test_results = calculate_returns(df_features, 'test_signal')
        
        print(f"\n阈值 {threshold}:")
        print(f"信号数量: {(filtered_signal != 0).sum()}")
        print(f"总收益率: {test_results['total_return']:,.2%}")
        print(f"夏普比率: {test_results['sharpe_ratio']:.2f}")
        print(f"最大回撤: {test_results['max_drawdown']:,.2%}")
        
        # 更新最佳阈值
        if test_results['sharpe_ratio'] > best_sharpe:
            best_sharpe = test_results['sharpe_ratio']
            best_threshold = threshold
            best_filtered_signal = filtered_signal.copy()
    
    print(f"\n选择最佳阈值 {best_threshold}")
    df_features['filtered_signal'] = best_filtered_signal

    print('原始信号数量:', (df_features['signal'] != 0).sum())
    print('过滤后信号数量:', (df_features['filtered_signal'] != 0).sum())

    # 6. 回测过滤后的信号
    print("\n计算回测结果...")
    original_results = calculate_returns(df_features, 'signal')
    filtered_results = calculate_returns(df_features, 'filtered_signal')

    # 打印结果比较
    print('\n原始信号表现:')
    print(f'总收益率: {original_results["total_return"]:,.2%}')
    print(f'夏普比率: {original_results["sharpe_ratio"]:.2f}')
    print(f'最大回撤: {original_results["max_drawdown"]:,.2%}')

    print('\n过滤后信号表现:')
    print(f'总收益率: {filtered_results["total_return"]:,.2%}')
    print(f'夏普比率: {filtered_results["sharpe_ratio"]:.2f}')
    print(f'最大回撤: {filtered_results["max_drawdown"]:,.2%}')

    # 绘制结果
    plot_results(original_results, filtered_results)

    # 7. 保存过滤后的信号
    output_file = 'v4_filtered_results.csv'
    df_features[['start_t', 'close', 'signal', 'filtered_signal']].to_csv(output_file, index=False)
    print(f'\n过滤后的信号已保存到{output_file}')

if __name__ == "__main__":
    main()
