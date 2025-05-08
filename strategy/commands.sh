python strategy/break.py --symbol BTCUSD_PERP --dnn 67000 --upp 73250 --vol 4 &
python strategy/break.py --symbol DOGEUSD_PERP --dnn 0.13912 --upp 0.19031 --vol 40 --stgname DOGE-GUARD &
python strategy/grid.py --symbol DOGEUSD_PERP --dnn 0.13912 --upp 0.19031 --grid 33 --vol 2 --stgname big &
python strategy/grid.py --symbol DOGEUSD_PERP --dnn 0.14211 --upp 0.18662 --grid 36 --vol 1 &
python strategy/grid.py --symbol DOGEUSD_PERP --dnn 0.14211 --upp 0.18662 --grid 36 --vol 1 --stgname range &
python strategy/hand.py --symbol BTCUSD_PERP --vol 20 --stop-ratio 0.97,0.94,0.90 --stgname btc &
python strategy/shot2.py --symbol DOGEUSD_PERP -B 0.012 -S 0.01,0.007 --stgname complex --vol 1 &
python strategy/shot2.py --symbol DOGEUSD_PERP -B 0.023 -S 0.02,0.01 --stgname huge --vol 10 &
python strategy/shot3.py --symbol BTCUSD_PERP -B 0.011 -S 0.009,0.007 --stgname btc_v3 --vol 2 &
python strategy/shot3.py --symbol BTCUSD_PERP -B 0.02 -S 0.015,0.01 --stgname btc_huge --vol 6 &
python strategy/shot3.py --symbol DOGEUSD_PERP -B 0.012 -S 0.01,0.007 --stgname doge_v3 --vol 10 &
python strategy/trend.py --symbol DOGEUSD_PERP --last-trade-action 1 &


# bad case
python strategy/shot3.py --symbol DOGEUSD_PERP -B 0.005 -S 0.01,0.005 --stgname shot-fast --vol 1 &
