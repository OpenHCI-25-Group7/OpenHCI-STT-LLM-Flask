import os
import threading
import datetime
import time
from flask import Flask, jsonify, request
import speech_recognition as sr
from concurrent import futures
from openai import OpenAI, RateLimitError
import json

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SpeechRecognizer:
    def __init__(self):
        os.makedirs("./asr_output", exist_ok=True)

        self.rec = sr.Recognizer()
        self.mic = sr.Microphone(device_index=1)
        self.lock = threading.Lock()

        self.pool = futures.ThreadPoolExecutor(thread_name_prefix="Rec Thread")
        self.speech = []
        self.running = True

        self.start_time = datetime.datetime.now()
        self.current_path = self._generate_path(self.start_time)
        self.asr_file_update_seconds = 3600
        self._ensure_file_exists(self.current_path)
        self.start_rotation_timer()

    def _generate_path(self, timestamp: datetime.datetime) -> str:
        formatted = timestamp.strftime("%Y-%m-%d-%H-%M-%S")
        return f"./asr_output/asr_{formatted}.txt"

    def _ensure_file_exists(self, path: str):
        with self.lock:
            if not os.path.exists(path):
                open(path, 'a').close()

    def _rotate_file_if_needed(self):
        now = datetime.datetime.now()
        if (now - self.start_time).total_seconds() >= self.asr_file_update_seconds:
            self.start_time = now
            self.current_path = self._generate_path(now)
            self._ensure_file_exists(self.current_path)

    def start_rotation_timer(self):
        def loop():
            while self.running:
                self._rotate_file_if_needed()
                time.sleep(1)
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def recognize_audio_thread_pool(self, audio):
        future = self.pool.submit(self.recognize_audio, audio)
        self.speech.append(future)

    def grab_audio(self) -> sr.AudioData:
        with self.mic as source:
            audio = self.rec.listen(source, timeout=10, phrase_time_limit=5)
        return audio

    def recognize_audio(self, audio: sr.AudioData) -> str:
        try:
            text = self.rec.recognize_google(audio, language="zh-CN")
            self._rotate_file_if_needed()
            with self.lock:
                with open(self.current_path, mode='a', encoding="utf-8") as out:
                    out.write(f"{text}\n")
            return text
        except sr.UnknownValueError:
            return "[Unrecognized]"
        except sr.RequestError as e:
            return f"Error: {e}"

    def run(self):
        with self.mic as source:
            self.rec.adjust_for_ambient_noise(source, duration=1)

        while self.running:
            try:
                audio = self.grab_audio()
                self.recognize_audio_thread_pool(audio)
            except Exception:
                continue

    def stop(self):
        self.running = False
        futures.wait(self.speech)

recognizer = SpeechRecognizer()
thread = threading.Thread(target=recognizer.run, daemon=True)
thread.start()

@app.route("/asr", methods=["GET"])
def get_transcript():
    path = recognizer.current_path
    transcript = ""
    if os.path.exists(path):
        with recognizer.lock:
            with open(path, encoding="utf-8") as f:
                transcript = f.read().strip()
    return jsonify({"transcript": transcript, "file": os.path.basename(path)})

@app.route("/asr/clear", methods=["POST"])
def clear_transcript():
    with recognizer.lock:
        open(recognizer.current_path, 'w').close()
    return jsonify({"status": "cleared"})

import re
import json

