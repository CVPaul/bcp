#include <sqlite3.h>
#include <vector>
#include <iostream>
#include <cmath>
#include <algorithm>
#include <fstream>

#include "atr_break.h"
#include "atr_strategy.h"

using namespace std;

vector<Kline> load_data(char *data_path)
{
    sqlite3 *db;
    sqlite3_open(data_path, &db);

    vector<Kline> data;
    char *zErrMsg = 0;
    int rc = sqlite3_exec(
        db,
        "SELECT open,high,low,close FROM klines ORDER BY start_t",
        [](void *data_ptr, int argc, char **argv, char **azColName) -> int
        {
            vector<Kline> *vec = static_cast<vector<Kline> *>(data_ptr);
            Kline k;
            k.open = atof(argv[0]);
            k.high = atof(argv[1]);
            k.low = atof(argv[2]);
            k.close = atof(argv[3]);
            vec->push_back(k);
            return 0;
        },
        &data,
        &zErrMsg);

    sqlite3_close(db);
    return data;
}

void calculate_ATR(vector<Kline> &data, int period = 14)
{
    for (size_t i = 0; i < data.size(); i++)
    {
        // Calculate True Range
        if (i == 0)
        {
            data[i].TR = data[i].high - data[i].low;
        }
        else
        {
            double prev_close = data[i - 1].close;
            data[i].TR = max({data[i].high - data[i].low,
                              abs(data[i].high - prev_close),
                              abs(data[i].low - prev_close)});
        }

        // Calculate ATR (Simple Moving Average)
        if (i >= period - 1)
        {
            double sum = 0;
            for (int j = i - period + 1; j <= i; j++)
            {
                sum += data[j].TR;
            }
            data[i].ATR = sum / period;
        }
        else
        {
            data[i].ATR = 0; // Not enough data
        }
    }
}

void calculate_extremes(vector<Kline> &data, int period = 30)
{
    for (size_t i = period - 1; i < data.size(); i++)
    {
        int start = i - period + 1;
        double max_high = 0;
        double min_low = INFINITY;
        for (int j = start; j <= i; j++)
        {
            if (data[j].high > max_high)
                max_high = data[j].high;
            if (data[j].low < min_low)
                min_low = data[j].low;
        }
        data[i].highest = max_high;
        data[i].lowest = min_low;
    }
}

vector<Kline> aggregate(const vector<Kline> &data, int period)
{
    vector<Kline> aggregated;
    for (size_t i = 0; i < data.size(); i += period)
    {
        int end = static_cast<int>(std::min(i + period, data.size()));
        Kline k;
        k.open = data[i].open;
        k.close = data[end - 1].close;
        double max_high = data[i].high;
        double min_low = data[i].low;
        for (int j = i; j < end; ++j)
        {
            if (data[j].high > max_high)
                max_high = data[j].high;
            if (data[j].low < min_low)
                min_low = data[j].low;
        }
        k.high = max_high;
        k.low = min_low;
        aggregated.push_back(k);
    }
    return aggregated;
}

int main(int argc, char *argv[])
{
    int atr_period = 14;
    double fee = 5e-4; // 新增手续费参数
    int lookback_lens[] = {10, 20, 30, 45, 60};
    double k_values[] = {1.0, 1.5, 2.0, 2.5, 3.0};
    double stop_loss_values[] = {0.06, 0.07, 0.08, 0.09, 0.1};
    double take_profit_values[] = {0.25, 0.3, 0.35, 0.4};
    // double take_profit_values[] = {0.05, 0.1, 0.15, 0.2};

    auto data = load_data(argv[1]);
    // 聚合到8小时数据
    int period = 480;
    vector<Kline> aggregated = aggregate(data, period);

    // 计算aggregated的ATR
    calculate_ATR(aggregated, 14); // 使用14个8小时周期计算ATR

    // 将aggregated的ATR映射回原始数据
    for (size_t i = period; i < data.size(); i++)
        data[i].ATR = aggregated[i / period - 1].ATR;

    double best_balance = 0;
    double best_sharpe = -INFINITY;
    std::vector<std::tuple<double, double, double>> best_trades;
    int best_lb;
    double best_k, best_stop_loss, best_take_profit;

    for (int lb : lookback_lens)
    {
        // 计算高低
        calculate_extremes(data, lb);

        for (double k : k_values)
        {
            for (double sl : stop_loss_values)
            {
                for (double tp : take_profit_values)
                {
                    // ATRStrategy strategy(k, sl, tp);
                    ATRBREAKStrategy strategy(k/2, sl, tp * 2);
                    BacktestResult res = strategy.run(data, fee);
                    // Compute returns and Sharpe ratio
                    vector<double> returns;
                    for (size_t i = 1; i < res.balance_history.size(); ++i)
                    {
                        double prev = res.balance_history[i - 1];
                        double curr = res.balance_history[i];
                        returns.push_back((curr - prev) / prev);
                    }

                    double mean_return = 0.0;
                    for (double r : returns)
                    {
                        mean_return += r;
                    }
                    mean_return /= returns.size();

                    double variance = 0.0;
                    for (double r : returns)
                    {
                        variance += (r - mean_return) * (r - mean_return);
                    }
                    variance /= returns.size();
                    double std_dev = sqrt(variance);
                    double sharpe_ratio = mean_return / std_dev;

                    // Update best parameters
                    if (res.balance > best_balance || (res.balance == best_balance && sharpe_ratio > best_sharpe))
                    {
                        best_balance = res.balance;
                        best_sharpe = sharpe_ratio;
                        best_k = k;
                        best_lb = lb;
                        best_stop_loss = sl;
                        best_take_profit = tp;
                        best_trades = res.trades;
                    }
                }
            }
        }
    }

    cout << "Best parameters: k=" << best_k << ", lookback=" << best_lb
         << ", stop_loss=" << best_stop_loss << ", take_profit=" << best_take_profit
         << ", trade_cnt:" << best_trades.size() << endl;
    cout << "Best balance: " << best_balance << endl;
    cout << "Best Sharpe Ratio: " << best_sharpe << endl;

    ofstream outfile("best_trades.csv");
    if (outfile.is_open())
    {
        outfile << "Entry,Exit,Profit\n";
        for (const auto &trade : best_trades)
        {
            outfile << get<0>(trade) << "," << get<1>(trade) << "," << get<2>(trade) << "\n";
        }
        outfile.close();
    }
    else
    {
        cerr << "Unable to open file for writing.\n";
    }
    return 0;
}
