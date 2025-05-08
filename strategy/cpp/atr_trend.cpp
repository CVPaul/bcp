#include "strategy_common.h"
#include "atr_strategy.h" // Include header with order functions and enums

class ATRTrendStrategy : public Strategy { // Ensure Strategy has placeOrder and enums
private:
    int period_;
    int ma_length_;
    double k_;
    std::vector<double> close_prices_;
    std::vector<double> ma_values_;

public:
    ATRTrendStrategy() : period_(45), ma_length_(7), k_(0.02) {}

    BacktestResult run(const std::vector<Kline>& data, double fee) const override {
        // Implement backtest logic here
        return BacktestResult(); // Placeholder
    }

private:
    void calculateMA() {
        double sum = 0.0;
        for (int i = close_prices_.size() - ma_length_; i < close_prices_.size(); ++i) {
            sum += close_prices_[i];
        }
        ma_values_.push_back(sum / ma_length_);
    }

    double calculateCurvature() const {
        if (ma_values_.size() < 3) return 0.0;
        return (ma_values_.back() - 2*ma_values_[ma_values_.size()-2] + ma_values_[ma_values_.size()-3]) 
               / (period_ * period_);
    }

    void generateSignal(double curvature) {
        if (curvature > k_) {
            placeOrder(BUY);
        } else if (curvature < -k_) {
            placeOrder(SELL);
        }
    }
};

STRATEGY_REGISTER(ATRTrendStrategy)
