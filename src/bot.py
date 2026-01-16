import time
import random
import datetime
import os
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

class DiploBot:
    def __init__(self):
        self.solver = CaptchaSolver()
        # إضافة اللغة الإنجليزية للرابط لضمان ثبات النصوص
        self.base_url_template = Config.TARGET_URL + "&request_locale=en"

    def get_month_urls(self):
        """توليد روابط للأشهر الـ 6 القادمة"""
        urls = []
        today = datetime.date.today()
        # استخراج الرابط الأساسي النظيف
        if "&dateStr=" in self.base_url_template:
            base_clean = self.base_url_template.split("&dateStr=")[0]
        else:
            base_clean = self.base_url_template

        for i in range(6): 
            future_month = (today.month + i - 1) % 12 + 1
            future_year = today.year + ((today.month + i - 1) // 12)
            # يوم 15 لضمان منتصف الشهر
            date_str = f"15.{future_month:02d}.{future_year}"
            full_url = f"{base_clean}&dateStr={date_str}"
            urls.append(full_url)
        return urls

    def handle_captcha(self, page):
        """دالة الكابتشا الموحدة"""
        try:
            if page.locator("input[name='captchaText']").is_visible():
                print("🚧 [Captcha] Processing...")
                captcha_element = page.locator("captcha > div").first
                if captcha_element.is_visible():
                    page.wait_for_timeout(500) # انتظار تحميل الصورة
                    captcha_bytes = captcha_element.screenshot()
                    code = self.solver.solve(captcha_bytes)
                    print(f"🧩 Decoded: {code}")
                    page.fill("input[name='captchaText']", code)
                    
                    submit_btn = page.locator("input[type='submit'][name^='action:appointment']").first
                    if submit_btn.is_visible():
                        submit_btn.click()
                        page.wait_for_load_state("networkidle")
                        return True
        except Exception as e:
            print(f"⚠️ Captcha Error: {e}")
        return False

    def smart_fill_by_label(self, page, keywords, value):
        """الخوارزمية الذكية: البحث عن الحقل عبر ربط Label -> ID"""
        try:
            for word in keywords:
                # نبحث عن Label يحتوي على الكلمة المفتاحية
                label_locator = page.locator(f"//label[contains(text(), '{word}')]")
                
                if label_locator.count() > 0:
                    first_label = label_locator.first
                    target_id = first_label.get_attribute("for")
                    
                    if target_id:
                        print(f"   -> Linked '{word}' to Input ID: #{target_id}")
                        page.fill(f"#{target_id}", value)
                        return True
            return False
        except Exception as e:
            print(f"   -> Smart fill error for {keywords}: {e}")
            return False

    def fill_booking_form(self, page):
        print("📝 Filling Booking Form (Label-ID Strategy)...")
        try:
            # 1. الحقول الثابتة
            page.fill("input[name='lastname']", Config.LAST_NAME)
            page.fill("input[name='firstname']", Config.FIRST_NAME)
            page.fill("input[name='email']", Config.EMAIL)
            
            if page.locator("input[name='emailrepeat']").is_visible():
                page.fill("input[name='emailrepeat']", Config.EMAIL)
            elif page.locator("input[name='emailRepeat']").is_visible():
                page.fill("input[name='emailRepeat']", Config.EMAIL)

            # 2. الحقول الديناميكية (الجواز)
            passport_keywords = ["Passport", "Reisepass", "Passeport"]
            if not self.smart_fill_by_label(page, passport_keywords, Config.PASSPORT):
                print("   ⚠️ Label search failed for Passport, trying fallback...")
                if page.locator("input[name='passportNumber']").is_visible():
                    page.fill("input[name='passportNumber']", Config.PASSPORT)
                elif page.locator("input[name='fields[0].content']").is_visible():
                    page.fill("input[name='fields[0].content']", Config.PASSPORT)

            # 3. الحقول الديناميكية (الهاتف)
            phone_keywords = ["Phone", "Telephone", "Telefon", "Mobile", "Handy"]
            if not self.smart_fill_by_label(page, phone_keywords, Config.PHONE):
                print("   ⚠️ Label search failed for Phone, trying fallback...")
                if page.locator("input[name='phone']").is_visible():
                    page.fill("input[name='phone']", Config.PHONE)
                elif page.locator("input[name='fields[1].content']").is_visible():
                    page.fill("input[name='fields[1].content']", Config.PHONE)

            # 4. القوائم المنسدلة
            selects = page.locator("select").all()
            for select in selects:
                if select.is_visible():
                    try:
                        select.select_option(index=1)
                        print("   -> Dropdown option selected.")
                    except:
                        pass

            # 5. كابتشا الإرسال
            self.handle_captcha(page)
            
            # 6. الإرسال والتوثيق
            print("🚨 FORM READY! Saving screenshot...")
            screenshot_path = "final_filled.png"
            page.screenshot(path=screenshot_path)
            
            # إرسال الصورة لتيليجرام
            send_photo(screenshot_path, caption="🚨 Attempting to submit form...")
            
            # ============================================================
            # التنفيذ الحقيقي (تم تفعيله)
            # ============================================================
            submit_btn = page.locator("input[type='submit'][name^='action:appointment_add']")
            if submit_btn.is_visible():
                submit_btn.click()
                print("✅ SUBMIT BUTTON CLICKED!")
                
                # ننتظر قليلاً لنرى نتيجة الحجز
                page.wait_for_timeout(5000)
                page.screenshot(path="result.png")
                send_photo("result.png", caption="✅ Booking Result (Check Image)")
                return True
            else:
                send_alert("❌ Submit button not found!")
                return False

        except Exception as e:
            print(f"❌ Form Error: {e}")
            send_alert(f"❌ Form Error: {e}")
            return False

    def run(self):
        with sync_playwright() as p:
            # تشغيل المتصفح
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            # زيادة وقت الانتظار الافتراضي
            context.set_default_timeout(30000)
            page = context.new_page()
            
            print(f"🚀 Sniper Active. Target: {Config.TARGET_URL}")
            send_alert("🚀 Diplo Sniper Started & Watching...")
            
            while True:
                month_urls = self.get_month_urls()
                for url in month_urls:
                    try:
                        # طباعة التاريخ فقط للمتابعة
                        date_part = url.split("dateStr=")[1] if "dateStr=" in url else "Unknown"
                        print(f"🔎 Scanning: {date_part}")
                        
                        try:
                            page.goto(url, wait_until="domcontentloaded")
                        except:
                            print("   -> Timeout loading page, skipping...")
                            continue
                        
                        self.handle_captcha(page)
                        
                        content = page.content()
                        if "Unfortunately, there are no appointments" in content or "keine Termine" in content:
                            # انتظار عشوائي قصير
                            time.sleep(random.uniform(2, 4)) 
                            continue
                        
                        # البحث عن رابط اليوم
                        day_link = page.locator("a.arrow[href*='appointment_showDay']").first
                        if day_link.is_visible():
                            print("🔥 DAY FOUND!")
                            send_alert(f"🔥 DAY FOUND! {date_part}")
                            day_link.click()
                            self.handle_captcha(page)
                            
                            # البحث عن رابط الوقت
                            time_link = page.locator("a.arrow[href*='appointment_showForm']").first
                            if time_link.is_visible():
                                print("⏰ TIME FOUND!")
                                time_link.click()
                                self.handle_captcha(page)
                                
                                if self.fill_booking_form(page):
                                    print("✅ DONE. Bot stopping to prevent spam.")
                                    send_alert("✅ Bot finished successfully.")
                                    return
                    except Exception as e:
                        print(f"⚠️ Loop Error: {e}")
                        time.sleep(5)
                
                print("💤 Cycle done. Sleeping 60s...")
                time.sleep(60)