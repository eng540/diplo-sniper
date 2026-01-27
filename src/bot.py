import time
import random
import datetime
import logging
import pytz
import sys
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

# ---------------------------------------------------------
# إعدادات السجل الاحترافية
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("KingSniper")

class KingSniper:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url = Config.TARGET_URL + "&request_locale=en"
        self.tz_yemen = pytz.timezone('Asia/Aden')
        
        # قائمة هويات مزيفة (User-Agents) للتنكر
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ]
        
        # حالة النظام
        self.is_banned = False

    # ---------------------------------------------------------
    # 1. العقل المدبر: استراتيجية الوقت (The Brain)
    # ---------------------------------------------------------
    def get_mode(self):
        """
        تحديد وضع التشغيل بناءً على توقيت صنعاء
        """
        now = datetime.datetime.now(self.tz_yemen)
        
        # الساعة الذهبية (01:58 ص - 02:05 ص) -> وضع الوحش
        if (now.hour == 1 and now.minute >= 58) or (now.hour == 2 and now.minute <= 5):
            return "BEAST"
            
        # وقت التحمية (01:45 ص - 01:58 ص) -> وضع الاستعداد
        if now.hour == 1 and now.minute >= 45:
            return "WARMUP"
            
        # باقي اليوم -> وضع السبات/الحراسة
        return "PATROL"

    # ---------------------------------------------------------
    # 2. أدوات الجراحة: الحقن المباشر (Injection Tools)
    # ---------------------------------------------------------
    def fast_inject(self, page, selector, value):
        try:
            page.evaluate(f"""
                const el = document.querySelector("{selector}");
                if(el) {{ 
                    el.value = "{value}"; 
                    el.dispatchEvent(new Event('input', {{ bubbles: true }})); 
                    el.dispatchEvent(new Event('change', {{ bubbles: true }})); 
                }}
            """)
        except: pass

    # ---------------------------------------------------------
    # 3. بروتوكول إعادة الولادة (Rebirth Protocol)
    # ---------------------------------------------------------
    def rebirth(self, context, browser):
        """
        يتم استدعاؤها عند اكتشاف الحظر 4333
        """
        logger.critical("☣️ 4333 DETECTED! INITIATING REBIRTH PROTOCOL...")
        send_alert("⚠️ 4333 Detected! Switching Identity...")
        
        try: context.close()
        except: pass
        
        # انتظار إجباري لتهدئة السيرفر
        time.sleep(random.uniform(10, 20))
        
        # إنشاء هوية جديدة
        new_context = browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={"width": 1366 + random.randint(0, 50), "height": 768 + random.randint(0, 50)},
            locale="en-US",
            timezone_id="Asia/Aden",
            # proxy={"server": "http://..."} # <--- هنا تضع البروكسي إذا توفر
        )
        
        new_page = new_context.new_page()
        new_page.add_init_script("""Object.defineProperty(navigator, 'webdriver', { get: () => undefined });""")
        
        logger.info("✨ REBIRTH SUCCESSFUL. New Identity Created.")
        return new_context, new_page

    # ---------------------------------------------------------
    # 4. معالج الكابتشا (The Key)
    # ---------------------------------------------------------
    def solve_captcha(self, page, mode):
        if not page.locator("input[name='captchaText']").is_visible():
            return True

        # في وضع الوحش، لا ننتظر. في وضع الحراسة، نتصرف كبشر
        if mode == "PATROL":
            time.sleep(random.uniform(1, 2))

        try:
            captcha_div = page.locator("captcha > div").first
            if captcha_div.is_visible():
                png = captcha_div.screenshot()
                code = self.solver.solve(png).replace(" ", "").strip()
                
                if len(code) > 3:
                    self.fast_inject(page, "input[name='captchaText']", code)
                    page.keyboard.press("Enter")
                    
                    # انتظار ذكي للنتيجة
                    try: page.wait_for_load_state("domcontentloaded", timeout=4000)
                    except: pass
                    
                    # التحقق من الحظر بعد الكابتشا
                    content = page.content().lower()
                    if "forbidden" in content or "access denied" in content:
                        self.is_banned = True
                        return False
                        
                    return not page.locator("input[name='captchaText']").is_visible()
        except: pass
        return False

    # ---------------------------------------------------------
    # 5. المحرك الرئيسي (The Engine)
    # ---------------------------------------------------------
    def run(self):
        with sync_playwright() as p:
            # تشغيل المتصفح (Headless=True للسرعة، False للتصحيح)
            browser = p.chromium.launch(
                headless=True, 
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            
            # الولادة الأولى
            context, page = self.rebirth(None, browser) # نستخدم دالة إعادة الولادة للإنشاء الأولي
            
            logger.info("👑 KING SNIPER ONLINE. 24/7 Watch Started.")
            send_alert("👑 King Sniper Started.")

            while True:
                try:
                    # 1. فحص الحالة وتحديد السرعة
                    if self.is_banned:
                        context, page = self.rebirth(context, browser)
                        self.is_banned = False
                        continue

                    mode = self.get_mode()
                    
                    # 2. إدارة الموارد حسب الوضع
                    if mode == "BEAST":
                        # حظر الصور للسرعة القصوى
                        page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())
                        sleep_time = 0.1
                    elif mode == "WARMUP":
                        # السماح بالصور لتبدو الجلسة طبيعية قبل الهجوم
                        page.unroute("**/*")
                        sleep_time = 5
                    else: # PATROL
                        page.unroute("**/*")
                        sleep_time = random.uniform(180, 300) # نوم 3-5 دقائق

                    # 3. النوم الذكي
                    if mode != "BEAST":
                        logger.info(f"🛡️ Mode: {mode}. Sleeping {int(sleep_time)}s...")
                        time.sleep(sleep_time)
                    
                    # 4. مسح الروابط
                    # في وضع الوحش والتحمية: نفحص الشهرين القادمين فقط
                    # في وضع الحراسة: نفحص 4 أشهر لنبدو طبيعيين
                    months_count = 2 if mode in ["BEAST", "WARMUP"] else 4
                    
                    today = datetime.date.today()
                    
                    for i in range(months_count):
                        # حساب التاريخ
                        target_date = today + datetime.timedelta(days=30*i)
                        date_str = target_date.strftime("15.%m.%Y")
                        base = self.base_url.split("&dateStr=")[0]
                        url = f"{base}&dateStr={date_str}"
                        
                        try:
                            # Timeout قصير جداً في وضع الوحش
                            to = 5000 if mode == "BEAST" else 30000
                            page.goto(url, timeout=to, wait_until="domcontentloaded")
                        except: continue

                        # فحص الحظر الفوري
                        if "403" in page.title() or "Forbidden" in page.content():
                            self.is_banned = True
                            break

                        # حل الكابتشا
                        if not self.solve_captcha(page, mode):
                            if self.is_banned: break # خروج فوري لإعادة الولادة
                            continue

                        # التحقق من المواعيد
                        if "appointment_showDay" in page.content():
                            logger.info("🔥 SLOTS FOUND! ENGAGING...")
                            
                            # استراتيجية النقر
                            days = page.locator("a.arrow[href*='appointment_showDay']").all()
                            if days:
                                # في وضع الوحش: الأول فوراً. في الحراسة: عشوائي (بشري)
                                target = days[0] if mode == "BEAST" else random.choice(days)
                                target.click()
                                
                                self.solve_captcha(page, mode)
                                
                                times = page.locator("a.arrow[href*='appointment_showForm']").all()
                                if times:
                                    times[0].click() # الوقت دائماً الأول (الأفضل)
                                    
                                    # تعبئة الفورم
                                    logger.info("📝 Filling Form...")
                                    self.fast_inject(page, "input[name='lastname']", Config.LAST_NAME)
                                    self.fast_inject(page, "input[name='firstname']", Config.FIRST_NAME)
                                    self.fast_inject(page, "input[name='email']", Config.EMAIL)
                                    # ... (باقي الحقول كما في النسخ السابقة) ...
                                    
                                    # حل كابتشا النهاية
                                    if self.solve_captcha(page, mode):
                                        # التحقق النهائي
                                        if "appointment number" in page.content().lower():
                                            logger.info("🏆 KING VICTORY!")
                                            send_photo(page.screenshot(), "✅ KING SNIPER VICTORY!")
                                            return # إنهاء البرنامج، المهمة أنجزت
                                        
                        else:
                            if mode == "BEAST": logger.info(f"⚡ Scan {date_str}: Empty.")
                            else: logger.info(f"Scan {date_str}: Empty.")

                except Exception as e:
                    logger.error(f"⚠️ Error: {e}")
                    # أي خطأ غير متوقع قد يعني مشكلة في الاتصال أو حظر
                    # نزيد عداد الأخطاء، وإذا تكرر نقوم بإعادة الولادة (يمكن إضافة منطق هنا)
                    time.sleep(5)

if __name__ == "__main__":
    bot = KingSniper()
    bot.run()