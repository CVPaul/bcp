curl https://console.scitix.ai/siflow/aries/ailab4sci/xqli/qwq-32b/v1/chat/completions \
	-X POST \
	-H "Content-Type: application/json" \
	-d '{
		"model": "/models/models/QWQ-32B/",
		"messages": [
			{
				"role": "user",
				"content": "Write a haiku that explains the concept of recursion."
			}
		]
	}'
