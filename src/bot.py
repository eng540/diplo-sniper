
import time
import random
import datetime
import os
import re
import json
import logging
import traceback
import tempfile
import hashlib
import base64
from pathlib import Path
from datetime import timedelta
from typing import Optional, Dict, List, Tuple
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# ========== إعدادات متقدمة ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'diplobot_{datetime.datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# استيراد الوحدات الخاصة
try:
    from .config import Config
    from .captcha import CaptchaSolver
    from .notifier import send_alert, send_photo
except ImportError:
    # للاختبار المباشر
    class Config:
        TARGET_URL = ""
        LAST_NAME = ""
        FIRST_NAME = ""
        EMAIL = ""
        PASSPORT = ""
        PHONE = ""
    
    class CaptchaSolver:
        def solve(self, image_bytes):
            return "test123"
    
    def send_alert(message):
        print(f"📢 Alert: {message}")
    
    def send_photo(path, caption):
        print(f"📷 Photo: {path} - {caption}")

class DiploBot:
    """الإصدار النهائي - جاهز للإنتاج"""
    
    def __init__(self):
        """تهيئة البوت مع إعدادات الإنتاج"""
        self.solver = CaptchaSolver()
        self.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        
        # إدارة الحالة
        self.state = {
            'running': True,
            'cycle_count': 0,
            'captcha_success': 0,
            'captcha_failed': 0,
            'pages_scanned': 0,
            'last_success': None
        }
        
        # التخزين المؤقت
        self.cache = {
            'captcha_attempts': {},
            'page_elements': {},
            'error_patterns': set()
        }
        
        # إعدادات الأداء
        self.settings = {
            'scan_months': 6,
            'max_captcha_refreshes': 5,
            'page_load_timeout': 30000,
            'captcha_timeout': 10000,
            'form_submit_timeout': 15000,
            'retry_delay': random.uniform(2, 5),
            'cycle_sleep': 60,
            'max_cycles': 1000,
            'stealth_mode': True
        }
        
        # أنماط الاكتشاف (محدثة بناءً على البيانات الفعلية)
        self.patterns = {
            'captcha_input': [
                "input[name='captchaText']",
                "input#appointment_captcha_month_captchaText",
                "input#appointment_captcha_day_captchaText",
                "input#appointment_newAppointmentForm_captchaText"
            ],
            'captcha_image': [
                "captcha > div",
                "div[id^='_']",
                "div[style*='background:white url']"
            ],
            'refresh_button': [
                "input[name^='action:appointment_refreshCaptcha']",
                "input[value*='Refresh']",
                "input[value*='Neues Bild']",
                "input[value*='Load another']"
            ],
            'submit_button': [
                "input[name^='action:appointment_showMonth']",
                "input[name^='action:appointment_showDay']",
                "input[name^='action:appointment_addAppointment']",
                "input[type='submit'][value*='Weiter']",
                "input[type='submit'][value*='Continue']",
                "input[type='submit'][value*='Submit']"
            ],
            'available_day': "a.arrow[href*='appointment_showDay']",
            'available_time': "a.arrow[href*='appointment_showForm']",
            'no_appointments': [
                "Unfortunately, there are no appointments",
                "keine Termine",
                "no appointments available"
            ],
            'booking_form': [
                "input[name='lastname']",
                "input[name='firstname']",
                "input[name='email']"
            ],
            # 🔥 أنماط النجاح المثبتة فعلياً
            'success_strong': [
                r"successfully booked an appointment",
                r"appointment number is \d{8,}",
                r"you have successfully booked",
                r"termin wurde erfolgreich gebucht",
                r"erfolgreich gebucht"
            ],
            'success_medium': [
                "confirmation email",
                "printout of the confirmation",
                "federal foreign office",
                "appointment for visa.*booked"
            ],
            'failure': [
                "error occurred while processing",
                "please try again",
                "invalid captcha",
                "session expired",
                "browser open for a very long time"
            ]
        }
        
        # قاعدة معرفة اختيار التأشيرة
        self.visa_knowledge = {
            'yemeni_student': {
                'primary': ['language course', 'student visa', 'study', 'student'],
                'secondary': ['schulbesuch', 'school visit', 'studium', 'university'],
                'alternatives': ['sprachkurs', 'language', 'education', 'learn german'],
                'avoid': ['au-pair', 'voluntary service', 'self employment', 'internship']
            },
            'score_weights': {
                'primary': 3,
                'secondary': 2,
                'alternatives': 1,
                'avoid': -5
            }
        }
        
        logger.info(f"🚀 DiploBot Diamond Edition {self.session_id} initialized")
    
    # ========== أدوات مساعدة ==========
    
    def get_timestamp(self) -> str:
        """توليد طابع زمني فريد"""
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def wait_random(self, min_seconds: float = 0.5, max_seconds: float = 2.0):
        """انتظار عشوائي لمحاكاة السلوك البشري"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def cleanup_temp_files(self):
        """تنظيف الملفات المؤقتة القديمة"""
        try:
            temp_dir = tempfile.gettempdir()
            for filename in os.listdir(temp_dir):
                if filename.startswith('diplobot_'):
                    filepath = os.path.join(temp_dir, filename)
                    if os.path.getmtime(filepath) < time.time() - 3600:
                        os.remove(filepath)
        except:
            pass
    
    # ========== خوارزمية الأشهر ==========
    
    def get_month_urls_intelligent(self) -> List[str]:
        """
        توليد روابط الأشهر القادمة بذكاء
        البدء من الشهر القادم مباشرة (ليس الشهر الحالي)
        """
        urls = []
        today = datetime.date.today()
        
        # تنظيف الرابط الأساسي
        base_url = Config.TARGET_URL
        if "request_locale=" not in base_url:
            base_url += "&request_locale=en" if "?" in base_url else "?request_locale=en"
        
        if "&dateStr=" in base_url:
            base_clean = base_url.split("&dateStr=")[0]
        else:
            base_clean = base_url
        
        # 🔥 إستراتيجية ذكية: البدء من الشهر القادم مباشرة
        for i in range(self.settings['scan_months']):
            # الشهر القادم = i + 1 (نتخطى الشهر الحالي)
            month_offset = i + 1
            
            # حساب التاريخ بدقة
            future_date = today + timedelta(days=30 * month_offset)
            
            # نستخدم يوم 15 من كل شهر
            date_str = f"15.{future_date.month:02d}.{future_date.year}"
            full_url = f"{base_clean}&dateStr={date_str}"
            urls.append(full_url)
            
            logger.debug(f"Generated URL for {date_str}")
        
        logger.info(f"📅 Scanning {len(urls)} months starting from next month")
        return urls
    
    # ========== نظام الكابتشا الذكي ==========
    
    def handle_captcha_production(self, page: Page, context: str = "unknown") -> bool:
        """
        نظام كابتشا إنتاجي ذكي:
        1. محاولة واحدة فقط لكل كابتشا
        2. تغيير فوري إذا كانت صعبة
        3. فلترة صارمة للأكواد
        """
        logger.info(f"🛡️ Handling captcha for {context}")
        
        for refresh_count in range(self.settings['max_captcha_refreshes']):
            captcha_path = None
            try:
                # 1. التحقق من وجود حقل الكابتشا
                if not self._is_captcha_visible(page):
                    logger.debug(f"No captcha field in {context}")
                    return True
                
                logger.info(f"Attempt {refresh_count + 1}/{self.settings['max_captcha_refreshes']}")
                
                # 2. التقاط صورة الكابتشا
                captcha_element = self._find_captcha_element(page)
                if not captcha_element:
                    logger.warning("Could not find captcha image")
                    return False
                
                # 3. حفظ الصورة مؤقتاً
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    captcha_element.screenshot(path=tmp.name)
                    captcha_path = tmp.name
                
                # 4. قراءة وحل الكابتشا
                with open(captcha_path, 'rb') as f:
                    image_bytes = f.read()
                
                code = self.solver.solve(image_bytes)
                
                # 5. 🔥 الفلترة الذكية (قبل المحاولة)
                if not self._validate_captcha_code_strict(code):
                    logger.warning(f"Invalid code pattern: {code}")
                    self._refresh_captcha_smart(page, context)
                    continue
                
                logger.info(f"Captcha solved: {code}")
                
                # 6. إدخال الكود
                page.fill("input[name='captchaText']", code)
                self.wait_random(0.3, 0.7)
                
                # 7. الإرسال (بطرق متعددة)
                if not self._submit_captcha_form(page):
                    page.keyboard.press("Enter")
                
                # 8. الانتظار الذكي للنتيجة
                result = self._wait_for_captcha_result(page)
                
                if result == "success":
                    self.state['captcha_success'] += 1
                    logger.info(f"✅ Captcha passed in {context}")
                    return True
                elif result == "invalid":
                    self.state['captcha_failed'] += 1
                    logger.warning("Invalid captcha code")
                else:
                    logger.warning("Captcha still present")
                
                # 9. تغيير الكابتشا للمحاولة التالية
                self._refresh_captcha_smart(page, context)
                
            except Exception as e:
                logger.error(f"Captcha error: {str(e)}")
                if "captcha_path" in locals() and captcha_path and os.path.exists(captcha_path):
                    os.unlink(captcha_path)
                self._refresh_captcha_smart(page, context)
            
            finally:
                if 'captcha_path' in locals() and captcha_path and os.path.exists(captcha_path):
                    os.unlink(captcha_path)
        
        logger.error(f"Failed all captcha attempts in {context}")
        return False
    
    def _validate_captcha_code_strict(self, code: str) -> bool:
        """فلترة صارمة لأكواد الكابتشا"""
        if not code or len(code) != 6:
            return False
        
        # يجب أن يكون خليط من أحرف وأرقام
        has_letter = bool(re.search(r'[a-zA-Z]', code))
        has_digit = bool(re.search(r'\d', code))
        
        if not (has_letter and has_digit):
            return False
        
        # تجنب الأنماط المنتظمة
        patterns_to_avoid = [
            r'^(\w)\1+$',  # مثل: aaaaaa
            r'^\d{6}$',    # أرقام فقط
            r'^[a-z]{6}$', # أحرف صغيرة فقط
            r'^[A-Z]{6}$', # أحرف كبيرة فقط
            r'^[0-9]{3}[a-z]{3}$',  # نمط منتظم
            r'^[a-z]{3}[0-9]{3}$',  # نمط منتظم
        ]
        
        for pattern in patterns_to_avoid:
            if re.match(pattern, code):
                return False
        
        return True
    
    def _refresh_captcha_smart(self, page: Page, context: str):
        """تغيير ذكي للكابتشا"""
        # أولاً: البحث عن زر تحديث
        for selector in self.patterns['refresh_button']:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=1000):
                    element.click()
                    self.wait_random(1.5, 2.5)
                    logger.debug("Refreshed captcha via button")
                    return
            except:
                continue
        
        # إذا لم يجد زر تحديث، أعد تحميل الصفحة
        logger.debug("Reloading page for new captcha")
        page.reload()
        page.wait_for_timeout(3000)
    
    def _wait_for_captcha_result(self, page: Page, timeout: int = 5000) -> str:
        """انتظار ذكي لنتيجة الكابتشا"""
        try:
            # انتظار اختفاء حقل الكابتشا
            page.wait_for_selector(
                "input[name='captchaText']",
                state="hidden",
                timeout=timeout
            )
            return "success"
        except:
            # التحقق من رسائل الخطأ
            error_texts = ["Wrong code", "Falscher Code", "Invalid", "Ungültig"]
            for text in error_texts:
                if page.locator(f"text={text}").is_visible(timeout=1000):
                    return "invalid"
            
            # إذا كان الحقل لا يزال ظاهراً
            if page.locator("input[name='captchaText']").is_visible(timeout=1000):
                return "visible"
            
            return "unknown"
    
    # ========== نظام ملء النموذج الذكي ==========
    
    def fill_form_production(self, page: Page) -> bool:
        """
        ملء النموذج بمعايير إنتاجية:
        - اختيار تأشيرة ذكي
        - معالجة أخطاء شاملة
        - توثيق كامل
        """
        logger.info("📝 Starting production form filling")
        
        try:
            # 1. التحقق من أننا في صفحة النموذج الصحيحة
            if not self._is_booking_form_visible(page):
                logger.error("Not on booking form page")
                return False
            
            # 2. تسجيل بدء العملية
            start_time = time.time()
            ts = self.get_timestamp()
            
            # 3. ملء الحقول الأساسية
            self._fill_basic_fields(page)
            self.wait_random(0.5, 1)
            
            # 4. تأكيد البريد الإلكتروني
            self._fill_email_confirmation(page)
            
            # 5. ملء جواز السفر والهاتف
            self._fill_passport_field(page)
            self._fill_phone_field(page)
            
            # 6. 🔥 اختيار نوع التأشيرة الذكي
            if not self._select_visa_type_intelligent(page):
                logger.warning("Using fallback visa selection")
                self._select_visa_fallback(page)
            
            # 7. كابتشا الإرسال النهائي
            logger.info("Solving final captcha...")
            if not self.handle_captcha_production(page, "final_submission"):
                logger.error("Final captcha failed")
                return False
            
            # 8. التوثيق: لقطة قبل الإرسال
            screenshot_path = f"form_pre_submit_{ts}.png"
            page.screenshot(path=screenshot_path)
            send_photo(screenshot_path, "📋 Form ready for submission")
            
            # 9. الإرسال النهائي
            logger.info("🚀 Submitting form...")
            self._submit_final_form(page)
            
            # 10. الانتظار للنتيجة
            page.wait_for_timeout(8000)
            
            # 11. التحقق من النتيجة
            result_path = f"result_{ts}.png"
            page.screenshot(path=result_path)
            
            # 12. 🔥 التحقق الدقيق من النجاح
            verification = self._verify_booking_result_comprehensive(page)
            
            if verification['success']:
                elapsed = time.time() - start_time
                success_msg = self._format_success_message(verification['details'])
                
                logger.info(f"✅ Booking successful in {elapsed:.1f}s")
                logger.info(success_msg)
                
                send_photo(result_path, success_msg)
                self.state['last_success'] = datetime.datetime.now()
                
                return True
            else:
                logger.warning(f"Booking uncertain: {verification['reason']}")
                send_photo(result_path, f"⚠️ Manual verification needed: {verification['reason']}")
                return False  # ❗ إرجاع False للسماح بإعادة المحاولة
            
        except Exception as e:
            logger.error(f"Form error: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _select_visa_type_intelligent(self, page: Page) -> bool:
        """اختيار ذكي لنوع التأشيرة"""
        try:
            # البحث عن قائمة التأشيرة
            select_locator = page.locator("select[name*='fields']").first
            if not select_locator.is_visible():
                logger.warning("Visa select not found")
                return False
            
            options = select_locator.locator("option").all()
            if len(options) <= 1:
                return False
            
            best_option = None
            best_score = -999
            
            # حساب النقاط لكل خيار
            for option in options:
                text = (option.text_content() or "").lower()
                value = option.get_attribute("value")
                
                if not value or value.strip() == "":
                    continue
                
                score = 0
                
                # النقاط الإيجابية
                for keyword in self.visa_knowledge['yemeni_student']['primary']:
                    if keyword in text:
                        score += self.visa_knowledge['score_weights']['primary']
                
                for keyword in self.visa_knowledge['yemeni_student']['secondary']:
                    if keyword in text:
                        score += self.visa_knowledge['score_weights']['secondary']
                
                for keyword in self.visa_knowledge['yemeni_student']['alternatives']:
                    if keyword in text:
                        score += self.visa_knowledge['score_weights']['alternatives']
                
                # النقاط السلبية
                for keyword in self.visa_knowledge['yemeni_student']['avoid']:
                    if keyword in text:
                        score += self.visa_knowledge['score_weights']['avoid']
                
                if score > best_score:
                    best_score = score
                    best_option = {'value': value, 'text': text, 'score': score}
            
            # اختيار أفضل خيار
            if best_option and best_score > 0:
                select_locator.select_option(value=best_option['value'])
                logger.info(f"Selected visa: {best_option['text']} (score: {best_score})")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Visa selection error: {e}")
            return False
    
    def _verify_booking_result_comprehensive(self, page: Page) -> Dict:
        """
        تحقق شامل من نتيجة الحجز
        يعتمد على الأنماط الفعلية من النجاح السابق
        """
        content = page.content()
        content_lower = content.lower()
        
        result = {
            'success': False,
            'confidence': 0.0,
            'details': {},
            'reason': ''
        }
        
        # 🔥 المؤشرات القوية (من النجاح الفعلي)
        strong_indicators_matched = 0
        
        for pattern in self.patterns['success_strong']:
            if re.search(pattern, content, re.IGNORECASE):
                strong_indicators_matched += 1
                logger.debug(f"Strong indicator matched: {pattern}")
        
        # المؤشرات المتوسطة
        medium_indicators_matched = 0
        
        for indicator in self.patterns['success_medium']:
            if indicator in content_lower:
                medium_indicators_matched += 1
                logger.debug(f"Medium indicator matched: {indicator}")
        
        # استخراج رقم الموعد (دليل قاطع)
        appointment_match = re.search(r'appointment number is (\d{8,})', content, re.IGNORECASE)
        if appointment_match:
            result['details']['appointment_number'] = appointment_match.group(1)
            strong_indicators_matched += 2  # وزن مضاعف
        
        # حساب درجة الثقة
        confidence = (strong_indicators_matched * 2) + medium_indicators_matched
        
        # تحديد النتيجة
        if confidence >= 3:
            result['success'] = True
            result['confidence'] = min(confidence / 10.0, 1.0)
            result['reason'] = f"Strong evidence ({confidence} points)"
            
            # استخراج التفاصيل الإضافية
            self._extract_booking_details(content, result['details'])
            
        elif confidence >= 1:
            result['success'] = True  # نجاح محتمل
            result['confidence'] = confidence / 10.0
            result['reason'] = f"Moderate evidence ({confidence} points)"
            
        else:
            result['success'] = False
            result['confidence'] = 0.0
            result['reason'] = "Insufficient evidence"
        
        # التحقق من الفشل
        for indicator in self.patterns['failure']:
            if indicator in content_lower:
                result['success'] = False
                result['reason'] = f"Failure indicator: {indicator}"
                break
        
        logger.info(f"Verification result: {result['success']} (confidence: {result['confidence']:.1%})")
        return result
    
    def _extract_booking_details(self, content: str, details: Dict):
        """استخراج تفاصيل الحجز من المحتوى"""
        # التاريخ والوقت
        datetime_match = re.search(r'(\d{2}\.\d{2}\.\d{4}) (?:at|um) (\d{1,2}:\d{2})', content, re.IGNORECASE)
        if datetime_match:
            details['date'] = datetime_match.group(1)
            details['time'] = datetime_match.group(2)
        
        # البريد الإلكتروني
        email_match = re.search(r'email address ([\w\.-]+@[\w\.-]+\.\w+)', content, re.IGNORECASE)
        if email_match:
            details['email'] = email_match.group(1)
        
        # الموقع
        location_match = re.search(r'in (\w+) on \d{2}\.\d{2}\.\d{4}', content, re.IGNORECASE)
        if location_match:
            details['location'] = location_match.group(1)
    
    # ========== الوظائف المساعدة ==========
    
    def _is_captcha_visible(self, page: Page) -> bool:
        """التحقق من وجود حقل الكابتشا"""
        for selector in self.patterns['captcha_input']:
            try:
                if page.locator(selector).first.is_visible(timeout=1000):
                    return True
            except:
                continue
        return False
    
    def _find_captcha_element(self, page: Page):
        """العثور على عنصر الكابتشا"""
        for selector in self.patterns['captcha_image']:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=1000):
                    return element
            except:
                continue
        return None
    
    def _submit_captcha_form(self, page: Page) -> bool:
        """إرسال نموذج الكابتشا"""
        for selector in self.patterns['submit_button']:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=1000):
                    element.click()
                    self.wait_random(0.5, 1)
                    return True
            except:
                continue
        return False
    
    def _is_booking_form_visible(self, page: Page) -> bool:
        """التحقق من صفحة النموذج"""
        for selector in self.patterns['booking_form']:
            try:
                if page.locator(selector).first.is_visible(timeout=2000):
                    return True
            except:
                continue
        return False
    
    def _fill_basic_fields(self, page: Page):
        """ملء الحقول الأساسية"""
        page.fill("input[name='lastname']", Config.LAST_NAME)
        self.wait_random(0.2, 0.5)
        page.fill("input[name='firstname']", Config.FIRST_NAME)
        self.wait_random(0.2, 0.5)
        page.fill("input[name='email']", Config.EMAIL)
    
    def _fill_email_confirmation(self, page: Page):
        """ملء تأكيد البريد الإلكتروني"""
        selectors = ["input[name='emailrepeat']", "input[name='emailRepeat']", "input[name='confirmEmail']"]
        for selector in selectors:
            try:
                if page.locator(selector).first.is_visible(timeout=1000):
                    page.fill(selector, Config.EMAIL)
                    break
            except:
                continue
    
    def _fill_passport_field(self, page: Page):
        """ملء حقل جواز السفر"""
        selectors = [
            "input[name='passportNumber']",
            "input[name='fields[0].content']",
            "input[id*='passport']"
        ]
        for selector in selectors:
            try:
                if page.locator(selector).first.is_visible(timeout=1000):
                    page.fill(selector, Config.PASSPORT)
                    return
            except:
                continue
    
    def _fill_phone_field(self, page: Page):
        """ملء حقل الهاتف"""
        selectors = [
            "input[name='phone']",
            "input[name='fields[1].content']",
            "input[id*='phone']",
            "input[name='telephone']"
        ]
        for selector in selectors:
            try:
                if page.locator(selector).first.is_visible(timeout=1000):
                    page.fill(selector, Config.PHONE)
                    return
            except:
                continue
    
    def _select_visa_fallback(self, page: Page):
        """الاختيار الافتراضي للتأشيرة"""
        try:
            select = page.locator("select").first
            if select.is_visible():
                select.select_option(index=1)
        except:
            pass
    
    def _submit_final_form(self, page: Page):
        """إرسال النموذج النهائي"""
        try:
            # البحث عن زر إرسال محدد
            submit_selectors = [
                "input[name^='action:appointment_addAppointment']",
                "input[type='submit'][value*='Submit']",
                "input[type='submit'][value*='Buchen']"
            ]
            
            for selector in submit_selectors:
                try:
                    if page.locator(selector).first.is_visible(timeout=2000):
                        page.locator(selector).first.click()
                        return
                except:
                    continue
            
            # استخدام Enter كبديل
            page.keyboard.press("Enter")
            
        except Exception as e:
            logger.error(f"Form submission error: {e}")
            page.keyboard.press("Enter")
    
    def _format_success_message(self, details: Dict) -> str:
        """تنسيق رسالة النجاح"""
        lines = ["✅ BOOKING CONFIRMED!"]
        
        if details.get('appointment_number'):
            lines.append(f"🔢 Number: {details['appointment_number']}")
        
        if details.get('date') and details.get('time'):
            lines.append(f"📅 Date: {details['date']} at {details['time']}")
        
        if details.get('email'):
            lines.append(f"📧 Email: {details['email']}")
        
        if details.get('location'):
            lines.append(f"📍 Location: {details['location']}")
        
        return "\n".join(lines)
    
    # ========== الدورة الرئيسية ==========
    
    def run_production(self):
        """
        الدورة الرئيسية للبيئة الإنتاجية
        - إدارة أخطاء شاملة
        - إعادة محاولة ذكية
        - مراقبة الأداء
        """
        logger.info("🚀 Starting DiploBot Production Cycle")
        
        # تنظيف الملفات القديمة
        self.cleanup_temp_files()
        
        # تشغيل البوت
        while self.state['running'] and self.state['cycle_count'] < self.settings['max_cycles']:
            self.state['cycle_count'] += 1
            cycle_start = time.time()
            
            logger.info(f"🔄 Cycle #{self.state['cycle_count']} started")
            
            try:
                with sync_playwright() as p:
                    # إعداد المتصفح مع ميزات التخفي
                    browser = self._setup_browser(p)
                    context = self._setup_context(browser)
                    page = context.new_page()
                    
                    # تطبيق إعدادات التخفي
                    self._apply_stealth_settings(page)
                    
                    logger.info("🌐 Browser ready - starting scan")
                    
                    # الحصول على روابط الأشهر
                    month_urls = self.get_month_urls_intelligent()
                    
                    for url in month_urls:
                        if not self.state['running']:
                            break
                        
                        try:
                            date_part = url.split("dateStr=")[-1] if "dateStr=" in url else "unknown"
                            logger.info(f"🔍 Scanning: {date_part}")
                            
                            # تحميل الصفحة
                            page.goto(url, wait_until="domcontentloaded", timeout=self.settings['page_load_timeout'])
                            self.state['pages_scanned'] += 1
                            
                            # معالجة كابتشا الدخول
                            if not self.handle_captcha_production(page, "initial_access"):
                                logger.warning(f"Skipping {date_part} due to captcha")
                                continue
                            
                            # التحقق من حالة "لا توجد مواعيد"
                            page_content = page.content()
                            if any(pattern in page_content for pattern in self.patterns['no_appointments']):
                                logger.debug(f"No appointments in {date_part}")
                                self.wait_random()
                                continue
                            
                            # البحث عن أيام متاحة
                            day_link = page.locator(self.patterns['available_day']).first
                            if day_link.is_visible():
                                logger.info(f"🔥 Available day found: {date_part}")
                                send_alert(f"🔥 Day available: {date_part}")
                                
                                day_link.click()
                                
                                # كابتشا اختيار اليوم
                                if not self.handle_captcha_production(page, "day_selection"):
                                    continue
                                
                                # البحث عن أوقات متاحة
                                time_link = page.locator(self.patterns['available_time']).first
                                if time_link.is_visible():
                                    logger.info("⏰ Available time found")
                                    
                                    time_link.click()
                                    
                                    # كابتشا اختيار الوقت
                                    if not self.handle_captcha_production(page, "time_selection"):
                                        continue
                                    
                                    # ملء النموذج
                                    if self.fill_form_production(page):
                                        logger.info("🎉 Booking completed successfully!")
                                        browser.close()
                                        return
                            
                        except Exception as e:
                            logger.error(f"Page error: {str(e)}")
                            self.wait_random(3, 5)
                            continue
                    
                    # إغلاق المتصفح بعد كل دورة
                    browser.close()
                    
            except Exception as e:
                logger.error(f"Cycle error: {str(e)}")
                logger.error(traceback.format_exc())
            
            # إحصاءات الدورة
            cycle_duration = time.time() - cycle_start
            logger.info(f"Cycle #{self.state['cycle_count']} completed in {cycle_duration:.1f}s")
            logger.info(f"Stats: {self.state['captcha_success']}/{self.state['captcha_success'] + self.state['captcha_failed']} captchas successful")
            
            # انتظار قبل الدورة التالية
            if self.state['running']:
                logger.info(f"💤 Sleeping for {self.settings['cycle_sleep']}s")
                time.sleep(self.settings['cycle_sleep'])
        
        logger.info("🏁 DiploBot finished all cycles")
    
    def _setup_browser(self, playwright) -> Browser:
        """إعداد المتصفح مع إعدادات الإنتاج"""
        return playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding"
            ]
        )
    
    def _setup_context(self, browser: Browser) -> BrowserContext:
        """إعداد السياق مع إعدادات واقعية"""
        return browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Europe/Berlin",
            permissions=["geolocation"],
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
        )
    
    def _apply_stealth_settings(self, page: Page):
        """تطبيق إعدادات التخفي"""
        # إخفاء WebDriver
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            Object.define