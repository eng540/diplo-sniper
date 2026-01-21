import time
import random
import datetime
import logging
import pytz
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("SentinelBot")

class SentinelBot:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url = Config.TARGET_URL + "&request_locale=en"
        self.tz_yemen = pytz.timezone('Asia/Aden')
        self.consecutive_errors = 0
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ]

    def get_dynamic_delay(self):
        """
        العقل المدبر: يحدد سرعة البوت حسب الوقت لتجنب الحظر
        """
        now = datetime.datetime.now(self.tz_yemen)
        
        # 1. وقت الذروة (01:55 - 02:10) -> سرعة قصوى
        if (now.hour == 1 and now.minute >= 55) or (now.hour == 2 and now.minute <= 10):
            return 0.1  # Sniper Mode
            
        # 2. أوقات الدوام الرسمي (08:00 - 15:00) -> فحص متوسط
        if 8 <= now.hour <= 15:
            return random.uniform(15, 45)  # Human Patrol
            
        # 3. وقت الموت (باقي اليوم) -> فحص بطيء جداً للحفاظ على الجلسة فقط
        return random.uniform(120, 300)  # Hibernate Mode (2-5 minutes)

    def create_context(self, p):
        browser = p.chromium.launch(
            headless=True, # اجعله False إذا كنت تريد المراقبة
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Asia/Aden"
        )
        page = context.new_page()
        # حظر الصور لتخفيف الحمل على الشبكة وتقليل البصمة
        page.route("**/*", lambda route: route.abort() 
                   if route.request.resource_type in ["image", "media", "font"] 
                   else route.continue_())
        return browser, context, page

    def fast_inject(self, page, selector, value):
        try:
            page.evaluate(f"""
                const el = document.querySelector("{selector}");
                if(el) {{ el.value = "{value}"; el.dispatchEvent(new Event('input')); }}
            """)
        except: pass

    def handle_captcha(self, page):
        try:
            if not page.locator("input[name='captchaText']").is_visible():
                return True

            captcha_div = page.locator("captcha > div").first
            if captcha_div.is_visible():
                # انتظار عشوائي بسيط لمحاكاة البشر في الأوقات العادية
                if self.get_dynamic_delay() > 1:
                    time.sleep(random.uniform(0.5, 1.5))
                
                png = captcha_div.screenshot()
                code = self.solver.solve(png).replace(" ", "").strip()
                
                if len(code) > 3:
                    self.fast_inject(page, "input[name='captchaText']", code)
                    page.keyboard.press("Enter")
                    try: page.wait_for_load_state("domcontentloaded", timeout=5000)
                    except: pass
                    
                    # التحقق من النجاح
                    if not page.locator("input[name='captchaText']").is_visible():
                        return True
        except: pass
        return False

    def check_for_block(self, page):
        """
        التحقق مما إذا تم حظرنا (403/429/Error)
        """
        try:
            content = page.content().lower()
            if "403 forbidden" in content or "access denied" in content or "ip blocked" in content:
                logger.critical("⛔ IP BLOCKED! Entering Cool-down mode for 10 minutes...")
                return True
            if "error occurred" in content:
                # خطأ عادي، نزيد العداد
                self.consecutive_errors += 1
                return False
        except: pass
        
        self.consecutive_errors = 0
        return False

    def run(self):
        with sync_playwright() as p:
            browser, context, page = self.create_context(p)
            logger.info("🛡️ SENTINEL BOT STARTED (24/7 Mode)")
            
            while True:
                try:
                    # 1. حساب وقت الانتظار
                    delay = self.get_dynamic_delay()
                    
                    # إذا كان هناك أخطاء متتالية، نزيد وقت الانتظار إجبارياً
                    if self.consecutive_errors > 3:
                        logger.warning("⚠️ High error rate. Backing off for 2 minutes.")
                        time.sleep(120)
                        self.consecutive_errors = 0
                        # إعادة تشغيل المتصفح لتنظيف الجلسة السيئة
                        context.close()
                        browser.close()
                        browser, context, page = self.create_context(p)
                        continue

                    if delay > 10:
                        logger.info(f"💤 Sleeping {int(delay)}s (Low Activity)...")
                        time.sleep(delay)
                    
                    # 2. الحصول على الروابط (نركز على شهرين فقط لتخفيف الضغط)
                    today = datetime.date.today()
                    # مسح شهرين فقط هو الأكثر أماناً للعمل 24 ساعة
                    for i in range(2): 
                        target_month = today + datetime.timedelta(days=30*i)
                        date_str = target_month.strftime("15.%m.%Y")
                        base = self.base_url.split("&dateStr=")[0]
                        url = f"{base}&dateStr={date_str}"
                        
                        try:
                            page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        except: 
                            self.consecutive_errors += 1
                            continue

                        # فحص الحظر
                        if self.check_for_block(page):
                            time.sleep(600) # نوم 10 دقائق
                            break

                        # كابتشا
                        if not self.handle_captcha(page): continue

                        # التحقق من وجود مواعيد
                        if "appointment_showDay" in page.content():
                            logger.info("🔥 SLOTS DETECTED! SWITCHING TO ATTACK MODE!")
                            send_alert("🔥 SLOTS FOUND! WAKE UP!")
                            
                            # هنا نتحول لوضع الهجوم المباشر
                            day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                            if day_links:
                                day_links[0].click()
                                self.handle_captcha(page)
                                
                                # محاولة الحجز... (نفس منطق البوتات السابقة)
                                time_links = page.locator("a.arrow[href*='appointment_showForm']").all()
                                if time_links:
                                    time_links[0].click()
                                    self.handle_captcha(page)
                                    # ... (استدعاء دالة التعبئة Fill Form)
                                    # إذا نجح الحجز، نخرج
                                    return 

                        else:
                            logger.info(f"Scanning {date_str}: No slots.")

                except Exception as e:
                    logger.error(f"Error: {e}")
                    self.consecutive_errors += 1
                    time.sleep(10)

if __name__ == "__main__":
    bot = SentinelBot()
    bot.run()