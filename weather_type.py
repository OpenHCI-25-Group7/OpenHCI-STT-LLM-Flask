from typing import Literal, Dict

# 天氣隱喻類型
'''
你是一個對話分析助手。請根據輸入的語句判斷三件事：
1. 整體語句的情緒類型（例如：大笑、安靜、偏見、碎碎念、吵架、大吵等）；
2. 語句中「不愉快氛圍」的總持續時間（以秒為單位，估算即可）；
3. 語句中偏見語句出現的次數（偏見包含指責、刻板印象或歧視性語言）。

請輸出 JSON 格式如下：
{
  "emotion_label": "...",
  "duration": ...,
  "bias_count": ...
}'''
WeatherType = Literal["晴天", "陰天（☁️）", "小雨（🌦）", "雷陣雨（⛈）"]

def map_to_weather(emotion_label: str, duration: float, bias_count: int) -> WeatherType:
    """
    根據情緒標籤、負面氛圍持續時間與偏見次數，回傳天氣隱喻。
    """
    if emotion_label == "大笑":
        return "晴天"
    elif emotion_label == "安靜" and duration >= 30:
        return "陰天（☁️）"
    elif emotion_label in ["偏見", "碎碎念", "吵架"] and duration >= 60 and bias_count >= 2:
        return "小雨（🌦）"
    elif emotion_label == "大吵" and duration >= 90 and bias_count >= 3:
        return "雷陣雨（⛈）"
    else:
        return "晴天"  # 預設為晴天

# 接收輸入範例
# 假設這是從 OpenAI API 獲得的輸出
example_input = {
    "emotion_label": "偏見",
    "duration": 65,  # 單位：秒
    "bias_count": 2
}

# 呼叫對應函數
weather_result = map_to_weather(**example_input)
print(f"對應天氣隱喻：{weather_result}")