import os
import importlib
from qlib.data import D
from qlib.contrib.evaluate import backtest as qlib_backtest
from qlib.contrib.evaluate import plt_performances
from qlib.contrib.strategy import BaseStrategy

# 配置QLib数据源
D.set_config("config.yml")

class QlibStrategyAdapter(BaseStrategy):
    """适配用户现有策略到QLib框架"""
    def __init__(self, user_strategy, **kwargs):
        super().__init__(**kwargs)
        self.user_strategy = user_strategy

    def gen_signals(self, *args, **kwargs):
        # 这里需要根据用户策略的具体实现调整
        # 假设用户策略有generate_signal方法
        return self.user_strategy.generate_signal(*args, **kwargs)

# 自动加载所有策略
strategies = []
strategy_dir = "strategy"
for filename in os.listdir(strategy_dir):
    if filename.endswith(".py") and not filename.startswith("__"):
        module_name = f"{strategy_dir}.{filename[:-3]}"
        try:
            module = importlib.import_module(module_name)
            # 假设每个策略模块有一个Strategy类
            user_strategy = module.Strategy()
            qlib_strategy = QlibStrategyAdapter(user_strategy)
            strategies.append(qlib_strategy)
        except (ModuleNotFoundError, AttributeError) as e:
            print(f"Skipping {filename}: {e}")

# 回测参数
start_time = "2023-01-01"
end_time = "2023-12-31"
benchmark = "BINANCE:DOGEUSD_PERP"
freq = "1min"
account = 1000000

# 执行回测
for strategy in strategies:
    print(f"Running backtest for {strategy.user_strategy.__class__.__name__}")
    portfolio, records = qlib_backtest(
        strategy=strategy,
        start_time=start_time,
        end_time=end_time,
        benchmark=benchmark,
        account=account,
        freq=freq,
    )
    
    # 保存结果
    output_dir = f"backtest_results/{strategy.user_strategy.__class__.__name__}"
    os.makedirs(output_dir, exist_ok=True)
    plt_performances(portfolio, records, savefig=True, fig_dir=output_dir)
    with open(f"{output_dir}/metrics.txt", "w") as f:
        f.write(f"Total Return: {portfolio.total_return}\n")
        f.write(f"Max Drawdown: {portfolio.max_drawdown}\n")
        f.write(f"Sharpe Ratio: {portfolio.sharpe_ratio}\n")

print("Backtesting completed. Results saved in backtest_results/")
