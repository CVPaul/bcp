#include <sqlite3.h>
#include <vector>
#include <iostream>
#include <cmath>
#include <algorithm>
#include <fstream>
using namespace std;

struct Kline
{
    double open, high, low, close;
    double high_30m, low_30m;
    double TR, ATR;
};

double run_backtest(const vector<Kline> &data, double k, double stop_loss, double take_profit, double fee = 5e-4)
{
    double balance = 10000;
    string position = "";
    double entry_price = 0;
    double stop = 0.0;
    double take = 0.0;
    vector<tuple<double, double, double>> trades;

    for (const auto &row : data)
    {
        if (position.empty())
        {
            // Long entry condition
            if (row.close > row.high_30m - k * row.ATR)
            {
                position = "long";
                entry_price = row.close;
                stop = entry_price * (1 - stop_loss);
                take = entry_price * (1 + take_profit);
            }
            // Short entry condition
            else if (row.close < row.low_30m + k * row.ATR)
            {
                position = "short";
                entry_price = row.close;
                stop = entry_price * (1 + stop_loss);
                take = entry_price * (1 - take_profit);
            }
        }
        else
        {
            double current_price = row.close;
            double profit = 0;
            if (position == "long")
            {
                if (current_price <= row.high_30m - k * row.ATR ||
                    current_price <= stop || current_price >= take)
                {
                    profit = (current_price - entry_price) / entry_price - 2 * fee;
                    balance *= 1 + profit;
                    trades.push_back({entry_price, current_price, profit});
                    position = "";
                }
            }
            else if (position == "short")
            {
                if (current_price >= row.low_30m + k * row.ATR ||
                    current_price >= stop || current_price <= take)
                {
                    profit = (entry_price - current_price) / entry_price - 2 * fee;
                    balance *= 1 + profit;
                    trades.push_back({entry_price, current_price, profit});
                    position = "";
                }
            }
        }
    }
    return balance;
}

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

void calculate_30m_extremes(vector<Kline> &data)
{
    for (size_t i = 0; i < data.size(); i++)
    {
        int start = max(0, static_cast<int>(i) - 29);
        double max_high = 0;
        double min_low = INFINITY;
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

int main()
{
    int atr_period = 14;
    double fee = 5e-4; // 新增手续费参数
    double k_values[] = {1.0, 1.5, 2.0, 2.5, 3.0};
    double stop_loss_values[] = {0.06, 0.07, 0.08, 0.09, 0.1};
    double take_profit_values[] = {0.25, 0.3, 0.35, 0.4};

    auto data = load_data();
    // 聚合到8小时数据
    int period = 480;
    vector<Kline> aggregated = aggregate(data, period);

    // 计算aggregated的ATR
    calculate_ATR(aggregated, 14); // 使用14个8小时周期计算ATR

    // 将aggregated的ATR映射回原始数据
    int aggregated_size = aggregated.size();
    for (size_t i = period; i < data.size(); i++)
        data[i].ATR = aggregated[i/period - 1].ATR; // 没有足够的数据时设为0

    // 计算30分钟的高低
    calculate_30m_extremes(data);

    double best_balance = 0;
    double best_k, best_stop_loss, best_take_profit;

    for (double k : k_values)
    {
        for (double sl : stop_loss_values)
        {
            for (double tp : take_profit_values)
            {
                double current_balance = run_backtest(data, k, sl, tp, fee);
                if (current_balance > best_balance)
                {
                    best_balance = current_balance;
                    best_k = k;
                    best_stop_loss = sl;
                    best_take_profit = tp;
                }
            }
        }
    }

    cout << "Best parameters: k=" << best_k << ", stop_loss=" << best_stop_loss << ", take_profit=" << best_take_profit << endl;
    cout << "Best balance: " << best_balance << endl;
    return 0;
}
