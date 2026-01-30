import time
import random
import datetime
import logging
import pytz 
from playwright.sync_api import sync_playwright
from src.config import Config
from src.captcha import CaptchaSolver
from src.notifier import send_alert, send_photo

# ------------------------------------------------------------------
# إعدادات السجل
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("KingSniper_V2")

# ------------------------------------------------------------------
# 1. العقل المدبر للبروكسي (Proxy Brain)
# ------------------------------------------------------------------
class ProxyManager:
    def __init__(self, proxy_list):
        # هيكل البيانات: {proxy_url: {'score': 100, 'cooldown': 0}}
        self.proxies = {p: {'score': 100, 'cooldown': 0} for p in proxy_list}
        # إضافة Tor كخيار احتياطي (إذا كان متاحاً على الجهاز/السيرفر)
        # self.proxies["socks5://127.0.0.1:9050"] = {'score': 50, 'cooldown': 0} 

    def get_best_proxy(self):
        now = time.time()
        # فلترة البروكسيات المتاحة (التي انتهى وقت تبريدها)
        available = [p for p, data in self.proxies.items() if data['cooldown'] < now]
        
        if not available:
            logger.warning("⚠️ All proxies are cooling down! Resetting cooldowns.")
            for p in self.proxies: self.proxies[p]['cooldown'] = 0
            available = list(self.proxies.keys())

        # الاختيار بناءً على أعلى سكور (مع قليل من العشوائية لتوزيع الحمل)
        # نختار من أفضل 3 بروكسيات
        available.sort(key=lambda p: self.proxies[p]['score'], reverse=True)
        top_candidates = available[:3]
        return random.choice(top_candidates) if top_candidates else None

    def report_success(self, proxy):
        if proxy and proxy in self.proxies:
            self.proxies[proxy]['score'] = min(100, self.proxies[proxy]['score'] + 5)

    def report_failure(self, proxy, fatal=False):
        if proxy and proxy in self.proxies:
            penalty = 30 if fatal else 10
            cooldown_time = 300 if fatal else 60 # 5 دقائق للحظر، دقيقة للخطأ العادي
            
            self.proxies[proxy]['score'] -= penalty
            self.proxies[proxy]['cooldown'] = time.time() + cooldown_time
            logger.warning(f"📉 Proxy {proxy[-5:]} penalized. Score: {self.proxies[proxy]['score']}")

