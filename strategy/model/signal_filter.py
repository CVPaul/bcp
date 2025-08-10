import itertools
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
import matplotlib.pyplot as plt 
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report)


class SignalFilter:
    def get_label(self, sharp):
        """
        根据夏普比率生成标签
        """
        if sharp > 0.8:  # 高夏普比率
            return 2
        elif sharp < -0.5:  # 低夏普比率
            return 0
        else:  # 中性
            return 1
    def __init__(self):
        self.model = lgb.LGBMClassifier(
            objective='multiclass',
            num_class=3,
            n_estimators=1000,     # 增加树的数量
            learning_rate=0.05,    # 降低学习率
            max_depth=8,           # 增加树的深度
            num_leaves=100,        # 增加叶子节点数
            min_child_samples=10,  # 减少每个叶子节点最小样本数
            subsample=0.9,         # 增加采样比例
            colsample_bytree=0.9,  # 增加特征采样比例
            reg_alpha=0.5,         # 增加L1正则化
            reg_lambda=1.5,        # 增加L2正则化
            class_weight='balanced', # 处理类别不平衡
            random_state=42,
            importance_type='gain'
        )
        self.important_features = None  # 存储重要特征
        
    def prepare_features(self, df):
        """准备特征
        Args:
            df (pd.DataFrame): 包含交易信号的DataFrame，至少需要包含以下列:
                - pos: 交易方向 (1: 做多, -1: 做空)
                - profit: 该笔交易的盈亏
                以及其他市场特征列
        """
        # 创建特征的副本以避免警告
        df = df.copy()
        
        # 计算收益率特征
        df['return'] = (df['profit'] / df['enpp']).shift(1)
        
        # 计算风险调整后的收益
        # 1. 计算移动波动率
        for window in [10, 20, 40]:
            df[f'vol_{window}'] = df['return'].rolling(window).std()
            # 计算移动夏普比率
            df[f'sharpe_{window}'] = df['return'].rolling(window).mean() / df[f'vol_{window}'].replace(0, np.inf)
            # 计算最大回撤
            rolling_max = df['return'].rolling(window).max()
            df[f'drawdown_{window}'] = (rolling_max - df['return']) / rolling_max
            
        # 计算ATR
        def calculate_atr(high, low, close, window=14):
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(window).mean()
            
        df['ATR'] = calculate_atr(df['high'], df['low'], df['close'])
        df['ATR_ratio'] = df['ATR'] / df['close']  # 归一化ATR
        
        # 添加价格特征
        df['hl_ratio'] = (df['high'] - df['low']) / df['low']  # 振幅
        df['oc_ratio'] = (df['close'] - df['open']) / df['open']  # 涨跌幅
        df['co_ratio'] = (df['close'] - df['open']) / df['high'] - df['low']  # K线实体比例
        
        # 计算价格波动强度
        df['price_volatility'] = df['hl_ratio'].rolling(window=20).std()
        df['price_momentum'] = df['close'].pct_change(periods=5).rolling(window=20).mean()
        
        # 计算成交量和价格的相关性
        def rolling_corr(x, y, window=20):
            return pd.Series(x).rolling(window).corr(pd.Series(y))
            
        df['vol_price_corr'] = rolling_corr(df['volume'], df['close'])

        # 计算移动平均线
        for window in [5, 10, 20, 60]:
            df[f'ma{window}'] = df['close'].rolling(window=window).mean()
            df[f'ma{window}_slope'] = df[f'ma{window}'].diff(5) / df[f'ma{window}']  # 均线斜率
            df[f'close_ma{window}_ratio'] = df['close'] / df[f'ma{window}']  # 价格与均线比值

        # 计算EMV (Ease of Movement Value)
        def calculate_emv(high, low, volume, window=14):
            distance = ((high + low) / 2) - ((high.shift(1) + low.shift(1)) / 2)
            box_ratio = (volume / 1000000) / (high - low)
            emv = distance / box_ratio
            return emv.rolling(window).mean()
        
        df['emv'] = calculate_emv(df['high'], df['low'], df['volume'])

        # 添加成交量特征
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        df['volume_ma20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma5']
        df['volume_trend'] = df['volume'].diff(5) / df['volume']
        df['amount_mean'] = df['amount'].rolling(window=20).mean()
        df['turnover_rate'] = df['volume'] * df['close'] / df['amount_mean']

        # 计算MACD
        def calculate_macd(close, fast=12, slow=26, signal=9):
            ema_fast = close.ewm(span=fast, adjust=False).mean()
            ema_slow = close.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            return macd_line, signal_line

        df['macd'], df['macd_signal'] = calculate_macd(df['close'])
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # 计算RSI
        def calculate_rsi(close, periods=14):
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))

        df['rsi'] = calculate_rsi(df['close'])

        # 计算Stochastic Oscillator
        def calculate_stoch(high, low, close, k_window=14, d_window=3):
            lowest_low = low.rolling(window=k_window).min()
            highest_high = high.rolling(window=k_window).max()
            k_line = ((close - lowest_low) / (highest_high - lowest_low)) * 100
            d_line = k_line.rolling(window=d_window).mean()
            return k_line, d_line

        df['stoch_k'], df['stoch_d'] = calculate_stoch(df['high'], df['low'], df['close'])

        # 计算布林带
        def calculate_bollinger_bands(close, window=20, num_std=2):
            middle = close.rolling(window=window).mean()
            std = close.rolling(window=window).std()
            upper = middle + (std * num_std)
            lower = middle - (std * num_std)
            return (close - middle) / (upper - lower)  # 归一化的价格位置

        df['bb_position'] = calculate_bollinger_bands(df['close'])

        # 增强时间特征
        seconds_per_hour = 3600
        seconds_per_day = 86400
        df['hour'] = (df['start_t'] % seconds_per_day) // seconds_per_hour
        df['minute'] = ((df['start_t'] % seconds_per_day) % seconds_per_hour) // 60
        df['dayofweek'] = (df['start_t'] // seconds_per_day) % 7
        
        # 添加交易时段特征
        df['is_morning'] = ((df['hour'] >= 9) & (df['hour'] < 12)).astype(int)
        df['is_afternoon'] = ((df['hour'] >= 13) & (df['hour'] < 16)).astype(int)
        df['is_opening_hour'] = (df['hour'] == 9).astype(int)
        df['is_closing_hour'] = (df['hour'] == 15).astype(int)
        
        # 计算每日价格位置
        daily_high = df.groupby((df['start_t'] // seconds_per_day))['high'].transform('max')
        daily_low = df.groupby((df['start_t'] // seconds_per_day))['low'].transform('min')
        df['price_position'] = (df['close'] - daily_low) / (daily_high - daily_low)

        # 处理缺失值
        df = df.ffill().fillna(0)
        
        # 添加与pos相关的特征
        pos_features = [col for col in df.columns if col not in [
            'pos', 'profit', 'entry_i', 'stop_i', 'enpp', 'price', 'type', 'return',
            'start_t', 'end_t'  # 排除时间戳
        ]]
        for col in pos_features:
            df[f'{col}_pos'] = df[col] * df['pos']
        
        # 计算特征相关性并移除高度相关特征
        feature_columns = pos_features + [f'{col}_pos' for col in pos_features]
        X = df[feature_columns].copy()
        
        # 计算风险调整后的收益率
        df['sharp'] = df.apply(lambda row: (row['profit'] / row['enpp']) / 
                                         (row['vol_20'] if not pd.isna(row['vol_20']) and row['vol_20'] > 0 else 0.01), 
                             axis=1)
        
        if not hasattr(self, 'selected_features'):
            # 计算相关性矩阵
            corr_matrix = X.corr().abs()
            upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
            
            # 找出相关性高于阈值的特征
            to_drop = [column for column in upper.columns if any(upper[column] > 0.95)]
            
            # 保留重要特征
            important_features = ['ATR_ratio', 'ATR', 'drawdown_20', 'vol_10', 'rsi', 
                               'macd', 'stoch_k', 'bb_position', 'price_position']
            
            # 确保重要特征不被删除
            to_drop = [col for col in to_drop if col not in important_features]
            self.selected_features = [col for col in X.columns if col not in to_drop]
        
        X = X[self.selected_features]
        
        # 标准化数值特征
        if not hasattr(self, 'feature_means'):
            self.feature_means = X.mean()
            self.feature_stds = X.std().clip(lower=1e-7)  # 避免除以0
            
        X = (X - self.feature_means) / self.feature_stds
            
        # 生成标签
        y = df['sharp'].apply(self.get_label)
            
        # 计算样本权重
        if hasattr(self, 'sample_weight'):
            sample_weight = self.sample_weight
        else:
            sample_weight = df.apply(lambda x: abs(x['profit'] / x['enpp']) + 1, axis=1)
            self.sample_weight = sample_weight
            
        return X, y, sample_weight
        
    def train(self, train_data, valid_size=0.2):
        """训练信号过滤模型
        Args:
            train_data (pd.DataFrame): 训练数据
            valid_size (float): 验证集比例
        Returns:
            tuple: (训练集指标, 验证集指标, 训练数据索引, 验证数据索引)
            
        Notes:
            使用样本权重平衡类别，增加高收益样本的重要性
        """
        X, y, sample_weight = self.prepare_features(train_data)
        
        # 分割训练集和验证集
        train_idx, valid_idx = train_test_split(
            np.arange(len(X)), 
            test_size=valid_size, 
            random_state=42, 
            shuffle=True,
            stratify=y  # 确保训练集和验证集中的正负样本比例一致
        )
        X_train, X_valid = X.iloc[train_idx], X.iloc[valid_idx]
        y_train, y_valid = y.iloc[train_idx], y.iloc[valid_idx]
        
        # 进行交叉验证
        cv_scores = cross_val_score(self.model, X_train, y_train, cv=5)
        print("\n=== 5折交叉验证结果 ===")
        print(f"准确率: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
        
        # 训练模型
        train_sample_weight = sample_weight.iloc[train_idx]
        valid_sample_weight = sample_weight.iloc[valid_idx]
        
        self.model.fit(
            X_train, y_train,
            sample_weight=train_sample_weight,
            eval_set=[(X_train, y_train), (X_valid, y_valid)],
            eval_metric=['multi_logloss', 'multi_error'],
            eval_names=['train', 'valid'],
            callbacks=[
                lgb.early_stopping(50),
                lgb.log_evaluation(100)
            ]
        )
        
        # 评估训练集
        y_pred_train = self.model.predict(X_train)
        train_metrics = self._calculate_metrics(y_train, y_pred_train)
        
        # 评估验证集
        y_pred_valid = self.model.predict(X_valid)
        valid_metrics = self._calculate_metrics(y_valid, y_pred_valid)
        
        # 绘制混淆矩阵
        self._plot_confusion_matrix(y_valid, y_pred_valid, "验证集混淆矩阵")
        
        # 打印分类报告
        print("\n=== 验证集分类报告 ===")
        print(classification_report(y_valid, y_pred_valid))
        
        # 打印特征重要性
        feature_importance = pd.DataFrame({
            'feature': X_train.columns,
            'importance': self.model.feature_importances_
        })
        feature_importance = feature_importance.sort_values('importance', ascending=False)
        print("\n=== 特征重要性排序 ===")
        print(feature_importance)
        
        # 绘制特征重要性图
        plt.figure(figsize=(10, 6))
        plt.bar(range(len(feature_importance)), feature_importance['importance'])
        plt.xticks(range(len(feature_importance)), feature_importance['feature'], rotation=45, ha='right')
        plt.title('Feature Importance')
        plt.tight_layout()
        plt.show()
        
        return train_metrics, valid_metrics, train_idx, valid_idx
    
    def _calculate_metrics(self, y_true, y_pred):
        """计算多分类评估指标"""
        return {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision_macro': precision_score(y_true, y_pred, average='macro'),
            'recall_macro': recall_score(y_true, y_pred, average='macro'),
            'f1_macro': f1_score(y_true, y_pred, average='macro')
        }
    
    def _plot_confusion_matrix(self, y_true, y_pred, title):
        """绘制混淆矩阵"""
        cm = confusion_matrix(y_true, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title(title)
        plt.ylabel('真实标签')
        plt.xlabel('预测标签')
        plt.show()
        
    def plot_feature_importance(self):
        """绘制特征重要性"""
        if not hasattr(self, 'important_features'):
            return
            
        importance = pd.DataFrame({
            'feature': self.selected_features,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=True)
        
        plt.figure(figsize=(10, max(8, len(importance) * 0.3)))
        sns.barplot(data=importance.tail(20), y='feature', x='importance')
        plt.title('特征重要性（Top 20）')
        plt.tight_layout()
        plt.show()
    
    def predict(self, data):
        """预测信号的质量
        Args:
            data (pd.DataFrame): 待预测的数据
        Returns:
            np.array: 预测结果，2表示好的信号，1表示中性信号，0表示应该过滤掉的信号
        """
        X, y, _ = self.prepare_features(data)
        
        # 获取预测概率
        proba = self.model.predict_proba(X)
        
        # 使用预测概率和阈值来做决策
        predictions = np.zeros(len(X))
        
        # 只有当好的类别的概率大于0.4时才预测为好的信号
        predictions[proba[:, 2] > 0.4] = 2
        # 当中性类别的概率大于0.5且不是好的信号时，预测为中性
        mask = (proba[:, 1] > 0.5) & (predictions != 2)
        predictions[mask] = 1
        
        if not hasattr(self, 'important_features'):
            # 在第一次预测时计算并保存特征重要性
            importance = pd.DataFrame({
                'feature': X.columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            print("\n=== 特征重要性（前20个）===")
            print(importance.head(20))
            self.important_features = importance
            
        return predictions
    
    def save_model(self, path):
        """保存模型
        Args:
            path (str): 模型保存路径
        """
        joblib.dump(self.model, path)
    
    def load_model(self, path):
        """加载模型
        Args:
            path (str): 模型文件路径
        """
        self.model = joblib.load(path)

def calculate_metrics(transactions):
    """计算交易的性能指标
    Args:
        transactions (pd.DataFrame): 交易记录
    Returns:
        dict: 包含各项性能指标的字典
    """
    # 计算累计收益
    # 如果transactions为空，返回所有指标为0
    if len(transactions) == 0:
        return {
            'total_pnl': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'profit_loss_ratio': 0,
            'total_trades': 0,
            'avg_return': 0,
            'return_std': 0,
            'sharpe_ratio': 0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0
        }
    
    cumulative_returns = transactions['profit'].cumsum()
    
    # 计算最大回撤
    running_max = cumulative_returns.expanding().max()
    drawdowns = running_max - cumulative_returns
    max_drawdown = drawdowns.max()
    
    # 计算胜率
    win_rate = (transactions['profit'] > 0).mean()
    
    # 计算盈亏比
    wins = transactions[transactions['profit'] > 0]
    losses = transactions[transactions['profit'] < 0]
    avg_win = wins['profit'].mean() if len(wins) > 0 else 0
    avg_loss = abs(losses['profit'].mean()) if len(losses) > 0 else 0
    profit_loss_ratio = avg_win / avg_loss if avg_loss != 0 else 0  # 改为0而不是inf
    
    # 计算夏普比率（假设无风险利率为0）
    returns = transactions['profit']
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() != 0 and not np.isnan(returns.std()) else 0
    
    # 计算最大连续盈利和亏损次数
    wins = (transactions['profit'] > 0).astype(int)
    losses = (transactions['profit'] < 0).astype(int)
    consecutive_wins = [len(list(v)) for k, v in itertools.groupby(wins) if k == 1]
    consecutive_losses = [len(list(v)) for k, v in itertools.groupby(losses) if k == 1]
    max_consecutive_wins = max(consecutive_wins) if consecutive_wins else 0
    max_consecutive_losses = max(consecutive_losses) if consecutive_losses else 0
    
    return {
        'total_pnl': cumulative_returns.iloc[-1],
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'profit_loss_ratio': profit_loss_ratio,
        'total_trades': len(transactions),
        'avg_return': transactions['profit'].mean(),
        'return_std': transactions['profit'].std(),
        'sharpe_ratio': sharpe,
        'max_consecutive_wins': max_consecutive_wins,
        'max_consecutive_losses': max_consecutive_losses
    }
    
def plot_equity_curve(transactions, title):
    """绘制权益曲线
    Args:
        transactions (pd.DataFrame): 交易记录
        title (str): 图表标题
    """
    equity = transactions['profit'].cumsum()
    drawdown = equity - equity.cummax()
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
    
    # 绘制权益曲线
    ax1.plot(equity.index, equity.values, label='Equity')
    ax1.set_title(title)
    ax1.set_xlabel('交易次数')
    ax1.set_ylabel('累计收益')
    ax1.grid(True)
    ax1.legend()
    
    # 绘制回撤
    ax2.fill_between(drawdown.index, drawdown.values, 0, color='red', alpha=0.3, label='Drawdown')
    ax2.set_xlabel('交易次数')
    ax2.set_ylabel('回撤')
    ax2.grid(True)
    ax2.legend()
    
    plt.tight_layout()
    plt.show()
    
def plot_monthly_stats(transactions, title):
    """绘制月度统计图
    Args:
        transactions (pd.DataFrame): 交易记录
        title (str): 图表标题
    """
    # 转换时间戳为日期时间
    transactions['date'] = pd.to_datetime(transactions['start_t'], unit='s')
    monthly = transactions.set_index('date').resample('M')
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # 月度收益
    monthly_returns = monthly['profit'].sum()
    monthly_returns.plot(kind='bar', ax=ax1)
    ax1.set_title(f"{title} - 月度收益")
    ax1.set_ylabel('收益')
    ax1.grid(True)
    
    # 月度交易次数
    monthly_trades = monthly['profit'].count()
    monthly_trades.plot(kind='bar', ax=ax2)
    ax2.set_title('月度交易次数')
    ax2.set_ylabel('交易次数')
    ax2.grid(True)
    
    plt.tight_layout()
    plt.show()

def print_metrics_comparison(before_metrics, after_metrics):
    """打印过滤前后的性能对比
    """
    print("\n=== 性能指标对比 ===")
    print(f"{'指标':<20} {'过滤前':>15} {'过滤后':>15} {'改善比例':>15}")
    print("="*65)
    
    for metric in before_metrics.keys():
        before_value = before_metrics[metric]
        after_value = after_metrics[metric]
        
        if before_value != 0:
            improvement = (after_value - before_value) / abs(before_value) * 100
        else:
            improvement = float('inf') if after_value > 0 else 0
            
        # 对于某些指标，数值太大时使用科学计数法
        if abs(before_value) > 1000:
            before_str = f"{before_value:.2e}"
        else:
            before_str = f"{before_value:.4f}"
            
        if abs(after_value) > 1000:
            after_str = f"{after_value:.2e}"
        else:
            after_str = f"{after_value:.4f}"
            
        print(f"{metric:<20} {before_str:>15} {after_str:>15} {improvement:>14.2f}%")

def print_model_metrics(name, metrics):
    print(f"\n{name}集评估指标:")
    print("-" * 40)
    for metric_name, value in metrics.items():
        print(f"{metric_name}: {value:.4f}")

def main():
    import itertools
    
    # 加载交易记录数据
    transactions = pd.read_csv('transaction.csv')
    
    print("\n=== 特征列表 ===")
    print("原始特征:", transactions.columns.tolist())
    print("\n计算技术指标...")
    
    # 添加技术指标特征，只使用开仓时的市场数据
    transactions['close_std'] = transactions['close'].rolling(20).std()
    transactions['ma5'] = transactions['close'].rolling(5).mean()
    transactions['ma10'] = transactions['close'].rolling(10).mean()
    transactions['ma20'] = transactions['close'].rolling(20).mean()
    transactions['ma5_ma20_cross'] = (transactions['ma5'] > transactions['ma20']).astype(int)
    transactions['volatility'] = transactions['close_std'] / transactions['close']
    
    # 计算动量指标
    transactions['momentum'] = transactions['close'].pct_change(5)
    transactions['momentum_ma'] = transactions['momentum'].rolling(5).mean()
    
    # 计算RSI
    def calculate_rsi(prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    transactions['rsi'] = calculate_rsi(transactions['close'])
    
    # 计算成交量相关指标
    transactions['volume_ma5'] = transactions['volume'].rolling(5).mean()
    transactions['volume_ma20'] = transactions['volume'].rolling(20).mean()
    transactions['volume_ratio'] = transactions['volume'] / transactions['volume_ma5']
    
    # 计算趋势指标
    transactions['trend'] = transactions['ma5'].diff().rolling(5).apply(lambda x: (x > 0).sum() / 5)
    transactions['price_range'] = (transactions['high'] - transactions['low']) / transactions['close']
    transactions['up_shadow'] = (transactions['high'] - transactions[['open', 'close']].max(axis=1)) / transactions['close']
    transactions['down_shadow'] = (transactions[['open', 'close']].min(axis=1) - transactions['low']) / transactions['close']
    
    # 去除包含NaN的行
    transactions = transactions.dropna()
    
    print("添加技术指标后的特征:", transactions.columns.tolist())
    
    # 计算过滤前的性能指标
    before_metrics = calculate_metrics(transactions)
    print("\n=== 过滤前整体表现 ===")
    print_metrics_comparison(before_metrics, before_metrics)
    
    # 创建并训练模型
    filter_model = SignalFilter()
    train_metrics, valid_metrics, train_idx, valid_idx = filter_model.train(transactions)
    
    # 打印模型评估指标
    print_model_metrics("训练", train_metrics)
    print_model_metrics("验证", valid_metrics)
    
    # 分别评估训练集和验证集的交易表现
    train_trans = transactions.iloc[train_idx]
    valid_trans = transactions.iloc[valid_idx]
    
    # 对训练集进行预测和评估
    train_pred = filter_model.predict(train_trans)
    filtered_train = train_trans[train_pred == 1]
    train_before = calculate_metrics(train_trans)
    train_after = calculate_metrics(filtered_train)
    
    # 对验证集进行预测和评估
    valid_pred = filter_model.predict(valid_trans)
    filtered_valid = valid_trans[valid_pred == 1]
    valid_before = calculate_metrics(valid_trans)
    valid_after = calculate_metrics(filtered_valid)
    
    # 打印训练集和验证集的交易表现对比
    print("\n=== 训练集交易表现 ===")
    print_metrics_comparison(train_before, train_after)
    
    print("\n=== 验证集交易表现 ===")
    print_metrics_comparison(valid_before, valid_after)
    
    # 保存模型
    filter_model.save_model('models/signal_filter.joblib')

if __name__ == "__main__":
    main()
