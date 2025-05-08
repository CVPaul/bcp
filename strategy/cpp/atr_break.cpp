#include <string>
#include <iostream>
#include "atr_break.h"
#include "strategy_common.h"

ATRBREAKStrategy::ATRBREAKStrategy(double k, double stop_loss, double take_profit)
    : k_(k), stop_loss_(stop_loss), take_profit_(take_profit) {}

BacktestResult ATRBREAKStrategy::run(const std::vector<Kline> &data, double fee) const
{
    BacktestResult result;
    result.balance_history.push_back(10000); // 初始资金
    int position = 0;
    double balance = 10000;
    double entry_price = 0;
    double stop = 0.0;
    double take = 0.0;

    for (const auto &row : data)
    {
        if (row.ATR <= 1e-8)
            continue;

        if (position == 0)
        {
            // 多头开仓条件：价格突破均线+k*ATR
            if (row.close > row.ma + k_ * row.ATR)
            {
                position = 1;
                entry_price = row.close;
                stop = entry_price * (1 - stop_loss_);
                take = entry_price * (1 + take_profit_);
            }
            // 空头开仓条件：价格跌破均线-k*ATR
            else if (row.close < row.ma - k_ * row.ATR)
            {
                position = -1;
                entry_price = row.close;
                stop = entry_price * (1 + stop_loss_);
                take = entry_price * (1 - take_profit_);
            }
        }
        else
        {
            double current_price = row.close;
            double profit = 0;
            if (position == 1)
            {
                // 多头平仓条件：跌破均线+k*ATR 或 触及止损/止盈
                if (// current_price <= row.ma + k_*row.ATR || 
                    current_price <= stop || current_price >= take)
                {
                    profit = ((current_price - entry_price)/entry_price) - 2*fee;
                    balance *= 1 + profit;
                    result.balance_history.push_back(balance);
                    result.trades.emplace_back(entry_price, current_price, profit);
                    position = 0;
                }
            }
            else if (position == -1)
            {
                // 空头平仓条件：回升到均线-k*ATR 或 触及止损/止盈
                if (// current_price >= row.ma - k_*row.ATR || 
                    current_price >= stop || current_price <= take)
                {
                    profit = ((entry_price - current_price)/entry_price) - 2*fee;
                    balance *= 1 + profit;
                    result.balance_history.push_back(balance);
                    result.trades.emplace_back(entry_price, current_price, profit);
                    position = 0;
                }
            }
        }
    }
    result.balance = balance;
    return result;
}
