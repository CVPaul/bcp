import requests
import json

# webhook_url = "https://www.feishu.cn/flow/api/trigger-webhook/2ac55edf784a7e4b7c4dba86afe3d57c"
# base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
webhook_url = "https://www.feishu.cn/flow/api/trigger-webhook/50827e6ac3d3ed1a6cdd31ab04964346"

# 自定义卡片消息内容
card_payload = {
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": "任务通知",
            "template": "wathet"  # 蓝色标题栏
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "content": "**用户ID**: 12345\n**状态**: 待处理",
                    "tag": "lark_md"  # 支持Markdown
                }
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "content": "点击处理",
                            "tag": "plain_text"
                        },
                        "type": "primary",
                        "url": "https://example.com"  # 点击跳转链接
                    }
                ]
            }
        ]
    }
}

response = requests.post(webhook_url, json=card_payload)
print(response.status_code, response.text)