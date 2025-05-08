g++ -o backtest atr_backtest.cpp atr_strategy.cpp atr_break.cpp -I. -lsqlite3 && ./backtest ../../data/DOGEUSD_PERP.db
