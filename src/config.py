import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    LAST_NAME = os.getenv("LAST_NAME")
    FIRST_NAME = os.getenv("FIRST_NAME")
    EMAIL = os.getenv("EMAIL")
    PASSPORT = os.getenv("PASSPORT")
    PHONE = os.getenv("PHONE")

    TARGET_URL = os.getenv("TARGET_URL")
