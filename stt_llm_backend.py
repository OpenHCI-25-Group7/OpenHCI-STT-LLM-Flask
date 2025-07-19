import os
import threading
import datetime
import time
from flask import Flask, jsonify, request
import speech_recognition as sr
from concurrent import futures
from openai import OpenAI, RateLimitError
import json
import serial
import threading
from threading import Thread
from flask_cors import CORS
import re
import requests
from pydantic import BaseModel
from typing import Literal

class EmotionAnalysisResult(BaseModel):
    emotion_label: str
    duration: float
    bias_count: int
    weather: str

    def to_dict(self):
        return {
            "emotion_label": self.emotion_label,
            "duration": self.duration,
            "bias_count": self.bias_count,
            "weather": self.weather
        }



app = Flask(__name__)
CORS(app)

SERIAL_PORT = '/dev/tty.usbmodem1301'
BAUD_RATE = 9600

FRONTEND_RPI_IP = "http://172.20.10.9:8080"

SER = False

if SER:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)

serial_message = ""

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SpeechRecognizer:
    def __init__(self):
        os.makedirs("./asr_output", exist_ok=True)

        self.rec = sr.Recognizer()
        self.mic = sr.Microphone(device_index=1)
        
        microphones = sr.Microphone.list_microphone_names()
        print("Available:")
        for i, mic_name in enumerate(microphones):
            print(f"{i}: {mic_name}")

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
    prompt = summary
    sys_prompt = ""
    with open("sys_prompt.txt", "r", encoding="utf-8") as file:
        sys_prompt = file.read()
        # print(sys_prompt)

    try:
        # Make the API call to GPT-4 to generate a response
        response = client.responses.parse(
            model="gpt-4o-2024-08-06",
            input=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt}
            ],
            text_format=EmotionAnalysisResult
        )

        parsed_result = response.output_parsed
        print(response)
        print(parsed_result)
        return jsonify(response.to_dict()['output'][0]['content'][0]['parsed'])
        
    except RateLimitError:
        # Handle OpenAI API rate limit errors
        return jsonify({"error": "OpenAI API quota exceeded"}), 429
    except Exception as e:
        # Handle general exceptions and log the error
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

def read_serial():
    """
    TODO: Pass signals from arduino to the frontend
    """
    global serial_message
    while True:
        try:
            if ser.in_waiting > 0:
                message = ser.readline().decode('utf-8').strip()
                if message:
                    serial_message = message
                    print("Received message:", serial_message)

                    if(message[0:5] == "MODE:"):
                        mode = int(serial_message[5])
                        print(mode)

                        start = datetime.datetime.now()
                        file = {
                            "mode": mode 
                        }
                        response = requests.post(FRONTEND_RPI_IP + "/set_mode", files=file) # request for result
                        end = datetime.datetime.now()
                        print("Response time: {} ms".format(int((end-start).microseconds/1000)))

                        if response.status_code == 200:
                            result = response.json()['result']
                            return result
                        else:
                            return "NULL"

        except serial.SerialException as e:
            print(f"SerialException: {e}")
            if str(e) == 'device reports readiness to read but returned no data (device disconnected or multiple access on port?)':
                print("Attempting to reconnect...")
                try:
                    ser.close()  # 關閉串口
                    time.sleep(2)  # 等待一段時間再重新開啟串口
                    ser.open()  # 重新開啟串口
                    print("Reconnected to the serial device.")
                except Exception as ex:
                    print(f"Failed to reconnect: {ex}")
        time.sleep(0.1)


def start_serial_read():
    serial_thread = Thread(target=read_serial)
    serial_thread.daemon = True
    serial_thread.start()



# 原 前端設定

# 👉 解決 CORS
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], 
     allow_headers=["Content-Type"])

@app.route("/display_content_sentence", methods=["POST"])
def display_content_sentence():
    print("收到前端請求：", request.json)
    
    return jsonify({
        "result": {
            "suggestion": "精選書摘《我不是不努力，只是做不到你滿意》：大人一句無心的話，如何把孩子推入困境？",
            "fortune": "今天稱讚家人一句，氣氛 +1°C ☀️"
        }
    })

@app.route("/family_weather", methods=["POST"])
def family_weather():
    print("收到家庭天氣請求：", request.json)
    
    return jsonify({
        #接收llm response
        "status": "小雨"  # 可改成：晴天、多雲、小雨、雷陣雨
    })

# 用於暫存切換頁面事件資料（這邊是切換頁面事件的參數記憶）
event_logs = []
@app.route('/log', methods=['POST'])
def log_event():
    try:
        data = request.get_json()
        log_entry = {
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
            "event": data.get("event"),
            "weather": data.get("weather"),
            "person_near": data.get("person_near")
        }
        event_logs.append(log_entry)
        print(f"✅ 收到事件紀錄: {log_entry}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400
    

if __name__ == "__main__":
    print("Flask STT server running...")
    # display_content()
    # start_serial_read()

    app.run(host="0.0.0.0", port=5000, threaded=True)
