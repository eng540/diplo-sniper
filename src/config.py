"""
Elite Sniper v2.0 - Configuration Module
Enhanced with proxy support, timing thresholds, and category mappings
"""

import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv("config.env")


class Config:
    """Centralized configuration for Elite Sniper v2.0"""
    
    # ==================== Telegram ====================
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    # ==================== User Data ====================
    LAST_NAME = os.getenv("LAST_NAME")
    FIRST_NAME = os.getenv("FIRST_NAME")
    EMAIL = os.getenv("EMAIL")
    PASSPORT = os.getenv("PASSPORT")
    PHONE = os.getenv("PHONE")
    
    # ==================== Target ====================
    TARGET_URL = os.getenv("TARGET_URL")
    TIMEZONE = "Asia/Aden"  # GMT+3
    
    # ==================== Proxies (3 sessions) ====================
    # Format: "http://user:pass@host:port" or "socks5://host:port"
    PROXIES = [
        os.getenv("PROXY_1"),  # Scout proxy
        os.getenv("PROXY_2"),  # Attacker 1 proxy
        os.getenv("PROXY_3"),  # Attacker 2 proxy
    ]
    
    # ==================== Session Thresholds ====================
    SESSION_MAX_AGE = 60          # Maximum session age in seconds (Hard-Kill)
    SESSION_MAX_IDLE = 15         # Maximum idle time before refresh
    HEARTBEAT_INTERVAL = 10       # Keep-alive interval in seconds
    MAX_CAPTCHA_ATTEMPTS = 5      # Per session before rebirth
    MAX_CONSECUTIVE_ERRORS = 3    # Before forced rebirth
    
    # ==================== Timing Configuration ====================
    ATTACK_HOUR = 2               # Attack hour in Aden time (2:00 AM)
    PRE_ATTACK_MINUTE = 59        # Pre-attack minute (1:59 AM)
    PRE_ATTACK_SECOND = 30        # Pre-attack second (1:59:30 AM)
    ATTACK_WINDOW_MINUTES = 2     # Duration of attack window
    
    # ==================== Sleep Intervals ====================
    PATROL_SLEEP_MIN = 10.0       # Normal patrol minimum sleep
    PATROL_SLEEP_MAX = 20.0       # Normal patrol maximum sleep
    WARMUP_SLEEP = 5.0            # Warmup mode sleep
    ATTACK_SLEEP_MIN = 0.5        # Attack mode minimum sleep
    ATTACK_SLEEP_MAX = 1.5        # Attack mode maximum sleep
    PRE_ATTACK_SLEEP = 0.5        # Pre-attack ready state
    
    # ==================== Category IDs ====================
    # Map purpose names to their exact Value attribute for server-side trigger
    CATEGORY_IDS = {
        "study": "1",
        "student": "1",
        "work": "2",
        "family": "3",
        "tourism": "4",
        "other": "5",
    }
    DEFAULT_CATEGORY = "1"  # Default if not matched
    
    # ==================== NTP Servers ====================
    NTP_SERVERS = [
        "pool.ntp.org",
        "time.google.com",
        "time.windows.com",
        "time.nist.gov"
    ]
    NTP_SYNC_INTERVAL = 300  # Re-sync every 5 minutes
    
    # ==================== Browser Configuration ====================
    HEADLESS = True
    BROWSER_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--no-first-run",
        "--disable-extensions"
    ]
    
    # ==================== Evidence Configuration ====================
    EVIDENCE_DIR = "evidence"
    MAX_EVIDENCE_AGE_HOURS = 48  # Auto-cleanup after 48 hours
