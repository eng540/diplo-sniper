import time
import random
import datetime
import logging
import pytz
import re
import ntplib # ### ADDED: For Atomic Precision
from playwright.sync_api import sync_playwright

from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

# ---------------------------------------------------------
# 1. Logging Setup
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
        self.time_offset = 0 # الفرق الزمني مع التوقيت العالمي
        self.sync_time() # ضبط الساعة عند البدء
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ]
        
        self.poisoned_session = False

    # ---------------------------------------------------------
    # ### ADDED: NTP Time Synchronization
    # ---------------------------------------------------------
    def sync_time(self):
        try:
            client = ntplib.NTPClient()
            response = client.request('pool.ntp.org', version=3)
            self.time_offset = response.offset
            logger.info(f"⏱️ Time Synced. Offset: {self.time_offset:.4f}s")
        except:
            logger.warning("⚠️ NTP Sync Failed. Using Server Time.")

    def get_precise_time(self):
        # الوقت الحالي + فرق التوقيت العالمي
        return datetime.datetime.now(self.tz_yemen) + datetime.timedelta(seconds=self.time_offset)

    # ---------------------------------------------------------
    # 2. Time Strategy
    # ---------------------------------------------------------
    def get_mode(self):
        now = self.get_precise_time() # استخدام الوقت الذري
        if (now.hour == 1 and now.minute >= 58) or (now.hour == 2 and now.minute <= 5):
            return "BEAST"
        if now.hour == 1 and now.minute >= 45:
            return "WARMUP"
        return "PATROL"

    # ---------------------------------------------------------
    # 3. Rebirth Protocol (Optimized)
    # ---------------------------------------------------------
    def rebirth(self, context, browser):
        logger.critical("☣️ SESSION POISONED! INITIATING REBIRTH...")
        
        try: context.close()
        except: pass
        
        mode = self.get_mode()
        # في وضع الوحش، لا ننتظر طويلاً، نحتاج العودة فوراً
        sleep_time = 0.1 if mode == "BEAST" else random.uniform(5, 10)
        time.sleep(sleep_time)
        
        new_context = browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Asia/Aden"
        )
        
        new_page = new_context.new_page()
        
        # ### ADDED: Resource Blocking (Speed Hack)
        # هذا الكود يمنع تحميل الصور والخطوط لتسريع الصفحة 3 أضعاف
        new_page.route("**/*", lambda route: route.abort() 
                   if route.request.resource_type in ["image", "stylesheet", "font", "media"] 
                   else route.continue_())

        new_page.add_init_script("""Object.defineProperty(navigator, 'webdriver', { get: () => undefined });""")
        
        logger.info("✨ REBIRTH COMPLETE.")
        self.poisoned_session = False
        return new_context, new_page

    # ---------------------------------------------------------
    # 4. Surgeon's Injection
    # ---------------------------------------------------------
    def fast_inject(self, page, selector, value):
        try:
            # التحقق من الوجود قبل الحقن لتجنب الأخطاء
            if page.locator(selector).count() == 0: return False
            
            page.evaluate(f"""
                const el = document.querySelector("{selector}");
                if(el) {{ 
                    el.value = "{value}"; 
                    el.dispatchEvent(new Event('input', {{ bubbles: true }})); 
                    el.dispatchEvent(new Event('change', {{ bubbles: true }})); 
                }}
            """)
            return True
        except: return False
            
    def robust_fill_form(self, page):
        logger.info("📝 Injecting Data...")
        # 1. الحقول الثابتة
        self.fast_inject(page, "input[name='lastname']", Config.LAST_NAME)
        self.fast_inject(page, "input[name='firstname']", Config.FIRST_NAME)
        self.fast_inject(page, "input[name='email']", Config.EMAIL)
        
        # 2. حقل تكرار الإيميل (يتغير اسمه أحياناً)
        if not self.fast_inject(page, "input[name='emailrepeat']", Config.EMAIL):
             self.fast_inject(page, "input[name='emailRepeat']", Config.EMAIL)

        # 3. الحقول الديناميكية (الجواز والهاتف)
        # نحاول البحث عن الـ ID المرتبط بالـ Label أولاً (الطريقة الذكية)
        passport_id = self.find_input_id_by_label(page, "Passport")
        if passport_id: self.fast_inject(page, f"#{passport_id}", Config.PASSPORT)
        else: self.fast_inject(page, "input[name*='fields[0]']", Config.PASSPORT) # Fallback

        phone_id = self.find_input_id_by_label(page, "Telephone")
        phone_val = Config.PHONE.replace("+", "00").strip()
        if phone_id: self.fast_inject(page, f"#{phone_id}", phone_val)
        else: self.fast_inject(page, "input[name*='fields[1]']", phone_val) # Fallback

        # 4. القائمة المنسدلة (Select)
        try:
            page.evaluate("""
                const s = document.querySelector('select');
                if (s) { s.selectedIndex = 1; s.dispatchEvent(new Event('change')); }
            """)
        except: pass

    def find_input_id_by_label(self, page, keyword):
        try:
            return page.evaluate(f"""
                () => {{
                    const labels = Array.from(document.querySelectorAll('label'));
                    const target = labels.find(l => l.innerText.toLowerCase().includes("{keyword.lower()}"));
                    return target ? target.getAttribute('for') : null;
                }}
            """)
        except: return None

    # ---------------------------------------------------------
    # 5. Poison Detection
    # ---------------------------------------------------------
    def check_session_poison(self, page):
        try:
            # إذا عدنا لصفحة الكابتشا الشهرية ونحن في منتصف العملية
            if "appointment_captcha_month" in page.content() and "appointment_showDay" not in page.url:
                logger.warning("☠️ POISON: Bounced to Start.")
                self.poisoned_session = True
                return True
            
            if "global-error" in page.content():
                 logger.warning("☠️ POISON: Global Error.")
                 self.poisoned_session = True
                 return True
            return False
        except: return False

    # ---------------------------------------------------------
    # 6. Captcha Logic (With Black Image Check)
    # ---------------------------------------------------------
    def solve_captcha(self, page, mode):
        if not page.locator("input[name='captchaText']").is_visible():
            return True

        if mode == "PATROL": time.sleep(random.uniform(1, 2))

        try:
            captcha_div = page.locator("captcha > div").first
            if captcha_div.is_visible():
                
                # ### CRITICAL: فحص الكابتشا السوداء (4333)
                img_bytes = captcha_div.screenshot()
                if len(img_bytes) < 1500: # حجم صغير جداً = صورة تالفة
                    logger.critical("⚫ BLACK CAPTCHA (4333) DETECTED.")
                    self.poisoned_session = True
                    return False

                code = self.solver.solve(img_bytes).replace(" ", "").strip()
                if len(code) > 3:
                    logger.info(f"🧩 Solving: {code}")
                    self.fast_inject(page, "input[name='captchaText']", code)
                    page.keyboard.press("Enter")
                    
                    try: page.wait_for_load_state("domcontentloaded", timeout=4000)
                    except: pass
                    
                    if self.check_session_poison(page): return False
                    return not page.locator("input[name='captchaText']").is_visible()
        except: pass
        return False

    # ---------------------------------------------------------
    # 7. Main Loop
    # ---------------------------------------------------------
    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, 
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-gpu"]
            )
            
            context, page = self.rebirth(None, browser)
            logger.info("👑 KING SNIPER (FINAL) ONLINE.")

            while True:
                try:
                    if self.poisoned_session:
                        context, page = self.rebirth(context, browser)
                        continue

                    mode = self.get_mode()
                    
                    # قائمة الروابط المستهدفة (شهرين للأمام)
                    urls = []
                    today = datetime.date.today()
                    months_to_scan = 2 if mode in ["BEAST", "WARMUP"] else 4
                    for i in range(months_to_scan):
                         d = today + datetime.timedelta(days=30*i)
                         urls.append(f"{self.base_url.split('&dateStr')[0]}&dateStr={d.strftime('15.%m.%Y')}")
                    
                    for url in urls:
                        try:
                            # Timeout قصير جداً في وضع الوحش
                            to = 5000 if mode == "BEAST" else 30000
                            page.goto(url, timeout=to, wait_until="domcontentloaded")
                        except: continue

                        if self.check_session_poison(page): break
                        
                        if not self.solve_captcha(page, mode):
                            if self.poisoned_session: break
                            continue

                        # --- GHOST CLICK (التنقل الشبحي) ---
                        day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                        if day_links:
                            logger.info(f"🔥 {len(day_links)} DAYS FOUND!")
                            
                            # استخراج الرابط والانتقال مباشرة (أسرع من النقر)
                            target_href = day_links[0].get_attribute("href")
                            if target_href:
                                full_url = self.base_url.split("/extern")[0] + "/extern/" + target_href.split("extern/")[1]
                                logger.info("👻 Ghost Jump to Day...")
                                page.goto(full_url)
                            else:
                                day_links[0].click()

                            if self.check_session_poison(page): break
                            if not self.solve_captcha(page, mode):
                                if self.poisoned_session: break
                                continue
                            
                            # اختيار الوقت
                            time_links = page.locator("a.arrow[href*='appointment_showForm']").all()
                            if time_links:
                                target_href = time_links[0].get_attribute("href")
                                logger.info("⏰ TIME FOUND! Ghost Jumping...")
                                
                                full_url = self.base_url.split("/extern")[0] + "/extern/" + target_href.split("extern/")[1]
                                page.goto(full_url)

                                if self.check_session_poison(page): break
                                if not self.solve_captcha(page, mode):
                                    if self.poisoned_session: break
                                    continue

                                # تعبئة وإرسال
                                self.robust_fill_form(page)
                                if self.solve_captcha(page, mode):
                                    if "appointment number" in page.content().lower():
                                        logger.info("🏆 VICTORY!")
                                        send_photo(page.screenshot(), "✅ KING VICTORY!")
                                        return 

                    # استراحة المحارب
                    if mode != "BEAST":
                        time.sleep(random.uniform(10, 30))

                except Exception as e:
                    logger.error(f"Loop Error: {e}")
                    time.sleep(1)

if __name__ == "__main__":
    bot = KingSniper()
    bot.run()
