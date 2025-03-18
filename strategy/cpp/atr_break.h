#ifndef ATR_BREAK_H
#define ATR_BREAK_H

#include "strategy_common.h"

class ATRBREAKStrategy {
public:
    explicit ATRBREAKStrategy(double k, double stop_loss, double take_profit);
    BacktestResult run(const std::vector<Kline>& data, double fee) const;

private:
    double k_;
    double stop_loss_;
    double take_profit_;
};

#endif // ATR_BREAK_H
