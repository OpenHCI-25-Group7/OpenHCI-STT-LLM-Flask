import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

# 這段是語音轉文字的結果
transcript_text = """

"""

# prompt 模板
system_prompt = """
你是一個對話分析助手。請根據輸入的語句判斷三件事：
1. 整體語句的情緒類型（例如：大笑、安靜、偏見、碎碎念、吵架、大吵等）；
2. 語句中「不愉快氛圍」的總持續時間（以秒為單位，估算即可）；
3. 語句中偏見語句出現的次數（偏見包含指責、刻板印象或歧視性語言）。

請輸出 JSON 格式如下：
{
  "emotion_label": "...",
  "duration": ...,
  "bias_count": ...
}
"""

# 呼叫 OpenAI API
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": transcript_text}
    ],
    temperature=0.2
)

# 解析 JSON
import json

try:
    result_text = response.choices[0].message.content
    parsed = json.loads(result_text)
    print(parsed)
except Exception as e:
    print("解析錯誤：", e)
    print("原始輸出：", result_text)