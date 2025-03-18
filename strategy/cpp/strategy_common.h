#ifndef STRATEGY_COMMON_H
#define STRATEGY_COMMON_H

#include <vector>
#include <tuple>

enum OrderType { BUY, SELL };

struct Kline {
    double open, high, low, close;
    double highest, lowest;
    double ma; // 新增移动平均线字段
    double TR, ATR;
};

struct BacktestResult {
    double balance;
    std::vector<std::tuple<double, double, double>> trades;
    std::vector<double> balance_history; // 新增字段
};

class Strategy {
public:
    virtual ~Strategy() {}
    virtual BacktestResult run(const std::vector<Kline>& data, double fee) const = 0;
    virtual void placeOrder(OrderType type) = 0;
};

#endif // STRATEGY_COMMON_H
