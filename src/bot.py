import time
import random
import datetime
import os
import re
import logging
import traceback
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

# إعداد نظام السجلات الاحترافي
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
        
        # إعدادات الأداء
        self.settings = {
            'page_load_timeout': 60000,
            'captcha_retries': 10,
            'cycle_sleep_min': 45,
            'cycle_sleep_max': 90
        }

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

    def _setup_browser(self, p):
        """إعداد المتصفح بتقنيات التخفي العالية"""
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--disable-web-security"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Europe/Berlin",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        page = context.new_page()
        # حقن سكربت لإخفاء البوت
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        context.set_default_timeout(self.settings['page_load_timeout'])
        return browser, context, page

    def refresh_captcha(self, page):
        """تحديث الصورة (الاستراتيجية الآمنة)"""
        try:
            logger.info("   -> 🔄 Refreshing Captcha...")
            refresh_btn = page.locator("input[name^='action:appointment_refreshCaptcha']").first
            if refresh_btn.is_visible():
                refresh_btn.click()
                page.wait_for_timeout(3000)
                return True
            else:
                # إذا لم يوجد زر، نحدث الصفحة
                page.reload()
                page.wait_for_load_state("domcontentloaded")
                return True
        except:
            pass
        return False

    def handle_captcha(self, page):
        """معالجة الكابتشا مع الفلترة والذكاء"""
        for attempt in range(self.settings['captcha_retries']):
            try:
                if not page.locator("input[name='captchaText']").is_visible():
                    return True 

                logger.info(f"🚧 [Captcha] Attempt {attempt+1}...")
                captcha_element = page.locator("captcha > div").first
                
                if captcha_element.is_visible():
                    page.wait_for_timeout(1500)
                    captcha_bytes = captcha_element.screenshot()
                    code = self.solver.solve(captcha_bytes)
                    
                    # فلترة الطول (الأمان أولاً)
                    if len(code) < 5 or len(code) > 8:
                        logger.warning(f"⚠️ Invalid length ({len(code)}: {code}). Refreshing...")
                        self.refresh_captcha(page)
                        continue
                    
                    logger.info(f"🧩 Decoded: {code}")
                    page.fill("input[name='captchaText']", code)
                    
                    logger.info("   -> Pressing Enter...")
                    page.keyboard.press("Enter")
                    
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except:
                        pass

                    if page.locator("input[name='captchaText']").is_visible():
                        logger.warning("❌ Captcha failed. Refreshing image...")
                        self.refresh_captcha(page)
                        continue 
                    
                    content = page.content().lower()
                    if "error occurred" in content or "ref-id" in content:
                        logger.error("❌ Critical Error Page detected.")
                        return False

                    logger.info("✅ Captcha passed.")
                    return True

            except Exception as e:
                logger.error(f"⚠️ Captcha Error: {e}")
                self.refresh_captcha(page)
        
        return False

    def smart_fill_by_label(self, page, keywords, value):
        try:
            for word in keywords:
                label_locator = page.locator(f"//label[contains(text(), '{word}')]")
                if label_locator.count() > 0:
                    first_label = label_locator.first
                    target_id = first_label.get_attribute("for")
                    if target_id:
                        page.fill(f"#{target_id}", value)
                        return True
            return False
        except:
            return False

    def select_visa_smart(self, page):
        """نظام النقاط لاختيار التأشيرة (مقتبس من المراجعة)"""
        try:
            select_locator = page.locator("select").first
            if not select_locator.is_visible(): return

            options = select_locator.locator("option").all()
            best_value = None
            best_score = -1

            # كلمات مفتاحية مع أوزان
            keywords = {
                "yemeni": 10,
                "student": 5,
                "studium": 5,
                "language": 3,
                "university": 3,
                "school": 2
            }

            for option in options:
                text = option.text_content().lower()
                value = option.get_attribute("value")
                if not value: continue
                
                score = 0
                for word, points in keywords.items():
                    if word in text:
                        score += points
                
                if score > best_score:
                    best_score = score
                    best_value = value
                    logger.info(f"   -> Found candidate: '{text}' (Score: {score})")

            if best_value and best_score > 0:
                select_locator.select_option(value=best_value)
                logger.info(f"🎯 Selected Visa Category (Score {best_score})")
            else:
                logger.warning("⚠️ No strong match found. Selecting index 1.")
                select_locator.select_option(index=1)

        except Exception as e:
            logger.error(f"Visa selection error: {e}")

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

    def fill_booking_form(self, page):
        logger.info("📝 Filling Booking Form...")
        try:
            if not page.locator("input[name='lastname']").is_visible():
                return False

            page.fill("input[name='lastname']", Config.LAST_NAME)
            page.fill("input[name='firstname']", Config.FIRST_NAME)
            page.fill("input[name='email']", Config.EMAIL)
            
            if page.locator("input[name='emailrepeat']").is_visible():
                page.fill("input[name='emailrepeat']", Config.EMAIL)
            elif page.locator("input[name='emailRepeat']").is_visible():
                page.fill("input[name='emailRepeat']", Config.EMAIL)

            passport_keywords = ["Passport", "Reisepass", "Passeport"]
            if not self.smart_fill_by_label(page, passport_keywords, Config.PASSPORT):
                if page.locator("input[name='passportNumber']").is_visible():
                    page.fill("input[name='passportNumber']", Config.PASSPORT)
                elif page.locator("input[name='fields[0].content']").is_visible():
                    page.fill("input[name='fields[0].content']", Config.PASSPORT)

            clean_phone = Config.PHONE.replace("+", "00").replace(" ", "").strip()
            phone_keywords = ["Phone", "Telephone", "Telefon", "Mobile"]
            if not self.smart_fill_by_label(page, phone_keywords, clean_phone):
                if page.locator("input[name='phone']").is_visible():
                    page.fill("input[name='phone']", clean_phone)
                elif page.locator("input[name='fields[1].content']").is_visible():
                    page.fill("input[name='fields[1].content']", clean_phone)

            self.select_visa_smart(page)

            if not self.handle_captcha(page):
                return False
            
            logger.info("🚨 Submitting Form...")
            page.wait_for_timeout(5000)
            
            success, details = self.extract_and_verify_success(page)
            ts = self.get_timestamp()
            
            if success:
                logger.info(details)
                page.screenshot(path=f"success_{ts}.png")
                send_photo(f"success_{ts}.png", caption=details)
                return True
            else:
                logger.error("❌ Booking Failed (Error Page).")
                page.screenshot(path=f"error_{ts}.png")
                send_photo(f"error_{ts}.png", caption="❌ Booking Failed (See Image)")
                return False

        except Exception as e:
            logger.error(f"❌ Form Error: {e}")
            return False

    def run(self):
        with sync_playwright() as p:
            browser, context, page = self._setup_browser(p)
            
            logger.info(f"🚀 Sniper Active. Target: {Config.TARGET_URL}")
            send_alert("🚀 Diplo Sniper V17 (Hybrid Pro) Started...")
            
            while True:
                month_urls = self.get_month_urls()
                for url in month_urls:
                    try:
                        date_part = url.split("dateStr=")[1] if "dateStr=" in url else "Unknown"
                        logger.info(f"🔎 Scanning: {date_part}")
                        
                        try:
                            page.goto(url, wait_until="domcontentloaded")
                        except Exception as e:
                            logger.error(f"   -> Connection Error: {e}")
                            continue
                        
                        if not self.handle_captcha(page):
                            continue 

                        content = page.content()
                        if "Unfortunately, there are no appointments" in content or "keine Termine" in content:
                            time.sleep(random.uniform(2, 4)) 
                            continue
                        
                        # وضع الحصار (Siege Mode)
                        while True:
                            day_link = page.locator("a.arrow[href*='appointment_showDay']").first
                            if not day_link.is_visible():
                                logger.info("⚠️ Slot disappeared or taken.")
                                break 

                            logger.info("🔥 DAY FOUND! Attacking...")
                            send_alert(f"🔥 DAY FOUND! {date_part} - Attacking...")
                            
                            day_link.click()
                            if not self.handle_captcha(page):
                                logger.warning("   -> Captcha failed on Day. Retrying...")
                                page.go_back()
                                page.reload()
                                continue
                            
                            time_link = page.locator("a.arrow[href*='appointment_showForm']").first
                            if time_link.is_visible():
                                logger.info("⏰ TIME FOUND!")
                                time_link.click()
                                if not self.handle_captcha(page):
                                    logger.warning("   -> Captcha failed on Time. Retrying...")
                                    page.go_back()
                                    continue
                                
                                if self.fill_booking_form(page):
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
                        time.sleep(5)
                
                # نوم عشوائي لتجنب الحظر
                sleep_time = random.randint(self.settings['cycle_sleep_min'], self.settings['cycle_sleep_max'])
                logger.info(f"💤 Cycle done. Sleeping {sleep_time}s...")
                time.sleep(sleep_time)