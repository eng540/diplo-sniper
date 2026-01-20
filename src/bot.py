import time
import random
import datetime
import os
import logging
import pytz 
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MuscatAmbush")

class DiploBot:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url_template = Config.TARGET_URL + "&request_locale=en"
        # توقيت اليمن (GMT+3) هو المعيار
        self.timezone = pytz.timezone("Asia/Aden") 
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]

    def wait_for_zero_hour(self):
        """
        بروتوكول الكمين: الانتظار الصامت حتى 01:59:50
        """
        logger.info("⏳ AMBUSH MODE: Waiting for Zero Hour (01:59:50)...")
        
        while True:
            now = datetime.datetime.now(self.timezone)
            
            # هل وصلنا للوقت المحدد؟ (01:59:50) أو نحن بالفعل في الساعة 2؟
            if (now.hour == 1 and now.minute == 59 and now.second >= 50) or (now.hour == 2):
                logger.info("⚡ ZERO HOUR REACHED! LAUNCHING ATTACK! ⚡")
                return # كسر حلقة الانتظار والانطلاق
            
            # طباعة حالة كل 30 ثانية لطمأنة المستخدم أن البوت حي
            if now.second % 30 == 0:
                logger.info(f"🕒 Waiting... Current time: {now.strftime('%H:%M:%S')}")
                time.sleep(1)
            
            # فحص سريع جداً (عشر ثانية) للدقة
            time.sleep(0.1)

    def get_month_urls(self):
        urls = []
        today = datetime.datetime.now(self.timezone).date()
        base_clean = self.base_url_template.split("&dateStr=")[0] if "&dateStr=" in self.base_url_template else self.base_url_template
        
        for i in range(6): 
            future_month = (today.month + i - 1) % 12 + 1
            future_year = today.year + ((today.month + i - 1) // 12)
            date_str = f"15.{future_month:02d}.{future_year}"
            full_url = f"{base_clean}&dateStr={date_str}"
            urls.append(full_url)
        return urls

    def type_fast(self, page, selector, text):
        try:
            page.focus(selector)
            page.fill(selector, text)
        except: pass
            
    def create_context(self, browser):
        ua = random.choice(self.user_agents)
        context = browser.new_context(
            user_agent=ua,
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Asia/Aden"
        )
        page = context.new_page()
        page.add_init_script("""Object.defineProperty(navigator, 'webdriver', { get: () => undefined });""")
        context.set_default_timeout(30000)
        return context, page

    def handle_captcha(self, page, location="General"):
        for attempt in range(5):
            try:
                if not page.locator("input[name='captchaText']").is_visible():
                    return True 

                captcha_div = page.locator("captcha > div").first
                
                if captcha_div.is_visible():
                    # لا انتظار في وقت الهجوم
                    # page.wait_for_timeout(300) 
                    captcha_bytes = captcha_div.screenshot()
                    code = self.solver.solve(captcha_bytes)
                    code = code.replace(" ", "").strip()

                    if len(code) < 4 or len(code) > 8: 
                        refresh_btn = page.locator("input[name*='refreshCaptcha']")
                        if refresh_btn.is_visible():
                            refresh_btn.click()
                            page.wait_for_timeout(500)
                        else:
                            page.reload()
                        continue
                    
                    logger.info(f"🧩 {location} Captcha: {code}")
                    page.fill("input[name='captchaText']", code)
                    page.keyboard.press("Enter")
                    
                    try: page.wait_for_load_state("domcontentloaded", timeout=3000)
                    except: pass

                    if page.locator("input[name='captchaText']").is_visible():
                        continue 
                    
                    content = page.content().lower()
                    if "error occurred" in content or "ref-id" in content:
                        return False

                    return True

            except Exception:
                page.reload()
        return False

    def select_visa_category(self, page):
        try:
            select_locator = page.locator("select").first
            if not select_locator.is_visible(): return
            priority = ["student", "studium", "language", "sprachkurs", "master", "bachelor"]
            options = select_locator.locator("option").all()
            for option in options:
                if any(k in option.text_content().lower() for k in priority):
                    select_locator.select_option(value=option.get_attribute("value"))
                    return
            select_locator.select_option(index=1)
        except: pass

    def fill_booking_form(self, page, context):
        logger.info("📝 Fast-Filling...")
        try:
            if not page.locator("input[name='lastname']").is_visible(): return False

            self.type_fast(page, "input[name='lastname']", Config.LAST_NAME)
            self.type_fast(page, "input[name='firstname']", Config.FIRST_NAME)
            self.type_fast(page, "input[name='email']", Config.EMAIL)
            
            if page.locator("input[name='emailrepeat']").is_visible():
                self.type_fast(page, "input[name='emailrepeat']", Config.EMAIL)
            elif page.locator("input[name='emailRepeat']").is_visible():
                self.type_fast(page, "input[name='emailRepeat']", Config.EMAIL)

            if page.locator("input[name='passportNumber']").is_visible():
                self.type_fast(page, "input[name='passportNumber']", Config.PASSPORT)
            elif page.locator("input[name='fields[0].content']").is_visible():
                self.type_fast(page, "input[name='fields[0].content']", Config.PASSPORT)

            clean_phone = Config.PHONE.replace("+", "00").replace(" ", "").strip()
            if page.locator("input[name='phone']").is_visible():
                self.type_fast(page, "input[name='phone']", clean_phone)
            elif page.locator("input[name='fields[1].content']").is_visible():
                self.type_fast(page, "input[name='fields[1].content']", clean_phone)

            self.select_visa_category(page)

            for _ in range(10): # زيادة عدد المحاولات في وقت الذروة
                if not self.handle_captcha(page, location="Form"):
                    if page.locator("input[name='lastname']").is_visible(): continue
                    return False

                try: page.wait_for_load_state("networkidle", timeout=3000)
                except: pass
                
                content = page.content().lower()
                if "appointment number" in content or "successfully booked" in content:
                    details = f"✅ VICTORY! {Config.FIRST_NAME} {Config.LAST_NAME}"
                    logger.info(details)
                    ts = datetime.datetime.now().strftime("%H%M%S")
                    page.screenshot(path=f"WIN_{ts}.png")
                    send_photo(f"WIN_{ts}.png", caption=details)
                    return True
                
                if page.locator("input[name='lastname']").is_visible():
                    logger.warning("⚠️ Silent Reject. Retrying...")
                    continue
                
                return False 

            return False
        except: return False

    def run(self):
        with sync_playwright() as p:
            # تشغيل المتصفح مسبقاً (Pre-warm)
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--no-first-run", "--disable-extensions"]
            )
            context, page = self.create_context(browser)
            
            logger.info("🛡️ SYSTEM READY. Engaging Ambush Protocol...")
            
            # 🛑 نقطة التوقف: هنا ينتظر البوت حتى 01:59:50
            self.wait_for_zero_hour()
            
            # 🚀 الانطلاق: الكود أدناه ينفذ فوراً بعد كسر الانتظار
            send_alert("🚀 ZERO HOUR! ATTACK STARTED!")
            
            while True:
                month_urls = self.get_month_urls()
                for url in month_urls:
                    try:
                        # محاولة الدخول بأقصى سرعة (Timeout قصير جداً)
                        try: page.goto(url, wait_until="domcontentloaded", timeout=10000)
                        except: continue
                        
                        if not self.handle_captcha(page, location="Month"): continue 

                        # منطق التحقق الصارم (الكلب البوليسي)
                        if page.locator("#calendarform").is_visible():
                            day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                            
                            if not day_links:
                                continue # الشهر فارغ، التالي!
                            
                            logger.info(f"🔥 {len(day_links)} DAYS OPEN!")
                            # في وقت الذروة، الاختيار العشوائي هو النجاة
                            random.choice(day_links).click()
                            
                            if not self.handle_captcha(page, location="Day"):
                                page.go_back()
                                continue
                            
                            time_links = page.locator("a.arrow[href*='appointment_showForm']").all()
                            if time_links:
                                logger.info(f"⏰ {len(time_links)} SLOTS!")
                                random.choice(time_links).click()
                                
                                if not self.handle_captcha(page, location="PreForm"):
                                    page.go_back()
                                    continue
                                
                                if self.fill_booking_form(page, context):
                                    return 
                                else:
                                    page.goto(url) 
                                    continue
                        else:
                            # التعامل مع حالات الخطأ أو الكابتشا المعلقة
                            content = page.content()
                            if "captchaText" in content: continue
                            if "Unfortunately" in content: continue
                            page.reload()

                    except Exception as e:
                        # في وقت الهجوم، تجاهل الأخطاء وأعد المحاولة
                        try: context.close()
                        except: pass
                        context, page = self.create_context(browser)
                
                # لا نوم في وقت الذروة (الساعة 2)
                now = datetime.datetime.now(self.timezone)
                if now.hour == 2 and now.minute < 30:
                    pass # استمر في القصف
                else:
                    logger.info("💤 Patrol sleep...")
                    time.sleep(30)