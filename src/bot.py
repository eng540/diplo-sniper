"""
King Sniper v11.0.0 - النسخة النهائية المحسنة للإنتاج
الإصدار: 11.0.0 (Production Ready - Enhanced)
الوصف: نظام حجز مواعيد دبلوماسي فائق السرعة والأمان
الميزات: حقن DOM مباشر، مزامنة NTP، إدارة جلسات ذكية
التاريخ: 2024
"""

import time
import random
import datetime
import logging
import re
import sys
import json
from typing import Optional, List, Dict, Tuple, Any
from urllib.parse import urljoin, urlparse
from datetime import timedelta

import pytz
import ntplib
from playwright.sync_api import sync_playwright, Page, BrowserContext, Browser

# ==================== IMPORTS الأساسية ====================
try:
    from src.config import Config
    from src.captcha import CaptchaSolver
    from src.notifier import send_alert, send_photo
except ImportError as e:
    print(f"❌ خطأ في استيراد التكوين: {e}")
    print("⚠️ تأكد من وجود ملفات: config.py, captcha.py, notifier.py")
    sys.exit(1)

# ==================== إعدادات السجل ====================
logging.basicConfig(
    level=getattr(Config, 'LOG_LEVEL', 'INFO'),
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('king_sniper.log') if getattr(Config, 'ENABLE_FILE_LOG', False) 
        else logging.NullHandler()
    ]
)
logger = logging.getLogger("KingSniper")

# ==================== فئات البيانات ====================
class FieldMapping:
    """تمثيل تعيين الحقل الديناميكي"""
    
    def __init__(self, field_type: str, patterns: List[str], config_value: str):
        self.field_type = field_type
        self.patterns = patterns
        self.value = config_value
        self.found_name = None
        self.found_selector = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'field_type': self.field_type,
            'patterns': self.patterns,
            'found_name': self.found_name,
            'found_selector': self.found_selector,
            'mapped': self.found_name is not None
        }

