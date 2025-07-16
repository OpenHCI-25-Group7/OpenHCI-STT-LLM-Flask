import os
import speech_recognition as sr
from concurrent import futures

class SpeechRecognizer:
    def __init__(self):
        os.makedirs("./out", exist_ok=True)
        self.path = f"./out/asr.txt"

        self.rec = sr.Recognizer()
        self.mic = sr.Microphone(device_index=1)

        self.pool = futures.ThreadPoolExecutor(thread_name_prefix="Rec Thread")
        self.speech = []

    def recognize_audio_thread_pool(self, audio, event=None):
        future = self.pool.submit(self.recognize_audio, audio)
        self.speech.append(future)

    def grab_audio(self) -> sr.AudioData:
        with self.mic as source:
            # audio = self.rec.listen(source)
            audio = self.rec.listen(source, timeout=10, phrase_time_limit=5)
        return audio

    def recognize_audio(self, audio: sr.AudioData) -> str:
        print("Processing...")
        try:
            # Google Speech-to-Text API
            speech = self.rec.recognize_google(audio, language="zh-CN")
            print(f"Result: {speech}")
            with open(self.path, mode='a', encoding="utf-8") as out:
                out.write(f"{speech}\n")

        except sr.UnknownValueError:
            print(speech)
        except sr.RequestError as e:
            speech = f"Error: {e}"
            print(speech)
        return speech

    def run(self):
        print("Listening...")
        with self.mic as source:
            self.rec.adjust_for_ambient_noise(source, duration=1)

        try:
            while True:
                audio = self.grab_audio()
                self.recognize_audio_thread_pool(audio) 
        except KeyboardInterrupt:
            print("Interrupted")
        finally:
            futures.wait(self.speech)

if __name__ == "__main__":
    sp = SpeechRecognizer()

    microphones = sr.Microphone.list_microphone_names()
    print("Available:")
    for i, mic_name in enumerate(microphones):
        print(f"{i}: {mic_name}")

    sp.run()
