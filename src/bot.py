import time
import random
import datetime
import logging
import re
import pytz
from playwright.sync_api import sync_playwright

from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("DiploHyper")

# ================= BOT =================
class DiploBot:

    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url = Config.TARGET_URL + "&request_locale=en"

        self.tz = pytz.timezone("Asia/Aden")
        self.consecutive_errors = 0

        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Chrome/124.0.0.0",
            "Mozilla/5.0 (X11; Linux x86_64) Chrome/123.0.0.0"
        ]

    # ================= DYNAMIC SPEED =================
    def dynamic_delay(self):
        now = datetime.datetime.now(self.tz)

        if (now.hour == 1 and now.minute >= 55) or (now.hour == 2 and now.minute <= 10):
            return 0.1  # Attack Window

        if 8 <= now.hour <= 15:
            return random.uniform(15, 45)

        return random.uniform(120, 300)

    # ================= CONTEXT =================
    def create_context(self, p):
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )

        context = browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Asia/Aden"
        )

        page = context.new_page()

        # تقليل البصمة
        page.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ["image", "media", "font"]
            else route.continue_()
        )

        return browser, context, page

    # ================= CAPTCHA =================
    def handle_captcha(self, page):
        try:
            if not page.locator("input[name='captchaText']").is_visible():
                return True

            captcha_div = page.locator("captcha > div").first
            if not captcha_div.is_visible():
                return False

            png = captcha_div.screenshot()
            code = self.solver.solve(png).replace(" ", "").strip()

            if 3 < len(code) < 9:
                page.fill("input[name='captchaText']", code)
                page.keyboard.press("Enter")
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                except:
                    pass

                return not page.locator("input[name='captchaText']").is_visible()
        except:
            pass

        return False

    # ================= FORM =================
    def fill_form(self, page):
        try:
            if not page.locator("input[name='lastname']").is_visible():
                return False

            page.fill("input[name='lastname']", Config.LAST_NAME)
            page.fill("input[name='firstname']", Config.FIRST_NAME)
            page.fill("input[name='email']", Config.EMAIL)

            if page.locator("input[name='emailrepeat']").is_visible():
                page.fill("input[name='emailrepeat']", Config.EMAIL)

            if page.locator("input[name='passportNumber']").is_visible():
                page.fill("input[name='passportNumber']", Config.PASSPORT)

            if page.locator("input[name='phone']").is_visible():
                phone = Config.PHONE.replace("+", "00")
                page.fill("input[name='phone']", phone)

            return True
        except:
            return False

    # ================= MAIN LOOP =================
    def run(self):
        with sync_playwright() as p:
            browser, context, page = self.create_context(p)

            logger.info("🚀 DIPLO HYPER BOT STARTED")
            send_alert("🚀 Diplo Hyper Bot Online")

            while True:
                try:
                    delay = self.dynamic_delay()

                    if delay > 1:
                        logger.info(f"💤 Sleeping {int(delay)}s")
                        time.sleep(delay)

                    today = datetime.date.today()

                    for i in range(2):
                        target = today + datetime.timedelta(days=30 * i)
                        date_str = target.strftime("15.%m.%Y")
                        base = self.base_url.split("&dateStr=")[0]
                        url = f"{base}&dateStr={date_str}"

                        logger.info(f"🔎 Scanning {date_str}")
                        try:
                            page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        except:
                            self.consecutive_errors += 1
                            continue

                        if not self.handle_captcha(page):
                            continue

                        content = page.content().lower()

                        if "appointment_showDay" not in content:
                            continue

                        logger.info("🔥 DAY FOUND")
                        send_alert(f"🔥 Slot found {date_str}")

                        day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                        if not day_links:
                            continue

                        day_links[0].click()
                        self.handle_captcha(page)

                        time_links = page.locator("a.arrow[href*='appointment_showForm']").all()
                        if not time_links:
                            continue

                        time_links[0].click()
                        self.handle_captcha(page)

                        if self.fill_form(page):
                            if "appointment number" in page.content().lower():
                                logger.info("🎯 BOOKED SUCCESSFULLY")
                                send_alert("🎯 BOOKING SUCCESS")
                                return

                except Exception as e:
                    logger.error(f"❌ ERROR: {e}")
                    self.consecutive_errors += 1
                    time.sleep(10)

                    if self.consecutive_errors > 5:
                        logger.warning("♻️ RESETTING SESSION")
                        try:
                            context.close()
                            browser.close()
                        except:
                            pass
                        browser, context, page = self.create_context(p)
                        self.consecutive_errors = 0