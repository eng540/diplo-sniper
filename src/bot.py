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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("DiploSniper")

class DiploBot:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url_template = Config.TARGET_URL + "&request_locale=en"
        self.debug_photo_sent = False
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        ]

    def get_timestamp(self):
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    def get_month_urls(self):
        urls = []
        today = datetime.date.today()
        if "&dateStr=" in self.base_url_template:
            base_clean = self.base_url_template.split("&dateStr=")[0]
        else:
            base_clean = self.base_url_template

        for i in range(6): 
            future_month = (today.month + i - 1) % 12 + 1
            future_year = today.year + ((today.month + i - 1) // 12)
            date_str = f"15.{future_month:02d}.{future_year}"
            full_url = f"{base_clean}&dateStr={date_str}"
            urls.append(full_url)
        return urls

    def type_like_human(self, page, selector, text):
        for char in text:
            page.type(selector, char, delay=random.randint(50, 150))
            
    def create_context(self, browser):
        ua = random.choice(self.user_agents)
        context = browser.new_context(
            user_agent=ua,
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Europe/Berlin"
        )
        page = context.new_page()
        page.add_init_script("""Object.defineProperty(navigator, 'webdriver', { get: () => undefined });""")
        context.set_default_timeout(60000)
        return context, page

    def refresh_captcha(self, page):
        try:
            logger.info("   -> 🔄 Refreshing Captcha...")
            refresh_btn = page.locator("input[name^='action:appointment_refreshCaptcha']").first
            if refresh_btn.is_visible():
                refresh_btn.click()
                page.wait_for_timeout(3000)
                return True
            else:
                page.reload()
                page.wait_for_load_state("domcontentloaded")
                return True
        except:
            pass
        return False

    def handle_captcha(self, page, context, max_retries=5):
        for attempt in range(max_retries):
            try:
                if not page.locator("input[name='captchaText']").is_visible():
                    return True, page 

                logger.info(f"🚧 [Captcha] Attempt {attempt+1}...")
                captcha_element = page.locator("captcha > div").first
                
                if captcha_element.is_visible():
                    page.wait_for_timeout(1500)
                    captcha_bytes = captcha_element.screenshot()
                    code = self.solver.solve(captcha_bytes)
                    
                    if len(code) != 6:
                        logger.warning(f"⚠️ Invalid length ({len(code)}). Hard Resetting...")
                        context.clear_cookies()
                        page.reload()
                        page.wait_for_load_state("domcontentloaded")
                        continue
                    
                    logger.info(f"🧩 Decoded: {code}")
                    self.type_like_human(page, "input[name='captchaText']", code)
                    
                    logger.info("   -> Pressing Enter...")
                    page.keyboard.press("Enter")
                    
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except:
                        pass

                    if page.locator("input[name='captchaText']").is_visible():
                        logger.warning("❌ Captcha failed. Resetting Session...")
                        context.clear_cookies()
                        page.reload()
                        continue 
                    
                    content = page.content().lower()
                    if "error occurred" in content or "ref-id" in content:
                        logger.error("❌ Critical Error Page detected.")
                        return False, page

                    logger.info("✅ Captcha passed.")
                    return True, page

            except Exception as e:
                logger.error(f"⚠️ Captcha Error: {e}")
                page.reload()
        
        return False, page

    def smart_fill_by_label(self, page, keywords, value):
        try:
            for word in keywords:
                label_locator = page.locator(f"//label[contains(text(), '{word}')]")
                if label_locator.count() > 0:
                    first_label = label_locator.first
                    target_id = first_label.get_attribute("for")
                    if target_id:
                        self.type_like_human(page, f"#{target_id}", value)
                        return True
            return False
        except:
            return False

    def select_visa_category(self, page):
        try:
            select_locator = page.locator("select").first
            if not select_locator.is_visible(): return

            priority_keywords = ["yemeni national", "student visa", "language course", "studium", "sprachkurs", "university"]
            options = select_locator.locator("option").all()
            
            for option in options:
                text = option.text_content()
                if text and any(k.lower() in text.lower() for k in priority_keywords):
                    val = option.get_attribute("value")
                    if val:
                        select_locator.select_option(value=val)
                        logger.info(f"🎯 Smart Match: '{text}'")
                        return
            select_locator.select_option(index=1)
        except: pass

    def extract_and_verify_success(self, page):
        content = page.content()
        if "error occurred" in content.lower() or "ref-id" in content.lower():
            return False, None

        if "appointment number" in content.lower() or "successfully booked" in content.lower():
            details = "✅ BOOKING CONFIRMED!\n"
            match_num = re.search(r"Appointment number is\s+(\d+)", content, re.IGNORECASE)
            if match_num: details += f"🆔 App Num: {match_num.group(1)}\n"
            match_date = re.search(r"(\d{2}\.\d{2}\.\d{4})", content)
            if match_date: details += f"📅 Date: {match_date.group(1)}\n"
            details += f"👤 Name: {Config.FIRST_NAME} {Config.LAST_NAME}"
            return True, details
        return False, None

    def fill_booking_form(self, page, context):
        logger.info("📝 Filling Booking Form...")
        try:
            if not page.locator("input[name='lastname']").is_visible():
                return False

            # تعبئة الحقول (مرة واحدة فقط)
            self.type_like_human(page, "input[name='lastname']", Config.LAST_NAME)
            self.type_like_human(page, "input[name='firstname']", Config.FIRST_NAME)
            self.type_like_human(page, "input[name='email']", Config.EMAIL)
            
            if page.locator("input[name='emailrepeat']").is_visible():
                self.type_like_human(page, "input[name='emailrepeat']", Config.EMAIL)
            elif page.locator("input[name='emailRepeat']").is_visible():
                self.type_like_human(page, "input[name='emailRepeat']", Config.EMAIL)

            passport_keywords = ["Passport", "Reisepass", "Passeport"]
            if not self.smart_fill_by_label(page, passport_keywords, Config.PASSPORT):
                if page.locator("input[name='passportNumber']").is_visible():
                    self.type_like_human(page, "input[name='passportNumber']", Config.PASSPORT)
                elif page.locator("input[name='fields[0].content']").is_visible():
                    self.type_like_human(page, "input[name='fields[0].content']", Config.PASSPORT)

            clean_phone = Config.PHONE.replace("+", "00").replace(" ", "").strip()
            phone_keywords = ["Phone", "Telephone", "Telefon", "Mobile"]
            if not self.smart_fill_by_label(page, phone_keywords, clean_phone):
                if page.locator("input[name='phone']").is_visible():
                    self.type_like_human(page, "input[name='phone']", clean_phone)
                elif page.locator("input[name='fields[1].content']").is_visible():
                    self.type_like_human(page, "input[name='fields[1].content']", clean_phone)

            self.select_visa_category(page)

            # حلقة الإصرار على الإرسال
            for attempt in range(5):
                logger.info(f"🚀 Submission Attempt {attempt+1}/5...")
                
                success, page = self.handle_captcha(page, context)
                if not success:
                    # التحقق من بقاء النموذج
                    if page.locator("input[name='lastname']").is_visible():
                        logger.warning("   -> Captcha failed but form is safe. Retrying...")
                        continue
                    else:
                        logger.error("❌ Lost form page.")
                        return False

                logger.info("🚨 Form Submitted via Captcha Enter. Verifying...")
                page.wait_for_timeout(5000)
                
                success_verify, details = self.extract_and_verify_success(page)
                ts = self.get_timestamp()
                
                if success_verify:
                    logger.info(details)
                    page.screenshot(path=f"success_{ts}.png")
                    send_photo(f"success_{ts}.png", caption=details)
                    return True
                
                content = page.content().lower()
                if "error occurred" in content or "ref-id" in content:
                    logger.error("❌ Booking Failed (Error Page).")
                    page.screenshot(path=f"error_{ts}.png")
                    send_photo(f"error_{ts}.png", caption="❌ Booking Failed (See Image)")
                    return False
                
                if page.locator("input[name='lastname']").is_visible():
                    logger.warning("⚠️ Still on form page. Retrying submission...")
                    continue

            return False

        except Exception as e:
            logger.error(f"❌ Form Error: {e}")
            return False

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--no-first-run", "--disable-web-security"]
            )
            
            context, page = self.create_context(browser)
            
            logger.info(f"🚀 Sniper Active. Target: {Config.TARGET_URL}")
            send_alert("🚀 Diplo Sniper V21 (Persistent) Started...")
            
            while True:
                month_urls = self.get_month_urls()
                for url in month_urls:
                    try:
                        date_part = url.split("dateStr=")[1] if "dateStr=" in url else "Unknown"
                        logger.info(f"🔎 Scanning: {date_part}")
                        try: page.goto(url, wait_until="domcontentloaded")
                        except: continue
                        
                        success, page = self.handle_captcha(page, context)
                        if not success: continue 

                        content = page.content()
                        if "Unfortunately, there are no appointments" in content or "keine Termine" in content:
                            time.sleep(random.uniform(2, 4)) 
                            continue
                        
                        while True:
                            day_link = page.locator("a.arrow[href*='appointment_showDay']").first
                            if not day_link.is_visible():
                                logger.info("⚠️ Slot disappeared or taken.")
                                break 

                            logger.info("🔥 DAY FOUND! Attacking...")
                            send_alert(f"🔥 DAY FOUND! {date_part} - Attacking...")
                            
                            day_link.click()
                            success, page = self.handle_captcha(page, context)
                            if not success:
                                logger.warning("   -> Captcha failed on Day. Retrying...")
                                page.go_back()
                                page.reload()
                                continue
                            
                            time_link = page.locator("a.arrow[href*='appointment_showForm']").first
                            if time_link.is_visible():
                                logger.info("⏰ TIME FOUND!")
                                time_link.click()
                                success, page = self.handle_captcha(page, context)
                                if not success:
                                    logger.warning("   -> Captcha failed on Time. Retrying...")
                                    page.go_back()
                                    continue
                                
                                if self.fill_booking_form(page, context):
                                    logger.info("✅ DONE. Exiting.")
                                    return
                                else:
                                    logger.error("❌ Form submission failed. Retrying slot...")
                                    page.goto(url)
                                    continue
                            else:
                                logger.warning("⚠️ Day open but time slots gone.")
                                break
                    except Exception as e:
                        logger.error(f"⚠️ Loop Error: {e}")
                        context.close()
                        context, page = self.create_context(browser)
                        time.sleep(5)
                
                logger.info("💤 Cycle done. Sleeping 60s...")
                time.sleep(60)