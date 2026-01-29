import time
import random
import datetime
import logging
import pytz
import re
from playwright.sync_api import sync_playwright

# استيراد الوحدات (معدل ليتوافق مع بيئتك)
try:
    from .config import Config
    from .captcha import CaptchaSolver
    from .notifier import send_alert, send_photo
except ImportError:
    # Fallback for direct execution
    from config import Config
    from captcha import CaptchaSolver
    from notifier import send_alert, send_photo

# ---------------------------------------------------------
# 1. Logging Setup
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("KingSniper_Hybrid")

class KingSniper:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url = Config.TARGET_URL + "&request_locale=en"
        self.tz_yemen = pytz.timezone('Asia/Aden')
        self.user_agents = [
             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
             "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ]
        self.poisoned_session = False

    # ---------------------------------------------------------
    # 2. Time Warfare (Zero Hour)
    # ---------------------------------------------------------
    def wait_for_zero_hour(self):
        logger.info("⏳ AMBUSH MODE: Waiting for 01:59:50...")
        while True:
            now = datetime.datetime.now(self.tz_yemen)
            if (now.hour == 1 and now.minute == 59 and now.second >= 50) or (now.hour == 2):
                logger.info("⚔️ ZERO HOUR REACHED! LAUNCHING ATTACK!")
                return
            time.sleep(0.1)

    def get_mode(self):
        now = datetime.datetime.now(self.tz_yemen)
        if (now.hour == 1 and now.minute == 59 and now.second >= 50) or (now.hour == 2 and now.minute <= 10):
            return "BEAST"
        if now.hour == 1 and now.minute >= 45:
            return "WARMUP"
        return "PATROL"

    # ---------------------------------------------------------
    # 3. Infrastructure (Rebirth)
    # ---------------------------------------------------------
    def rebirth(self, context, browser):
        logger.warning("☣️ REBIRTH PROTOCOL ACTIVATED.")
        try: context.close()
        except: pass
        
        mode = self.get_mode()
        sleep_time = 0.1 if mode == "BEAST" else random.uniform(3, 5)
        time.sleep(sleep_time)
        
        new_context = browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Asia/Aden",
            ignore_https_errors=True
        )
        
        page = new_context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        
        # حظر الصور لتسريع الاتصال
        page.route("**/*", lambda route: route.abort() 
                   if route.request.resource_type in ["image", "media", "font", "stylesheet"] 
                   else route.continue_())

        self.poisoned_session = False
        return new_context, page

    # ---------------------------------------------------------
    # 4. Injection Tools (Surgeon's Injection)
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

    def robust_fill_form(self, page):
        """تعبئة ذكية للحقول"""
        # 1. الحقول الأساسية
        self.fast_inject(page, "input[name='lastname']", Config.LAST_NAME)
        self.fast_inject(page, "input[name='firstname']", Config.FIRST_NAME)
        self.fast_inject(page, "input[name='email']", Config.EMAIL)
        
        if not self.fast_inject(page, "input[name='emailrepeat']", Config.EMAIL):
             self.fast_inject(page, "input[name='emailRepeat']", Config.EMAIL)

        # 2. الحقول الديناميكية (الجواز والهاتف)
        # نحاول الحقن في كل الأماكن المحتملة لضمان النجاح
        self.fast_inject(page, "input[name='fields[0].content']", Config.PASSPORT)
        self.fast_inject(page, "input[name*='passport']", Config.PASSPORT)
        
        phone = Config.PHONE.replace("+", "00").strip()
        self.fast_inject(page, "input[name='fields[1].content']", phone)
        self.fast_inject(page, "input[name*='phone']", phone)

        # 3. اختيار الفئة
        try:
            page.evaluate("""
                const s = document.querySelector('select');
                if(s){ 
                    for(let i=0; i<s.options.length; i++){
                        if(s.options[i].text.toLowerCase().includes('student') || 
                           s.options[i].text.toLowerCase().includes('language') ||
                           s.options[i].text.toLowerCase().includes('studium')) {
                            s.selectedIndex = i; s.dispatchEvent(new Event('change')); return;
                        }
                    }
                    s.selectedIndex=1; s.dispatchEvent(new Event('change')); 
                }
            """)
        except: pass

    # ---------------------------------------------------------
    # 5. Captcha & Poison Check
    # ---------------------------------------------------------
    def check_poison(self, page, location="Unknown"):
        # إذا رأينا كابتشا الشهر ونحن في الداخل، فهذا طرد
        if location == "Form" and page.locator("form#appointment_captcha_month").count() > 0:
            logger.warning("☠️ POISON: Bounced back.")
            self.poisoned_session = True
            return True
        return False

    def solve_captcha(self, page, mode):
        if not page.locator("input[name='captchaText']").is_visible(): return True
        
        captcha_div = page.locator("captcha > div").first
        if captcha_div.is_visible():
            if mode == "PATROL": time.sleep(1)
            
            img_bytes = captcha_div.screenshot()
            # فحص الحظر (صورة سوداء صغيرة)
            if len(img_bytes) < 1000:
                logger.critical("⚫ BLACK CAPTCHA DETECTED.")
                self.poisoned_session = True
                return False
                
            code = self.solver.solve(img_bytes).replace(" ","").strip()
            
            # في وضع الدورية، نرفض الأكواد الطويلة
            if mode == "PATROL" and (len(code) < 4 or len(code) > 6):
                page.reload()
                return False

            if len(code) > 3:
                self.fast_inject(page, "input[name='captchaText']", code)
                page.keyboard.press("Enter")
                
                try: page.wait_for_load_state("domcontentloaded", timeout=4000)
                except: pass
                
                if self.check_poison(page): return False
                if page.locator("input[name='captchaText']").is_visible(): return False
                return True
        return False

    # ---------------------------------------------------------
    # 6. Deathmatch Loop
    # ---------------------------------------------------------
    def deathmatch_submit(self, page, mode):
        logger.info("💀 ENTERING DEATHMATCH SUBMISSION LOOP...")
        
        self.robust_fill_form(page)
        
        for i in range(10):
            if not self.solve_captcha(page, mode):
                if page.locator("input[name='lastname']").count() > 0: continue
                return False 
            
            try: page.wait_for_load_state("networkidle", timeout=5000)
            except: pass
            
            content = page.content().lower()
            if "appointment number" in content:
                logger.info("🏆 VICTORY! APPOINTMENT SECURED.")
                try: send_photo(page.screenshot(), "✅ VICTORY!")
                except: pass
                return True
            
            if page.locator("input[name='lastname']").count() > 0:
                logger.warning(f"⚔️ Silent Reject (Attempt {i+1}). Retrying...")
                continue
            
            if "error" in content:
                logger.error("❌ Server Error.")
                return False
                
        return False

    # ---------------------------------------------------------
    # 7. Main Engine
    # ---------------------------------------------------------
    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, 
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-gpu"]
            )
            context, page = self.rebirth(None, browser)
            logger.info("👑 KING SNIPER HYBRID ONLINE.")

            while True:
                try:
                    if self.poisoned_session: 
                        context, page = self.rebirth(context, browser)
                    
                    mode = self.get_mode()
                    
                    if mode == "WARMUP" and datetime.datetime.now(self.tz_yemen).minute >= 58:
                         self.wait_for_zero_hour()
                         mode = "BEAST"

                    # أولويات الأشهر: 3 -> 4 -> 2 -> 5
                    today = datetime.datetime.now(self.tz_yemen).date()
                    priority_offsets = [2, 3, 1, 4]
                    targets = []
                    
                    for off in priority_offsets:
                        future_month = (today.month + off - 1) % 12 + 1
                        future_year = today.year + ((today.month + off - 1) // 12)
                        date_str = f"15.{future_month:02d}.{future_year}"
                        base = self.base_url.split('&dateStr')[0]
                        targets.append(f"{base}&dateStr={date_str}")
                    
                    for url in targets:
                        try: 
                            to = 5000 if mode == "BEAST" else 15000
                            # إذا كنا في نفس الصفحة، نحدث فقط
                            if mode == "BEAST" and url in page.url:
                                page.reload()
                            else:
                                page.goto(url, timeout=to, wait_until="domcontentloaded")
                        except: continue

                        if page.locator("input[name='captchaText']").count() > 0:
                            if not self.solve_captcha(page, mode):
                                if self.poisoned_session: break 
                                continue
                        
                        if self.check_poison(page, "Month"): break

                        # Scan Days
                        if page.locator("#calendarform").is_visible():
                            day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                            if day_links:
                                logger.info(f"🔥 DAYS FOUND! Ghost Jumping...")
                                
                                # Ghost Click
                                href = day_links[0].get_attribute("href")
                                if "http" not in href:
                                    href = "https://service2.diplo.de/rktermin/" + href
                                page.goto(href)
                                
                                if not self.solve_captcha(page, mode):
                                    if self.poisoned_session: break
                                    continue

                                # Scan Slots
                                time_links = page.locator("a.arrow[href*='appointment_showForm']").all()
                                if time_links:
                                    href = time_links[0].get_attribute("href")
                                    logger.info(f"⏰ SLOT FOUND! Ghost Jumping to Form...")
                                    
                                    if "http" not in href:
                                        href = "https://service2.diplo.de/rktermin/" + href
                                    page.goto(href)
                                    
                                    if not self.solve_captcha(page, mode):
                                        if self.poisoned_session: break
                                        continue
                                    
                                    if self.check_poison(page, "Form"): break

                                    # DEATHMATCH
                                    if self.deathmatch_submit(page, mode):
                                        time.sleep(9999) # Victory Sleep
                                        return 
                                    else:
                                        break 
                        else:
                            # صفحة غريبة؟
                            content = page.content()
                            if "captchaText" in content: continue
                            if "Unfortunately" in content: continue
                            page.reload()

                except Exception as e:
                    logger.error(f"Loop Error: {e}")
                    time.sleep(1)
                
                if mode != "BEAST":
                    time.sleep(random.uniform(30, 60))

if __name__ == "__main__":
    KingSniper().run()