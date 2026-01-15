import time
import random
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert

class DiploBot:
    def __init__(self):
        self.solver = CaptchaSolver()

    def handle_captcha_if_present(self, page):
        """
        دالة ذكية تفحص الصفحة الحالية، إذا وجدت كابتشا تقوم بحلها وتضغط استمرار.
        تعيد True إذا تم حل كابتشا، و False إذا لم تجد شيئاً.
        """
        try:
            # نبحث عن حقل إدخال الكابتشا (بناءً على الصورة عادة يكون اسمه captcha)
            # سنبحث عن أي حقل إدخال يقع بالقرب من صورة الكابتشا
            if page.locator("input[name='captcha']").is_visible() or page.locator("#captcha").is_visible():
                print("🚧 [Captcha Detected] Found a captcha checkpoint!")
                
                # 1. تحديد مكان الصورة
                # في موقع ديبلو، الصورة عادة تكون داخل div معين.
                # سنحاول التقاط الصورة بدقة
                captcha_element = page.locator("captcha_div_selector_here img").first # يحتاج تحديث السلكتور
                
                # إذا لم نجد الصورة بالسلكتور الدقيق، نأخذ لقطة لأي صورة في منطقة الكابتشا
                if not captcha_element.is_visible():
                    captcha_element = page.locator("img[src*='captcha']").first

                # 2. التقاط الصورة وحلها
                captcha_bytes = captcha_element.screenshot()
                code = self.solver.solve(captcha_bytes)
                print(f"🧩 Solution attempt: {code}")

                # 3. الكتابة في الحقل
                # نحاول ملء الحقل سواء كان اسمه captcha أو id الخاص به captcha
                try:
                    page.fill("input[name='captcha']", code)
                except:
                    page.fill("#captcha", code)

                # 4. الضغط على زر "Weiter" (استمرار)
                # نبحث عن زر يحتوي على كلمة Weiter
                page.click("input[value='Weiter'], button:has-text('Weiter')")
                
                # انتظار التحميل بعد الضغط
                page.wait_for_load_state("networkidle")
                return True
        except Exception as e:
            print(f"⚠️ Captcha check warning: {e}")
        
        return False

    def run(self):
        with sync_playwright() as p:
            # إعدادات المتصفح
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            print(f"🚀 Starting Sniper on: {Config.TARGET_URL}")
            
            while True:
                try:
                    # 1. الذهاب للرابط
                    page.goto(Config.TARGET_URL, timeout=60000)
                    
                    # --- نقطة تفتيش 1: كابتشا الدخول ---
                    self.handle_captcha_if_present(page)

                    # 2. فحص محتوى الصفحة (هل نحن في التقويم؟)
                    content = page.content()
                    
                    # التحقق من وجود رسالة "لا توجد مواعيد"
                    if "No appointments" in content or "keine Termine" in content:
                        print("💤 No slots. Sleeping...")
                        # انتظار عشوائي لتجنب الحظر
                        time.sleep(random.randint(40, 80))
                        continue
                    
                    # --- إذا وصلنا هنا، يعني الصفحة تغيرت (احتمال وجود موعد) ---
                    print("🔥 POTENTIAL SLOT DETECTED!")
                    
                    # البحث عن رابط الحجز (يختلف السلكتور حسب الصفحة)
                    # نبحث عن رابط يحتوي على كلمة حجز أو تاريخ
                    slot_link = page.locator("a:has-text('Book'), a:has-text('Termin buchen')").first
                    
                    if slot_link.is_visible():
                        slot_link.click()
                        print("point_right: Clicked slot!")
                        
                        # --- نقطة تفتيش 2: كابتشا ما بعد اختيار الموعد (إن وجدت) ---
                        self.handle_captcha_if_present(page)

                        # 3. تعبئة النموذج
                        print("📝 Filling form...")
                        page.wait_for_selector("#lastname", timeout=5000)
                        
                        page.fill("#lastname", Config.LAST_NAME)
                        page.fill("#firstname", Config.FIRST_NAME)
                        page.fill("#email", Config.EMAIL)
                        # قد يطلب تكرار الإيميل
                        if page.locator("#emailRepeat").is_visible():
                            page.fill("#emailRepeat", Config.EMAIL)
                        page.fill("#passportNumber", Config.PASSPORT)
                        page.fill("#phone", Config.PHONE)

                        # --- نقطة تفتيش 3: كابتشا الإرسال النهائي ---
                        # (أحياناً تكون الكابتشا في نفس صفحة البيانات في الأسفل)
                        self.handle_captcha_if_present(page)

                        # إرسال التنبيه (مع لقطة شاشة قبل الضغط النهائي)
                        page.screenshot(path="pre_submit.png")
                        send_alert("🚨 Form Filled! Check server for pre_submit.png")
                        
                        # الضغط على زر الحجز النهائي (Submit)
                        # page.click("input[type='submit']") 
                        
                        print("✅ Process Finished. Check Telegram.")
                        break
                    else:
                        print("🤔 Page changed but no slot link found. Retrying...")
                        self.handle_captcha_if_present(page) # ربما ظهرت كابتشا منعت ظهور الرابط

                except Exception as e:
                    print(f"❌ Error in loop: {e}")
                    time.sleep(5)