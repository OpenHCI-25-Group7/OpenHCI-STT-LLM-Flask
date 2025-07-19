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



app = Flask(__name__)
CORS(app)

SERIAL_PORT = '/dev/tty.usbmodem1301'
BAUD_RATE = 9600

FRONTEND_RPI_IP = "http://192.168.0.153:5555"

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
        print(sys_prompt)

    try:
        # Make the API call to GPT-4 to generate a response
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": sys_prompt},
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
                if all(k in parsed for k in ("emotion_label", "duration", "bias_count", "weather")):
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
                        payload = {
                            "mode": message 
                        }
                        response = requests.post(FRONTEND_RPI_IP + "/api/set_mode", files=payload) # request for result
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

if __name__ == "__main__":
    print("Flask STT server running...")
    # display_content()
    # start_serial_read()

    app.run(host="0.0.0.0", port=5000, threaded=True)
