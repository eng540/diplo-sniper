import requests
import os
from src.config import Config

def send_alert(message):
    """إرسال رسالة نصية"""
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": Config.TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Telegram Text Error: {e}")
        return False

def send_photo(photo_path, caption=""):
    """إرسال صورة (لقطة الشاشة)"""
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendPhoto"
    data = {"chat_id": Config.TELEGRAM_CHAT_ID, "caption": caption}
    try:
        if os.path.exists(photo_path):
            with open(photo_path, "rb") as image_file:
                files = {"photo": image_file}
                response = requests.post(url, data=data, files=files, timeout=20)
                response.raise_for_status()
                return True
    except Exception as e:
        print(f"Telegram Photo Error: {e}")
    return False

def send_file(file_path, caption=""):
    """✅ THE PROBE: إرسال ملف مستند (HTML/Log)"""
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendDocument"
    data = {"chat_id": Config.TELEGRAM_CHAT_ID, "caption": caption}
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                files = {"document": f}
                response = requests.post(url, data=data, files=files, timeout=30)
                response.raise_for_status()
                print(f"📤 File sent to Telegram: {file_path}")
                return True
    except Exception as e:
        print(f"Telegram File Error: {e}")
    return False

# ==================== التوافق مع King Sniper v12 ====================
# هذه التوابع مطلوبة لـ King Sniper v12 ولا توجد في النسخة الأصلية
def send_document(document_path: str, caption: str = "") -> bool:
    """
    إرسال مستند - متوافق مع King Sniper v12
    هذه مجرد wrapper حول send_file للحفاظ على التوافق
    """
    return send_file(document_path, caption)