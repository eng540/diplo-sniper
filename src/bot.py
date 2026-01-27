import time
import random
import datetime
import logging
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("KingSniper")

# ================= BOT =====================
class KingSniper:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url = Config.TARGET_URL + "&request_locale=en"

        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Chrome/124.0.0.0",
            "Mozilla/5.0 (X11; Linux x86_64) Chrome/123.0.0.0"
        ]

    # -------- Browser ----------
    def create_browser(self, p):
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        context = browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={"width": 1366, "height": 768},
            locale="en-US"
        )
        page = context.new_page()

        # حظر الصور لتخفيف الحمل
        page.route("**/*", lambda r: r.abort()
                   if r.request.resource_type in ["image", "media", "font"]
                   else r.continue_())
        return browser, context, page

    # -------- CAPTCHA ----------
    def handle_captcha(self, page):
        try:
            if not page.locator("input[name='captchaText']").is_visible():
                return True

            captcha = page.locator("captcha > div").first
            if not captcha.is_visible():
                return False

            img = captcha.screenshot()
            code = self.solver.solve(img).replace(" ", "").strip()

            if len(code) < 4:
                return False

            page.fill("input[name='captchaText']", code)
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)

            return not page.locator("input[name='captchaText']").is_visible()
        except:
            return False

    # -------- MAIN LOOP ----------
    def run(self):
        with sync_playwright() as p:
            browser, context, page = self.create_browser(p)
            logger.info("👑 KING SNIPER ONLINE")

            while True:
                try:
                    today = datetime.date.today()

                    # فحص شهرين فقط (آمن)
                    for i in range(2):
                        target = today + datetime.timedelta(days=30 * i)
                        date_str = target.strftime("15.%m.%Y")
                        url = f"{self.base_url}&dateStr={date_str}"

                        logger.info(f"🔎 Scanning {date_str}")
                        try:
                            page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        except:
                            continue

                        if not self.handle_captcha(page):
                            continue

                        # هل توجد أيام؟
                        if "appointment_showDay" not in page.content():
                            continue

                        logger.info("🔥 DAY FOUND")
                        send_alert("🔥 Appointment Day Found")

                        day = page.locator("a.arrow[href*='appointment_showDay']").first
                        if not day.is_visible():
                            continue
                        day.click()

                        if not self.handle_captcha(page):
                            continue

                        time_slot = page.locator("a.arrow[href*='appointment_showForm']").first
                        if not time_slot.is_visible():
                            continue

                        logger.info("⏰ TIME FOUND")
                        time_slot.click()

                        if not self.handle_captcha(page):
                            continue

                        # ===== SUCCESS POINT =====
                        logger.info("🎯 BOOKING PAGE REACHED")
                        send_alert("🎯 Booking Page Reached")
                        page.screenshot(path="SUCCESS.png")
                        send_photo("SUCCESS.png", "🎯 Booking page reached")

                        return  # إيقاف هذا الـ King عند النجاح

                    time.sleep(30)

                except Exception as e:
                    logger.error(f"⚠️ Error: {e}")
                    time.sleep(10)