@app.route("/display_content", methods=["POST"])
def display_content():
    summary = ""
    # Loop through the files in the directory to create the conversation summary
    for fname in sorted(os.listdir("./asr_output")):
        if fname.endswith(".txt"):
            path = os.path.join("./asr_output", fname)
            with open(path, encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    # Formatting time information from the filename
                    time_info = fname.replace("asr_", "").replace(".txt", "").replace("-", ":", 2)
                    summary += f"[{time_info}] {content}\n"

    # Construct the prompt to send to GPT
    prompt = (
        "請你根據以下時間順序排列的家庭對話紀錄：\n" + summary +
        "\n請進行情緒與溝通分析，並觀察是否有好轉或惡化的趨勢。"
        "如果今天的對話比前幾天更融洽，請給予鼓勵性的今日運勢與天氣；"
        "如果今天比前幾天更緊張，請給予建設性的建議與觀察；"
        "若趨勢不明顯，請採用中立但正向的一般性鼓勵用語。"
        "接著請依據下列規則輸出：\n"
        "1. 依據整體情緒選出最相似的天氣（晴天、毛毛雨、暴風雪、雷陣雨、颳風）\n"
        "2. 依據話題寫出一句具新聞感的『每日頭條』\n"
        "3. 依據對話趨勢與狀態，寫出一句具鼓勵或建議性的『今日運勢』\n"
        "接著請「嚴格依據」下列規則輸出結果，格式為 JSON，不能做額外解釋或背景說明：\n"
        '{"weather": ..., "headline": ..., "fortune": ...}'

        "以下是如何進行分析的範例：\n"
        "範例 1:\n"
        "對話紀錄：\n"
        "[2025-07-10 10:00] 今天早上我們討論了一些問題，我覺得我們的溝通進展得不錯。\n"
        "[2025-07-10 10:30] 是的，雖然有點小爭執，但最終我們都能理解對方的觀點。\n"
        "分析：很理性溝通、無激烈情緒字眼，判斷為晴天、富有希望的新聞、漸入佳境的運勢\n"
        "GPT response: "
        '{"weather": 晴天, "headline": 美國高關稅將上路 台、日、歐、印等仍可達成協議。, "fortune": 今天的溝通會較為融洽，建議保持開放的態度，繼續良好的合作。}'

        "範例 2:\n"
        "對話紀錄：\n"
        "[2025-07-09 14:00] 我我我。\n"
        "[2025-07-09 14:05] 我沒有不聽。\n"
        "[2025-07-09 14:10] 哈囉哈囉。\n"
        "[2025-07-09 14:05] XXXYYYmejfnjfn。\n"
        "分析：若收音不穩、對話內容、情緒不明顯，請採用中立的陰天、一般的氣象新聞、中立但正向的一般性鼓勵用語。\n"
        "GPT response: "
        '{"weather": 陰天, "headline": 今天氣不穩「6縣市大雨特報」周五起留意熱帶系統動向。, "fortune": 今天的溝通會較為融洽，建議保持開放的態度，繼續良好的合作。}'

        "範例 3:\n"
        "對話紀錄：\n"
        "[2025-07-10 14:00] 不要讀設計系，我有點擔心你未來的工作機會。\n"
        "[2025-07-10 14:05] 我明白你的擔心，但我覺得設計系是個充滿創意的領域，應該很有發展空間。\n"
        "[2025-07-10 14:10] 為什麼。\n"
        "[2025-07-10 14:05] 我不明白。\n"
        "分析：理性但相互不太理解，採用中立的颳風天、促進該話題理解的新聞、正向的鼓勵溝通用語。\n"
        "GPT response: "
        '{"weather": "颳風", "headline": "新一代設計展開幕，未來設計領域將成為最具創意的職業之一", "fortune": "今日的溝通會有一些矛盾，建議冷靜處理並聽取彼此觀點，能有所進展。"}\n'

        "範例 4:\n"
        "對話紀錄：\n"
        "[2025-07-10 16:00] 你為什麼都不交男朋友\n"
        "[2025-07-10 16:05] 我只是有不同的看法\n"
        "[2025-07-10 16:10] 請不要這麼激動\n"
        "[2025-07-10 16:50] 好吧\n"
        "[2025-07-10 16:50] 都這樣啊\n"
        "分析：這段對話顯示出強烈的情緒波動，有爭吵的情況，情緒較為負面，伴侶議題相關。採用激烈的雷陣雨、促進該話題理解的新聞、建議冷靜嘗試理解的用語\n"
        "分析：理性但相互不太理解，採用中立的颳風天、促進該話題理解的新聞、正向的鼓勵溝通用語。\n"
        "GPT response: "
        '{"weather": "雷陣雨", "headline": "台灣生育率全球最低，如何解鎖年輕世代「不婚不生」背後的深層心結？", "fortune": "今天容易有情緒化反應，建議嘗試理解對方立場，說不定有新的發現。"}\n'
    )

    try:
        # Make the API call to GPT-4 to generate a response
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        result = response.choices[0].message.content.strip()

        # Debug: Print GPT response content
        print("GPT Response Content: ", result)

        # Try extracting the JSON part from the GPT response using regex
        match = re.search(r'\{.*\}', result)
        if match:
            json_str = match.group(0)  # Extract the JSON part
            print("Extracted JSON String: ", json_str)

            # Attempt to parse the extracted JSON string
            try:
                parsed = json.loads(json_str)
                if all(k in parsed for k in ("weather", "headline", "fortune")):
                    # If successful, return the parsed JSON
                    return jsonify({"result": parsed})
            except json.JSONDecodeError as e:
                # Handle JSON parsing errors
                print(f"JSON Decode Error: {e}")
                return jsonify({"error": "Invalid JSON format in GPT response"}), 500
        else:
            # If no valid JSON is found, return an error
            return jsonify({"error": "Failed to extract valid JSON from the response"}), 500

    except RateLimitError:
        # Handle OpenAI API rate limit errors
        return jsonify({"error": "OpenAI API quota exceeded"}), 429
    except Exception as e:
        # Handle general exceptions and log the error
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("Flask STT server running...")
    app.run(host="0.0.0.0", port=5000, threaded=True)
