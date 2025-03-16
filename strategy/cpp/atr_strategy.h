#ifndef ATR_STRATEGY_H
#define ATR_STRATEGY_H

#include "strategy_common.h"

class ATRStrategy : public Strategy {
private:
    double k_;
    double stop_loss_;
    double take_profit_;
    mutable std::vector<double> entry_ATR; // 新增
public:
    ATRStrategy(double k, double stop_loss, double take_profit);
    BacktestResult run(const std::vector<Kline>& data, double fee) const override;
};

#endif // ATR_STRATEGY_H
