from typing import Literal, Dict

# 天氣隱喻類型
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