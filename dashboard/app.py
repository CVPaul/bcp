#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import glob
import psutil
import pandas as pd
import streamlit as st

from binance.fut.unicm import CoinM
from strategy.common.utils import get_auth_keys


st.set_page_config(page_title="Trader-XII", layout='wide')
COIN_LIST = ['BTC', 'BNB', 'DOGE']
BUTTON_STYLE = '''<style>
div.stButton>button {
    background-color: #f63366;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 1px 1px;
    cursor: pointer;
    height: 30px;
    width: 100%;
}
</style>'''


def trade_info(cli, symbol, start_time, stgname=None):
    orders = cli.get_orders(
        symbol=symbol, limit=100)
    end_time = orders[0]['time']
    start_time = (start_time.timestamp() - 8 * 3600) * 1000 # to utc
    while end_time >= start_time:
        order_t = cli.get_orders(
            symbol=symbol, limit=100, endTime=end_time)
        if len(order_t) == 1: # not more orders any more
            break
        end_time = order_t[0]['time']
        orders = order_t[:-1] + orders
    orders = pd.DataFrame(orders)
    slc_fields = ["time", "status", "price", "avgPrice", "side",
        "span", "executedQty"]
    if stgname:
        stgname = f'{stgname}_'
        orders = orders[orders['clientOrderId'].str.startswith(stgname)] 
    orders['status'] = orders.pop('clientOrderId').apply(
        lambda x: x.split('_')[-2].upper())
    orders.time = pd.to_datetime((orders.time + 8 * 3600000) * 1e6)
    orders['span'] = orders['price'].astype(float).diff()
    orders = orders[orders.status != 'OPEN']
    orders['span'] *= orders['side'].apply(lambda x: -1 if x == 'BUY' else 1)
    return orders[slc_fields]


def account_info():
    api_key, private_key = get_auth_keys()
    client = CoinM(
        api_key=api_key,
        private_key=private_key)
    # orderbook info
    orders = client.get_open_orders()
    orders = pd.DataFrame(orders)[[
        'time', 'pair', 'side', 'price', 'status', 'clientOrderId', 'origQty']]
    orders.time = pd.to_datetime((orders.time+ 8 * 3600000) * 1e6)
    orders = orders.sort_values(['pair', 'time'])
    # account info
    acc_info = client.account()
    ## asset info
    assets = pd.DataFrame(acc_info['assets'])[
        ['asset', 'walletBalance', 'unrealizedProfit']]
    assets = assets[assets["walletBalance"].astype(float) != 0]
    assets = assets.sort_values("asset")
    price_cache, prices = {}, []
    for symbol in assets['asset']:
        symbol = f'{symbol}USD_PERP'
        rsp = client.ticker_price(symbol)[0]
        prices.append(float(rsp['price']))
        price_cache[symbol] = prices[-1]
    total = 0
    for field in ["walletBalance", "unrealizedProfit"]:
        assets[field] = assets[field].astype(float) * prices
        total += assets[field]
    assets['total'] = total
    ## postion info
    pos_fields = [
        'symbol', 'initialMargin', 'positionAmt', 'entryPrice', 'unrealizedProfit',
        'leverage', 'maxQty']
    positions = pd.DataFrame(acc_info['positions'])[pos_fields]
    positions = positions.sort_values("symbol")
    if not positions.empty:
        positions = positions[positions['positionAmt'] != '0']
        # market info
        result = []
        for symbol in positions['symbol']:
            if symbol in price_cache:
                price = price_cache[symbol]
            else:
                rsp = client.ticker_price(symbol)[0]
                price = float(rsp['price'])
            result.append(price)
        positions['lastPrice'] = result
        for field in ['initialMargin', 'entryPrice', 'unrealizedProfit']:
            positions[field] = positions[field].astype(float)
        positions['unrealizedProfit'] /= positions['initialMargin']
        positions['initialMargin'] *= positions['lastPrice']
        pos_fields.insert(2, 'lastPrice')
        positions = positions[pos_fields]
    return client, assets, positions, orders
    

def overview(ratio):
    res = []
    for filename in glob.glob("./*.log"):
        df = log_parser(filename, ratio)
        if df.empty:
            continue
        rcd = [
            os.path.basename(filename), (df.gross > 0).sum() / df.shape[0],
            df.shape[0], df.gross.sum(), df.commis.sum()]
        rcd.append(rcd[-2] - rcd[-1])
        res.append(rcd)
    df = pd.DataFrame(res, columns=[
        'strategy', 'win-ratio', 'trade-cnt',
        'gross', 'commis', 'net-value'])
    return df


