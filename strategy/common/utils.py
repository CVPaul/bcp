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
from websocket import WebSocketConnectionClosedException


def on_open(self):
    logging.info("ws is connected!")


def on_close(self):
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
    def __init__(self, event, freq='1s'):
        super().__init__()
        self.event = event
        self.running = True
        self.stopped = False
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
        if self.stopped:
            self.stopped = False
            self.send_email(f'Heartbeat recorverd@{timestamp}')

    def send_email(self, info=None):
        receivers = ['xianqiu_li@163.com']  # 接收方邮箱
        mail_host = "smtp.126.com"          # 设置服务器
        mail_user = "xianqiu_li@126.com"    # 用户名
        mail_pass = "ZEsmCPDYt27dfkKE"      # 口令

        if info is None:
            self.stopped = True
            info = f'Heartbeat exceeded {self.freq} seconds'
        message = MIMEText(info, 'plain', 'utf-8')
        message['From'] = Header("HeartBeat Monitor", 'utf-8')
        message['To'] = Header("Recipient", 'utf-8')
        subject = f"stop={self.stopped}|{self.event}'s Heartbeat Alert"
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