# ==================== الفئة الرئيسية ====================
class KingSniper:
    """
    النسخة النهائية المحسنة مع الحقن المباشر ومزامنة الوقت
    - سرعة فائقة بحقن DOM مباشر
    - دقة توقيت مع مزامنة NTP
    - إدارة جلسات ذكية
    """
    
    def __init__(self):
        """تهيئة النظام مع التحقق من التكوين"""
        self._validate_config()
        
        # المكونات الأساسية
        self.solver = CaptchaSolver()
        self.base_url = self._prepare_base_url(Config.TARGET_URL)
        self.timezone = pytz.timezone(getattr(Config, 'TIMEZONE', 'Asia/Aden'))
        
        # مزامنة الوقت
        self.ntp_offset = 0.0
        self.time_synced = False
        self._sync_ntp_time()
        
        # إعدادات الأداء
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
        ]
        
        # حالة النظام
        self.consecutive_errors = 0
        self.session_id = f"king_{int(time.time())}_{random.randint(1000, 9999)}"
        self.start_time = datetime.datetime.now()
        self.is_poisoned = False
        self.current_user_agent = random.choice(self.user_agents)
        
        # إحصاءات متقدمة
        self.stats = {
            'scans': 0,
            'captchas_solved': 0,
            'captchas_failed': 0,
            'forms_filled': 0,
            'errors': 0,
            'success': False,
            'poisoned_sessions': 0,
            'dom_injections': 0,
            'page_fills': 0,
            'fast_mode_activations': 0,
            'avg_fill_time_ms': 0,
            'ntp_corrections': 0
        }
        
        logger.info(f"👑 King Sniper v11.0.0 - Session: {self.session_id}")
        logger.info(f"⏰ NTP Offset: {self.ntp_offset:.3f}s (Synced: {self.time_synced})")
    
    def _validate_config(self) -> None:
        """التحقق من صحة التكوين"""
        required_configs = [
            'TARGET_URL', 'LAST_NAME', 'FIRST_NAME', 
            'EMAIL', 'PASSPORT', 'PHONE'
        ]
        
        missing = []
        for config_name in required_configs:
            if not hasattr(Config, config_name):
                missing.append(config_name)
        
        if missing:
            raise ValueError(f"❌ تكوين مفقود: {', '.join(missing)}")
        
        logger.info("✅ التكوين صالح")
    
    def _prepare_base_url(self, url: str) -> str:
        """تحضير URL مع إضافة locale إذا لم يكن موجوداً"""
        if not url:
            raise ValueError("❌ TARGET_URL فارغ")
        
        if "request_locale" not in url:
            if "?" in url:
                return url + "&request_locale=en"
            else:
                return url + "?request_locale=en"
        return url
    
    def _sync_ntp_time(self) -> None:
        """مزامنة الوقت مع خوادم NTP"""
        try:
            ntp_servers = [
                'pool.ntp.org',
                'time.google.com',
                'time.windows.com',
                'ntp.ubuntu.com'
            ]
            
            for server in ntp_servers:
                try:
                    client = ntplib.NTPClient()
                    response = client.request(server, timeout=3, version=3)
                    
                    # حساب الفرق بين الوقت المحلي والـ NTP
                    self.ntp_offset = response.offset
                    self.time_synced = True
                    
                    logger.info(f"⏰ مزامنة NTP مع {server}: offset={self.ntp_offset:.3f}s")
                    return
                    
                except Exception as e:
                    logger.debug(f"⚠️ فشل المزامنة مع {server}: {e}")
                    continue
            
            logger.warning("⚠️ فشل جميع خوادم NTP، استخدام الوقت المحلي")
            
        except Exception as e:
            logger.error(f"❌ خطأ في مزامنة NTP: {e}")
    
    def get_synced_time(self) -> datetime.datetime:
        """الحصول على الوقت المصحح مع NTP"""
        if self.time_synced:
            corrected = datetime.datetime.now() + timedelta(seconds=self.ntp_offset)
            self.stats['ntp_corrections'] += 1
            return corrected
        return datetime.datetime.now()
    
    # ==================== إدارة الوقت ====================
    def get_operational_mode(self) -> str:
        """تحديد نمط التشغيل مع التصحيح الزمني"""
        try:
            now = self.get_synced_time().astimezone(self.timezone)
            
            # النافذة الهجومية الموسعة: 01:59:45 - 02:10:10
            if (now.hour == 1 and now.minute == 59 and now.second >= 45) or \
               (now.hour == 2 and now.minute <= 10) or \
               (now.hour == 2 and now.minute == 10 and now.second <= 10):
                return "ASSAULT"
            
            # مرحلة الإحماء الموسعة: 01:40 - 01:59:44
            elif now.hour == 1 and now.minute >= 40:
                return "WARMUP"
            
            # المسح العادي
            return "SCOUT"
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحديد النمط: {e}")
            return "SCOUT"
    
    def calculate_delay(self) -> float:
        """حساب التأخير المناسب"""
        mode = self.get_operational_mode()
        
        if mode == "ASSAULT":
            self.stats['fast_mode_activations'] += 1
            return random.uniform(0.01, 0.08)  # 10-80ms فائق السرعة
        
        elif mode == "WARMUP":
            return random.uniform(0.5, 1.5)    # 0.5-1.5 ثانية
        
        else:  # SCOUT
            return random.uniform(15.0, 30.0)  # 15-30 ثانية (مختصر)
    
    # ==================== إدارة المتصفح ====================
    def create_stealth_context(self, browser: Browser) -> Tuple[BrowserContext, Page]:
        """إنشاء سياق متخفي وآمن"""
        try:
            # اختيار User-Agent عشوائي
            self.current_user_agent = random.choice(self.user_agents)
            
            context = browser.new_context(
                user_agent=self.current_user_agent,
                viewport={
                    "width": 1366 + random.randint(-30, 30),
                    "height": 768 + random.randint(-30, 30)
                },
                locale="en-US",
                timezone_id="Asia/Aden",
                java_script_enabled=True,
                ignore_https_errors=True,
                permissions=[]  # لا أذونات
            )
            
            page = context.new_page()
            
            # منع اكتشاف الأتمتة المتقدم
            stealth_script = """
            // إخفاء WebDriver تماماً
            Object.defineProperty(navigator, 'webdriver', { 
                get: () => undefined,
                configurable: true
            });
            
            // تعديل الخصائص الأخرى
            Object.defineProperty(navigator, 'plugins', { 
                get: () => [1, 2, 3, 4, 5],
                configurable: true
            });
            
            Object.defineProperty(navigator, 'languages', { 
                get: () => ['en-US', 'en', 'ar-YE'],
                configurable: true
            });
            
            // إخفاء Chrome runtime بشكل كامل
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // تعديل permissions بشكل متقدم
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // إخفاء طابع الزمن
            Object.defineProperty(document, 'hidden', { get: () => false });
            Object.defineProperty(document, 'visibilityState', { get: () => 'visible' });
            
            // إخفاء صوتيات الأتمتة
            Object.defineProperty(HTMLMediaElement.prototype, 'play', {
                value: function() { return Promise.resolve(); }
            });
            """
            
            page.add_init_script(stealth_script)
            
            # تحسين الأداء بحظر الموارد غير الضرورية
            def route_handler(route):
                resource_type = route.request.resource_type
                url = route.request.url
                
                # حظر أكثر عدوانية في وضع ASSAULT
                if self.get_operational_mode() == "ASSAULT":
                    if resource_type in ["image", "media", "font", "stylesheet"]:
                        route.abort()
                        return
                
                # الحظر العادي
                if resource_type in ["image", "media"]:
                    route.abort()
                elif "google-analytics" in url or "gtag" in url:
                    route.abort()
                else:
                    route.continue_()
            
            page.route("**/*", route_handler)
            
            # مهلات ذكية حسب النمط
            mode = self.get_operational_mode()
            if mode == "ASSAULT":
                context.set_default_timeout(8000)    # 8 ثواني
                context.set_default_navigation_timeout(10000)  # 10 ثواني
            else:
                context.set_default_timeout(15000)   # 15 ثانية
                context.set_default_navigation_timeout(20000)  # 20 ثانية
            
            logger.info(f"✨ السياق الجديد جاهز (UA: {self.current_user_agent[:40]}...)")
            return context, page
            
        except Exception as e:
            logger.error(f"❌ فشل إنشاء السياق: {e}")
            raise
    
    # ==================== نظام الحقن المباشر ====================
    def dom_fill(self, page: Page, selector: str, value: str, field_type: str = "") -> bool:
        """
        حقن مباشر للقيمة في عنصر DOM (أسرع بـ 100x من page.fill)
        
        Args:
            page: صفحة Playwright
            selector: محدد CSS
            value: القيمة للحقن
            field_type: نوع الحقل (للتسجيل)
            
        Returns:
            bool: نجاح العملية
        """
        start_time = time.time()
        
        try:
            # تنظيف القيمة لحقن آمن في JavaScript
            safe_value = str(value)
            replacements = {
                '\\': '\\\\',
                '"': '\\"',
                "'": "\\'",
                '\n': '\\n',
                '\r': '\\r',
                '\t': '\\t'
            }
            
            for old, new in replacements.items():
                safe_value = safe_value.replace(old, new)
            
            # حقن JavaScript مباشر
            js_code = f"""
            (function() {{
                try {{
                    // البحث عن العنصر
                    const el = document.querySelector(`{selector}`);
                    if (!el) {{
                        return {{success: false, reason: "Element not found: {selector[:30]}"}};
                    }}
                    
                    // حفظ الحالة الأصلية
                    const oldValue = el.value;
                    
                    // تعيين القيمة الجديدة
                    el.value = "{safe_value}";
                    
                    // تشغيل سلسلة أحداث محاكاة للواقع
                    el.dispatchEvent(new FocusEvent('focus', {{ bubbles: true }}));
                    
                    // محاكاة الكتابة التدريجية للكابتشا فقط
                    if (el.name === 'captchaText' || el.id.includes('captcha')) {{
                        // للكابتشا، محاكاة كتابة أبطأ
                        setTimeout(() => {{
                            el.dispatchEvent(new InputEvent('input', {{
                                bubbles: true,
                                inputType: 'insertText',
                                data: "{safe_value}"
                            }}));
                        }}, 50);
                    }} else {{
                        // للحقول العادية، إدخال فوري
                        el.dispatchEvent(new InputEvent('input', {{
                            bubbles: true,
                            inputType: 'insertText',
                            data: "{safe_value}"
                        }}));
                    }}
                    
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    
                    // التحقق من نجاح التعيين
                    const success = el.value === "{safe_value}";
                    
                    return {{
                        success: success,
                        oldValue: oldValue,
                        newValue: el.value,
                        selector: "{selector[:50]}"
                    }};
                }} catch(error) {{
                    return {{success: false, reason: error.message}};
                }}
            }})()
            """
            
            result = page.evaluate(js_code)
            
            elapsed = (time.time() - start_time) * 1000  # بالمللي ثانية
            
            if result.get('success'):
                self.stats['dom_injections'] += 1
                
                # تحديث متوسط وقت الحقن
                if self.stats['avg_fill_time_ms'] == 0:
                    self.stats['avg_fill_time_ms'] = elapsed
                else:
                    self.stats['avg_fill_time_ms'] = (self.stats['avg_fill_time_ms'] * 0.9) + (elapsed * 0.1)
                
                if field_type:
                    logger.debug(f"⚡ حقن DOM: {field_type} ({elapsed:.1f}ms)")
                else:
                    logger.debug(f"⚡ حقن DOM ناجح ({elapsed:.1f}ms)")
                return True
            else:
                logger.warning(f"⚠️ فشل الحقن: {result.get('reason', 'Unknown')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في DOM Fill: {str(e)[:100]}")
            elapsed = (time.time() - start_time) * 1000
            self.stats['errors'] += 1
            return False
    
    def safe_fill(self, page: Page, selector: str, value: str, field_type: str = "") -> bool:
        """
        تعبئة ذكية مع Fallback تلقائي
        """
        # المحاولة 1: الحقن المباشر (الأسرع)
        if self.dom_fill(page, selector, value, field_type):
            return True
        
        # المحاولة 2: page.fill العادية (أبطأ)
        try:
            start_time = time.time()
            page.fill(selector, value)
            elapsed = (time.time() - start_time) * 1000
            
            self.stats['page_fills'] += 1
            logger.debug(f"📝 Fallback fill: {field_type} ({elapsed:.1f}ms)")
            return True
            
        except Exception as e:
            logger.error(f"❌ فشل Fallback fill: {e}")
            return False
    
    # ==================== نظام الكابتشا فائق السرعة ====================
    def solve_captcha_ultrafast(self, page: Page, location: str = "GENERAL") -> bool:
        """
        حل كابتشا فائق السرعة مع الحقن المباشر
        """
        max_attempts = 2  # محاولتان فقط للسرعة
        
        for attempt in range(1, max_attempts + 1):
            try:
                # التحقق الفوري من وجود كابتشا
                try:
                    captcha_input = page.locator("input[name='captchaText']").first
                    if not captcha_input.is_visible(timeout=300):  # 300ms فقط
                        return True
                except:
                    return True
                
                logger.info(f"⚡ [{location}] كابتشا محاولة {attempt}/{max_attempts}")
                
                # البحث السريع عن عنصر الكابتشا
                captcha_element = None
                fast_selectors = [
                    "img[src*='captcha']",
                    "div.captcha img",
                    "#captcha img",
                    "img.captcha-image",
                    "div[class*='captcha'] img"
                ]
                
                for selector in fast_selectors:
                    try:
                        if page.locator(selector).first.is_visible(timeout=200):
                            captcha_element = page.locator(selector).first
                            break
                    except:
                        continue
                
                if not captcha_element:
                    logger.warning(f"⚠️ [{location}] عنصر الكابتشا غير موجود")
                    self.stats['captchas_failed'] += 1
                    return False
                
                # التقاط الشاشة والتحقق من الحجم بسرعة
                try:
                    screenshot = captcha_element.screenshot()
                    
                    # فحص سريع للكابتشا السوداء (The 4333 Reaction)
                    if len(screenshot) < 1500:  # أقل من 1.5KB يعني صورة تالفة
                        logger.critical(f"⚫ [{location}] الكابتشا السوداء! (Poisoned Session)")
                        
                        self.stats['poisoned_sessions'] += 1
                        self.is_poisoned = True
                        
                        # تنفيذ Hard Reset فوري
                        return self._emergency_session_reboot(page, "BLACK_CAPTCHA")
                    
                except Exception as e:
                    logger.warning(f"⚠️ خطأ في التقاط الكابتشا: {e}")
                    continue
                
                # حل الكابتشا
                try:
                    start_solve = time.time()
                    code = self.solver.solve(captcha_element.screenshot())
                    solve_time = (time.time() - start_solve) * 1000
                    
                    if not code:
                        logger.warning(f"⚠️ [{location}] محلول الكابتشا لم يرجع كوداً")
                        continue
                    
                    # تنظيف الكود
                    code = str(code).replace(" ", "").replace("-", "").strip()[:10]
                    
                    if len(code) < 4:
                        logger.warning(f"⚠️ كود قصير جداً: {len(code)} أحرف")
                        continue
                    
                    logger.debug(f"🔢 كود الكابتشا: {code} (حل في {solve_time:.0f}ms)")
                    
                    # حقن مباشر فائق السرعة للكود
                    if self.dom_fill(page, "input[name='captchaText']", code, "CAPTCHA"):
                        
                        # إرسال فوري بـ Enter (أسرع من النقر)
                        page.keyboard.press("Enter")
                        
                        # انتظار قصير جداً حسب النمط
                        mode = self.get_operational_mode()
                        wait_time = 500 if mode == "ASSAULT" else 1000  # 0.5-1 ثانية
                        page.wait_for_timeout(wait_time)
                        
                        # التحقق الفوري من النجاح
                        if not captcha_input.is_visible(timeout=300):
                            self.stats['captchas_solved'] += 1
                            logger.info(f"✅ [{location}] كابتشا محلولة (حقن مباشر)")
                            return True
                        else:
                            logger.warning(f"🔄 [{location}] الكابتشا مازالت موجودة")
                            page.wait_for_timeout(500)
                            continue
                            
                except Exception as e:
                    logger.error(f"❌ [{location}] خطأ في حل الكابتشا: {str(e)[:80]}")
                    continue
                    
            except Exception as e:
                logger.error(f"❌ [{location}] خطأ عام في الكابتشا: {str(e)[:80]}")
                self.stats['errors'] += 1
        
        self.stats['captchas_failed'] += 1
        logger.error(f"❌ [{location}] فشل بعد {max_attempts} محاولات")
        return False
    
    def _emergency_session_reboot(self, page: Page, reason: str) -> bool:
        """
        إعادة تشغيل طارئة للجلسة (Hard Reset)
        """
        try:
            logger.critical(f"🚨 إعادة تشغيل طارئة للجلسة: {reason}")
            
            # إغلاق السياق الحالي
            if hasattr(self, 'context') and self.context:
                try:
                    self.context.close()
                except:
                    pass
            
            # تغيير User-Agent جذري
            new_ua_pool = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ]
            
            self.current_user_agent = random.choice(new_ua_pool)
            self.user_agents = [self.current_user_agent]  # تحديث المخزن
            
            # إعادة تعيين الحالة
            self.consecutive_errors = 0
            self.is_poisoned = False
            
            # إعادة مزامنة الوقت
            self._sync_ntp_time()
            
            logger.info(f"🔄 الجلسة الجديدة جاهزة (UA: {self.current_user_agent[:40]}...)")
            return False  # لإعادة إنشاء السياق في الدورة الرئيسية
            
        except Exception as e:
            logger.error(f"❌ فشل إعادة تشغيل الجلسة: {e}")
            return False
    
    # ==================== نظام التعيين الديناميكي السريع ====================
    def build_dynamic_field_map_fast(self, page: Page) -> List[FieldMapping]:
        """
        بناء خريطة الحقول الديناميكية بسرعة
        """
        field_mappings = [
            FieldMapping(
                "LAST_NAME",
                ["last name", "family name", "surname", "nachname", "الاسم الأخير", "اسم العائلة"],
                Config.LAST_NAME
            ),
            FieldMapping(
                "FIRST_NAME", 
                ["first name", "given name", "vorname", "الاسم الأول", "الاسم الشخصي"],
                Config.FIRST_NAME
            ),
            FieldMapping(
                "EMAIL",
                ["email", "e-mail", "mail address", "البريد الإلكتروني", "البريد الالكتروني"],
                Config.EMAIL
            ),
            FieldMapping(
                "PASSPORT",
                ["passport", "passport number", "reisepass", "رقم الجواز", "وثيقة سفر", "جواز سفر"],
                Config.PASSPORT
            ),
            FieldMapping(
                "PHONE",
                ["phone", "telephone", "mobile", "contact number", "رقم الهاتف", "رقم الجوال"],
                Config.PHONE.replace("+", "00").strip()
            )
        ]
        
        try:
            # البحث السريع باستخدام JavaScript
            labels_info = page.evaluate("""
                () => {
                    const results = [];
                    const labels = document.querySelectorAll('label, span, div, p, td, th');
                    
                    for(const label of labels) {
                        const text = (label.textContent || label.innerText || "").trim().toLowerCase();
                        
                        if(text && text.length < 80 && text.length > 1) {
                            let associatedInput = null;
                            
                            // طريقة 1: for attribute
                            if(label.htmlFor) {
                                associatedInput = document.getElementById(label.htmlFor);
                            }
                            
                            // طريقة 2: العنصر التالي مباشرة
                            if(!associatedInput) {
                                let next = label.nextElementSibling;
                                while(next && !associatedInput) {
                                    if(next.matches('input, select, textarea')) {
                                        associatedInput = next;
                                    }
                                    next = next.nextElementSibling;
                                }
                            }
                            
                            // طريقة 3: البحث في الاب
                            if(!associatedInput) {
                                associatedInput = label.querySelector('input, select, textarea');
                            }
                            
                            if(associatedInput) {
                                results.push({
                                    text: text,
                                    inputName: associatedInput.name || '',
                                    inputId: associatedInput.id || '',
                                    tagName: associatedInput.tagName,
                                    type: associatedInput.type || 'text'
                                });
                            }
                        }
                    }
                    
                    return results.slice(0, 30); // أول 30 فقط للسرعة
                }
            """)
            
            # تعيين سريع
            for mapping in field_mappings:
                for label in labels_info:
                    for pattern in mapping.patterns:
                        if pattern in label['text']:
                            if label['inputName']:
                                mapping.found_name = label['inputName']
                                mapping.found_selector = f"input[name='{label['inputName']}']"
                            elif label['inputId']:
                                mapping.found_selector = f"#{label['inputId']}"
                            
                            if mapping.found_selector:
                                logger.debug(f"🔗 عُيّن: {mapping.field_type} -> {mapping.found_selector}")
                            break
                    
                    if mapping.found_selector:
                        break
            
            return field_mappings
            
        except Exception as e:
            logger.error(f"❌ خطأ في بناء خريطة الحقول السريعة: {e}")
            return field_mappings
    
    def fill_form_ultrafast(self, page: Page, field_mappings: List[FieldMapping]) -> bool:
        """
        تعبئة فائقة السرعة للنموذج
        """
        start_time = time.time()
        
        try:
            success_count = 0
            total_fields = len(field_mappings)
            
            # تجميع عمليات الحقن دفعة واحدة إن أمكن
            for mapping in field_mappings:
                filled = False
                
                # المحاولة 1: التعيين الديناميكي
                if mapping.found_selector:
                    if self.safe_fill(page, mapping.found_selector, mapping.value, mapping.field_type):
                        filled = True
                
                # المحاولة 2: الأسماء الثابتة
                if not filled:
                    fallback_selectors = {
                        "LAST_NAME": [
                            "input[name='lastname']", 
                            "input[name='familyName']",
                            "#lastname",
                            "input[name='fields[3].content']"
                        ],
                        "FIRST_NAME": [
                            "input[name='firstname']", 
                            "input[name='givenName']",
                            "#firstname",
                            "input[name='fields[2].content']"
                        ],
                        "EMAIL": [
                            "input[name='email']", 
                            "input[name='eMail']",
                            "#email",
                            "input[name='fields[4].content']"
                        ],
                        "PASSPORT": [
                            "input[name='passportNumber']", 
                            "input[name='fields[0].content']",
                            "#passportNumber",
                            "input[name='passport']"
                        ],
                        "PHONE": [
                            "input[name='phone']", 
                            "input[name='fields[1].content']",
                            "#phone",
                            "input[name='telephone']"
                        ]
                    }
                    
                    for selector in fallback_selectors.get(mapping.field_type, []):
                        if self.safe_fill(page, selector, mapping.value, mapping.field_type):
                            filled = True
                            break
                
                if filled:
                    success_count += 1
                else:
                    logger.warning(f"⚠️ فشل ملء حقل: {mapping.field_type}")
                    # محاولة طوارئ باستخدام JavaScript المباشر
                    try:
                        page.evaluate(f"""
                            const inputs = document.querySelectorAll('input');
                            for(const input of inputs) {{
                                const placeholder = (input.placeholder || '').toLowerCase();
                                const name = (input.name || '').toLowerCase();
                                if(placeholder.includes('{mapping.field_type.lower().replace('_', ' ')}') || 
                                   name.includes('{mapping.field_type.lower().replace('_', ' ')}')) {{
                                    input.value = '{mapping.value}';
                                    success_count += 1;
                                    break;
                                }}
                            }}
                        """)
                    except:
                        pass
            
            # اختيار فئة التأشيرة بسرعة
            if self._select_visa_category_ultrafast(page):
                success_count += 1
            
            # حقل تكرار الإيميل
            if self._fill_email_repeat_fast(page, Config.EMAIL):
                success_count += 1
            
            fill_time = (time.time() - start_time) * 1000
            self.stats['forms_filled'] += 1
            
            logger.info(f"⚡ تم تعبئة {success_count}/{total_fields + 2} حقول في {fill_time:.0f}ms")
            
            return success_count >= total_fields  # نجاح إذا عُبئت معظم الحقول
            
        except Exception as e:
            logger.error(f"❌ خطأ في التعبئة الفائقة: {e}")
            return False
    
    def _fill_email_repeat_fast(self, page: Page, email: str) -> bool:
        """تعبئة حقل تكرار الإيميل بسرعة"""
        try:
            repeat_selectors = [
                "input[name='emailrepeat']",
                "input[name='emailRepeat']",
                "input[name='confirmEmail']",
                "input[name='email_confirm']",
                "#emailRepeat",
                "#confirmEmail"
            ]
            
            for selector in repeat_selectors:
                try:
                    if page.locator(selector).first.is_visible(timeout=200):
                        return self.dom_fill(page, selector, email, "EMAIL_REPEAT")
                except:
                    continue
            
            return False
        except:
            return False
    
    def _select_visa_category_ultrafast(self, page: Page) -> bool:
        """
        اختيار فائق السرعة لفئة التأشيرة
        """
        try:
            # البحث السريع عن عنصر select
            select_js = """
            () => {
                const selects = document.querySelectorAll('select');
                for(const select of selects) {
                    const name = (select.name || '').toLowerCase();
                    const id = (select.id || '').toLowerCase();
                    const options = select.querySelectorAll('option');
                    
                    if(options.length > 1 && 
                       (name.includes('visa') || name.includes('category') || 
                        name.includes('purpose') || id.includes('visa') ||
                        select.name === 'fields[2].content')) {
                        return {
                            element: select,
                            name: select.name,
                            id: select.id,
                            optionsCount: options.length
                        };
                    }
                }
                return null;
            }
            """
            
            select_info = page.evaluate(select_js)
            
            if not select_info:
                logger.warning("⚠️ لم يتم العثور على عنصر select للفيزا")
                return False
            
            # كلمات V1 المفتاحية بالترتيب
            v1_keywords = [
                "yemeni national",
                "student visa", 
                "language course",
                "studium",
                "sprachkurs",
                "university",
                "student",
                "language"
            ]
            
            # البحث عن أفضل خيار
            best_index = 1  # افتراضي: الخيار الثاني
            
            options_js = f"""
            (selectName) => {{
                const select = document.querySelector(`select[name="${{selectName}}"]`);
                if(!select) return {{index: 1, text: ""}};
                
                const options = select.querySelectorAll('option');
                const keywords = {json.dumps(v1_keywords)};
                
                for(const keyword of keywords) {{
                    for(let i = 0; i < options.length; i++) {{
                        const text = (options[i].textContent || "").toLowerCase();
                        if(text.includes(keyword)) {{
                            return {{index: i, text: text}};
                        }}
                    }}
                }}
                
                // Fallback للخيار الثاني
                return {{index: 1, text: options[1]?.textContent || ""}};
            }}
            """
            
            result = page.evaluate(options_js, select_info['name'])
            
            # الاختيار
            select_selector = f"select[name='{select_info['name']}']"
            page.select_option(select_selector, index=result['index'])
            
            logger.info(f"📋 اختيار الفئة: الخيار {result['index'] + 1} ({result['text'][:30]}...)")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في اختيار الفئة السريع: {e}")
            return False
    
    # ==================== بناء الروابط الآمن ====================
    def safe_url_join(self, base: str, href: str) -> str:
        """
        بناء رابط آمن باستخدام urljoin
        """
        try:
            if not href or href == "#" or href.startswith("javascript:"):
                return base
            
            # إذا كان الرابط كامل
            if href.startswith(("http://", "https://")):
                return href
            
            # استخدام urljoin للبناء الآمن
            joined = urljoin(base, href)
            
            # تنظيف الروابط المزدوجة
            parsed = urlparse(joined)
            path = parsed.path.replace("//", "/")
            
            # إعادة بناء الرابط
            result = f"{parsed.scheme}://{parsed.netloc}{path}"
            if parsed.query:
                result += f"?{parsed.query}"
            if parsed.fragment:
                result += f"#{parsed.fragment}"
            
            return result
            
        except Exception as e:
            logger.error(f"❌ خطأ في بناء الرابط: {e}")
            
            # Fallback ذكي
            if href.startswith("/"):
                return f"https://service2.diplo.de{href}"
            elif href.startswith("./"):
                return f"{base.rsplit('/', 1)[0]}/{href[2:]}"
            else:
                return f"{base.rstrip('/')}/{href.lstrip('/')}"
    
    # ==================== نظام المسح فائق السرعة ====================
    def generate_priority_month_urls(self) -> List[str]:
        """إنشاء روابط الأشهر بأولويات استراتيجية"""
        try:
            today = self.get_synced_time().astimezone(self.timezone).date()
            base_clean = self.base_url.split("&dateStr=")[0] if "&dateStr=" in self.base_url else self.base_url
            
            urls = []
            
            # أولويات V4 مع تعديلات ذكية
            month_priorities = [
                (2, "مارس"),   # الأولوية 1
                (3, "أبريل"),  # الأولوية 2
                (1, "فبراير"), # الأولوية 3
                (4, "مايو"),   # الأولوية 4
                (5, "يونيو"),  # احتياطي
                (6, "يوليو")   # احتياطي
            ]
            
            for offset, month_name in month_priorities:
                future_month = (today.month + offset - 1) % 12 + 1
                future_year = today.year + ((today.month + offset - 1) // 12)
                date_str = f"15.{future_month:02d}.{future_year}"
                full_url = f"{base_clean}&dateStr={date_str}"
                urls.append(full_url)
                
                # في وضع ASSAULT، نجرب تواريخ متعددة
                if self.get_operational_mode() == "ASSAULT" and offset <= 3:
                    # تواريخ إضافية في نفس الشهر
                    for day in [1, 10, 20]:
                        date_str_alt = f"{day:02d}.{future_month:02d}.{future_year}"
                        urls.append(f"{base_clean}&dateStr={date_str_alt}")
            
            # خلط الروابط لمنع الأنماط
            if self.get_operational_mode() != "ASSAULT":
                random.shuffle(urls)
            
            logger.debug(f"📅 تم إنشاء {len(urls)} رابط شهر")
            return urls[:12]  # أخذ أول 12 رابط فقط
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء روابط الأشهر: {e}")
            return []
    
    def scan_month_for_days_fast(self, page: Page, url: str) -> Tuple[bool, List[str]]:
        """مسح سريع للشهر للبحث عن أيام متاحة"""
        try:
            self.stats['scans'] += 1
            
            # التحميل السريع
            mode = self.get_operational_mode()
            timeout = 5000 if mode == "ASSAULT" else 10000
            
            logger.debug(f"🔍 مسح سريع: {url.split('dateStr=')[-1] if 'dateStr=' in url else url}")
            
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            
            # حل كابتشا سريع
            if not self.solve_captcha_ultrafast(page, "MONTH"):
                return False, []
            
            # البحث السريع عن الأيام باستخدام JavaScript
            day_links = []
            
            try:
                # طريقة JavaScript فائقة السرعة
                links = page.evaluate("""
                    () => {
                        const results = [];
                        // جميع الأنماط المحتملة
                        const selectors = [
                            'a[href*="showDay"]',
                            'a.arrow[href*="appointment"]',
                            'td.buchbar a',
                            'td.free a',
                            'a.appointment',
                            'a:has-text("Book")',
                            'a:has-text("Appointment")',
                            'a:has-text("Termin")'
                        ];
                        
                        for(const selector of selectors) {
                            const elements = document.querySelectorAll(selector);
                            for(const el of elements) {
                                const href = el.getAttribute('href');
                                if(href && href.includes('showDay')) {
                                    results.push({
                                        href: href,
                                        text: el.textContent?.trim() || ''
                                    });
                                }
                            }
                            if(results.length >= 3) break; // أول 3 فقط
                        }
                        
                        return results.slice(0, 3);
                    }
                """)
                
                for link_info in links:
                    full_url = self.safe_url_join(url, link_info['href'])
                    if full_url not in day_links:
                        day_links.append(full_url)
                
            except Exception as e:
                logger.warning(f"⚠️ خطأ في البحث السريع: {e}")
                # Fallback للطريقة الأصلية
                pass
            
            if day_links:
                logger.info(f"🔥 وجدت {len(day_links)} يوم/أيام")
                return True, day_links
            
            logger.debug("📭 لا توجد أيام متاحة")
            return True, []
            
        except Exception as e:
            logger.error(f"❌ خطأ في مسح الشهر السريع: {str(e)[:100]}")
            self.stats['errors'] += 1
            return False, []
    
    def scan_day_for_slots_fast(self, page: Page, day_url: str) -> Tuple[bool, List[str]]:
        """مسح سريع لليوم للبحث عن مواعيد"""
        try:
            # الانتقال السريع لليوم
            page.goto(day_url, timeout=8000, wait_until="domcontentloaded")
            
            # حل كابتشا سريع
            if not self.solve_captcha_ultrafast(page, "DAY"):
                return False, []
            
            # البحث السريع عن المواعيد
            slot_links = []
            
            try:
                # طريقة JavaScript فائقة السرعة
                slots = page.evaluate("""
                    () => {
                        const results = [];
                        const selectors = [
                            'a[href*="showForm"]',
                            'a.arrow[href*="appointment_showForm"]',
                            'td a:has-text("Select")',
                            'td a:has-text("Book")',
                            'a:has-text("Time")',
                            'a:has-text("Zeit")',
                            'button[onclick*="showForm"]'
                        ];
                        
                        for(const selector of selectors) {
                            const elements = document.querySelectorAll(selector);
                            for(const el of elements) {
                                let href = el.getAttribute('href');
                                if(!href && el.onclick) {
                                    // استخراج من onclick
                                    const match = el.onclick.toString().match(/showForm[^']*'([^']+)'/);
                                    if(match) href = match[1];
                                }
                                
                                if(href && href.includes('showForm')) {
                                    results.push({
                                        href: href,
                                        text: el.textContent?.trim() || '',
                                        time: el.closest('td')?.textContent?.trim() || ''
                                    });
                                }
                            }
                            if(results.length >= 2) break; // أول موعدين فقط
                        }
                        
                        return results.slice(0, 2);
                    }
                """)
                
                for slot_info in slots:
                    full_url = self.safe_url_join(day_url, slot_info['href'])
                    if full_url not in slot_links:
                        slot_links.append(full_url)
                        logger.debug(f"⏰ موعد: {slot_info['time'][:20]}")
                
            except Exception as e:
                logger.warning(f"⚠️ خطأ في البحث عن المواعيد: {e}")
            
            if slot_links:
                logger.info(f"⏰ وجدت {len(slot_links)} موعد/مواعيد")
                return True, slot_links
            
            logger.debug("⏳ لا توجد مواعيد متاحة")
            return True, []
            
        except Exception as e:
            logger.error(f"❌ خطأ في مسح اليوم السريع: {e}")
            return False, []
    
    # ==================== محرك الحجز فائق السرعة ====================
    def attempt_booking_ultrafast(self, page: Page, slot_url: str) -> bool:
        """محاولة حجز فائقة السرعة"""
        try:
            logger.info("🎯 بدء حجز فائق السرعة...")
            
            # الانتقال الفوري لصفحة الحجز
            page.goto(slot_url, timeout=6000, wait_until="domcontentloaded")
            
            # حل كابتشا فوري
            if not self.solve_captcha_ultrafast(page, "FORM"):
                return False
            
            # التحقق السريع من وجود النموذج
            if not page.locator("form").first.is_visible(timeout=2000):
                logger.error("❌ النموذج غير موجود")
                return False
            
            # بناء خريطة الحقول الديناميكية بسرعة
            field_mappings = self.build_dynamic_field_map_fast(page)
            
            # تعبئة فائقة السرعة
            if not self.fill_form_ultrafast(page, field_mappings):
                logger.error("❌ فشل تعبئة النموذج")
                return False
            
            # الإرسال النهائي فائق السرعة
            return self._submit_booking_ultrafast(page)
            
        except Exception as e:
            logger.error(f"❌ خطأ في محاولة الحجز الفائق: {e}")
            return False
    
    def _submit_booking_ultrafast(self, page: Page, max_attempts: int = 2) -> bool:
        """إرسال نموذج الحجز فائق السرعة"""
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"📤 محاولة إرسال فائقة السرعة {attempt}/{max_attempts}")
                
                # حل كابتشا الإرسال النهائي
                if not self.solve_captcha_ultrafast(page, "SUBMIT"):
                    # تحقق سريع إذا مازال في النموذج
                    if page.locator("input[name='lastname']").first.is_visible(timeout=500):
                        continue
                    else:
                        return False
                
                # البحث الفوري عن زر الإرسال
                submit_found = False
                
                # محاولة باستخدام JavaScript أولاً
                submit_result = page.evaluate("""
                    () => {
                        const submitSelectors = [
                            'input[type="submit"]',
                            'button[type="submit"]',
                            'button:contains("Book")',
                            'button:contains("Submit")',
                            'button:contains("Confirm")',
                            'button:contains("Absenden")',
                            'button:contains("Buchen")'
                        ];
                        
                        for(const selector of submitSelectors) {
                            const el = document.querySelector(selector);
                            if(el && el.offsetParent !== null) {
                                el.click();
                                return {success: true, selector: selector};
                            }
                        }
                        return {success: false};
                    }
                """)
                
                if submit_result.get('success'):
                    submit_found = True
                    logger.debug(f"🖱️ نقر بـ JS: {submit_result.get('selector')}")
                else:
                    # Fallback للنقر العادي
                    submit_selectors = [
                        "input[type='submit']",
                        "button[type='submit']",
                        "button:has-text('Book')",
                        "button:has-text('Submit')",
                        "button:has-text('Confirm')"
                    ]
                    
                    for selector in submit_selectors:
                        if page.locator(selector).first.is_visible(timeout=500):
                            page.locator(selector).first.click()
                            submit_found = True
                            break
                
                if not submit_found:
                    # محاولة أخيرة بـ Enter
                    page.keyboard.press("Enter")
                    submit_found = True
                
                # انتظار قصير جداً
                mode = self.get_operational_mode()
                wait_time = 2000 if mode == "ASSAULT" else 3000
                page.wait_for_timeout(wait_time)
                
                # التحقق الفوري من النجاح
                page_content = page.content().lower()
                
                success_indicators = [
                    "appointment number",
                    "successfully booked",
                    "booking confirmed",
                    "vorgang wurde gespeichert",
                    "termin wurde gebucht",
                    "buchung erfolgreich",
                    "confirmation number"
                ]
                
                for indicator in success_indicators:
                    if indicator in page_content:
                        # استخراج سريع لتفاصيل الحجز
                        appointment_num = re.search(r"appointment number is\s+(\d+)", page_content, re.IGNORECASE)
                        appointment_date = re.search(r"(\d{2}\.\d{2}\.\d{4})", page_content)
                        
                        success_msg = "\n" + "="*60 + "\n"
                        success_msg += "🎉🎉🎉 الحجز الناجح! 🎉🎉🎉\n"
                        success_msg += "="*60 + "\n"
                        if appointment_num:
                            success_msg += f"📋 رقم الحجز: {appointment_num.group(1)}\n"
                        if appointment_date:
                            success_msg += f"📅 التاريخ: {appointment_date.group(1)}\n"
                        success_msg += f"👤 الاسم: {Config.FIRST_NAME} {Config.LAST_NAME}\n"
                        success_msg += f"⚡ النمط: {mode}\n"
                        success_msg += f"⏰ وقت التشغيل: {(datetime.datetime.now() - self.start_time).total_seconds():.0f}s\n"
                        success_msg += "="*60
                        
                        logger.info(success_msg)
                        
                        # إرسال الإشعارات السريعة
                        self._send_success_notifications_fast(page, appointment_num, appointment_date)
                        
                        self.stats['success'] = True
                        return True
                
                # تحقق سريع إذا مازال في النموذج
                if page.locator("input[name='lastname']").first.is_visible(timeout=500):
                    logger.warning("🔄 مازال في النموذج، إعادة المحاولة...")
                    page.wait_for_timeout(1000)
                    continue
                
                # إذا ظهر خطأ
                error_indicators = ["error", "fehler", "خطأ", "invalid", "ungültig", "failed", "failure"]
                for indicator in error_indicators:
                    if indicator in page_content:
                        logger.error("❌ خطأ في الخادم")
                        return False
                
            except Exception as e:
                logger.error(f"❌ خطأ في الإرسال الفائق: {str(e)[:100]}")
                if attempt < max_attempts:
                    page.wait_for_timeout(1500)
        
        logger.error(f"❌ فشل بعد {max_attempts} محاولات إرسال")
        return False
    
    def _send_success_notifications_fast(self, page: Page, appointment_num, appointment_date):
        """إرسال إشعارات النجاح السريعة"""
        try:
            # حفظ لقطة الشاشة السريعة
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"king_booking_{timestamp}.png"
            
            # لقطة سريعة (ليس كاملة الصفحة للسرعة)
            page.screenshot(path=screenshot_path, full_page=False)
            
            # بناء رسالة الإشعار السريعة
            alert_message = f"""
✅ الحجز الناجح! (King Sniper v11.0.0)

📋 رقم الحجز: {appointment_num.group(1) if appointment_num else 'غير معروف'}
📅 التاريخ: {appointment_date.group(1) if appointment_date else 'غير معروف'}
👤 الاسم: {Config.FIRST_NAME} {Config.LAST_NAME}
🆔 الجلسة: {self.session_id}
⚡ النمط: {self.get_operational_mode()}
⏰ الوقت: {datetime.datetime.now().strftime('%H:%M:%S')}
📊 الإحصاءات: 
   • المسوحات: {self.stats['scans']}
   • الكابتشات: {self.stats['captchas_solved']}/{self.stats['captchas_failed']}
   • الحقن المباشر: {self.stats['dom_injections']}
   • متوسط الحقن: {self.stats['avg_fill_time_ms']:.1f}ms
            """
            
            # إرسال الإشعار
            send_alert(alert_message.strip())
            
            # إرسال الصورة
            photo_caption = f"✅ King Sniper - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            send_photo(screenshot_path, caption=photo_caption)
            
            # تسجيل النجاح في ملف
            with open("king_success.log", "a", encoding="utf-8") as f:
                f.write(f"\n{datetime.datetime.now().isoformat()} - {alert_message}\n")
            
        except Exception as e:
            logger.error(f"⚠️ خطأ في إرسال الإشعارات: {e}")
    
    # ==================== الدورة الرئيسية المحسنة ====================
    def run_king_mode(self):
        """الدورة الرئيسية للتشغيل فائق السرعة"""
        logger.info("="*60)
        logger.info("👑 King Sniper v11.0.0 - بدء التشغيل")
        logger.info("="*60)
        
        try:
            with sync_playwright() as p:
                # إعداد متصفح محسن للسرعة
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--no-first-run",
                        "--single-process",  # ⚡ لسرعة أكبر
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process,VizDisplayCompositor",
                        "--disable-accelerated-2d-canvas",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--disable-ipc-flooding-protection",
                        "--enable-features=NetworkService,NetworkServiceInProcess",
                        "--disable-dev-shm-usage"
                    ],
                    timeout=30000
                )
                
                # إنشاء السياق الأول
                self.context, page = self.create_stealth_context(browser)
                
                cycle = 0
                last_stats_log = time.time()
                
                while not self.stats['success']:
                    cycle += 1
                    
                    logger.info(f"\n👑 الدورة #{cycle} - النمط: {self.get_operational_mode()}")
                    
                    # التحقق من حالة النظام
                    if self.is_poisoned:
                        logger.critical("💀 جلسة مسمومة - إعادة تشغيل كاملة")
                        if self._emergency_session_reboot(page, "SESSION_POISONED"):
                            # إعادة إنشاء السياق
                            try:
                                self.context.close()
                            except:
                                pass
                            self.context, page = self.create_stealth_context(browser)
                        continue
                    
                    # التأخير الذكي
                    delay = self.calculate_delay()
                    if delay > 0.2:
                        logger.info(f"⏳ تأخير: {delay:.2f} ثانية")
                        time.sleep(delay)
                    
                    # الحصول على روابط الأشهر
                    month_urls = self.generate_priority_month_urls()
                    
                    if not month_urls:
                        logger.error("❌ لا توجد روابط أشهر")
                        time.sleep(30)
                        continue
                    
                    # مسح كل شهر
                    for month_url in month_urls:
                        if self.stats['success']:
                            break
                        
                        # مسح الشهر السريع
                        scan_success, day_urls = self.scan_month_for_days_fast(page, month_url)
                        
                        if not scan_success:
                            self.consecutive_errors += 1
                            if self.consecutive_errors >= 5:
                                logger.warning("⚠️ أخطاء متتالية، تجاوز هذا الشهر")
                                break
                            continue
                        
                        self.consecutive_errors = 0
                        
                        if not day_urls:
                            continue
                        
                        # مسح كل يوم
                        for day_url in day_urls:
                            if self.stats['success']:
                                break
                            
                            # مسح اليوم السريع
                            day_success, slot_urls = self.scan_day_for_slots_fast(page, day_url)
                            
                            if not day_success:
                                self.consecutive_errors += 1
                                break
                            
                            if not slot_urls:
                                break
                            
                            # محاولة الحجز لكل موعد
                            for slot_url in slot_urls:
                                if self.stats['success']:
                                    break
                                
                                logger.info(f"🎯 محاولة حجز فائقة السرعة: {slot_url[-50:]}")
                                
                                # محاولة الحجز فائق السرعة
                                if self.attempt_booking_ultrafast(page, slot_url):
                                    logger.info("🏆 المهمة مكتملة بنجاح!")
                                    break
                                else:
                                    self.consecutive_errors += 1
                                    logger.warning("⚠️ فشل الحجز، الانتقال للموعد التالي")
                                    page.wait_for_timeout(1000)
                    
                    # عرض إحصاءات الدورة
                    current_time = time.time()
                    if current_time - last_stats_log > 60:  # كل دقيقة
                        logger.info(f"📊 إحصاءات النظام:")
                        logger.info(f"   • الدورات: {cycle}")
                        logger.info(f"   • المسوحات: {self.stats['scans']}")
                        logger.info(f"   • الكابتشات الناجحة: {self.stats['captchas_solved']}")
                        logger.info(f"   • الكابتشات الفاشلة: {self.stats['captchas_failed']}")
                        logger.info(f"   • الحقن المباشر: {self.stats['dom_injections']}")
                        logger.info(f"   • متوسط وقت الحقن: {self.stats['avg_fill_time_ms']:.1f}ms")
                        logger.info(f"   • الجلسات المسمومة: {self.stats['poisoned_sessions']}")
                        logger.info(f"   • تصحيحات NTP: {self.stats['ntp_corrections']}")
                        logger.info(f"   • الأخطاء المتتالية: {self.consecutive_errors}")
                        last_stats_log = current_time
                    
                    # إعادة تشغيل وقائية كل 15 دقيقة
                    runtime = datetime.datetime.now() - self.start_time
                    if runtime.total_seconds() > 900:  # 15 دقيقة
                        logger.info("🔄 إعادة تشغيل وقائية للحفاظ على الأداء")
                        try:
                            self.context.close()
                        except:
                            pass
                        self.context, page = self.create_stealth_context(browser)
                        self.start_time = datetime.datetime.now()
                        self._sync_ntp_time()  # إعادة مزامنة الوقت
                
                # النجاح - إغلاق نظيف
                logger.info("\n" + "="*60)
                logger.info("🎊 المهمة مكتملة بنجاح!")
                logger.info("="*60)
                
                # إغلاق نهائي
                try:
                    self.context.close()
                    browser.close()
                except:
                    pass
                
                return True
                
        except KeyboardInterrupt:
            logger.info("\n🛑 تم إوقف التشغيل بواسطة المستخدم")
            return False
            
        except Exception as e:
            logger.error(f"💀 خطأ حرج: {e}")
            logger.exception("تفاصيل الخطأ:")
            return False

    def run(self):
        """واجهة تشغيل متوافقة"""
        return self.run_king_mode()


# ==================== نقطة الدخول الرئيسية ====================
if __name__ == "__main__":
    """
    نقطة الدخول الرئيسية للبرنامج
    الاستخدام: python king_sniper.py
    """
    
    print("="*60)
    print("👑 King Sniper v11.0.0 - نظام الحجز الدبلوماسي فائق السرعة")
    print("="*60)
    print("الميزات:")
    print("  ⚡ الحقن المباشر للDOM (أسرع 100x)")
    print("  ⏰ مزامنة NTP بدقة ±0.1 ثانية")
    print("  🔄 إدارة جلسات ذكية مع Hard Reset")
    print("  🔗 بناء روابط آمن مع urljoin")
    print("="*60)
    
    try:
        sniper = KingSniper()
        success = sniper.run()
        
        if success:
            print("\n✅ التشغيل مكتمل بنجاح!")
            sys.exit(0)
        else:
            print("\n❌ انتهى التشغيل بدون نجاح")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف التشغيل بواسطة المستخدم")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n💀 خطأ فادح: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)