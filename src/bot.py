import time
import random
import datetime
import logging
import pytz
import re
from playwright.sync_api import sync_playwright

# محاولة استيراد الملفات المساعدة
try:
    from .config import Config
    from .captcha import CaptchaSolver
    from .notifier import send_alert, send_photo
except ImportError:
    from config import Config
    from captcha import CaptchaSolver
    from notifier import send_alert, send_photo

# إعدادات السجل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("KingSniper_V4")

class KingSniper:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url = Config.TARGET_URL + "&request_locale=en"
        self.tz_yemen = pytz.timezone('Asia/Aden')
        self.user_agents = [
             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
             "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ]
        self.is_dead = False
        self.captcha_retry_count = 0 # عداد لفحص الحلقة المفرغة

    def wait_for_zero_hour(self):
        logger.info("⏳ AMBUSH MODE: Waiting for 01:59:50...")
        while True:
            now = datetime.datetime.now(self.tz_yemen)
            if (now.hour == 1 and now.minute == 59 and now.second >= 50) or (now.hour == 2):
                logger.info("⚔️ ZERO HOUR REACHED! PRECISION ATTACK STARTED!")
                return
            time.sleep(0.1)

    def get_mode(self):
        now = datetime.datetime.now(self.tz_yemen)
        if (now.hour == 1 and now.minute == 59 and now.second >= 50) or (now.hour == 2 and now.minute <= 10):
            return "KILL"
        if now.hour == 1 and now.minute >= 45:
            return "WARMUP"
        return "PATROL"

    # ---------------------------------------------------------
    # بروتوكول إعادة الولادة (عند اكتشاف الحظر)
    # ---------------------------------------------------------
    def rebirth(self, context, browser):
        logger.critical("☣️ BAN DETECTED! INITIATING REBIRTH...")
        try: context.close()
        except: pass
        
        # انتظار عشوائي بسيط لتغيير البصمة
        time.sleep(random.uniform(2, 5))
        
        new_context = browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={"width": 1366 + random.randint(0, 50), "height": 768 + random.randint(0, 50)},
            locale="en-US",
            timezone_id="Asia/Aden",
            ignore_https_errors=True
        )
        
        page = new_context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        
        # حظر الصور للسرعة
        page.route("**/*", lambda route: route.abort() 
                   if route.request.resource_type in ["image", "media", "font", "stylesheet"] 
                   else route.continue_())

        self.is_dead = False
        self.captcha_retry_count = 0
        logger.info("✨ NEW SESSION CREATED.")
        return new_context, page

    # ---------------------------------------------------------
    # أدوات الحقن
    # ---------------------------------------------------------
    def fast_inject(self, page, selector, value):
        if page.locator(selector).count() == 0: return False
        try:
            page.evaluate(f"""
                const el = document.querySelector("{selector}");
                if(el) {{ 
                    el.value = "{value}"; 
                    el.dispatchEvent(new Event('input', {{bubbles:true}}));
                    el.dispatchEvent(new Event('change', {{bubbles:true}})); 
                }}
            """)
            return True
        except: return False

    # ---------------------------------------------------------
    # كشف الحظر الذكي (Smart Ban Detection)
    # ---------------------------------------------------------
    def check_ban_signs(self, page):
        """يفحص علامات الحظر المؤكدة"""
        try:
            # 1. فحص العنوان والمحتوى
            if "403" in page.title() or "Forbidden" in page.content():
                logger.error("💀 BAN SIGN: 403 Forbidden")
                return True
            
            # 2. فحص رسائل الخطأ القاتلة
            content = page.content().lower()
            if "error occurred" in content or "ref-id" in content:
                logger.error("💀 BAN SIGN: Server Error Ref-ID")
                return True

            return False
        except: return False

    # ---------------------------------------------------------
    # معالج الكابتشا الصارم (Strict 6-Digit Logic)
    # ---------------------------------------------------------
    def handle_captcha(self, page, location="General"):
        if self.is_dead: return False
        
        try:
            # هل يوجد كابتشا؟
            if not page.locator("input[name='captchaText']").is_visible():
                self.captcha_retry_count = 0
                return True 

            # فحص الحظر قبل الحل
            if self.check_ban_signs(page):
                self.is_dead = True
                return False

            captcha_div = page.locator("captcha > div").first
            if captcha_div.is_visible():
                # 1. فحص الكابتشا السوداء (الحجم)
                img_bytes = captcha_div.screenshot()
                if len(img_bytes) < 1500:
                    logger.critical("⚫ BAN SIGN: Black/Tiny Captcha Detected.")
                    self.is_dead = True
                    return False

                # 2. الحل
                code = self.solver.solve(img_bytes).replace(" ", "").strip()
                
                # 3. الفلتر الصارم (6 أرقام فقط)
                if len(code) != 6:
                    logger.warning(f"⚠️ Invalid Length ({len(code)}). Refreshing Captcha...")
                    # نضغط زر التحديث بدلاً من تحديث الصفحة كاملة (أسرع وأقل شبهة)
                    refresh_btn = page.locator("input[name*='refreshCaptcha']")
                    if refresh_btn.is_visible():
                        refresh_btn.click()
                        page.wait_for_timeout(1000) # انتظار الصورة الجديدة
                    else:
                        page.reload()
                    return False # نعود للحلقة لنحل الجديدة

                # 4. الحقن والإرسال
                logger.info(f"🧩 Solving: {code} (6-Digits)")
                self.fast_inject(page, "input[name='captchaText']", code)
                page.keyboard.press("Enter")
                
                try: page.wait_for_load_state("domcontentloaded", timeout=4000)
                except: pass

                # 5. التحقق من النتيجة
                if page.locator("input[name='captchaText']").is_visible():
                    # هل فشلنا؟
                    if page.locator(".global-error").is_visible():
                        logger.warning("❌ Wrong Code. Retrying...")
                    else:
                        # لا يوجد خطأ ولكننا في نفس المكان؟ هذا حظر صامت
                        self.captcha_retry_count += 1
                        if self.captcha_retry_count >= 3:
                            logger.error("💀 BAN SIGN: Silent Loop (3x).")
                            self.is_dead = True
                            return False
                    return False
                
                # نجاح
                self.captcha_retry_count = 0
                return True

        except Exception as e:
            logger.error(f"Captcha Error: {e}")
            return False
        return False

    def fill_form(self, page):
        logger.info("⚔️ INJECTING DATA...")
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
            clean_phone = Config.PHONE.replace("+", "00").strip()
            self.fast_inject(page, "input[name*='fields[1]']", clean_phone)

            # اختيار الفئة
            page.evaluate("""
                const s = document.querySelector('select');
                if(s){ 
                    for(let i=0; i<s.options.length; i++){
                        if(s.options[i].text.toLowerCase().includes('student') || 
                           s.options[i].text.toLowerCase().includes('language')) {
                            s.selectedIndex = i; s.dispatchEvent(new Event('change')); return;
                        }
                    }
                    s.selectedIndex=1; s.dispatchEvent(new Event('change')); 
                }
            """)

            # حلقة القتال (10 محاولات)
            for i in range(10):
                if self.is_dead: return False
                
                logger.info(f"🚀 Submit #{i+1}")
                if not self.handle_captcha(page, location="Form"):
                    if self.is_dead: return False
                    if page.locator("input[name='lastname']").is_visible(): continue
                    return False
                
                try: page.wait_for_load_state("networkidle", timeout=3000)
                except: pass
                
                content = page.content().lower()
                if "appointment number" in content:
                    logger.info("👑 KING VICTORY!")
                    send_alert(f"👑 KING VICTORY! {Config.FIRST_NAME}")
                    return True
                
                if self.check_ban_signs(page): 
                    self.is_dead = True
                    return False
                
                if page.locator("input[name='lastname']").is_visible():
                    logger.warning("⚠️ Silent Reject. Fighting back...")
                    continue
                return False
            return False
        except: return False

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, 
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-gpu"]
            )
            context, page = self.rebirth(None, browser)
            logger.info("🛡️ KING SNIPER V4 (Precision) ONLINE.")
            
            while True:
                # 1. التحقق من الموت
                if self.is_dead:
                    context, page = self.rebirth(context, browser)
                    continue

                mode = self.get_mode()
                
                if mode == "WARMUP" and datetime.datetime.now(self.tz_yemen).minute >= 58:
                     self.wait_for_zero_hour()
                     mode = "KILL"

                # ترتيب الأشهر: 3 -> 4 -> 2 -> 5
                priority_offsets = [2, 3, 1, 4]
                today = datetime.datetime.now(self.tz_yemen).date()
                
                for offset in priority_offsets:
                    if self.is_dead: break

                    future_month = (today.month + offset - 1) % 12 + 1
                    future_year = today.year + ((today.month + offset - 1) // 12)
                    date_str = f"15.{future_month:02d}.{future_year}"
                    base = self.base_url.split('&dateStr')[0]
                    url = f"{base}&dateStr={date_str}"

                    try:
                        # في وضع القتل، تحديث الصفحة أسرع
                        if mode == "KILL" and url in page.url:
                            page.reload()
                        else:
                            try: 
                                to = 10000 if mode == "KILL" else 20000
                                page.goto(url, timeout=to, wait_until="domcontentloaded")
                            except: continue

                        if self.check_ban_signs(page):
                            self.is_dead = True
                            break

                        if not self.handle_captcha(page, location="Month"): continue 

                        # التحقق من التقويم
                        if page.locator("#calendarform").is_visible():
                            day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                            if not day_links: continue 
                            
                            logger.info(f"💎 TARGET FOUND!")
                            send_alert("💎 TARGET FOUND!")
                            
                            # Ghost Click
                            href = day_links[0].get_attribute("href")
                            if "http" not in href: href = "https://service2.diplo.de/rktermin/" + href
                            page.goto(href, wait_until="domcontentloaded")
                            
                            if not self.handle_captcha(page, location="Day"): 
                                page.go_back(); continue
                            
                            time_links = page.locator("a.arrow[href*='appointment_showForm']").all()
                            if time_links:
                                logger.info("⏰ SLOTS! Ghost Jumping...")
                                href = time_links[0].get_attribute("href")
                                if "http" not in href: href = "https://service2.diplo.de/rktermin/" + href
                                page.goto(href, wait_until="domcontentloaded")

                                if not self.handle_captcha(page, location="PreForm"):
                                    page.go_back(); continue
                                
                                if self.fill_form(page):
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
                        logger.error(f"Loop Error: {e}")
                        # الأخطاء المتكررة قد تعني حظراً
                        if "Target closed" in str(e): self.is_dead = True
                
                if mode != "KILL":
                    time.sleep(random.uniform(30, 60))

if __name__ == "__main__":
    KingSniper().run()