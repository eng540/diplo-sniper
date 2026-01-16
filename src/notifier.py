import requests
from .config import Config

def send_alert(message):
    """إرسال رسالة نصية"""
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": Config.TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Telegram Text Error: {e}")

def send_photo(photo_path, caption=""):
    """إرسال صورة (لقطة الشاشة)"""
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendPhoto"
    data = {"chat_id": Config.TELEGRAM_CHAT_ID, "caption": caption}
    try:
        with open(photo_path, "rb") as image_file:
            files = {"photo": image_file}
            requests.post(url, data=data, files=files, timeout=20)
    except Exception as e:
        print(f"Telegram Photo Error: {e}")