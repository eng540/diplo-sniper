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

# إعدادات السجل (Logging) - دقة بالمللي ثانية
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("PredatorSniper")

class DiploBot:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url_template = Config.TARGET_URL + "&request_locale=en"
        self.timezone = pytz.timezone("Asia/Aden") 
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ]

    def wait_for_zero_hour(self):
        """
        الكمين: الانتظار الصامت حتى 01:59:50
        """
        logger.info("⏳ AMBUSH MODE: Waiting for 01:59:50...")
        while True:
            now = datetime.datetime.now(self.timezone)
            if (now.hour == 1 and now.minute == 59 and now.second >= 50) or (now.hour == 2):
                logger.info("⚡ ZERO HOUR! LAUNCHING ATTACK! ⚡")
                return 
            time.sleep(0.1)

    def get_month_urls(self):
        # التركيز على الأشهر الساخنة (3 و 4) أولاً
        urls = []
        today = datetime.datetime.now(self.timezone).date()
        base_clean = self.base_url_template.split("&dateStr=")[0]
        
        # ترتيب الأولويات: شهر 3، ثم 4، ثم 2، ثم 5
        priority_offsets = [2, 3, 1, 4] # (0=Current, 1=Next...)
        
        for offset in priority_offsets: 
            future_month = (today.month + offset - 1) % 12 + 1
            future_year = today.year + ((today.month + offset - 1) // 12)
            date_str = f"15.{future_month:02d}.{future_year}"
            full_url = f"{base_clean}&dateStr={date_str}"
            urls.append(full_url)
        return urls

    def fast_inject(self, page, selector, value):
        """حقن JS مباشر (أسرع من الكتابة)"""
        try:
            page.evaluate(f"""
                const el = document.querySelector("{selector}");
                if(el) {{ el.value = "{value}"; el.dispatchEvent(new Event('input')); }}
            """)
        except: pass
            
    def create_context(self, browser):
        context = browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Asia/Aden"
        )
        page = context.new_page()
        
        # 🚫 حظر الصور والخطوط لزيادة السرعة 300%
        page.route("**/*", lambda route: route.abort() 
                   if route.request.resource_type in ["image", "stylesheet", "font", "media"] 
                   else route.continue_())
                   
        page.add_init_script("""Object.defineProperty(navigator, 'webdriver', { get: () => undefined });""")
        context.set_default_timeout(30000)
        return context, page

    def handle_captcha(self, page, location="General"):
        # محاولة واحدة سريعة في وقت الذروة، التكرار يتم في الحلقة الخارجية
        try:
            if not page.locator("input[name='captchaText']").is_visible():
                return True 

            captcha_div = page.locator("captcha > div").first
            if captcha_div.is_visible():
                # التقاط الصورة (حتى مع الحظر، هذا العنصر Base64)
                captcha_bytes = captcha_div.screenshot()
                code = self.solver.solve(captcha_bytes)
                code = code.replace(" ", "").strip()

                # قبول الأكواد الطويلة وقت الذروة
                if len(code) > 3:
                    self.fast_inject(page, "input[name='captchaText']", code)
                    page.keyboard.press("Enter")
                    
                    # انتظار ذكي
                    try: page.wait_for_load_state("domcontentloaded", timeout=3000)
                    except: pass

                    if page.locator("input[name='captchaText']").is_visible():
                        return False # فشل، نعيد المحاولة من الخارج أسرع
                    
                    if "error occurred" in page.content().lower():
                        return False

                    return True
        except: pass
        return False

    def select_visa_category(self, page):
        try:
            # اختيار الفئة عبر الحقن المباشر (أسرع)
            page.evaluate("""
                const select = document.querySelector('select');
                if (select) {
                    // البحث عن خيار يحتوي على student أو language
                    for (let i = 0; i < select.options.length; i++) {
                        if (select.options[i].text.toLowerCase().includes('student') || 
                            select.options[i].text.toLowerCase().includes('language') ||
                            select.options[i].text.toLowerCase().includes('studium')) {
                            select.selectedIndex = i;
                            select.dispatchEvent(new Event('change'));
                            return;
                        }
                    }
                    select.selectedIndex = 1; // الافتراضي
                    select.dispatchEvent(new Event('change'));
                }
            """)
        except: pass

    def fill_booking_form(self, page):
        logger.info("📝 Injecting Data...")
        try:
            if not page.locator("input[name='lastname']").is_visible(): return False

            # الحقن المباشر
            self.fast_inject(page, "input[name='lastname']", Config.LAST_NAME)
            self.fast_inject(page, "input[name='firstname']", Config.FIRST_NAME)
            self.fast_inject(page, "input[name='email']", Config.EMAIL)
            
            if page.locator("input[name='emailrepeat']").count() > 0:
                self.fast_inject(page, "input[name='emailrepeat']", Config.EMAIL)
            else:
                self.fast_inject(page, "input[name='emailRepeat']", Config.EMAIL)

            self.fast_inject(page, "input[name*='fields[0]']", Config.PASSPORT)
            clean_phone = Config.PHONE.replace("+", "00").strip()
            self.fast_inject(page, "input[name*='fields[1]']", clean_phone)

            self.select_visa_category(page)

            # حلقة القتال (5 محاولات)
            for i in range(5):
                logger.info(f"🚀 Submit #{i+1}")
                if not self.handle_captcha(page, location="Form"):
                    if page.locator("input[name='lastname']").is_visible(): continue
                    return False

                try: page.wait_for_load_state("networkidle", timeout=3000)
                except: pass
                
                content = page.content().lower()
                if "appointment number" in content:
                    logger.info("✅ VICTORY!")
                    send_alert(f"✅ VICTORY! {Config.FIRST_NAME}")
                    # نلتقط صورة للذكرى (نعيد تفعيل الصور لحظياً لو أمكن، لكن هنا نكتفي بالنص للسرعة)
                    return True
                
                if page.locator("input[name='lastname']").is_visible():
                    logger.warning("⚠️ Silent Reject. Retrying...")
                    continue
                
                return False 

            return False
        except: return False

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--no-first-run"]
            )
            context, page = self.create_context(browser)
            
            logger.info("🛡️ PREDATOR READY. Waiting for 01:59:50...")
            
            # الدخول المسبق لشهر 3 (مارس) للتجهيز
            try:
                target_urls = self.get_month_urls()
                page.goto(target_urls[0], timeout=30000) # شهر مارس
                if page.locator("input[name='captchaText']").is_visible():
                    self.handle_captcha(page, location="WarmUp")
            except: pass

            # 🛑 انتظار ساعة الصفر
            self.wait_for_zero_hour()
            
            send_alert("🚀 ATTACK STARTED!")
            
            while True:
                month_urls = self.get_month_urls()
                for url in month_urls:
                    try:
                        # إذا كنا في نفس الصفحة، تحديث فقط
                        if url in page.url:
                            page.reload()
                        else:
                            try: page.goto(url, wait_until="domcontentloaded", timeout=10000)
                            except: continue
                        
                        if not self.handle_captcha(page, location="Month"): continue 

                        if page.locator("#calendarform").is_visible():
                            day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                            
                            if not day_links: continue 
                            
                            logger.info(f"🔥 FOUND {len(day_links)} DAYS!")
                            
                            # ⚡ الهجوم على أول يوم فوراً (بدون عشوائية)
                            day_links[0].click()
                            
                            if not self.handle_captcha(page, location="Day"): 
                                page.go_back()
                                continue
                            
                            time_links = page.locator("a.arrow[href*='appointment_showForm']").all()
                            if time_links:
                                logger.info(f"⏰ SLOTS! Taking FIRST one...")
                                # ⚡ الهجوم على أول وقت فوراً
                                time_links[0].click()
                                
                                if not self.handle_captcha(page, location="PreForm"):
                                    page.go_back()
                                    continue
                                
                                if self.fill_booking_form(page):
                                    return 
                                else:
                                    page.goto(url) 
                                    continue
                        else:
                            content = page.content()
                            if "captchaText" in content: continue
                            if "Unfortunately" in content: continue
                            page.reload()

                    except Exception as e:
                        try: context.close()
                        except: pass
                        context, page = self.create_context(browser)
                
                # لا نوم في وقت الذروة
                # time.sleep(0.1)