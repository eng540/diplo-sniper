import time
import random
import datetime
import os
import traceback
import re
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

class DiploBot:
    def __init__(self):
        self.solver = CaptchaSolver()
        self.base_url_template = Config.TARGET_URL + "&request_locale=en"
        self.debug_photo_sent = False

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

    def refresh_captcha(self, page):
        """تحديث صورة الكابتشا للحصول على واحدة أسهل"""
        try:
            print("   -> 🔄 Refreshing Captcha Image...")
            refresh_btn = page.locator("input[name^='action:appointment_refreshCaptcha']").first
            if refresh_btn.is_visible():
                refresh_btn.click()
                page.wait_for_timeout(2500) # انتظار التحميل
                return True
        except:
            pass
        return False

    def handle_captcha(self, page, max_retries=10):
        """استراتيجية: الحل السريع أو التغيير الفوري"""
        for attempt in range(max_retries):
            try:
                if not page.locator("input[name='captchaText']").is_visible():
                    return True 

                print(f"🚧 [Captcha] Attempt {attempt+1}...")
                captcha_element = page.locator("captcha > div").first
                
                if captcha_element.is_visible():
                    page.wait_for_timeout(800)
                    captcha_bytes = captcha_element.screenshot()
                    code = self.solver.solve(captcha_bytes)
                    
                    # 1. فلترة الطول: إذا خطأ، حدث الصورة فوراً
                    if len(code) != 6:
                        print(f"⚠️ Invalid length ({len(code)}). Refreshing...")
                        self.refresh_captcha(page)
                        continue
                    
                    print(f"🧩 Decoded: {code}")
                    page.fill("input[name='captchaText']", code)
                    
                    print("   -> Pressing Enter...")
                    page.keyboard.press("Enter")
                    
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except:
                        pass

                    # 2. إذا بقينا في نفس الصفحة، حدث الصورة فوراً
                    if page.locator("input[name='captchaText']").is_visible():
                        print("❌ Captcha failed. Refreshing image...")
                        self.refresh_captcha(page)
                        continue 
                    else:
                        print("✅ Captcha passed.")
                        return True

            except Exception as e:
                print(f"⚠️ Captcha Error: {e}")
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

    def extract_and_verify_success(self, page):
        """
        التحقق الصارم واستخراج البيانات
        """
        content = page.content()
        
        # 1. التحقق من الفشل الصريح
        if "error occurred" in content.lower() or "ref-id" in content.lower():
            print("❌ FAILED: Error Page Detected.")
            return False, None

        # 2. التحقق من النجاح واستخراج البيانات
        if "appointment number" in content.lower() or "successfully booked" in content.lower():
            details = "✅ BOOKING CONFIRMED!\n"
            
            # استخراج رقم الحجز
            match_num = re.search(r"Appointment number is\s+(\d+)", content, re.IGNORECASE)
            if match_num:
                details += f"🆔 App Num: {match_num.group(1)}\n"
            
            # استخراج التاريخ
            match_date = re.search(r"(\d{2}\.\d{2}\.\d{4})", content)
            if match_date:
                details += f"📅 Date: {match_date.group(1)}\n"

            # استخراج الوقت
            match_time = re.search(r"(\d{2}:\d{2})", content)
            if match_time:
                details += f"⏰ Time: {match_time.group(1)}\n"
            
            details += f"👤 Name: {Config.FIRST_NAME} {Config.LAST_NAME}"
            return True, details
            
        return False, None

    def fill_booking_form(self, page):
        print("📝 Filling Booking Form...")
        try:
            if not page.locator("input[name='lastname']").is_visible():
                return False

            # تعبئة الحقول
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

            # الاختيار الذكي للغرض
            target_keywords = ["student", "language course", "studium", "university", "yemeni national"]
            selects = page.locator("select").all()
            for select in selects:
                if select.is_visible():
                    found = False
                    try:
                        for option in select.locator("option").all():
                            txt = option.text_content()
                            if txt and any(k in txt.lower() for k in target_keywords):
                                select.select_option(value=option.get_attribute("value"))
                                found = True
                                break
                    except: pass
                    if not found:
                        try: select.select_option(index=1)
                        except: pass

            # كابتشا الإرسال
            if not self.handle_captcha(page, max_retries=10):
                return False
            
            print("🚨 Submitting...")
            page.keyboard.press("Enter")
            page.wait_for_timeout(5000)
            
            # التحقق الصارم
            success, details = self.extract_and_verify_success(page)
            ts = self.get_timestamp()
            
            if success:
                print(details)
                page.screenshot(path=f"success_{ts}.png")
                send_photo(f"success_{ts}.png", caption=details)
                return True
            else:
                print("❌ Booking Failed (Error Page).")
                page.screenshot(path=f"error_{ts}.png")
                send_photo(f"error_{ts}.png", caption="❌ Booking Failed (See Image)")
                return False

        except Exception as e:
            print(f"❌ Form Error: {e}")
            return False

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            context.set_default_timeout(60000)
            page = context.new_page()
            
            print(f"🚀 Sniper Active. Target: {Config.TARGET_URL}")
            send_alert("🚀 Diplo Sniper V8 (Siege Mode) Started...")
            
            while True:
                month_urls = self.get_month_urls()
                for url in month_urls:
                    try:
                        date_part = url.split("dateStr=")[1] if "dateStr=" in url else "Unknown"
                        print(f"🔎 Scanning: {date_part}")
                        
                        try:
                            page.goto(url, wait_until="domcontentloaded")
                        except:
                            continue
                        
                        if not self.handle_captcha(page):
                            continue 

                        content = page.content()
                        if "Unfortunately, there are no appointments" in content or "keine Termine" in content:
                            time.sleep(random.uniform(2, 4)) 
                            continue
                        
                        # --- وضع الحصار (Siege Mode) ---
                        # إذا وجدنا يوماً، لا نخرج من هذا الرابط حتى نحجز أو يختفي
                        while True:
                            day_link = page.locator("a.arrow[href*='appointment_showDay']").first
                            if not day_link.is_visible():
                                print("⚠️ Slot disappeared or taken.")
                                break # نخرج من حلقة الحصار ونكمل المسح

                            print("🔥 DAY FOUND! Attacking...")
                            send_alert(f"🔥 DAY FOUND! {date_part} - Attacking...")
                            
                            day_link.click()
                            
                            if not self.handle_captcha(page):
                                print("   -> Captcha failed on Day. Retrying same slot...")
                                page.go_back() # نعود للخلف لنحاول مجدداً
                                page.reload()
                                continue
                            
                            time_link = page.locator("a.arrow[href*='appointment_showForm']").first
                            if time_link.is_visible():
                                print("⏰ TIME FOUND!")
                                time_link.click()
                                
                                if not self.handle_captcha(page):
                                    print("   -> Captcha failed on Time. Retrying...")
                                    page.go_back()
                                    continue
                                
                                if self.fill_booking_form(page):
                                    print("✅ DONE. Exiting.")
                                    return
                                else:
                                    print("❌ Form submission failed. Retrying slot...")
                                    # نعود للبداية لمحاولة اقتناص الموعد مرة أخرى
                                    page.goto(url)
                                    continue
                            else:
                                print("⚠️ Day open but time slots gone/hidden.")
                                break

                    except Exception as e:
                        print(f"⚠️ Loop Error: {e}")
                        time.sleep(5)
                
                print("💤 Cycle done. Sleeping 60s...")
                time.sleep(60)