#ifndef STRATEGY_COMMON_H
#define STRATEGY_COMMON_H

#include <vector>
#include <tuple>

struct Kline {
    double open, high, low, close;
    double highest, lowest;
    double TR, ATR;
};

struct BacktestResult {
    double balance;
    std::vector<std::tuple<double, double, double>> trades;
};

class Strategy {
public:
    virtual ~Strategy() {}
    virtual BacktestResult run(const std::vector<Kline>& data, double fee) const = 0;
};

#endif // STRATEGY_COMMON_H
