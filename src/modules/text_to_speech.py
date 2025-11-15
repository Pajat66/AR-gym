import pyttsx3
import threading

# 初始化 pyttsx3 引擎
engine = pyttsx3.init()

def speak(text):
    """在单独的线程中播放语音"""
    def run():
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=run, daemon=True).start()