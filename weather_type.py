from typing import Literal, Dict

# 天氣隱喻類型
'''
你是一個對話分析助手。請根據輸入的語句判斷三件事：
1. 整體語句的情緒類型（例如：大笑、安靜、偏見、碎碎念、吵架、大吵等）；
2. 語句中「不愉快氛圍」的總持續時間（以秒為單位，估算即可）；
3. 語句中偏見語句出現的次數（偏見包含指責、刻板印象或歧視性語言）。

以下有些常見的偏見句型
當你偵測到以下的句式，請分析裡面的內容是否有潛在的偏見！當你遇到類似的句子的時候也請注意：

句式：

你本來就這樣/你一定會怎樣怎樣….
如果不讀書，以後就一定⋯⋯
成績不好一定是因為……
女生/男生不可以 •
那麼晚回家會⋯
XX的人一定都是⋯⋯
那麼胖以後一定⋯•
XX學校 科系一定⋯
XX職業都 ⋯
特定性傾向的人都是⋯•
喜歡 •⋯的人一定都⋯⋯
都沒有

請考量以上句式。

'''
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

import openai
import logging
import time

# 設定 logging 以便調試
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

def test_do_with_sdk():
    # 模擬 OpenAI 客戶端（這裡使用的是 OpenAI SDK 的方法，已經包含在 `openai` 模塊中）
    openai.api_key = "你的 API 金鑰"  # 替換為你自己的金鑰

    # 這是模擬的輸入和指令
    inputs = "請解釋量子計算的基本概念"
    instructions = "作為一個知識助手，解釋量子計算。"
    
    tools = [
        {"name": "tool1", "description": "A sample tool for demonstration purposes."}
    ]
    model_name = "gpt-4"  # 或者使用其他模型名稱，如 "assistant"

    # 取得上傳的文件
    uploaded_files = openai.files.list()
    uploaded_files_data = uploaded_files['data']
    uploaded_fileids = [file['id'] for file in uploaded_files_data]
    logger.debug("Uploaded file IDs: ", uploaded_fileids)

    # 創建知識助手
    assis = openai.beta.assistants.create(
        name="Knowledge Assistant",
        instructions=instructions,
        model=model_name,
        tools=tools,
        file_ids=uploaded_fileids,
    )

    # 創建一個討論串
    thread = openai.beta.threads.create()

    # 發送訊息到討論串
    openai.beta.threads.messages.create(
        thread_id=thread['id'],
        role="user",
        content=inputs,
    )

    # 創建執行任務
    run = openai.beta.threads.runs.create(
        thread_id=thread['id'], assistant_id=assis['id']
    )

    # 等待任務完成
    while True:
        retrieved_run = openai.beta.threads.runs.retrieve(
            thread_id=thread['id'], run_id=run['id']
        )
        logger.debug("Retrieved run: ", retrieved_run)
        if retrieved_run['status'] == "completed":
            break
        time.sleep(1)  # 等待 1 秒後再檢查狀態

    # 獲取討論內容
    thread_messages = openai.beta.threads.messages.list(thread['id'])
    logger.debug("Thread messages: ", thread_messages['data'])

    # 返回最初的回應內容
    return thread_messages['data'][0]['content'][0]['text']['value']

result = test_do_with_sdk()
print("Test result:", result)
