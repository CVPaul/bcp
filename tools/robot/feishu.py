import json
import requests


url = "https://www.feishu.cn/flow/api/trigger-webhook/2ac55edf784a7e4b7c4dba86afe3d57c"

class FeishuNotifier:
    def __init__(self, webhook_url: str):
        """ 初始化飞书通知类 """
        self.webhook_url = webhook_url

    def send_message(self, message: str):
        """ 发送飞书消息 """
        payload = {
            "msg_type": "text",
            "content": {
                "text": message
            }
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload)
            if response.status_code == 200:
                print("飞书消息已发送！")
            else:
                print(f"飞书消息发送失败，状态码: {response.status_code}")
        except Exception as e:
            print("飞书消息发送失败:", e)

# 使用示例
if __name__ == "__main__":
    # 这里填入你的飞书 Webhook URL
    feishu_notifier = FeishuNotifier("https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_url")
    
    # 发送消息
    feishu_notifier.send_message("心跳日志超时超过 2 分钟，可能存在异常！")

