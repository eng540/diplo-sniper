import time
import random
import datetime
import os
import logging
import pytz # مكتبة التوقيت ضرورية
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MuscatFalcon")

class DiploBot:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url_template = Config.TARGET_URL + "&request_locale=en"
        # توقيت اليمن/مسقط (نفس المنطقة الزمنية GMT+3)
        self.timezone = pytz.timezone("Asia/Aden") 
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]

    def is_golden_hour(self):
        """
        هل نحن في وقت الذروة (الساعة 2 صباحاً)؟
        """
        now = datetime.datetime.now(self.timezone)
        # الفترة الذهبية: من 1:55 صباحاً إلى 2:10 صباحاً
        if (now.hour == 1 and now.minute >= 55) or (now.hour == 2 and now.minute <= 10):
            return True
        return False

    def get_month_urls(self):
        urls = []
        today = datetime.datetime.now(self.timezone).date()
        base_clean = self.base_url_template.split("&dateStr=")[0] if "&dateStr=" in self.base_url_template else self.base_url_template
        
        # في مسقط، التركيز عادة على الأشهر القريبة للإلغاءات والبعيدة للطرح الجديد
        # سنمسح 5 أشهر
        for i in range(5): 
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
        context.set_default_timeout(30000) # مهلة سريعة
        return context, page

    def handle_captcha(self, page, location="General"):
        for attempt in range(5): # 5 محاولات
            try:
                if not page.locator("input[name='captchaText']").is_visible():
                    return True 

                # في وقت الذروة، لا نضيع وقتاً في السجلات
                if not self.is_golden_hour():
                    logger.info(f"⚡ [Captcha-{location}] Attempt {attempt+1}...")
                
                captcha_div = page.locator("captcha > div").first
                
                if captcha_div.is_visible():
                    page.wait_for_timeout(300) # انتظار خاطف
                    captcha_bytes = captcha_div.screenshot()
                    code = self.solver.solve(captcha_bytes)
                    code = code.replace(" ", "").strip()

                    # المنطق العقابي: نقبل أي كود بين 4 و 8 أرقام
                    if len(code) < 4 or len(code) > 8: 
                        refresh_btn = page.locator("input[name*='refreshCaptcha']")
                        if refresh_btn.is_visible():
                            refresh_btn.click()
                            page.wait_for_timeout(800)
                        else:
                            page.reload()
                        continue
                    
                    page.fill("input[name='captchaText']", code)
                    page.keyboard.press("Enter")
                    
                    try: page.wait_for_load_state("domcontentloaded", timeout=3000)
                    except: pass

                    # هل ما زلنا في الكابتشا؟
                    if page.locator("input[name='captchaText']").is_visible():
                        continue 
                    
                    # هل ظهر خطأ Ref-ID؟
                    content = page.content()
                    if "error occurred" in content.lower() or "ref-id" in content.lower():
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

            # الحقن السريع
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

            # حلقة القتال (5 محاولات)
            for _ in range(5):
                if not self.handle_captcha(page, location="Form"):
                    if page.locator("input[name='lastname']").is_visible(): continue
                    return False

                # انتظار ذكي للنتيجة
                try: page.wait_for_load_state("networkidle", timeout=4000)
                except: pass
                
                content = page.content().lower()
                if "appointment number" in content or "successfully booked" in content:
                    details = f"✅ VICTORY! {Config.FIRST_NAME} {Config.LAST_NAME}"
                    logger.info(details)
                    # إرسال الصورة فقط عند النصر
                    ts = datetime.datetime.now().strftime("%H%M%S")
                    page.screenshot(path=f"WIN_{ts}.png")
                    send_photo(f"WIN_{ts}.png", caption=details)
                    return True
                
                if page.locator("input[name='lastname']").is_visible():
                    logger.warning("⚠️ Silent Reject. Retrying...")
                    continue
                
                return False # خطأ آخر

            return False
        except: return False

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--no-first-run"]
            )
            context, page = self.create_context(browser)
            logger.info(f"🚀 FALCON ACTIVE. Target: {Config.TARGET_URL}")
            send_alert("🚀 FALCON V25 (Time-Aware) Started...")
            
            while True:
                # التحقق من الوضع القتالي
                golden_mode = self.is_golden_hour()
                if golden_mode:
                    logger.info("🔥 GOLDEN HOUR! NO SLEEP MODE ACTIVATED! 🔥")
                
                month_urls = self.get_month_urls()
                for url in month_urls:
                    try:
                        # في الوضع الذهبي، لا نضيع وقتاً في طباعة الروابط
                        if not golden_mode:
                            date_part = url.split("dateStr=")[1] if "dateStr=" in url else "Unknown"
                            logger.info(f"🔎 Scanning: {date_part}")
                        
                        try: page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        except: continue
                        
                        if not self.handle_captcha(page, location="Month"): continue 

                        # --- منطق الكلب البوليسي (Fact-Based Logic) ---
                        # 1. هل نحن في صفحة التقويم فعلاً؟
                        if page.locator("#calendarform").is_visible():
                            # نعم، الصفحة تحملت. الآن نبحث عن المواعيد.
                            day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                            
                            if not day_links:
                                # التقويم موجود، لكن لا توجد أسهم أيام.
                                # الحقيقة: الشهر فارغ 100%.
                                # الإجراء: انتقل فوراً للشهر التالي.
                                continue 
                            
                            # وجدنا أياماً!
                            logger.info(f"🔥 {len(day_links)} DAYS FOUND!")
                            send_alert("🔥 DAY FOUND! Attacking...")
                            
                            # العشوائية لتجنب التصادم
                            random.choice(day_links).click()
                            
                            if not self.handle_captcha(page, location="Day"):
                                page.go_back()
                                continue
                            
                            time_links = page.locator("a.arrow[href*='appointment_showForm']").all()
                            if time_links:
                                logger.info(f"⏰ {len(time_links)} SLOTS! Attacking...")
                                random.choice(time_links).click()
                                
                                if not self.handle_captcha(page, location="PreForm"):
                                    page.go_back()
                                    continue
                                
                                if self.fill_booking_form(page, context):
                                    return # النصر
                                else:
                                    page.goto(url) # فشل الحجز، نعود لنفس الشهر
                                    continue
                        
                        else:
                            # لا يوجد calendarform. هل هي صفحة خطأ؟ أم كابتشا معلقة؟
                            content = page.content()
                            if "captchaText" in content:
                                # ما زلنا في الكابتشا، نعيد المحاولة
                                continue
                            if "Unfortunately" in content:
                                continue
                            
                            # حالة غير معروفة، نعيد التحميل للأمان
                            page.reload()

                    except Exception as e:
                        # في وقت الذروة، لا تطبع الأخطاء لتوفير الوقت
                        if not golden_mode: logger.error(f"Err: {e}")
                        try: context.close()
                        except: pass
                        context, page = self.create_context(browser)
                
                # إدارة النوم بناءً على التوقيت
                if self.is_golden_hour():
                    # لا نوم في وقت المعركة!
                    pass 
                else:
                    # نوم الحراسة العادية
                    logger.info("💤 Patrol sleep (30s)...")
                    time.sleep(30)