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

# إعدادات السجل (Logging) - خفيفة وسريعة
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("RocketSniper")

class DiploBot:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url_template = Config.TARGET_URL + "&request_locale=en"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]

    def get_month_urls(self):
        urls = []
        today = datetime.date.today()
        base_clean = self.base_url_template.split("&dateStr=")[0] if "&dateStr=" in self.base_url_template else self.base_url_template

        # مسح 6 أشهر للأمام
        for i in range(6): 
            future_month = (today.month + i - 1) % 12 + 1
            future_year = today.year + ((today.month + i - 1) // 12)
            date_str = f"15.{future_month:02d}.{future_year}"
            full_url = f"{base_clean}&dateStr={date_str}"
            urls.append(full_url)
        return urls

    def type_fast(self, page, selector, text):
        """كتابة سريعة (لصق) لتوفير الوقت"""
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
            timezone_id="Europe/Berlin"
        )
        page = context.new_page()
        # منع الكشف عن الأتمتة
        page.add_init_script("""Object.defineProperty(navigator, 'webdriver', { get: () => undefined });""")
        context.set_default_timeout(45000) # مهلة زمنية قصيرة للسرعة
        return context, page

    def handle_captcha(self, page, context, location="General"):
        """
        معالج الكابتشا الذكي - يدرك إذا علق في الصفحة
        """
        for attempt in range(5): # 5 محاولات شرسة
            try:
                # هل يوجد كابتشا؟
                if not page.locator("input[name='captchaText']").is_visible():
                    return True # لا يوجد كابتشا، الطريق سالك

                logger.info(f"⚡ [Captcha-{location}] Attempt {attempt+1}...")
                captcha_div = page.locator("captcha > div").first

                if captcha_div.is_visible():
                    # انتظار قصير جداً لتحميل الصورة
                    page.wait_for_timeout(500) 
                    captcha_bytes = captcha_div.screenshot()
                    code = self.solver.solve(captcha_bytes)

                    # تنظيف الكود
                    code = code.replace(" ", "").strip()

                    # التحقق من الطول (6 أحرف عادة)
                    if len(code) < 4 or len(code) > 8: 
                        logger.warning(f"⚠️ Bad length ({len(code)}). Refreshing image...")
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

                    # التحقق الذكي من النتيجة
                    try:
                        # ننتظر قليلاً لنرى هل انتقلنا أم بقينا
                        page.wait_for_load_state("domcontentloaded", timeout=4000)
                    except: pass

                    # 1. هل ما زلنا في صفحة الكابتشا (خطأ في الكود)؟
                    if page.locator("input[name='captchaText']").is_visible():
                        err_msg = page.locator(".global-error").first
                        if err_msg.is_visible():
                            logger.warning("❌ Site rejected captcha. Retrying...")
                        else:
                            logger.warning("⚠️ Still on captcha page. Retrying...")
                        continue 

                    # 2. هل ظهرت صفحة خطأ عام؟
                    content = page.content().lower()
                    if "error occurred" in content or "ref-id" in content:
                        logger.error("❌ Critical Error Page. Backing out...")
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

            # الكلمات المفتاحية للحجز (الأولوية للطلاب واللغة)
            priority_keywords = ["yemeni national", "student visa", "language course", "studium", "sprachkurs", "university"]
            options = select_locator.locator("option").all()

            for option in options:
                text = option.text_content()
                if text and any(k.lower() in text.lower() for k in priority_keywords):
                    val = option.get_attribute("value")
                    if val:
                        select_locator.select_option(value=val)
                        return
            # الخيار الافتراضي الثاني
            select_locator.select_option(index=1)
        except: pass

    def fill_booking_form(self, page, context):
        logger.info("📝 Fast-Filling Form...")
        try:
            if not page.locator("input[name='lastname']").is_visible():
                return False

            # التعبئة السريعة (Fast Fill)
            self.type_fast(page, "input[name='lastname']", Config.LAST_NAME)
            self.type_fast(page, "input[name='firstname']", Config.FIRST_NAME)
            self.type_fast(page, "input[name='email']", Config.EMAIL)

            # التعامل مع تكرار الإيميل
            if page.locator("input[name='emailrepeat']").is_visible():
                self.type_fast(page, "input[name='emailrepeat']", Config.EMAIL)
            elif page.locator("input[name='emailRepeat']").is_visible():
                self.type_fast(page, "input[name='emailRepeat']", Config.EMAIL)

            # الجواز
            if page.locator("input[name='passportNumber']").is_visible():
                self.type_fast(page, "input[name='passportNumber']", Config.PASSPORT)
            elif page.locator("input[name='fields[0].content']").is_visible():
                self.type_fast(page, "input[name='fields[0].content']", Config.PASSPORT)

            # الهاتف
            clean_phone = Config.PHONE.replace("+", "00").replace(" ", "").strip()
            if page.locator("input[name='phone']").is_visible():
                self.type_fast(page, "input[name='phone']", clean_phone)
            elif page.locator("input[name='fields[1].content']").is_visible():
                self.type_fast(page, "input[name='fields[1].content']", clean_phone)

            self.select_visa_category(page)

            # حلقة الإرسال (The Retry Loop)
            for attempt in range(5):
                logger.info(f"🚀 Submission Attempt {attempt+1}/5...")

                # حل كابتشا النموذج
                if not self.handle_captcha(page, context, location="Form"):
                    # إذا فشل الكابتشا، نتأكد هل النموذج ما زال موجوداً
                    if page.locator("input[name='lastname']").is_visible():
                        continue # نحاول مرة أخرى
                    return False # خسرنا الصفحة

                logger.info("🚨 Form Submitted. Checking result...")

                # ننتظر قليلاً النتيجة
                try: page.wait_for_load_state("networkidle", timeout=5000)
                except: pass

                content = page.content()

                # 1. التحقق من النجاح
                if "appointment number" in content.lower() or "successfully booked" in content.lower():
                    details = "✅ ROCKET SUCCESS! BOOKING CONFIRMED!\n"
                    match_num = re.search(r"Appointment number is\s+(\d+)", content, re.IGNORECASE)
                    if match_num: details += f"🆔 App Num: {match_num.group(1)}\n"
                    match_date = re.search(r"(\d{2}\.\d{2}\.\d{4})", content)
                    if match_date: details += f"📅 Date: {match_date.group(1)}\n"
                    details += f"👤 Name: {Config.FIRST_NAME} {Config.LAST_NAME}"

                    logger.info(details)
                    # نلتقط صورة للتوثيق فقط عند النجاح
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    page.screenshot(path=f"VICTORY_{ts}.png")
                    send_photo(f"VICTORY_{ts}.png", caption=details)
                    return True

                # 2. هل عدنا لنفس الصفحة؟ (Silent Refresh / Burnt Data)
                if page.locator("input[name='lastname']").is_visible():
                    logger.warning("⚠️ Returned to form (Silent Reject). Retrying immediately...")
                    continue

                # 3. صفحة خطأ صريحة
                if "error occurred" in content.lower() or "ref-id" in content.lower():
                    logger.error("❌ Booking Failed (Server Error).")
                    return False

            return False

        except Exception as e:
            logger.error(f"❌ Form Logic Error: {e}")
            return False

    def run(self):
        with sync_playwright() as p:
            # تفعيل المتصفح بأقصى سرعة
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
            logger.info(f"🚀 ROCKET SNIPER ENGAGED. Target: {Config.TARGET_URL}")
            send_alert("🚀 ROCKET SNIPER V23 (Optimized) Started...")

            while True:
                month_urls = self.get_month_urls()
                for url in month_urls:
                    try:
                        date_part = url.split("dateStr=")[1] if "dateStr=" in url else "Unknown"
                        logger.info(f"🔎 Scanning: {date_part}")

                        try: 
                            page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        except: 
                            continue

                        # حل كابتشا الشهر
                        if not self.handle_captcha(page, context, location="Month"): 
                            continue 

                        # الفحص الحاسم: هل نحن في صفحة الشهر فعلاً؟
                        content = page.content()

                        # 1. هل ما زلنا في الكابتشا؟ (الحلقة المفرغة)
                        if "appointment_captcha_month" in content or "captchaText" in content:
                            logger.warning("🔄 Stuck on Month Captcha loop. Retrying same month...")
                            # إعادة المحاولة لنفس الشهر فوراً
                            page.reload()
                            continue

                        # 2. هل الصفحة فارغة (نصياً)؟
                        if "Unfortunately, there are no appointments" in content or "keine Termine" in content:
                            # لا داعي للبحث عن روابط، ننتقل فوراً
                            continue

                        # 3. البحث عن الأيام
                        day_links = page.locator("a.arrow[href*='appointment_showDay']").all()
                        if not day_links:
                            # وصلنا هنا ولم نجد كابتشا، ولم نجد رسالة "لا مواعيد"، ولم نجد روابط
                            # هذا يعني أن الصفحة تحملت بشكل خاطئ أو محتوى غير متوقع
                            logger.warning("⚠️ No slots & No error msg. Strange state. Moving on.")
                            continue 

                        # 4. وجدنا أياماً! الهجوم!
                        logger.info(f"🔥 {len(day_links)} DAYS FOUND! Attacking first one...")
                        send_alert(f"🔥 DAY FOUND! {date_part} - Attacking...")

                        # نضغط الأول فوراً
                        day_links[0].click()

                        # كابتشا اليوم
                        if not self.handle_captcha(page, context, location="Day"):
                            page.go_back()
                            continue

                        # البحث عن الوقت
                        time_link = page.locator("a.arrow[href*='appointment_showForm']").first
                        if time_link.is_visible():
                            logger.info("⏰ TIME FOUND! Clicking...")
                            time_link.click()

                            # كابتشا ما قبل الاستمارة
                            if not self.handle_captcha(page, context, location="Pre-Form"):
                                page.go_back()
                                continue

                            # تعبئة الاستمارة
                            if self.fill_booking_form(page, context):
                                logger.info("✅ MISSION COMPLETE. Exiting.")
                                return # إنهاء البرنامج بعد النجاح
                            else:
                                logger.error("❌ Booking failed. Restarting scan...")
                                page.goto(url)
                                continue
                        else:
                            logger.warning("⚠️ Day open but slots taken.")

                    except Exception as e:
                        logger.error(f"⚠️ Loop Error: {e}")
                        # إعادة إنشاء المتصفح عند الأخطاء الكبيرة لتنظيف الذاكرة
                        try: context.close()
                        except: pass
                        context, page = self.create_context(browser)
                        time.sleep(2)

                logger.info("💤 Cycle done. Sleeping 45s...")
                time.sleep(45)