def cmdline_process(cmdline):
    res = {}
    for i in range(2, len(cmdline) - 1):
        if cmdline[i][0] == '-':
            key = cmdline[i].split('-')[-1]
            val = cmdline[i+1]
            res[key] = val
    res['script'] = cmdline[1].split('/')[1]
    return res


def process_info():
    res = []
    fields = ['pid', 'cpu_percent', 'cmdline']
    for proc in psutil.process_iter(fields):
        try:
            if proc.info['cmdline'][1].startswith('strategy/'):
                res.append(proc.info)
        except (IndexError, psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # 如果进程不存在，或者访问被拒绝，或者进程是僵尸进程，则跳过
            pass
    df = pd.DataFrame(res)[fields]
    res = pd.DataFrame(
        df.pop('cmdline').apply(cmdline_process).values.tolist())
    res = res.rename(columns={'s':'symbol'})
    for col in res:
        df[col] = res[col] 
    return df.sort_values(['symbol', 'script']).reset_index(drop=True)


def line2dic(line):
    res = {}
    toks = line.split(',')
    for tk in toks:
        kv = tk.split('=')
        res[kv[0].strip()] = kv[1].strip()
    return res


def log_parser(filename, ratio):
    content = []
    with open(filename) as fp:
        for line in fp:
            if "/WIN" in line or "/LOSS" in line:
                direct = 'LONG' if 'LONG' in line else 'SHORT'
                action = 'OPEN' if 'OPEN' in line else 'CLOSE'
                line = f'direct={direct},action={action},' + line.split("|")[1]
                content.append(line2dic(line))
    df = pd.DataFrame(content)
    if df.empty:
        return df
    df['open'] = df.enpp
    if 'price' in df.columns:
        df['close'] = df.price.fillna(df.spp)
    else:
        df['close'] = df.spp
    df.open = df.open.astype(float)
    df.close = df.close.astype(float)
    df['side'] = df.direct.apply(lambda x: 1 if x == 'LONG' else -1)
    df['gross'] = df.side * (df.close - df.open)
    df['commis'] = (df.close + df.open) * ratio
    df.index = pd.to_datetime((df.pop('st').astype(float) + 8 * 3600000) * 1e6)
    return df


def log_summary(df):
    res = {}
    #if df.shape[0] > 60:
    #    res["### Head-30"] = df.head(30)
    #    res["### Tail-30"] = df.tail(30)
    #else:
    #    res["### All Trade History"] = df
    trade_days = (df.index[-1] - df.index[0]).days
    summary = f'''## Trade Summary
    - start-time: {df.index[0]}
    - stop-time: {df.index[-1]}
    - trade-days: {trade_days}
    - win-ratio: {(df.gross > 0).sum() / df.shape[0]:.4f}
    - trade-cnt: {df.shape[0]}
    - trade-cnt/day: {df.shape[0] / trade_days if trade_days else 0}
    - gross: {df.gross.sum():.6f}
    - commis: {df.commis.sum():.6f}
    - net-value: {(df.gross - df.commis).sum():.6f}'''
    return summary


def main():
    st.markdown(BUTTON_STYLE, unsafe_allow_html=True)
    st.markdown("## 进程信息")
    df = process_info()
    st.table(df)
    default = "请选择..."
    with st.sidebar:
        ratio = st.selectbox(
            '手续费率：', options=[0.0002, 0.0005])
        pid = st.selectbox(
            'kill进程：', options=[default] + df.pid.values.tolist())
        if pid != default:
            os.system(f'kill -9 {pid}')
        symbol = st.selectbox(
            '币种：', options=[default, "BTC", "BNB", "DOGE"])
        if symbol in {default}:
            symbol = "*"
        else:
            symbol = symbol.lower()
        filename = st.selectbox(
            '日志文件：', options=[default] + sorted(
                glob.glob(f"./{symbol}-*.log")))
        viewall = st.button("查看总览")
        if st.button("刷新"):
            st.rerun()
    if viewall:
        st.markdown("## 策略总览")
        df = overview(ratio) 
        st.table(df)
    # trade info
    cli, asset_info, pos_info, open_orders = account_info()
    st.markdown('## 资产列表')
    st.table(asset_info)
    st.markdown("## 持仓信息")
    st.table(pos_info)
    if st.button("刷新", key='refresh2'):
        st.rerun()
    st.markdown("## 挂单信息")
    st.table(open_orders)
    if filename != default:
        table = log_parser(filename, ratio)
        trans = trade_info(
            cli, f'{symbol.upper()}USD_PERP', table.index[0],
            os.path.basename(filename)[:-4])
        st.markdown("## 真实交易记录")
        st.table(trans)
        summary = log_summary(table)
        st.markdown(summary)
        st.markdown("## All Trade History")
        st.table(table)
    

if __name__ == "__main__":
    main()