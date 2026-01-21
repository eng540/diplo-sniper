import time
import random
import datetime
import logging
import pytz 
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert

logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("HydraUnit")

class DiploBot:
    def __init__(self, instance_id=1):
        self.id = instance_id
        self.solver = CaptchaSolver()
        self.base_url_template = Config.TARGET_URL + "&request_locale=en"
        self.timezone = pytz.timezone("Asia/Aden")
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ]

    def log(self, msg):
        logger.info(f"[Unit-{self.id}] {msg}")

    def wait_for_zero_hour(self):
        self.log("⏳ Waiting for 01:59:50...")
        while True:
            now = datetime.datetime.now(self.timezone)
            if (now.hour == 1 and now.minute == 59 and now.second >= 50) or (now.hour == 2):
                self.log("⚡ GO GO GO! ⚡")
                return 
            time.sleep(0.1)

    def get_month_urls(self):
        urls = []
        today = datetime.datetime.now(self.timezone).date()
        base_clean = self.base_url_template.split("&dateStr=")[0]
        # ترتيب الأشهر: 3, 4, 2, 5
        offsets = [2, 3, 1, 4] 
        for offset in offsets: 
            future_month = (today.month + offset - 1) % 12 + 1
            future_year = today.year + ((today.month + offset - 1) // 12)
            date_str = f"15.{future_month:02d}.{future_year}"
            full_url = f"{base_clean}&dateStr={date_str}"
            urls.append(full_url)
        return urls

    def fast_inject(self, page, selector, value):
        try:
            page.evaluate(f"""
                const el = document.querySelector("{selector}");
                if(el) {{ el.value = "{value}"; el.dispatchEvent(new Event('input')); }}
            """)
        except: pass

    def handle_captcha(self, page, location="General"):
        try:
            if not page.locator("input[name='captchaText']").is_visible(): return True 
            captcha_div = page.locator("captcha > div").first
            if captcha_div.is_visible():
                code = self.solver.solve(captcha_div.screenshot()).replace(" ", "").strip()
                if len(code) > 3:
                    self.fast_inject(page, "input[name='captchaText']", code)
                    page.keyboard.press("Enter")
                    try: page.wait_for_load_state("domcontentloaded", timeout=3000)
                    except: pass
                    if page.locator("input[name='captchaText']").is_visible(): return False
                    if "error occurred" in page.content().lower(): return False
                    return True
        except: pass
        return False

    def fill_booking_form(self, page):
        self.log("📝 Injecting Data...")
        try:
            if not page.locator("input[name='lastname']").is_visible(): return False
            self.fast_inject(page, "input[name='lastname']", Config.LAST_NAME)
            self.fast_inject(page, "input[name='firstname']", Config.FIRST_NAME)
            self.fast_inject(page, "input[name='email']", Config.EMAIL)
            if page.locator("input[name='emailrepeat']").count() > 0:
                self.fast_inject(page, "input[name='emailrepeat']", Config.EMAIL)
            else:
                self.fast_inject(page, "input[name='emailRepeat']", Config.EMAIL)
            self.fast_inject(page, "input[name*='fields[0]']", Config.PASSPORT)
            self.fast_inject(page, "input[name*='fields[1]']", Config.PHONE.replace("+", "00").strip())
            
            # Select Category
            page.evaluate("""
                const s = document.querySelector('select');
                if(s){ s.selectedIndex=1; s.dispatchEvent(new Event('change')); }
            """)

            for i in range(5):
                self.log(f"🚀 Submit #{i+1}")
                if not self.handle_captcha(page, location="Form"):
                    if page.locator("input[name='lastname']").is_visible(): continue
                    return False
                try: page.wait_for_load_state("networkidle", timeout=3000)
                except: pass
                if "appointment number" in page.content().lower():
                    self.log("✅ VICTORY!")
                    send_alert(f"✅ UNIT-{self.id} WON!")
                    return True
                if page.locator("input[name='lastname']").is_visible(): continue
                return False 
            return False
        except: return False

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--no-first-run"]
            )
            context = browser.new_context(
                user_agent=random.choice(self.user_agents),
                viewport={"width": 1366, "height": 768},
                locale="en-US",
                timezone_id="Asia/Aden"
            )
            page = context.new_page()
            page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())

            # الدخول المسبق لشهر 3
            try:
                target_urls = self.get_month_urls()
                page.goto(target_urls[0], timeout=30000)
                if page.locator("input[name='captchaText']").is_visible():
                    self.handle_captcha(page, location="WarmUp")
            except: pass

            self.wait_for_zero_hour()
            
            while True:
                month_urls = self.get_month_urls()
                for url in month_urls:
                    try:
                        if url in page.url: page.reload()
                        else: 
                            try: page.goto(url, wait_until="domcontentloaded", timeout=10000)
                            except: continue
                        
                        if not self.handle_captcha(page, location="Month"): continue 

                        if page.locator("#calendarform").is_visible():
                            day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                            if not day_links: continue 
                            
                            self.log(f"🔥 FOUND {len(day_links)} DAYS!")
                            day_links[0].click() # الأول فوراً
                            
                            if not self.handle_captcha(page, location="Day"): 
                                page.go_back(); continue
                            
                            time_links = page.locator("a.arrow[href*='appointment_showForm']").all()
                            if time_links:
                                self.log(f"⏰ SLOTS! Taking FIRST...")
                                time_links[0].click()
                                if not self.handle_captcha(page, location="PreForm"):
                                    page.go_back(); continue
                                if self.fill_booking_form(page): return 
                                else: page.goto(url); continue
                        else:
                            content = page.content()
                            if "captchaText" in content or "Unfortunately" in content: continue
                            page.reload()
                    except:
                        try: context.close()
                        except: pass
                        context, page = self.create_context(browser) # إعادة بناء سريع