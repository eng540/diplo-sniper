import time
import random
import datetime
import os
import traceback
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
            # يوم 15 آمن لأنه موجود في كل الشهور
            date_str = f"15.{future_month:02d}.{future_year}"
            full_url = f"{base_clean}&dateStr={date_str}"
            urls.append(full_url)
        return urls

    def handle_captcha(self, page, max_retries=3):
        """
        استراتيجية كابتشا متقدمة مع إعادة المحاولة والتحقق
        """
        for attempt in range(max_retries):
            try:
                # التحقق من وجود الكابتشا
                if not page.locator("input[name='captchaText']").is_visible():
                    return True # لا توجد كابتشا، ممتاز

                print(f"🚧 [Captcha] Attempt {attempt+1}/{max_retries}...")
                captcha_element = page.locator("captcha > div").first
                
                if captcha_element.is_visible():
                    page.wait_for_timeout(1000) # استقرار
                    captcha_bytes = captcha_element.screenshot()
                    code = self.solver.solve(captcha_bytes)
                    print(f"🧩 Decoded: {code}")
                    
                    page.fill("input[name='captchaText']", code)
                    
                    # محاولة النقر أولاً (الأكثر موثوقية)
                    submit_btn = page.locator("input[type='submit'][name^='action:appointment']").first
                    if submit_btn.is_visible():
                        submit_btn.click()
                    else:
                        # خطة بديلة: Enter
                        page.keyboard.press("Enter")
                    
                    # انتظار النتيجة
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except:
                        pass # تجاوز التايم أوت

                    # التحقق: هل ما زلنا في صفحة الكابتشا؟
                    if page.locator("input[name='captchaText']").is_visible():
                        print("❌ Captcha failed (Page didn't change). Retrying...")
                        # التحقق من وجود رسالة خطأ
                        if page.locator(".error, .errormsg").is_visible():
                            print("   -> Error message detected.")
                        continue # إعادة المحاولة
                    else:
                        print("✅ Captcha passed.")
                        return True

            except Exception as e:
                print(f"⚠️ Captcha Error: {e}")
                traceback.print_exc()
        
        print("❌ Failed to solve captcha after retries.")
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
        except Exception as e:
            print(f"Smart fill error: {e}")
            return False

    def verify_success(self, page):
        """التحقق الحقيقي من النجاح"""
        content = page.content().lower()
        success_keywords = ["booking successful", "appointment confirmed", "terminbestätigung", "barcode", "ref-id"]
        for keyword in success_keywords:
            if keyword in content:
                return True
        return False

    def fill_booking_form(self, page):
        print("📝 Filling Booking Form...")
        try:
            # التأكد من أننا في صفحة النموذج
            if not page.locator("input[name='lastname']").is_visible():
                print("❌ Not on form page!")
                return False

            page.fill("input[name='lastname']", Config.LAST_NAME)
            page.fill("input[name='firstname']", Config.FIRST_NAME)
            page.fill("input[name='email']", Config.EMAIL)
            
            if page.locator("input[name='emailrepeat']").is_visible():
                page.fill("input[name='emailrepeat']", Config.EMAIL)
            elif page.locator("input[name='emailRepeat']").is_visible():
                page.fill("input[name='emailRepeat']", Config.EMAIL)

            # تعبئة ذكية
            passport_keywords = ["Passport", "Reisepass", "Passeport"]
            if not self.smart_fill_by_label(page, passport_keywords, Config.PASSPORT):
                # Fallback
                if page.locator("input[name='passportNumber']").is_visible():
                    page.fill("input[name='passportNumber']", Config.PASSPORT)
                elif page.locator("input[name='fields[0].content']").is_visible():
                    page.fill("input[name='fields[0].content']", Config.PASSPORT)

            phone_keywords = ["Phone", "Telephone", "Telefon", "Mobile"]
            if not self.smart_fill_by_label(page, phone_keywords, Config.PHONE):
                if page.locator("input[name='phone']").is_visible():
                    page.fill("input[name='phone']", Config.PHONE)
                elif page.locator("input[name='fields[1].content']").is_visible():
                    page.fill("input[name='fields[1].content']", Config.PHONE)

            # القوائم المنسدلة
            selects = page.locator("select").all()
            for select in selects:
                if select.is_visible():
                    try:
                        select.select_option(index=1)
                    except:
                        pass

            # كابتشا الإرسال
            if not self.handle_captcha(page, max_retries=5):
                print("❌ Failed final captcha.")
                return False
            
            print("🚨 FORM READY! Submitting...")
            ts = self.get_timestamp()
            page.screenshot(path=f"form_filled_{ts}.png")
            send_photo(f"form_filled_{ts}.png", caption="🚨 Submitting Form...")
            
            # محاولة الإرسال (زر + Enter)
            submit_btn = page.locator("input[type='submit'][name^='action:appointment_add']")
            if submit_btn.is_visible():
                submit_btn.click()
            else:
                page.keyboard.press("Enter")
            
            # انتظار النتيجة والتحقق
            page.wait_for_timeout(5000)
            page.screenshot(path=f"result_{ts}.png")
            
            if self.verify_success(page):
                print("✅ BOOKING CONFIRMED!")
                send_photo(f"result_{ts}.png", caption="✅ BOOKING SUCCESSFUL!")
                return True
            else:
                print("⚠️ Booking verification failed (Check image).")
                send_photo(f"result_{ts}.png", caption="⚠️ Booking Result (Unverified)")
                # قد يكون نجح لكننا لم نلتقط الكلمة المفتاحية، لذا نعتبره نصف نجاح ولا نوقف البوت فوراً إلا إذا تأكدنا
                return True # نعتبره تم للخروج من الحلقة، المستخدم سيقرر

        except Exception as e:
            print(f"❌ Form Error: {e}")
            traceback.print_exc()
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
            send_alert("🚀 Diplo Sniper V2 (Professional) Started...")
            
            while True:
                month_urls = self.get_month_urls()
                for url in month_urls:
                    try:
                        date_part = url.split("dateStr=")[1] if "dateStr=" in url else "Unknown"
                        print(f"🔎 Scanning: {date_part}")
                        
                        try:
                            page.goto(url, wait_until="domcontentloaded")
                        except Exception as e:
                            print(f"   -> Timeout/Error loading page: {e}")
                            continue
                        
                        # معالجة الكابتشا مع إعادة المحاولة
                        if not self.handle_captcha(page):
                            continue # فشل الكابتشا، انتقل للشهر التالي

                        content = page.content()
                        if "Unfortunately, there are no appointments" in content or "keine Termine" in content:
                            time.sleep(random.uniform(2, 4)) 
                            continue
                        
                        # البحث عن يوم
                        day_link = page.locator("a.arrow[href*='appointment_showDay']").first
                        if day_link.is_visible():
                            print("🔥 DAY FOUND!")
                            send_alert(f"🔥 DAY FOUND! {date_part}")
                            day_link.click()
                            
                            if not self.handle_captcha(page): continue
                            
                            time_link = page.locator("a.arrow[href*='appointment_showForm']").first
                            if time_link.is_visible():
                                print("⏰ TIME FOUND!")
                                time_link.click()
                                
                                if not self.handle_captcha(page): continue
                                
                                if self.fill_booking_form(page):
                                    print("✅ DONE. Exiting.")
                                    return
                        else:
                            # تشخيص الفشل الصامت
                            if not self.debug_photo_sent and not page.locator("input[name='captchaText']").is_visible():
                                ts = self.get_timestamp()
                                print("📸 Sending Debug Screenshot...")
                                page.screenshot(path=f"debug_{ts}.png")
                                send_photo(f"debug_{ts}.png", caption=f"⚠️ Debug: Calendar View {date_part}")
                                self.debug_photo_sent = True

                    except Exception as e:
                        print(f"⚠️ Loop Error: {e}")
                        traceback.print_exc() # طباعة الخطأ كاملاً
                        time.sleep(5)
                
                print("💤 Cycle done. Sleeping 60s...")
                time.sleep(60)