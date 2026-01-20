import time
import random
import datetime
import os
import traceback
import re
import logging
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

# إعدادات السجل - التركيز على السرعة
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MuscatSniper")

class DiploBot:
    def __init__(self):
        self.solver = CaptchaSolver()
        # التأكد من اللغة الإنجليزية لضمان قراءة الرسائل بشكل صحيح
        self.base_url_template = Config.TARGET_URL + "&request_locale=en"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]

    def get_month_urls(self):
        urls = []
        today = datetime.date.today()
        # تنظيف الرابط الأساسي
        base_clean = self.base_url_template.split("&dateStr=")[0] if "&dateStr=" in self.base_url_template else self.base_url_template
        
        # مسح 6 أشهر للأمام (لتغطية المواعيد الملغاة والجديدة)
        for i in range(6): 
            future_month = (today.month + i - 1) % 12 + 1
            future_year = today.year + ((today.month + i - 1) // 12)
            date_str = f"15.{future_month:02d}.{future_year}"
            full_url = f"{base_clean}&dateStr={date_str}"
            urls.append(full_url)
        return urls

    def type_fast(self, page, selector, text):
        """حقن البيانات بسرعة البرق"""
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
            timezone_id="Asia/Muscat" # توقيت مسقط لضبط المتصفح
        )
        page = context.new_page()
        page.add_init_script("""Object.defineProperty(navigator, 'webdriver', { get: () => undefined });""")
        context.set_default_timeout(40000)
        return context, page

    def handle_captcha(self, page, context, location="General"):
        for attempt in range(5):
            try:
                if not page.locator("input[name='captchaText']").is_visible():
                    return True 

                logger.info(f"⚡ [Captcha-{location}] Attempt {attempt+1}...")
                captcha_div = page.locator("captcha > div").first
                
                if captcha_div.is_visible():
                    page.wait_for_timeout(500) 
                    captcha_bytes = captcha_div.screenshot()
                    code = self.solver.solve(captcha_bytes)
                    code = code.replace(" ", "").strip()

                    # قبول الكابتشا الطويلة لأن الموقع يصعبها وقت الذروة
                    if len(code) < 4 or len(code) > 8: 
                        logger.warning(f"⚠️ Bad length ({len(code)}). Refreshing...")
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
                        # إذا بقينا في نفس الصفحة، يعني الكود خطأ
                        logger.warning("⚠️ Captcha rejected or loop. Retrying...")
                        continue 
                    
                    content = page.content().lower()
                    if "error occurred" in content or "ref-id" in content:
                        logger.error("❌ Critical Error Page.")
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

            priority_keywords = ["student", "studium", "language", "sprachkurs", "master", "bachelor", "university"]
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

            # الحقن المباشر للبيانات
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

            # حلقة القتال (5 جولات)
            for attempt in range(5):
                logger.info(f"🚀 Submission Attempt {attempt+1}/5...")
                
                if not self.handle_captcha(page, context, location="Form"):
                    if page.locator("input[name='lastname']").is_visible():
                        continue
                    return False

                logger.info("🚨 Form Submitted. Checking result...")
                try: page.wait_for_load_state("networkidle", timeout=5000)
                except: pass
                
                content = page.content()
                
                if "appointment number" in content.lower() or "successfully booked" in content.lower():
                    details = "✅ MUSCAT VICTORY! BOOKING CONFIRMED!\n"
                    match_num = re.search(r"Appointment number is\s+(\d+)", content, re.IGNORECASE)
                    if match_num: details += f"🆔 App Num: {match_num.group(1)}\n"
                    match_date = re.search(r"(\d{2}\.\d{2}\.\d{4})", content)
                    if match_date: details += f"📅 Date: {match_date.group(1)}\n"
                    details += f"👤 Name: {Config.FIRST_NAME} {Config.LAST_NAME}"
                    
                    logger.info(details)
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    page.screenshot(path=f"VICTORY_{ts}.png")
                    send_photo(f"VICTORY_{ts}.png", caption=details)
                    return True
                
                if page.locator("input[name='lastname']").is_visible():
                    logger.warning("⚠️ Silent Reject (Form still visible). Retrying...")
                    continue

                if "error occurred" in content.lower() or "ref-id" in content.lower():
                    logger.error("❌ Booking Failed (Server Error).")
                    return False

            return False

        except Exception as e:
            logger.error(f"❌ Form Logic Error: {e}")
            return False

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled", 
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage", 
                    "--disable-gpu", 
                    "--no-first-run", 
                    "--disable-extensions",
                    "--disable-web-security"
                ]
            )
            
            context, page = self.create_context(browser)
            logger.info(f"🚀 MUSCAT SNIPER ENGAGED. Target: {Config.TARGET_URL}")
            send_alert("🚀 MUSCAT SNIPER V24 (Randomized) Started...")
            
            while True:
                month_urls = self.get_month_urls()
                for url in month_urls:
                    try:
                        date_part = url.split("dateStr=")[1] if "dateStr=" in url else "Unknown"
                        logger.info(f"🔎 Scanning: {date_part}")
                        
                        try: page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        except: continue
                        
                        if not self.handle_captcha(page, context, location="Month"): 
                            continue 

                        content = page.content()
                        
                        # التحقق الآمن: هل الصفحة فارغة فعلاً؟
                        if "Unfortunately, there are no appointments" in content or "keine Termine" in content:
                            # نعم، الموقع يقول صراحة لا توجد مواعيد
                            continue
                        
                        # إذا لم نجد رسالة الرفض، نبحث عن الروابط
                        day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                        
                        if not day_links:
                            # حالة غريبة: لا رسالة رفض ولا روابط أيام
                            # قد يكون خطأ تحميل أو تغيير في الموقع
                            # الإجراء: إعادة تحميل الصفحة للتأكد (Double Check)
                            logger.warning("⚠️ Ambiguous State (No slots & No error). Double checking...")
                            page.reload()
                            # إذا تكرر الأمر، سينتقل في الدورة القادمة
                            continue 

                        # 🔥 استراتيجية العشوائية (Randomization) لتفادي الزحام
                        logger.info(f"🔥 {len(day_links)} DAYS FOUND! Selecting RANDOM target...")
                        send_alert(f"🔥 DAY FOUND! {date_part} - Attacking Random...")
                        
                        # اختيار يوم عشوائي
                        target_day = random.choice(day_links)
                        target_day.click()
                        
                        if not self.handle_captcha(page, context, location="Day"):
                            page.go_back()
                            continue
                        
                        # البحث عن الأوقات واختيار عشوائي أيضاً
                        time_links = page.locator("a.arrow[href*='appointment_showForm']").all()
                        if time_links:
                            logger.info(f"⏰ {len(time_links)} SLOTS FOUND! Clicking Random...")
                            
                            target_time = random.choice(time_links)
                            target_time.click()
                            
                            if not self.handle_captcha(page, context, location="Pre-Form"):
                                page.go_back()
                                continue
                            
                            if self.fill_booking_form(page, context):
                                logger.info("✅ MISSION COMPLETE. Exiting.")
                                return 
                            else:
                                logger.error("❌ Booking failed. Restarting scan...")
                                page.goto(url)
                                continue
                        else:
                            logger.warning("⚠️ Day open but slots taken.")
                            
                    except Exception as e:
                        logger.error(f"⚠️ Loop Error: {e}")
                        try: context.close()
                        except: pass
                        context, page = self.create_context(browser)
                        time.sleep(2)
                
                # تقليل وقت الانتظار لزيادة فرص القنص
                logger.info("💤 Cycle done. Sleeping 30s...")
                time.sleep(30)