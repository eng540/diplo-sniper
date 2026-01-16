import time
import random
import datetime
import os
import re
import traceback
import tempfile
from playwright.sync_api import sync_playwright

# استيراد الوحدات الخاصة بك
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert, send_photo

class DiploBot:
    def __init__(self):
        self.solver = CaptchaSolver()
        # إضافة Locale لضمان اللغة الإنجليزية
        self.base_url_template = Config.TARGET_URL + "&request_locale=en"
        self.debug_photos_sent_today = 0
        self.last_debug_date = None
        print("💎 DiploBot Diamond Edition Initialized (Production Ready).")

    def get_timestamp(self):
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    def get_month_urls_dynamic(self):
        """
        توليد روابط الأشهر الـ 6 القادمة ديناميكياً وبدقة.
        """
        urls = []
        today = datetime.date.today()
        
        # تنظيف الرابط الأساسي
        if "&dateStr=" in self.base_url_template:
            base_clean = self.base_url_template.split("&dateStr=")[0]
        else:
            base_clean = self.base_url_template

        # فحص الأشهر الـ 6 القادمة
        for i in range(6):
            # حساب الشهر والسنة القادمين
            next_month_index = today.month + i
            
            future_year = today.year + ((next_month_index - 1) // 12)
            future_month = ((next_month_index - 1) % 12) + 1
            
            # نستخدم يوم 15 لضمان التواجد في منتصف الشهر
            date_str = f"15.{future_month:02d}.{future_year}"
            full_url = f"{base_clean}&dateStr={date_str}"
            urls.append(full_url)
            
        return urls

    def handle_captcha_smart(self, page, context="unknown", max_refreshes=5):
        """
        استراتيجية الكابتشا الذكية (مصححة):
        تقرأ الملف كبايتات لضمان التوافق مع ddddocr.
        """
        print(f"🎯 معالجة كابتشا ذكية ({context})")
        
        for refresh_attempt in range(max_refreshes):
            captcha_path = None
            try:
                # التحقق السريع من وجود الكابتشا
                if not page.locator("input[name='captchaText']").is_visible(timeout=2000):
                    return True
                
                # التقاط عنصر الكابتشا
                captcha_element = page.locator("captcha > div, div[id^='_']").first
                if not captcha_element.is_visible():
                    print("   ❌ لم يتم العثور على صورة الكابتشا")
                    return False 
                
                # انتظار ثبات الصورة
                page.wait_for_timeout(500)
                
                # حفظ مؤقت للصورة
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    captcha_element.screenshot(path=tmp.name)
                    captcha_path = tmp.name
                
                try:
                    # 🔥 قراءة الملف كبايتات (حل مشكلة padding)
                    with open(captcha_path, 'rb') as f:
                        image_bytes = f.read()

                    # حل الكابتشا
                    code = self.solver.solve(image_bytes)
                    
                    # الفلترة الذكية
                    is_valid, reason = self._validate_captcha_code(code)
                    
                    if not is_valid:
                        print(f"   ⚠️ كود مرفوض ({reason}). تحديث الصورة...")
                        self._refresh_captcha_immediately(page)
                        continue
                    
                    print(f"   🧩 تم الحل: {code}")
                    page.fill("input[name='captchaText']", code)
                    
                    # الضغط على Enter
                    page.keyboard.press("Enter")
                    
                    # الانتظار الذكي للنتيجة
                    try:
                        # ننتظر إما اختفاء الكابتشا (نجاح) أو ظهور رسالة خطأ/كابتشا جديدة
                        page.wait_for_function(
                            "() => !document.querySelector(\"input[name='captchaText']\")",
                            timeout=4000
                        )
                        print(f"   ✅ نجاح الكابتشا ({context})")
                        return True
                    except:
                        print(f"   ❌ الكود غير صحيح، المحاولة التالية...")
                        
                finally:
                    if captcha_path and os.path.exists(captcha_path):
                        os.unlink(captcha_path)
                
            except Exception as e:
                print(f"   ⚠️ خطأ أثناء المعالجة: {e}")
                if captcha_path and os.path.exists(captcha_path):
                        os.unlink(captcha_path)
                self._refresh_captcha_immediately(page)
        
        print(f"❌ فشل تجاوز الكابتشا بعد {max_refreshes} محاولات")
        return False

    def _validate_captcha_code(self, code):
        """قواعد قبول الكود"""
        if not code: return False, "فارغ"
        code = code.strip()
        if len(code) != 6: return False, f"الطول {len(code)}"
        if not re.match(r'^[a-zA-Z0-9]+$', code): return False, "رموز غير مسموحة"
        if len(set(code)) < 3: return False, "نمط متكرر"
        return True, "صالح"

    def _refresh_captcha_immediately(self, page):
        """النقر على أي زر تحديث متاح"""
        selectors = [
            "input[name^='action:appointment_refresh']",
            "a[href*='refreshCaptcha']", 
            "img[src*='refresh']"
        ]
        for sel in selectors:
            try:
                elem = page.locator(sel).first
                if elem.is_visible():
                    elem.click()
                    page.wait_for_timeout(1500)
                    return
            except: pass
        page.reload()

    def smart_fill_by_label(self, page, keywords, value):
        """التوجيه الدلالي: البحث عن الحقل عبر عنوانه"""
        try:
            for word in keywords:
                # XPath للبحث عن Label
                label = page.locator(f"//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{word.lower()}')]")
                if label.count() > 0:
                    target_id = label.first.get_attribute("for")
                    if target_id:
                        page.fill(f"#{target_id}", value)
                        print(f"   ✅ تم تعبئة الحقل المرتبط بـ '{word}'")
                        return True
            return False
        except Exception as e:
            print(f"   ⚠️ فشل الملء الذكي: {e}")
            return False

    def select_visa_type_smart(self, page):
        """نظام النقاط المرجحة لاختيار التأشيرة"""
        print("🎓 جاري اختيار نوع التأشيرة...")
        select = page.locator("select[name*='fields']").first
        if not select.is_visible(): return False
        
        options = select.locator("option").all()
        best_val = None
        best_score = -10
        
        score_rules = {
            'student': 5, 'studium': 5, 'study': 5,
            'language': 3, 'sprach': 3, 'course': 2, 'kurs': 2,
            'master': 4, 'bachelor': 4, 'university': 4,
            'au-pair': -5, 'internship': -2, 'voluntary': -5, 'employment': -2
        }

        for opt in options:
            txt = (opt.text_content() or "").lower()
            val = opt.get_attribute("value")
            if not val: continue
            
            score = 0
            for key, points in score_rules.items():
                if key in txt: score += points
            
            if score > best_score:
                best_score = score
                best_val = val
        
        if best_val and best_score > 0:
            select.select_option(value=best_val)
            print(f"   ✅ تم اختيار: (Score: {best_score})")
            return True
        
        try:
            select.select_option(index=1)
            print("   ⚠️ تم اختيار الخيار الثاني (افتراضي)")
            return True
        except: return False

    def fill_booking_form_enhanced(self, page):
        """تعبئة الاستمارة الكاملة (مع تحسين الانتظار)"""
        print("📝 بدء تعبئة الاستمارة...")
        try:
            # 1. الانتظار الذكي (زيادة المهلة إلى 60 ثانية)
            try:
                page.wait_for_selector(
                    "input[name='lastname'], input[name='captchaText'], div.error", 
                    state="visible", 
                    timeout=60000
                )
            except:
                print("❌ انتهت مهلة انتظار الاستمارة (الصفحة لم تفتح).")
                page.screenshot(path="timeout_debug.png")
                return False

            # 2. التحقق: هل عدنا للكابتشا؟
            if page.locator("input[name='captchaText']").is_visible():
                print("⚠️ يبدو أننا عدنا لصفحة الكابتشا (الكود السابق كان خاطئاً رغم القبول المبدئي).")
                return False 

            if not page.locator("input[name='lastname']").is_visible():
                print("❌ حقل الاسم غير موجود (قد يكون خطأ في تحميل الصفحة).")
                return False

            print("✅ تم تحميل الاستمارة بنجاح. جاري التعبئة...")

            # 3. الأسماء والإيميل
            page.fill("input[name='lastname']", Config.LAST_NAME)
            page.fill("input[name='firstname']", Config.FIRST_NAME)
            page.fill("input[name='email']", Config.EMAIL)
            
            email_repeat = page.locator("input[name*='emailrepeat'], input[name*='emailRepeat'], input[name*='confirm']").first
            if email_repeat.is_visible():
                email_repeat.fill(Config.EMAIL)

            # 4. الحقول الذكية (جواز / هاتف)
            passport_filled = self.smart_fill_by_label(page, ["Passport", "Reisepass", "Passeport", "No."], Config.PASSPORT)
            if not passport_filled:
                if page.locator("input[name*='passport']").count() > 0:
                    page.locator("input[name*='passport']").first.fill(Config.PASSPORT)
                elif page.locator("input[name='fields[0].content']").is_visible():
                    page.fill("input[name='fields[0].content']", Config.PASSPORT)

            phone_filled = self.smart_fill_by_label(page, ["Phone", "Telephone", "Telefon", "Mobile"], Config.PHONE)
            if not phone_filled:
                 if page.locator("input[name*='phone']").count() > 0:
                    page.locator("input[name*='phone']").first.fill(Config.PHONE)
                 elif page.locator("input[name='fields[1].content']").is_visible():
                    page.fill("input[name='fields[1].content']", Config.PHONE)

            # 5. اختيار التأشيرة
            self.select_visa_type_smart(page)

            # 6. كابتشا الإرسال النهائي
            if not self.handle_captcha_smart(page, "final_submit", max_refreshes=15):
                print("❌ فشل كابتشا الاستمارة")
                return False

            # 7. التوثيق قبل الإرسال
            ts = self.get_timestamp()
            screenshot_path = f"form_ready_{ts}.png"
            page.screenshot(path=screenshot_path)
            send_photo(screenshot_path, caption="🚨 Form Filled! Submitting...")

            # 8. الإرسال
            print("🚀 إرسال الطلب نهائياً...")
            page.keyboard.press("Enter")
            
            # 9. انتظار النتيجة (زيادة المهلة)
            page.wait_for_timeout(10000)
            result_path = f"result_{ts}.png"
            page.screenshot(path=result_path)
            
            # التحقق
            content = page.content().lower()
            if "success" in content or "termin" in content or "barcode" in content or "appointment" in content:
                print("✅✅✅ BOOKING SUCCESSFUL! ✅✅✅")
                send_photo(result_path, caption="✅ BOOKING CONFIRMED!")
                return True
            else:
                print("⚠️ نتيجة غير مؤكدة.")
                send_photo(result_path, caption="⚠️ Check Result Manually")
                return True

        except Exception as e:
            print(f"❌ خطأ في الاستمارة: {e}")
            traceback.print_exc()
            return False

    def run(self):
        """تشغيل البوت مع إعدادات التخفي (Stealth)"""
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            context.set_default_timeout(30000)
            
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            print(f"🚀 Sniper Active via Playwright. Target: {Config.TARGET_URL}")
            send_alert("🚀 DiploBot Started (Stealth Mode)")

            while True:
                try:
                    month_urls = self.get_month_urls_dynamic()
                    
                    for url in month_urls:
                        date_part = url.split("dateStr=")[-1]
                        print(f"🔎 فحص: {date_part}")
                        
                        try:
                            page.goto(url, wait_until="domcontentloaded")
                        except:
                            print("   ⚠️ Timeout loading page")
                            continue

                        if not self.handle_captcha_smart(page, "month_access"):
                            continue
                            
                        content = page.content()
                        if "Unfortunately, there are no appointments" in content or "keine Termine" in content:
                            time.sleep(random.uniform(1.5, 3.5))
                            continue
                        
                        day_link = page.locator("a.arrow[href*='appointment_showDay']").first
                        if day_link.is_visible():
                            print(f"🔥 تم العثور على يوم في {date_part}!")
                            send_alert(f"🔥 DAY OPEN: {date_part}")
                            
                            day_link.click()
                            if not self.handle_captcha_smart(page, "day_select"): continue
                            
                            time_link = page.locator("a.arrow[href*='appointment_showForm']").first
                            if time_link.is_visible():
                                print("⏰ وقت متاح! الدخول للاستمارة...")
                                time_link.click()
                                if not self.handle_captcha_smart(page, "time_select"): continue
                                
                                if self.fill_booking_form_enhanced(page):
                                    print("🎉 المهمة اكتملت.")
                                    return
                        else:
                            pass 

                except Exception as e:
                    print(f"⚠️ خطأ عام في الدورة: {e}")
                    time.sleep(10)
                
                print("💤 استراحة قصيرة (60 ثانية)...")
                time.sleep(60)

if __name__ == "__main__":
    bot = DiploBot()
    bot.run()