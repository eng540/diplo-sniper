import time
import random
import datetime
import os
import traceback
import re
import logging
import pytz 
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

# إعدادات السجل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("RocketMuscat")

class DiploBot:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url_template = Config.TARGET_URL + "&request_locale=en"
        # ضبط التوقيت على اليمن/مسقط
        self.timezone = pytz.timezone("Asia/Aden")
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]

    def wait_for_zero_hour(self):
        """
        الانتظار الصامت حتى 1:59:50
        """
        logger.info("⏳ Waiting for Zero Hour (01:59:50)...")
        while True:
            now = datetime.datetime.now(self.timezone)
            # الانطلاق قبل الموعد بـ 10 ثواني
            if (now.hour == 1 and now.minute == 59 and now.second >= 50) or (now.hour == 2):
                logger.info("⚡ ZERO HOUR REACHED! LAUNCHING! ⚡")
                return 
            time.sleep(0.1)

    def get_month_urls(self):
        urls = []
        today = datetime.datetime.now(self.timezone).date()
        base_clean = self.base_url_template.split("&dateStr=")[0] if "&dateStr=" in self.base_url_template else self.base_url_template
        
        # الترتيب الاستراتيجي: شهر 3، ثم 4، ثم 2، ثم 5
        # (Offset: 0=Current, 1=Next...)
        # شهر مارس هو (الشهر الحالي + 2) تقريباً حسب التاريخ الحالي
        priority_offsets = [2, 3, 1, 4] 
        
        for offset in priority_offsets: 
            future_month = (today.month + offset - 1) % 12 + 1
            future_year = today.year + ((today.month + offset - 1) // 12)
            date_str = f"15.{future_month:02d}.{future_year}"
            full_url = f"{base_clean}&dateStr={date_str}"
            urls.append(full_url)
        return urls

    def type_fast(self, page, selector, text):
        """حقن سريع (نفس الدالة الناجحة)"""
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
            timezone_id="Asia/Aden" # توقيت مسقط
        )
        page = context.new_page()
        
        # حظر الصور لزيادة السرعة (كما في النسخة الناجحة)
        page.route("**/*", lambda route: route.abort() 
                   if route.request.resource_type in ["image", "stylesheet", "font", "media"] 
                   else route.continue_())

        page.add_init_script("""Object.defineProperty(navigator, 'webdriver', { get: () => undefined });""")
        context.set_default_timeout(45000)
        return context, page

    def handle_captcha(self, page, context, location="General"):
        for attempt in range(5):
            try:
                if not page.locator("input[name='captchaText']").is_visible():
                    return True 

                logger.info(f"⚡ [Captcha-{location}] Attempt {attempt+1}...")
                captcha_div = page.locator("captcha > div").first
                
                if captcha_div.is_visible():
                    # التقاط سريع
                    captcha_bytes = captcha_div.screenshot()
                    code = self.solver.solve(captcha_bytes)
                    code = code.replace(" ", "").strip()

                    # قبول الأكواد الطويلة وقت الذروة
                    if len(code) < 4 or len(code) > 8: 
                        refresh_btn = page.locator("input[name*='refreshCaptcha']")
                        if refresh_btn.is_visible():
                            refresh_btn.click()
                            page.wait_for_timeout(1000)
                        else:
                            page.reload()
                        continue
                    
                    logger.info(f"🧩 Decoded: {code}")
                    page.fill("input[name='captchaText']", code)
                    page.keyboard.press("Enter")
                    
                    try: page.wait_for_load_state("domcontentloaded", timeout=4000)
                    except: pass

                    if page.locator("input[name='captchaText']").is_visible():
                        logger.warning("❌ Captcha failed. Retrying...")
                        continue 
                    
                    content = page.content().lower()
                    if "error occurred" in content or "ref-id" in content:
                        return False

                    logger.info("✅ Captcha passed.")
                    return True

            except Exception as e:
                logger.error(f"⚠️ Captcha Error: {e}")
                page.reload()
        
        return False

    def select_visa_category(self, page):
        try:
            select_locator = page.locator("select").first
            if not select_locator.is_visible(): return

            priority_keywords = ["student", "studium", "language", "sprachkurs", "university"]
            options = select_locator.locator("option").all()
            
            for option in options:
                text = option.text_content()
                if text and any(k.lower() in text.lower() for k in priority_keywords):
                    val = option.get_attribute("value")
                    if val:
                        select_locator.select_option(value=val)
                        return
            select_locator.select_option(index=1)
        except: pass

    def fill_booking_form(self, page, context):
        logger.info("📝 Fast-Filling Form...")
        try:
            if not page.locator("input[name='lastname']").is_visible():
                return False

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

            # حلقة الإصرار (نفس المنطق الناجح)
            for attempt in range(10): # زيادة المحاولات للضمان
                logger.info(f"🚀 Submission Attempt {attempt+1}/10...")
                
                if not self.handle_captcha(page, context, location="Form"):
                    if page.locator("input[name='lastname']").is_visible():
                        continue
                    else:
                        return False

                logger.info("🚨 Form Submitted. Verifying...")
                try: page.wait_for_load_state("networkidle", timeout=5000)
                except: pass
                
                content = page.content().lower()
                if "appointment number" in content or "successfully booked" in content:
                    details = "✅ VICTORY! BOOKING CONFIRMED!"
                    logger.info(details)
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    page.screenshot(path=f"success_{ts}.png")
                    send_photo(f"success_{ts}.png", caption=details)
                    return True
                
                if page.locator("input[name='lastname']").is_visible():
                    logger.warning("⚠️ Still on form page (Silent Reject). Retrying...")
                    continue
                
                if "error occurred" in content or "ref-id" in content:
                    logger.error("❌ Booking Failed (Error Page).")
                    return False

            return False

        except Exception as e:
            logger.error(f"❌ Form Error: {e}")
            return False

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--no-first-run", "--disable-extensions"]
            )
            
            context, page = self.create_context(browser)
            logger.info(f"🚀 ROCKET MUSCAT READY. Target: {Config.TARGET_URL}")
            
            # 🛑 الانتظار حتى ساعة الصفر
            self.wait_for_zero_hour()
            
            send_alert("🚀 ZERO HOUR! ATTACK STARTED!")
            
            while True:
                month_urls = self.get_month_urls()
                for url in month_urls:
                    try:
                        date_part = url.split("dateStr=")[1] if "dateStr=" in url else "Unknown"
                        logger.info(f"🔎 Scanning: {date_part}")
                        
                        try: page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        except: continue
                        
                        if not self.handle_captcha(page, context, location="Month"): continue 

                        # التحقق من التقويم
                        if page.locator("#calendarform").is_visible():
                            day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                            
                            if not day_links: continue 

                            logger.info("🔥 DAY FOUND! Attacking...")
                            send_alert(f"🔥 DAY FOUND! {date_part}")
                            
                            # الهجوم على أول يوم (للسرعة)
                            day_links[0].click()
                            
                            if not self.handle_captcha(page, context, location="Day"):
                                page.go_back()
                                page.reload()
                                continue
                            
                            time_link = page.locator("a.arrow[href*='appointment_showForm']").first
                            if time_link.is_visible():
                                logger.info("⏰ TIME FOUND!")
                                time_link.click()
                                
                                if not self.handle_captcha(page, context, location="Pre-Form"):
                                    page.go_back()
                                    continue
                                
                                if self.fill_booking_form(page, context):
                                    logger.info("✅ DONE. Exiting.")
                                    return
                                else:
                                    logger.error("❌ Form submission failed. Retrying slot...")
                                    page.goto(url)
                                    continue
                            else:
                                logger.warning("⚠️ Day open but time slots gone.")
                                break
                        else:
                            # إذا لم يكن تقويم ولا كابتشا، نعيد المحاولة
                            content = page.content()
                            if "captchaText" in content: continue
                            if "Unfortunately" in content: continue
                            page.reload()

                    except Exception as e:
                        logger.error(f"⚠️ Loop Error: {e}")
                        try: context.close()
                        except: pass
                        context, page = self.create_context(browser)
                        time.sleep(2)
                
                # لا نوم في وقت الذروة (الساعة 2)
                now = datetime.datetime.now(self.timezone)
                if now.hour == 2 and now.minute < 30:
                    pass 
                else:
                    logger.info("💤 Cycle done. Sleeping 45s...")
                    time.sleep(45)