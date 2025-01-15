#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import sys
import time
import json
import copy
import logging
import pandas as pd

from binance.fut.unicm import CoinM
from datetime import datetime as dt
from datetime import timedelta as td

from binance.websocket.futures.coin_m.stream import CoinMWSSStreamClient

from strategy.indicator.common import MA
from strategy.indicator.common import ATR


# logging
logging.basicConfig(
    filename='check.log', level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
# global
ROUND_AT = {
    "DOGEUSD_PERP": 5,
}
# ED25519 Keys
api_key = "../api_key.txt"
private_key = "../private_key.pem"
private_key_pass = ""

# strategy construct
length = 150
interval = 300000 # 300000 # 5m
k, B = 2.618, 0.005


class Checkpoint:
    # save the snapshot of the strategy
    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(self.filename):
            open(self.filename, 'w').close() # touch [support cross OS]
    
    def save(self, timestamp):
        with open(self.filename, 'w') as fp:
            ckpt = {
                "timestamp": timestamp,
                "params":{
                    "hpp": hpp,
                    "lpp": lpp,
                    "pos": pos,
                    "side": side,
                    "long.open.id": long_open_id,
                    "short.open.id": short_open_id,
                    "long.close.id": long_close_id,
                    "short.close.id": short_close_id,
                }}
            json.dump(ckpt, fp)
            logging.info(f"checkpoint={ckpt}")
    
    def load(self):
        with open(self.filename) as fp:
            content = fp.read().strip()
            if content:
                content = json.loads(content)
                tsp = content['timestamp']
                hpp = content['params']['hpp']
                lpp = content['params']['lpp']
                pos = content['params']['pos']
                side = content['params']['side']
                long_open_id = content['params']['long.open.id']
                short_open_id = content['params']['short.open.id']
                long_close_id = content['params']['long.close.id']
                short_close_id = content['params']['short.close.id']
            else:
                tsp, hpp, lpp, pos, side, \
                long_open_id, short_open_id, \
                long_close_id, short_close_id = \
                    0, 0, 1e8, 1, 0, 0, 0, 0, 0
        return tsp, hpp, lpp, pos, side, long_open_id, short_open_id, long_close_id, short_close_id


def on_message(self, message):
    global listen_key, listen_time
    global long_open_id, short_open_id
    global long_close_id, short_close_id
    global side, pos, hpp, lpp, last_kline
    message = json.loads(message)
    etype = message.get('e', '')
    if message.get('E', listen_time) - listen_time >= 50 * 300000: # 50min
        rsp = client.renew_listen_key(listen_key)
        logging.info(f'renew listenKey with rsp={rsp}')
    if long_open_id == 0 or short_open_id == 0: # not ready
        print('>>> Not Ready...')
        return # do nothing and return
    if etype == 'ORDER_TRADE_UPDATE':
        ord = message['o']
        if ord['x'] == 'TRADE':
            if side == 0:
                hpp = lpp = ord['p'] # 挂单价格 
                logging.info(
                    f'slippage={ord["ap"] - hpp}, '
                    f'trade_vol={pos}/{ord["q"]},side={ord["S"]}')
            if ord['S'] == 'BUY' and ord['ps'] == 'LONG': # BUY OPEN
                side = 1
                # stop by SELL
                order_lc["price"] = dnn
                order_lc["quantity"] = ord['z']
                rsp = client.new_order(**order_lc)
                long_close_id = rsp['orderId']
                logging.info(f'TRADE[BUY/OPEN], POST limit order with rsp={rsp}')
            elif ord['S'] == 'SELL' and ord['ps'] == 'SHORT': # SELL OPEN
                side = -1
                # stop by BUY
                order_lc["price"] = upp
                order_lc["quantity"] = ord['z']
                rsp = client.new_order(**order_sc)
                short_close_id = rsp['orderId']
                logging.info(f'TRADE[SELL/OPEN], POST limit order with rsp={rsp}')
            else: # side != 0, means position if closing(reducing) 
                if ord['X'] == 'FILLED': # all traded
                    if (side > 0 and ord['S'] == 'SELL'): # 避免反手的时候平仓落后于开仓message
                        logging.info(f'TRADE[BUY/CLOSE], position={ord["z"]}/{ord["q"]}')
                        side = 0
                    if (side < 0 and ord['S'] == 'BUY'): # 同上
                        logging.info(f'TRADE[SELL/CLOSE], position={ord["z"]}/{ord["q"]}')
                        side = 0
                    # 方向相同就忽略就行
            checkpoint.save(message['E'])

    if etype == 'kline':
        kline = message['k']
        if kline['t'] <= last_kline['t']:
            return # recived the old message
        if kline['t'] != last_kline['t']:
            t = last_kline['t']
            o = float(last_kline['o'])
            h = float(last_kline['h'])
            l = float(last_kline['l'])
            c = float(last_kline['c'])
            s = ma.update(c)
            a = atr.update(h, l, c)
            hpp = max(hpp, h)
            lpp = min(lpp, l)
            upp = round(s + k * a, ROUND_AT[symbol])
            dnn = round(s - k * a, ROUND_AT[symbol])
            # modify the long order
            if side == 0:
                # long
                if order_lo['price'] != upp: # 价格有变动
                    order_lo['price'] = order_lo['stopPrice'] = upp
                    rsp = client.cancel_order(symbol, orderId=long_open_id) # 删除之前的单子
                    logging.info(
                        f'ORDER[BUY/OPEN/UPDATE], replace old order(price={order_lo["price"]}) '
                        f'to now order(price={upp}), rsp={rsp}')
                    long_open_id = client.new_order(**order_lo)['orderId']
                # short
                if order_so['price'] != dnn: # 价格有变动
                    order_so['price'] = order_so['stopPrice'] = dnn
                    rsp = client.cancel_order(symbol, orderId=short_open_id) # 删除之前的单子
                    logging.info(
                        f'ORDER[SELL/OPEN/UPDATE], replace old order(price={order_so["price"]}) '
                        f'to now order(price={dnn}), rsp={rsp}')
                    short_open_id = client.new_order(**order_so)['orderId']
            elif side == 1: # 持有多仓，需要更新止盈/止损单
                spp = round(hpp * (1 - B), ROUND_AT[symbol])
                if order_lc['price'] != spp:
                    order_lc['price'] = spp
                    rsp = client.modify_order(**order_lc)
                    logging.info(
                        f'ORDER[BUY/CLOSE/UPDATE], replace old order(price={order_lc["price"]}) '
                        f'to now order(price={spp}), rsp={rsp}')
            else:
                spp = round(lpp * (1 + B), ROUND_AT[symbol])
                if order_sc['price'] != spp:
                    order_sc['price'] = spp
                    rsp = client.modify_order(**order_sc)
                    logging.info(
                        f'ORDER[SELL/CLOSE/UPDATE], replace old order(price={order_sc["price"]}) '
                        f'to now order(price={spp}), rsp={rsp}')
            checkpoint.save(message['E'])
            logging.info(f'UPDATE,t={t},o={o},h={h},l={l},c={c},ma={s},atr={a},upp={upp},dnn={dnn}')
        last_kline = kline # 这里必须是if etype == 'kline'之外

if __name__ == "__main__":
    # global
    symbol =  sys.argv[1] # 'DOGEUSD_PERP'

    with open(api_key) as f:
            api_key = f.read().strip()

    with open(private_key, 'rb') as f:
        private_key = f.read()

    client = CoinM(
        api_key=api_key,
        private_key=private_key,
        private_key_pass=private_key_pass,
        # base_url="https://dapi.binance.com"
    )

    # 如果距离下一根k线不足5s的话，就等到下一根k线过后至少5秒
    if interval - client.time()['serverTime'] % interval <= 5000: 
        logging.warning('>>> 距离下一根k线不足5s, 需等待10s...')
        time.sleep(10)
        logging.warning('>>> 等待结束!')
    
    df = client.klines(symbol, f'{interval // 60000}m', limit = length + 2)
    last_kline = {'t': df[-1][0], 'c': df[-1][4]}
    df = df[:-1] # 最后一根kline是不完整的
    df = pd.DataFrame(
        df, columns=[
            'start_t', 'open', 'high', 'low', 'close',
            'volume', 'end_t', 'amount', 'trade_cnt',
            'taker_vol', 'taker_amt', 'reserved'
        ]).astype(float)
    # df = df.reset_index(drop=True)
    ma = MA(length, df)
    atr = ATR(length, df)

    s = ma.value
    a = atr.value
    upp = round(s + k * a, ROUND_AT[symbol])
    dnn = round(s - k * a, ROUND_AT[symbol])

    # subscribe streams before any order send 
    listen_key = client.new_listen_key()['listenKey']
    listen_time = client.time()['serverTime']
    # create wedsocket stream client
    wscli = CoinMWSSStreamClient(on_message=on_message)
    wscli.kline(symbol, f'{interval // 60000}m')
    wscli.user_data(listen_key)

    # recover from checkpoint
    checkpoint = Checkpoint("strategy.trend.ckpt")
    tsp, hpp, lpp, pos, side, long_open_id, short_open_id, long_close_id, short_close_id = \
        checkpoint.load()
    # open orders
    order_lo = {
        "symbol": symbol, "side": "BUY", "type": "STOP",
        "timeInForce": "GTC", "quantity": pos, # 数量可以直接在这里倍数：pos * Quantity
        "price": upp, "stopPrice": upp, "positionSide": "LONG",
    }
    order_so = {
        "symbol": symbol, "side": "SELL", "type": "STOP",
        "timeInForce": "GTC", "quantity": pos, # 数量可以直接在这里倍数：pos * Quantity
        "price": dnn, "stopPrice": dnn, "positionSide": "SHORT",
    }
    # close orders
    order_lc = {
        "symbol": symbol, "side": "SELL", "type": "STOP",
        "timeInForce": "GTC", "quantity": None,
        "price": None, "stopPrice":None, "positionSide": "LONG",
    }
    order_sc = {
        "symbol": symbol, "side": "BUY", "type": "STOP",
        "timeInForce": "GTC", "quantity": None,
        "price": None, "stopPrice": None, "positionSide": "SHORT",
    }
    if tsp == 0: # 已经平仓，相当于重新开始，可能是用户自己删除的
        # long
        if long_open_id == 0:
            if last_kline['c'] >= order_lo['stopPrice']: # 如果已经突破，立即执行
                order_lo['type'] = 'MARKET' # 市价单立即成交
            rsp = client.new_order(**order_lo)
            long_open_id = rsp['orderId']
            logging.info(f'ORDER[BUY/OPEN], created new order : {rsp}')
            checkpoint.save(tsp)
        # short
        if short_open_id == 0:
            if last_kline['c'] <= order_sc['stopPrice']:
                order_so['type'] = 'MARKET'
            rsp = client.new_order(**order_so)
            short_open_id = rsp['orderId']
            logging.info(f'ORDER[SELL/OPEN], created new order : {rsp}')
            checkpoint.save(tsp)
    else: # 之前的仓位还在
        if side > 0:
            assert long_open_id and not short_open_id
        else:
            assert short_open_id and not long_open_id
        dft = df[df.start_t >= tsp]
        if dft.shape[0] > 0:
            hpp = max(hpp, dft.high.max())
            lpp = min(lpp, dft.low.min())
            if len(sys.argv) > 2: # e.g LC:3 -> LONG-CLOSE:HIST-POS=3 or SC:1 -> SHORT-CLOSE:HIST-POS=1
                action = sys.argv[2][:2].upper()
                hist_pos = int(sys.argv[2][3:])
                if action == 'LC':
                    spp = round(hpp * (1 - B), ROUND_AT[symbol])
                    if last_kline['c'] <= spp:
                        order_lc['type'] = 'MARKET'
                    order_lc["price"] = order_lc['stopPrice'] = spp
                    order_lc["quantity"] = hist_pos
                    rsp = client.new_order(**order_lc)
                    long_close_id = rsp['orderId']
                    logging.info(f'TRADE[BUY/OPEN], POST limit order with rsp={rsp}')
                if action == 'SC':
                    spp = round(lpp * (1 + B), ROUND_AT[symbol])
                    if last_kline['c'] >= spp:
                        order_sc['type'] = 'MARKET'
                    order_sc["price"] = order_sc['stopPrice'] = spp
                    order_sc["quantity"] = hist_pos
                    rsp = client.new_order(**order_sc)
                    short_close_id = rsp['orderId']
                    logging.info(f'TRADE[SELL/OPEN], POST limit order with rsp={rsp}')

