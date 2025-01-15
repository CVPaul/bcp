#!/usr/bin/env python
#-*- coding:utf-8 -*-


import smtplib
import logging

from email.header import Header
from email.mime.text import MIMEText
 

AUTH_TOKENS = {
    "xianqiu_li@126.com": "LHEMRMRITXYVXOHD",
}


class EMailManager:

    def __init__(self, sender, recivers):
        # 第三方 SMTP 服务
        self.host = f"smtp.{sender.split("@")[1]}"
        self.sender = sender                            # 发件人邮箱(最好写全, 不然会失败)
        self.receivers = recivers                       # 接收邮件，可设置为你的QQ邮箱或者其他邮箱
        self.auth_token = AUTH_TOKENS[self.sender]      # 在邮箱设置中POP3/SMPT/ 开启SMTP会提示生成

    def send(self, title, content):
        message = MIMEText(content, 'plain', 'utf-8')  # 内容, 格式, 编码
        message['From'] = "{}".format(self.sender)
        message['To'] = ",".join(self.receivers)
        message['Subject'] = title
        try:
            smtp = smtplib.SMTP_SSL(self.host, 465)                             # 启用SSL发信, 端口一般是465
            smtp.login(self.sender, self.auth_token)                              # 登录验证
            smtp.sendmail(self.sender, self.receivers, message.as_string())     # 发送
            smtp.quit()
            logging.info(f"mail(title={title}) has been send successfully!")
        except smtplib.SMTPException as e:
            logging.exception(f"send mail failed with exception: {e}")
    
 
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    email = EMailManager(
        'xianqiu_li@126.com',
        ['xianqiu_li@163.com'])
    email.send('local-test', 'connection test') 