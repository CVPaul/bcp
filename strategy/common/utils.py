#!/usr/bin/env python
#-*- coding:utf-8 -*-


import os
import json
import time
import smtplib
import logging
import threading
import pandas as pd

from email.header import Header
from email.mime.text import MIMEText


def get_auth_keys(prefix='strategy'):
    # ED25519 Keys
    api_key = f"{prefix}/api_key.txt"
    with open(api_key) as f:
        api_key = f.read().strip()

    private_key = f"{prefix}/private_key.pem"
    with open(private_key, 'rb') as f:
        private_key = f.read().strip()
    return api_key, private_key


def load_api_keys():
    path = f'{os.getenv("HOME")}/.vntrader/connect_unifycm.json'
    with open(path, 'r') as f:
        config = json.load(f)
        api_key = config['API Key']
        private_key = config['API Secret']
        if os.path.exists(private_key):
            with open(private_key, 'r') as f:
                private_key = f.read().strip()
    return api_key, private_key


def on_open(self):
    logging.info("ws is connected!")


def on_close(self):
    self.socket_manager.create_ws_connection()
    self.socket_manager.start()
    logging.info(f"try to re-connect to server!")


class FakeClient:

    def __init__(self):
        self.orderid = 0
        self.orders = []
        self.datetime = None

    def new_order(self, *args, **kw):
        self.orderid += 1
        kw['datetime'] = self.datetime
        self.orders.append(kw)
        return {"orderId": self.orderid}
    
    def profit(self):
        df = pd.DataFrame(self.orders)
        df['direction'] = 2 * (df['side'] == 'BUY') - 1
        df['pos'] = df['direction'].cumsum()
        df['profit'] = (df.pos * df.price.diff().shift(-1)).cumsum()
        df['mdd'] = df.profit.expanding().max() - df.profit
        return df



class HeartBeatThread(threading.Thread):
    def __init__(self, who, freq='1s'):
        super().__init__()
        self.running = True
        self.freq = float(freq[:-1])
        self.last_heartbeat_time = time.time()

    def run(self):
        while self.running:
            current_time = time.time()
            elapsed_time = current_time - self.last_heartbeat_time
            if elapsed_time > self.freq:
                self.send_email()
            time.sleep(1)  # 每隔1秒检查一次心跳间隔
    
    def keep_alive(self, timestamp):
        self.last_heartbeat_time = timestamp /  1000.0

    def send_email(self):
        receivers = ['xianqiu_li@163.com']  # 接收方邮箱
        mail_host = "smtp.163.com"          # 设置服务器
        mail_user = "xianqiu_li@126.com"    # 用户名
        mail_pass = "ZEsmCPDYt27dfkKE"      # 口令

        message = MIMEText(f'Heartbeat exceeded {self.freq} seconds', 'plain', 'utf-8')
        message['From'] = Header("HeartBeat Monitor", 'utf-8')
        message['To'] = Header("Recipient", 'utf-8')
        subject = 'Heartbeat Alert'
        message['Subject'] = Header(subject, 'utf-8')

        try:
            smtp_obj = smtplib.SMTP()
            smtp_obj.connect(mail_host, 25)  # 25 为 SMTP 端口号
            smtp_obj.login(mail_user, mail_pass)
            smtp_obj.sendmail(mail_user, receivers, message.as_string())
            logging.info("Email sent successfully")
        except smtplib.SMTPException as e:
            logging.exception("Error: unable to send email")

    def stop(self):
        self.running = False