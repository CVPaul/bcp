#!/usr/bin/env python
#-*- coding:utf-8 -*-


import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class Email:
    def __init__(self, smtp_server: str, smtp_port: int, sender_email: str, sender_password: str, receiver_email: str):
        """ 初始化邮件通知类 """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.receiver_email = receiver_email

    def send(self, subject: str, body: str):
        """ 发送邮件 """
        try:
            # 创建邮件内容
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            # 连接SMTP服务器并发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # 启用TLS加密
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.receiver_email, msg.as_string())
                print("邮件已发送！")
        except Exception as e:
            print(f"邮件发送失败: {e}")


if __name__ == "__main__":
    # 配置邮件信息
    SMTP_SERVER = "smtp.example.com"  # 你的SMTP服务器
    SMTP_PORT = 587  # 通常是 587 (TLS) 或 465 (SSL)
    SENDER_EMAIL = "your_email@example.com"  # 你的邮件地址
    SENDER_PASSWORD = "your_password"  # 邮箱的密码或授权码
    RECEIVER_EMAIL = "receiver_email@example.com"  # 收件人邮件地址

    # 初始化邮件通知类
    email = Email(
        SMTP_SERVER, SMTP_PORT, SENDER_EMAIL,
        SENDER_PASSWORD, RECEIVER_EMAIL)

    # 发送邮件
    email.send("Test", "This mail is send by python app")

