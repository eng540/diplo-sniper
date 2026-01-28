import time
import random
import datetime
import logging
import pytz
import ntplib
from playwright.sync_api import sync_playwright

# الحفاظ على الـ Imports الخاصة بنظامك كما هي
from src.config import Config
from src.captcha import CaptchaSolver
from src.notifier import send_alert, send_photo
# ---------------------------------------------------------
# 1. إعدادات السجل (كما هي)
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("EliteSniper")

class EliteSniper:
    def __init__(self):
        # استخدام الكلاسات الموجودة في نظامك
        self.solver = CaptchaSolver()
        self.base_url = Config.TARGET_URL + "&request_locale=en"
        self.tz_yemen = pytz.timezone('Asia/Aden')
        self.time_offset = 0
        self.user_agents = [
             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
             "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ]
        self.poisoned_session = False
        
        # مزامنة الوقت عند التشغيل
        self.sync_time()

    # ---------------------------------------------------------
    # 2. إدارة الوقت (تحسينات طفيفة للأداء)
    # ---------------------------------------------------------
    def sync_time(self):
        try:
            client = ntplib.NTPClient()
            response = client.request('pool.ntp.org', version=3)
            self.time_offset = response.offset
            logger.info(f"⏱️ Time Synced. Offset: {self.time_offset:.4f}s")
        except:
            logger.warning("⚠️ NTP Sync Failed. Using local time.")

    def get_precise_time(self):
        return datetime.datetime.now(self.tz_yemen) + datetime.timedelta(seconds=self.time_offset)

    def wait_for_zero_hour(self):
        target_hour = 1
        target_minute = 59
        target_second = 50
        
        while True:
            now = self.get_precise_time()
            if (now.hour == 2) or (now.hour == target_hour and now.minute == target_minute and now.second >= target_second):
                logger.info("⚔️ ZERO HOUR REACHED! LAUNCHING ATTACK!")
                break
            
            # انتظار نشط للدقة العالية في آخر الثواني
            if now.hour == target_hour and now.minute == target_minute and now.second > 45:
                pass 
            else:
                time.sleep(0.5)

    def get_mode(self):
        now = self.get_precise_time()
        if (now.hour == 1 and now.minute == 59 and now.second >= 50) or (now.hour == 2 and now.minute <= 10):
            return "BEAST"
        if now.hour == 1 and now.minute >= 45:
            return "WARMUP"
        return "PATROL"

    # ---------------------------------------------------------
    # 3. البنية التحتية (إصلاح مشكلة الـ CSS)
    # ---------------------------------------------------------
    def rebirth(self, context, browser):
        logger.critical("☣️ REBIRTH PROTOCOL ACTIVATED.")
        try: context.close()
        except: pass
        
        mode = self.get_mode()
        sleep_time = 0.5 if mode == "BEAST" else random.uniform(3, 5)
        time.sleep(sleep_time)
        
        new_context = browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={"width": 1366 + random.randint(0, 50), "height": 768 + random.randint(0, 50)},
            locale="en-US",
            timezone_id="Asia/Aden"
        )
        
        page = new_context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        
        # [تحسين] السماح للـ CSS والخطوط لتجنب كشف البوت (إصلاح الانهيار المحتمل)
        page.route("**/*", lambda route: route.abort() 
                   if route.request.resource_type in ["image", "media"] 
                   else route.continue_())

        self.poisoned_session = False
        logger.info("✨ REBIRTH COMPLETE.")
        return new_context, page

    # ---------------------------------------------------------
    # 4. أدوات الحقن والديناميكية (تطوير الوظائف)
    # ---------------------------------------------------------
    def fast_inject(self, page, selector, value):
        # دالة الحقن الأساسية (لم تتغير)
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

    def map_and_inject(self, page, label_keyword, value):
        """
        [جديد] محرك البحث الديناميكي: يربط الاسم الظاهر (Label) بالحقل المخفي (Input)
        هذا يضمن العمل حتى لو غيرت السفارة أسماء الحقول.
        """
        try:
            target_name = page.evaluate(f"""() => {{
                const labels = Array.from(document.querySelectorAll('label'));
                const targetLabel = labels.find(l => l.innerText.toLowerCase().includes("{label_keyword.lower()}"));
                if (targetLabel) {{
                    const inputId = targetLabel.getAttribute('for');
                    if (inputId) {{
                        const inputElement = document.getElementById(inputId);
                        if (inputElement) return inputElement.getAttribute('name');
                    }}
                }}
                return null;
            }}""")

            if target_name:
                logger.info(f"🔗 Mapped '{label_keyword}' -> '{target_name}'")
                return self.fast_inject(page, f"input[name='{target_name}']", value)
            
            # Fallback: المحاولة بالطريقة القديمة إذا فشل الديناميكي
            return False
        except: return False

    def select_visa_category(self, page):
        """
        [جديد] اختيار فئة الفيزا بذكاء حسب الأولوية (اليمنيين أولاً)
        """
        try:
            priority_keywords = [
                "yemeni national", "student", "studium", 
                "language", "sprachkurs", "university"
            ]
            
            result = page.evaluate(f"""(keywords) => {{
                const selects = Array.from(document.querySelectorAll('select'));
                const targetSelect = selects.find(s => s.options.length > 2) || selects[0];
                if (!targetSelect) return null;

                for (const keyword of keywords) {{
                    for (let i = 0; i < targetSelect.options.length; i++) {{
                        if (targetSelect.options[i].text.toLowerCase().includes(keyword)) {{
                            targetSelect.selectedIndex = i;
                            targetSelect.dispatchEvent(new Event('change', {{bubbles:true}}));
                            return targetSelect.options[i].text;
                        }}
                    }}
                }}
                // الافتراضي
                if (targetSelect.options.length > 1) {{
                     targetSelect.selectedIndex = 1;
                     targetSelect.dispatchEvent(new Event('change', {{bubbles:true}}));
                }}
                return "Default";
            }}""", priority_keywords)
            
            if result: logger.info(f"📋 Category Selected: {result}")
        except: pass

    def robust_fill_form(self, page):
        """
        تعبئة النموذج باستخدام المحرك الديناميكي المطور
        """
        # الحقول الأساسية
        if not self.map_and_inject(page, "Last name", Config.LAST_NAME):
            self.fast_inject(page, "input[name='lastname']", Config.LAST_NAME)
            
        if not self.map_and_inject(page, "First name", Config.FIRST_NAME):
            self.fast_inject(page, "input[name='firstname']", Config.FIRST_NAME)
            
        if not self.map_and_inject(page, "Email", Config.EMAIL):
            self.fast_inject(page, "input[name='email']", Config.EMAIL)
            
        if not self.map_and_inject(page, "Repeat", Config.EMAIL):
            self.fast_inject(page, "input[name='emailrepeat']", Config.EMAIL)

        # الحقول الديناميكية (الجواز والهاتف) - هنا تكمن القوة
        if not self.map_and_inject(page, "Passport", Config.PASSPORT):
            # محاولة يدوية إذا فشل الديناميكي
            self.fast_inject(page, "input[name='fields[0].content']", Config.PASSPORT)
            
        if not self.map_and_inject(page, "Telephone", Config.PHONE):
            self.fast_inject(page, "input[name='fields[1].content']", Config.PHONE)

        # اختيار الفئة
        self.select_visa_category(page)

    # ---------------------------------------------------------
    # 5. التقديم وحل الكابتشا
    # ---------------------------------------------------------
    def check_poison(self, page, location="Unknown"):
        # التحقق من الحظر
        if location == "Form" and page.locator("form#appointment_captcha_month").count() > 0:
            logger.warning("☠️ POISON: Bounced back.")
            self.poisoned_session = True
            return True
        return False

    def solve_captcha(self, page, mode):
        if not page.locator("input[name='captchaText']").is_visible(): return True
        
        captcha_div = page.locator("captcha > div").first
        if captcha_div.is_visible():
            # انتظار بسيط لضمان اكتمال تحميل الصورة
            page.wait_for_timeout(200)
            img_bytes = captcha_div.screenshot()
            
            # فحص الصورة التالفة
            if len(img_bytes) < 1000:
                logger.critical("⚫ BLACK CAPTCHA. POISONED.")
                self.poisoned_session = True
                return False
            
            # استخدام ملف الكابتشا الموجود لديك (بدون تغيير بنيته)
            code = self.solver.solve(img_bytes)
            
            # تنظيف الكود الناتج لضمان الجودة
            code = code.replace(" ", "").strip().lower()
            
            if len(code) > 3:
                self.fast_inject(page, "input[name='captchaText']", code)
                
                # [تحسين] محاولة ضغط الزر برمجياً بدلاً من الاعتماد فقط على Enter
                try:
                    page.evaluate("const btn = document.querySelector('input[type=\"submit\"]'); if(btn) btn.click();")
                except:
                    page.keyboard.press("Enter")
                
                try: page.wait_for_load_state("domcontentloaded", timeout=3000)
                except: pass
                
                if page.locator("input[name='captchaText']").is_visible(): return False
                return True
        return False

    def deathmatch_submit(self, page, mode):
        logger.info("💀 ENTERING DEATHMATCH SUBMISSION LOOP...")
        
        # تعبئة النموذج مرة واحدة بذكاء
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
    # 6. المحرك الرئيسي (Main Engine)
    # ---------------------------------------------------------
    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, 
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-gpu"]
            )
            context, page = self.rebirth(None, browser)

            while True:
                try:
                    if self.poisoned_session: 
                        context, page = self.rebirth(context, browser)
                    
                    mode = self.get_mode()
                    
                    if mode == "WARMUP" and self.get_precise_time().minute >= 58:
                         self.wait_for_zero_hour()
                         mode = "BEAST"

                    today = datetime.date.today()
                    # استراتيجية المسح (3 أشهر للأمام)
                    targets = []
                    for i in range(3): 
                        d = today + datetime.timedelta(days=30*i)
                        date_str = d.strftime("15.%m.%Y")
                        base = self.base_url.split('&dateStr')[0]
                        targets.append(f"{base}&dateStr={date_str}")
                    
                    for url in targets:
                        try: 
                            to = 5000 if mode == "BEAST" else 15000
                            page.goto(url, timeout=to, wait_until="domcontentloaded")
                        except: continue

                        if page.locator("input[name='captchaText']").count() > 0:
                            if not self.solve_captcha(page, mode):
                                if self.poisoned_session: break 
                                continue
                        
                        if self.check_poison(page, "Month"): break

                        # Scan Days
                        day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                        if day_links:
                            logger.info(f"🔥 DAYS FOUND! Ghost Jumping...")
                            href = day_links[0].get_attribute("href")
                            # بناء الرابط الكامل يدوياً للسرعة
                            if "http" not in href:
                                if href.startswith("/"): full_link = "https://service2.diplo.de" + href
                                else: full_link = self.base_url.split("/extern")[0] + "/extern/" + href.split("/extern/")[-1]
                            else: full_link = href
                            
                            page.goto(full_link)
                            
                            if not self.solve_captcha(page, mode):
                                if self.poisoned_session: break
                                continue

                            # Scan Slots
                            time_links = page.locator("a.arrow[href*='appointment_showForm']").all()
                            if time_links:
                                href = time_links[0].get_attribute("href")
                                logger.info(f"⏰ SLOT FOUND! Ghost Jumping to Form...")
                                
                                if "http" not in href:
                                    if href.startswith("/"): full_link = "https://service2.diplo.de" + href
                                    else: full_link = self.base_url.split("/extern")[0] + "/extern/" + href.split("/extern/")[-1]
                                else: full_link = href

                                page.goto(full_link)
                                
                                if not self.solve_captcha(page, mode):
                                    if self.poisoned_session: break
                                    continue
                                
                                if self.check_poison(page, "Form"): break

                                # بدء ملحمة الحجز
                                if self.deathmatch_submit(page, mode):
                                    time.sleep(9999) # التوقف للاحتفال
                                    return 
                                else:
                                    break 

                except Exception as e:
                    logger.error(f"Loop Error: {e}")
                    time.sleep(1)

if __name__ == "__main__":
    EliteSniper().run()