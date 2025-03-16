#include <string>
#include <iostream>
#include "atr_strategy.h"
#include "strategy_common.h"

ATRStrategy::ATRStrategy(double k, double stop_loss, double take_profit)
    : k_(k), stop_loss_(stop_loss), take_profit_(take_profit) {}

BacktestResult ATRStrategy::run(const std::vector<Kline> &data, double fee) const
{
    BacktestResult result;
    result.balance_history.push_back(10000); // Initialize with starting balance
    int position = 0;
    double balance = 10000;
    double entry_price = 0;
    double stop = 0.0;
    double take = 0.0;
    double enatr = 0.0;

    for (const auto &row : data)
    {
        if (row.ATR <= 1e-8)
            continue;

        if (position == 0)
        {
            if (row.close > row.highest - k_ * row.ATR)
            {
                position = 1;
                entry_price = row.close;
                stop = entry_price * (1 - stop_loss_);
                take = entry_price * (1 + take_profit_);
                enatr = row.ATR;
            }
            else if (row.close < row.lowest + k_ * row.ATR)
            {
                position = -1;
                entry_price = row.close;
                stop = entry_price * (1 + stop_loss_);
                take = entry_price * (1 - take_profit_);
                enatr = row.ATR;
            }
        }
        else
        {
            double current_price = row.close;
            double profit = 0;
            if (position == 1)
            {
                if (current_price <= row.highest - k_ * row.ATR ||
                    current_price <= stop || current_price >= take)
                {
                    double factor = entry_price / enatr / 100;
                    profit = ((current_price - entry_price) / entry_price) - 2 * fee;
                    balance *= 1 + profit * factor;
                    result.balance_history.push_back(balance); // Record new balance
                    result.trades.emplace_back(entry_price, current_price, profit);
                    position = 0;
                    entry_ATR.pop_back();
                }
            }
            else if (position == -1)
            {
                if (current_price >= row.lowest + k_ * row.ATR ||
                    current_price >= stop || current_price <= take)
                {
                    double factor = entry_price / enatr / 100;
                    profit = ((entry_price - current_price) / entry_price) - 2 * fee;
                    balance *= 1 + profit * factor;
                    result.balance_history.push_back(balance); // Record new balance
                    result.trades.emplace_back(entry_price, current_price, profit);
                    position = 0;
                }
            }
        }
    }
    result.balance = balance;
    return result;
}
