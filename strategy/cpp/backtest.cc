#include "strategy_common.h"
#include <sqlite3.h>
#include <iostream>
#include <fstream>
#include <cmath>
#include <algorithm>
using namespace std;

vector<Kline> load_data()
{
    sqlite3 *db;
    sqlite3_open("data/DOGEUSD_PERP.db", &db);

    vector<Kline> data;
    char *zErrMsg = 0;
    int rc = sqlite3_exec(
        db,
        "SELECT open,high,low,close FROM klines ORDER BY start_t",
        [](void *data_ptr, int argc, char **argv, char **azColName) -> int
        {
            auto vec = static_cast<vector<Kline> *>(data_ptr);
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

void calculate_ATR(vector<Kline> &data, int period)
{
    for (size_t i = 0; i < data.size(); i++)
    {
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
            data[i].ATR = 0;
        }
    }
}

void calculate_30m_extremes(vector<Kline> &data)
{
    for (size_t i = 0; i < data.size(); i++)
    {
        int start = max(0, static_cast<int>(i) - 29);
        double max_high = 0, min_low = INFINITY;
        for (int j = start; j <= i; j++)
        {
            if (data[j].high > max_high)
                max_high = data[j].high;
            if (data[j].low < min_low)
                min_low = data[j].low;
        }
        data[i].high_30m = max_high;
        data[i].low_30m = min_low;
    }
}

vector<Kline> aggregate(const vector<Kline> &data, int period)
{
    vector<Kline> aggregated;
    for (size_t i = 0; i < data.size(); i += period)
    {
        int end = i + period;
        if (end > data.size())
            end = data.size();
        Kline k;
        k.open = data[i].open;
        k.close = data[end - 1].close;
        double max_high = data[i].high, min_low = data[i].low;
        for (int j = i; j < end; j++)
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

int main()
{
    int atr_period = 14;
    double fee = 5e-4;
    double k_values[] = {1.0, 1.5, 2.0, 2.5, 3.0};
    double stop_loss_values[] = {0.06, 0.07, 0.08, 0.09, 0.1};
    double take_profit_values[] = {0.25, 0.3, 0.35, 0.4};

    auto data = load_data();
    int period = 480;
    vector<Kline> aggregated = aggregate(data, period);
    calculate_ATR(aggregated, 14);

    for (size_t i = period; i < data.size(); i++)
    {
        data[i].ATR = aggregated[i / period - 1].ATR;
    }
    calculate_30m_extremes(data);

    double best_balance = 0;
    vector<tuple<double, double, double>> best_trades;
    double best_k, best_stop_loss, best_take_profit;

    for (double k : k_values)
    {
        for (double sl : stop_loss_values)
        {
            for (double tp : take_profit_values)
            {
                auto result = run_backtest(data, k, sl, tp, fee);
                if (result.balance > best_balance)
                {
                    best_balance = result.balance;
                    best_k = k;
                    best_stop_loss = sl;
                    best_take_profit = tp;
                    best_trades = result.trades;
                }
            }
        }
    }

    cout << "Best parameters: k=" << best_k
         << ", stop_loss=" << best_stop_loss
         << ", take_profit=" << best_take_profit << endl;
    cout << "Best balance: " << best_balance << endl;

    ofstream outfile("best_trades.csv");
    if (outfile.is_open())
    {
        outfile << "Entry Price,Exit Price,Profit\n";
        for (const auto &trade : best_trades)
        {
            outfile << get<0>(trade) << ","
                    << get<1>(trade) << ","
                    << get<2>(trade) << "\n";
        }
        outfile.close();
    }
    else
    {
        cerr << "Error opening file for writing." << endl;
    }
    return 0;
}
