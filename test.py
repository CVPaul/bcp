from openai import OpenAI
client = OpenAI(
    base_url="https://console.scitix.ai/siflow/aries/ailab4sci/xqli/qwq-32b/",
    api_key="EMPTY",
)
resp = client.chat.completions.create(
    model="/models/models/QWQ-32B/",
    messages=[{"role": "user", "content": "hello"}],
)
print(resp.choices[0].message.content)
