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
        self.base_url_template = Config.TARGET_URL + "&request_locale=en"
        self.debug_photo_sent = False 

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

    def handle_captcha(self, page):
        try:
            if page.locator("input[name='captchaText']").is_visible():
                print("🚧 [Captcha] Found. Solving...")
                captcha_element = page.locator("captcha > div").first
                if captcha_element.is_visible():
                    page.wait_for_timeout(1000)
                    captcha_bytes = captcha_element.screenshot()
                    code = self.solver.solve(captcha_bytes)
                    print(f"🧩 Decoded: {code}")
                    
                    # الكتابة ثم ضغط Enter
                    page.fill("input[name='captchaText']", code)
                    page.keyboard.press("Enter")
                    
                    print("⏳ Enter pressed. Waiting...")
                    time.sleep(5) # انتظار التحميل
                    return True
        except Exception as e:
            print(f"⚠️ Captcha Error: {e}")
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

    def fill_booking_form(self, page):
        print("📝 Filling Booking Form...")
        try:
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

            phone_keywords = ["Phone", "Telephone", "Telefon", "Mobile"]
            if not self.smart_fill_by_label(page, phone_keywords, Config.PHONE):
                if page.locator("input[name='phone']").is_visible():
                    page.fill("input[name='phone']", Config.PHONE)
                elif page.locator("input[name='fields[1].content']").is_visible():
                    page.fill("input[name='fields[1].content']", Config.PHONE)

            selects = page.locator("select").all()
            for select in selects:
                if select.is_visible():
                    try:
                        select.select_option(index=1)
                    except:
                        pass

            self.handle_captcha(page)
            
            print("🚨 FORM READY! submitting...")
            page.screenshot(path="final_filled.png")
            send_photo("final_filled.png", caption="🚨 Submitting Form...")
            
            # محاولة الإرسال بـ Enter أيضاً
            page.keyboard.press("Enter")
            
            page.wait_for_timeout(5000)
            page.screenshot(path="result.png")
            send_photo("result.png", caption="✅ Booking Result")
            return True

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
            send_alert("🚀 Diplo Sniper Restarted (Enter Key Mode)...")
            
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
                        
                        self.handle_captcha(page)
                        
                        # فحص هل تجاوزنا الكابتشا؟
                        # إذا كنا لا نزال نرى حقل الكابتشا، فهذا يعني الفشل
                        if page.locator("input[name='captchaText']").is_visible():
                            print("   -> Captcha loop detected (Wrong code?). Skipping...")
                            continue

                        # --- منطقة التشخيص ---
                        day_link = page.locator("a.arrow[href*='appointment_showDay']").first
                        
                        if day_link.is_visible():
                            print("🔥 DAY FOUND!")
                            send_alert(f"🔥 DAY FOUND! {date_part}")
                            day_link.click()
                            self.handle_captcha(page)
                            
                            time_link = page.locator("a.arrow[href*='appointment_showForm']").first
                            if time_link.is_visible():
                                print("⏰ TIME FOUND!")
                                time_link.click()
                                self.handle_captcha(page)
                                if self.fill_booking_form(page):
                                    print("✅ DONE.")
                                    return
                        else:
                            # إرسال صورة فقط إذا لم نكن في صفحة الكابتشا
                            if not self.debug_photo_sent and not page.locator("input[name='captchaText']").is_visible():
                                print("📸 Sending Debug Screenshot...")
                                page.screenshot(path="debug_view.png")
                                send_photo("debug_view.png", caption=f"⚠️ Debug: Calendar View {date_part}")
                                self.debug_photo_sent = True

                    except Exception as e:
                        print(f"⚠️ Loop Error: {e}")
                        time.sleep(5)
                
                print("💤 Cycle done. Sleeping 60s...")
                time.sleep(60)