# ------------------------------------------------------------------
# 2. القناص الخالد (The Immortal Sniper)
# ------------------------------------------------------------------
class KingSniper:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url = Config.TARGET_URL + "&request_locale=en"
        self.timezone = pytz.timezone("Asia/Aden")
        
        # قائمة البروكسيات (يجب ملؤها ببروكسيات قوية)
        # مثال: "http://user:pass@ip:port"
        raw_proxies = [
            # "http://user:pass@1.2.3.4:8080",
            # "http://user:pass@5.6.7.8:8080",
        ]
        self.proxy_manager = ProxyManager(raw_proxies)
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ]
        
        self.current_proxy = None
        self.is_dead = False # حالة الموت السريري للجلسة

    def get_mode(self):
        now = datetime.datetime.now(self.timezone)
        # KILL MODE: 01:55 -> 02:10
        if (now.hour == 1 and now.minute >= 55) or (now.hour == 2 and now.minute <= 10):
            return "KILL"
        # WARMUP: 01:45 -> 01:55
        elif (now.hour == 1 and now.minute >= 45):
            return "WARMUP"
        return "PATROL"

    def rebirth(self, browser):
        """
        إعادة الولادة: تغيير الهوية والبروكسي بالكامل
        """
        logger.warning("♻️ INITIATING REBIRTH PROTOCOL...")
        
        # 1. الحصول على أفضل بروكسي متاح
        self.current_proxy = self.proxy_manager.get_best_proxy()
        proxy_config = {"server": self.current_proxy} if self.current_proxy else None
        
        if self.current_proxy:
            logger.info(f"🛡️ New Identity using Proxy: ...{self.current_proxy[-5:]}")
        else:
            logger.warning("⚠️ No Proxy available! Running Naked (Direct IP).")

        # 2. سياق جديد
        context = browser.new_context(
            user_agent=random.choice(self.user_agents),
            proxy=proxy_config,
            viewport={"width": 1366 + random.randint(0, 50), "height": 768 + random.randint(0, 50)},
            locale="en-US",
            timezone_id="Asia/Aden",
            ignore_https_errors=True
        )
        
        page = context.new_page()
        page.add_init_script("""Object.defineProperty(navigator, 'webdriver', { get: () => undefined });""")
        
        # حظر الموارد للسرعة
        page.route("**/*", lambda route: route.abort() 
                   if route.request.resource_type in ["image", "media", "font"] 
                   else route.continue_())
        
        self.is_dead = False
        return context, page

    def fast_inject(self, page, selector, value):
        try:
            page.evaluate(f"""
                const el = document.querySelector("{selector}");
                if(el) {{ el.value = "{value}"; el.dispatchEvent(new Event('input')); }}
            """)
        except: pass

    def handle_captcha(self, page, location="General"):
        # إذا كانت الجلسة ميتة، لا تحاول
        if self.is_dead: return False

        try:
            if not page.locator("input[name='captchaText']").is_visible(): return True 

            captcha_div = page.locator("captcha > div").first
            if captcha_div.is_visible():
                # في وضع الدورية، ننتظر قليلاً لنبدو كبشر
                if self.get_mode() == "PATROL": time.sleep(random.uniform(0.5, 1.5))
                
                code = self.solver.solve(captcha_div.screenshot()).replace(" ", "").strip()
                
                # منطق قبول الكود
                if len(code) < 4 or len(code) > 8:
                    # في وقت القتل، نقبل أي شيء ونحاول. في الدورية، نحدث الصفحة.
                    if self.get_mode() == "PATROL":
                        page.reload()
                        return False
                
                self.fast_inject(page, "input[name='captchaText']", code)
                page.keyboard.press("Enter")
                
                try: page.wait_for_load_state("domcontentloaded", timeout=5000)
                except: pass

                # التحقق من النتيجة
                if page.locator("input[name='captchaText']").is_visible():
                    # فشل الكابتشا
                    logger.warning(f"⚠️ Captcha Failed @ {location}")
                    # إبلاغ مدير البروكسي بفشل بسيط
                    self.proxy_manager.report_failure(self.current_proxy, fatal=False)
                    return False
                
                content = page.content().lower()
                if "error occurred" in content or "ref-id" in content or "forbidden" in content:
                    logger.error(f"💀 FATAL ERROR (4333/Ban) @ {location}")
                    # إبلاغ مدير البروكسي بفشل ذريع (حظر)
                    self.proxy_manager.report_failure(self.current_proxy, fatal=True)
                    self.is_dead = True # إعلان وفاة الجلسة
                    return False

                # نجاح!
                self.proxy_manager.report_success(self.current_proxy)
                return True
        except: 
            return False
        return False

    def fill_form(self, page):
        logger.info("📝 Injecting Data...")
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

            # Smart Category Selection
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

            # حلقة القتال (Deathmatch Loop)
            for i in range(10):
                if self.is_dead: return False # الهروب إذا ماتت الجلسة

                if not self.handle_captcha(page, location="Form"):
                    if page.locator("input[name='lastname']").is_visible(): continue
                    return False
                
                try: page.wait_for_load_state("networkidle", timeout=3000)
                except: pass
                
                content = page.content().lower()
                if "appointment number" in content:
                    logger.info("👑 KING SNIPER VICTORY!")
                    send_alert(f"👑 KING VICTORY! {Config.FIRST_NAME}")
                    return True
                
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
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
            )
            
            # الولادة الأولى
            context, page = self.rebirth(browser)
            logger.info("👑 KING SNIPER V2 ONLINE.")
            
            while True:
                # 1. التحقق من الموت وإعادة الولادة
                if self.is_dead:
                    try: context.close()
                    except: pass
                    context, page = self.rebirth(browser)
                    continue 

                mode = self.get_mode()
                
                # 2. ضبط التوقيت
                if mode == "PATROL":
                    sleep_time = random.uniform(180, 300) # 3-5 دقائق
                elif mode == "WARMUP":
                    sleep_time = 5
                else: # KILL
                    sleep_time = 0.1

                # 3. القصف المركز (مارس -> أبريل -> فبراير -> مايو)
                priority_months = [2, 3, 1, 4] 
                today = datetime.datetime.now(self.timezone).date()
                
                for offset in priority_months:
                    if self.is_dead: break 

                    future_month = (today.month + offset - 1) % 12 + 1
                    future_year = today.year + ((today.month + offset - 1) // 12)
                    date_str = f"15.{future_month:02d}.{future_year}"
                    base_clean = self.base_url.split("&dateStr=")[0]
                    url = f"{base_clean}&dateStr={date_str}"

                    try:
                        # في وضع القتل، لا نعيد التحميل إذا كنا في نفس الصفحة لتوفير الوقت
                        if mode == "KILL" and url in page.url:
                            page.reload()
                        else:
                            try: 
                                timeout = 10000 if mode == "KILL" else 30000
                                page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                            except: 
                                # فشل التحميل قد يعني مشكلة في البروكسي
                                self.proxy_manager.report_failure(self.current_proxy, fatal=False)
                                continue

                        if not self.handle_captcha(page, location=mode): continue

                        # التحقق الواعي (هل نحن في التقويم؟)
                        if page.locator("#calendarform").is_visible():
                            day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                            
                            if not day_links: continue # شهر فارغ
                            
                            logger.info(f"💎 TARGET FOUND in Month {future_month}!")
                            send_alert("💎 TARGET FOUND!")
                            
                            # الهجوم على الأول فوراً (السرعة هي الملك)
                            day_links[0].click()
                            
                            if not self.handle_captcha(page, location="Day"): 
                                page.go_back(); continue
                            
                            time_links = page.locator("a.arrow[href*='appointment_showForm']").all()
                            if time_links:
                                time_links[0].click()
                                if not self.handle_captcha(page, location="PreForm"):
                                    page.go_back(); continue
                                
                                if self.fill_form(page):
                                    return # النصر
                                else:
                                    page.goto(url)
                                    continue
                        else:
                            # صفحة غريبة (ليست تقويم وليست كابتشا)
                            content = page.content()
                            if "Unfortunately" in content: continue
                            if "captchaText" in content: continue # كابتشا معلقة
                            
                            # إذا وصلنا هنا، الصفحة بيضاء أو خطأ غير معروف
                            logger.warning("⚠️ Unknown Page State. Refreshing...")
                            self.proxy_manager.report_failure(self.current_proxy, fatal=False)
                            
                    except Exception as e:
                        logger.error(f"Loop Error: {e}")
                        self.is_dead = True # نعتبر أي خطأ غير متوقع سبباً لإعادة الولادة
                
                if mode != "KILL":
                    logger.info(f"💤 {mode} Sleep: {int(sleep_time)}s")
                    time.sleep(sleep_time)