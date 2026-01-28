"""
ElitePro Sniper - النسخة النهائية للإنتاج
الإصدار: 10.0.0 (Production Ready)
ملاحظة: تم تغيير اسم الفئة إلى EliteSniper ليتوافق مع متطلبات الاستيراد
"""

import time
import random
import datetime
import logging
import re
import sys
import json
from typing import Optional, List, Dict, Tuple, Any

import pytz
from playwright.sync_api import sync_playwright, Page, BrowserContext, Browser

# ==================== IMPORTS الأساسية ====================
# تم تعديل المسار ليتوافق مع الهيكل الشائع
try:
    # محاولة استيراد من المسار المباشر
    from config import Config
    from captcha import CaptchaSolver
    from notifier import send_alert, send_photo
except ImportError:
    try:
        # محاولة استيراد من المسار النسبي
        from .config import Config
        from .captcha import CaptchaSolver
        from .notifier import send_alert, send_photo
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
        logging.FileHandler('elitepro_sniper.log') if getattr(Config, 'ENABLE_FILE_LOG', False) 
        else logging.NullHandler()
    ]
)
logger = logging.getLogger("EliteSniper")

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
class EliteSniper:  # ⚠️ تم تغيير الاسم من EliteProSniper إلى EliteSniper
    """
    EliteSniper - النسخة النهائية المتكاملة للإنتاج
    تم تغيير اسم الفئة ليتوافق مع متطلبات الاستيراد
    """
    
    def __init__(self):
        """تهيئة النظام مع التحقق من التكوين"""
        self._validate_config()
        
        # المكونات الأساسية
        self.solver = CaptchaSolver()
        self.base_url = self._prepare_base_url(Config.TARGET_URL)
        self.timezone = pytz.timezone(getattr(Config, 'TIMEZONE', 'Asia/Aden'))
        
        # إعدادات الأداء
        self.user_agents = getattr(Config, 'USER_AGENTS', [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/124.0"
        ])
        
        # حالة النظام
        self.consecutive_errors = 0
        self.session_id = f"session_{int(time.time())}_{random.randint(1000, 9999)}"
        self.start_time = datetime.datetime.now()
        self.is_poisoned = False
        
        # إحصاءات
        self.stats = {
            'scans': 0,
            'captchas_solved': 0,
            'captchas_failed': 0,
            'forms_filled': 0,
            'errors': 0,
            'success': False
        }
        
        logger.info(f"🚀 EliteSniper v10.0.0 - Session: {self.session_id}")
    
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
    
    # ==================== إدارة الوقت ====================
    def get_operational_mode(self) -> str:
        """تحديد نمط التشغيل بناءً على الوقت"""
        try:
            now = datetime.datetime.now(self.timezone)
            
            # النافذة الهجومية: 01:59:50 - 02:10:00
            if (now.hour == 1 and now.minute == 59 and now.second >= 50) or \
               (now.hour == 2 and now.minute <= 10):
                return "ASSAULT"
            
            # مرحلة الإحماء: 01:45 - 01:59
            elif now.hour == 1 and now.minute >= 45:
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
            return random.uniform(0.05, 0.15)  # 50-150ms
        
        elif mode == "WARMUP":
            return random.uniform(1.0, 2.0)    # 1-2 ثانية
        
        else:  # SCOUT
            return random.uniform(30.0, 60.0)  # 30-60 ثانية
    
    # ==================== إدارة المتصفح ====================
    def create_stealth_context(self, browser: Browser) -> Tuple[BrowserContext, Page]:
        """إنشاء سياق متخفي وآمن"""
        try:
            context = browser.new_context(
                user_agent=random.choice(self.user_agents),
                viewport={
                    "width": 1366 + random.randint(-30, 30),
                    "height": 768 + random.randint(-30, 30)
                },
                locale="en-US",
                timezone_id="Asia/Aden",
                java_script_enabled=True,
                ignore_https_errors=True
            )
            
            page = context.new_page()
            
            # منع اكتشاف الأتمتة
            stealth_script = """
            // إخفاء WebDriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // تعديل الخصائص الأخرى
            Object.defineProperty(navigator, 'plugins', { 
                get: () => [1, 2, 3, 4, 5] 
            });
            
            Object.defineProperty(navigator, 'languages', { 
                get: () => ['en-US', 'en'] 
            });
            
            // إخفاء Chrome runtime
            window.chrome = { runtime: {} };
            """
            
            page.add_init_script(stealth_script)
            
            # تحسين الأداء بحظر الموارد غير الضرورية
            def route_handler(route):
                resource_type = route.request.resource_type
                # حظر الصور والفيديو فقط، السماح بـ CSS والخطوط
                if resource_type in ["image", "media"]:
                    route.abort()
                else:
                    route.continue_()
            
            page.route("**/*", route_handler)
            
            # مهلات ذكية
            context.set_default_timeout(20000)  # 20 ثانية
            context.set_default_navigation_timeout(30000)  # 30 ثانية للتنقل
            
            logger.info("✨ السياق الجديد جاهز")
            return context, page
            
        except Exception as e:
            logger.error(f"❌ فشل إنشاء السياق: {e}")
            raise
    
    # ==================== نظام الكابتشا الذكي ====================
    def solve_captcha_intelligently(self, page: Page, location: str = "GENERAL") -> bool:
        """
        حل الكابتشا بذكاء مع معالجة أخطاء شاملة
        """
        max_attempts = 3
        
        for attempt in range(1, max_attempts + 1):
            try:
                # التحقق من وجود كابتشا
                if not page.locator("input[name='captchaText']").first.is_visible(timeout=1000):
                    return True
                
                logger.info(f"🧩 [{location}] محاولة كابتشا {attempt}/{max_attempts}")
                
                # البحث عن عنصر الكابتشا
                captcha_selectors = [
                    "captcha > div",
                    "div.captcha",
                    ".captcha-image",
                    "img[src*='captcha']",
                    "div[class*='captcha']"
                ]
                
                captcha_element = None
                for selector in captcha_selectors:
                    if page.locator(selector).first.is_visible(timeout=1000):
                        captcha_element = page.locator(selector).first
                        break
                
                if not captcha_element:
                    logger.warning(f"⚠️ [{location}] عنصر الكابتشا غير موجود")
                    self.stats['captchas_failed'] += 1
                    return False
                
                # الانتظار لتحميل الصورة
                page.wait_for_timeout(300)
                
                # التقاط لقطة الشاشة
                try:
                    screenshot = captcha_element.screenshot()
                    if len(screenshot) < 1000:  # صورة صغيرة جداً (تالفة)
                        logger.warning("⚫ كابتشا تالفة محتملة")
                        page.wait_for_timeout(500)
                        continue
                except:
                    pass
                
                # حل الكابتشا
                try:
                    code = self.solver.solve(captcha_element.screenshot())
                    if not code:
                        logger.warning("⚠️ فشل حل الكابتشا")
                        continue
                    
                    # تنظيف الكود
                    code = str(code).replace(" ", "").strip()[:10]
                    
                    if len(code) < 4:
                        logger.warning(f"⚠️ كود قصير جداً: {len(code)} أحرف")
                        continue
                    
                    # إدخال الكود
                    page.fill("input[name='captchaText']", code)
                    
                    # إرسال النموذج
                    submit_selectors = [
                        "input[type='submit']",
                        "button[type='submit']",
                        "button:has-text('Submit')",
                        "button:has-text('Continue')"
                    ]
                    
                    submitted = False
                    for selector in submit_selectors:
                        if page.locator(selector).first.is_visible(timeout=500):
                            page.locator(selector).first.click()
                            submitted = True
                            break
                    
                    if not submitted:
                        page.keyboard.press("Enter")
                    
                    # الانتظار للنتيجة
                    wait_time = 2000 if self.get_operational_mode() == "ASSAULT" else 4000
                    page.wait_for_timeout(wait_time)
                    
                    # التحقق من النجاح
                    if not page.locator("input[name='captchaText']").first.is_visible(timeout=1000):
                        self.stats['captchas_solved'] += 1
                        logger.info(f"✅ [{location}] كابتشا محلولة بنجاح")
                        return True
                    else:
                        logger.warning(f"⚠️ [{location}] الكابتشا مازالت موجودة، إعادة المحاولة")
                        page.wait_for_timeout(1000)
                        continue
                        
                except Exception as e:
                    logger.error(f"❌ [{location}] خطأ في حل الكابتشا: {str(e)[:100]}")
                    continue
                    
            except Exception as e:
                logger.error(f"❌ [{location}] خطأ عام في الكابتشا: {str(e)[:100]}")
                self.stats['errors'] += 1
        
        self.stats['captchas_failed'] += 1
        logger.error(f"❌ [{location}] فشل بعد {max_attempts} محاولات")
        return False
    
    # ==================== نظام التعيين الديناميكي ====================
    def build_dynamic_field_map(self, page: Page) -> List[FieldMapping]:
        """
        بناء خريطة الحقول الديناميكية من الصفحة
        """
        field_mappings = [
            FieldMapping(
                "LAST_NAME",
                ["last name", "family name", "surname", "nachname", "الاسم الأخير"],
                Config.LAST_NAME
            ),
            FieldMapping(
                "FIRST_NAME", 
                ["first name", "given name", "vorname", "الاسم الأول"],
                Config.FIRST_NAME
            ),
            FieldMapping(
                "EMAIL",
                ["email", "e-mail", "mail address", "البريد الإلكتروني"],
                Config.EMAIL
            ),
            FieldMapping(
                "PASSPORT",
                ["passport", "passport number", "reisepass", "رقم الجواز", "وثيقة سفر"],
                Config.PASSPORT
            ),
            FieldMapping(
                "PHONE",
                ["phone", "telephone", "mobile", "contact number", "رقم الهاتف"],
                Config.PHONE.replace("+", "00").strip()
            )
        ]
        
        try:
            # البحث عن جميع labels
            labels = page.evaluate("""
                () => {
                    const allElements = Array.from(document.querySelectorAll('*'));
                    const labels = [];
                    
                    for(const el of allElements) {
                        const text = el.textContent || el.innerText || "";
                        const trimmed = text.trim();
                        
                        // إذا كان نص العنصر يشبه label
                        if (trimmed && trimmed.length < 100 && 
                            (el.tagName === 'LABEL' || 
                             el.tagName === 'SPAN' || 
                             el.tagName === 'DIV' || 
                             el.tagName === 'P')) {
                            
                            // البحث عن العنصر المرتبط
                            let associatedInput = null;
                            
                            // طريقة 1: for attribute
                            if (el.tagName === 'LABEL' && el.htmlFor) {
                                associatedInput = document.getElementById(el.htmlFor);
                            }
                            
                            // طريقة 2: العنصر التالي
                            if (!associatedInput) {
                                let sibling = el.nextElementSibling;
                                while(sibling && !associatedInput) {
                                    if (sibling.tagName === 'INPUT' || 
                                        sibling.tagName === 'SELECT' || 
                                        sibling.tagName === 'TEXTAREA') {
                                        associatedInput = sibling;
                                    }
                                    sibling = sibling.nextElementSibling;
                                }
                            }
                            
                            // طريقة 3: العنصر داخل
                            if (!associatedInput) {
                                const inputInside = el.querySelector('input, select, textarea');
                                if (inputInside) associatedInput = inputInside;
                            }
                            
                            if (associatedInput) {
                                labels.push({
                                    text: trimmed.toLowerCase(),
                                    element: el,
                                    input: associatedInput,
                                    inputName: associatedInput.getAttribute('name'),
                                    inputId: associatedInput.id
                                });
                            }
                        }
                    }
                    
                    return labels;
                }
            """)
            
            # تعيين الحقول بناءً على الـ labels
            for mapping in field_mappings:
                for label_info in labels:
                    for pattern in mapping.patterns:
                        if pattern in label_info['text']:
                            mapping.found_name = label_info['inputName']
                            if label_info['inputId']:
                                mapping.found_selector = f"#{label_info['inputId']}"
                            elif label_info['inputName']:
                                mapping.found_selector = f"input[name='{label_info['inputName']}']"
                            
                            logger.info(f"🔗 عُيّن: {mapping.field_type} -> {mapping.found_selector}")
                            break
                    
                    if mapping.found_name:
                        break
            
            return field_mappings
            
        except Exception as e:
            logger.error(f"❌ خطأ في بناء خريطة الحقول: {e}")
            return field_mappings
    
    def fill_form_with_dynamic_mapping(self, page: Page, field_mappings: List[FieldMapping]) -> bool:
        """
        تعبئة النموذج باستخدام التعيين الديناميكي
        """
        try:
            success_count = 0
            total_fields = len(field_mappings)
            
            # تعبئة كل حقل
            for mapping in field_mappings:
                filled = False
                
                # المحاولة 1: باستخدام التعيين الديناميكي
                if mapping.found_selector:
                    try:
                        page.fill(mapping.found_selector, mapping.value)
                        page.wait_for_timeout(50)  # تأخير بسيط بين الحقول
                        filled = True
                        logger.debug(f"✅ {mapping.field_type}: ملء ديناميكي")
                    except:
                        filled = False
                
                # المحاولة 2: الأسماء الثابتة (fallback)
                if not filled:
                    fallback_selectors = {
                        "LAST_NAME": ["input[name='lastname']", "input[name='familyName']"],
                        "FIRST_NAME": ["input[name='firstname']", "input[name='givenName']"],
                        "EMAIL": ["input[name='email']", "input[name='eMail']"],
                        "PASSPORT": ["input[name='passportNumber']", "input[name='fields[0].content']"],
                        "PHONE": ["input[name='phone']", "input[name='fields[1].content']"]
                    }
                    
                    for selector in fallback_selectors.get(mapping.field_type, []):
                        try:
                            if page.locator(selector).first.is_visible(timeout=500):
                                page.fill(selector, mapping.value)
                                filled = True
                                logger.debug(f"⚠️ {mapping.field_type}: ملء باستخدام fallback")
                                break
                        except:
                            continue
                
                if filled:
                    success_count += 1
                else:
                    logger.warning(f"⚠️ فشل ملء حقل: {mapping.field_type}")
            
            # اختيار فئة التأشيرة
            visa_selected = self._select_visa_category_smart(page)
            if visa_selected:
                success_count += 1
            
            # معالجة حقل تكرار الإيميل
            email_repeat_filled = self._fill_email_repeat(page, Config.EMAIL)
            if email_repeat_filled:
                success_count += 1
            
            self.stats['forms_filled'] += 1
            logger.info(f"📝 تم تعبئة {success_count}/{total_fields + 2} حقول")
            
            return success_count >= total_fields  # نجاح إذا عُبئت معظم الحقول
            
        except Exception as e:
            logger.error(f"❌ خطأ في تعبئة النموذج: {e}")
            return False
    
    def _fill_email_repeat(self, page: Page, email: str) -> bool:
        """تعبئة حقل تكرار الإيميل"""
        try:
            repeat_selectors = [
                "input[name='emailrepeat']",
                "input[name='emailRepeat']",
                "input[name='confirmEmail']",
                "input[name='email_confirm']"
            ]
            
            for selector in repeat_selectors:
                if page.locator(selector).first.is_visible(timeout=500):
                    page.fill(selector, email)
                    return True
            
            return False
        except:
            return False
    
    def _select_visa_category_smart(self, page: Page) -> bool:
        """
        اختيار ذكي لفئة التأشيرة باستخدام كلمات V1 المفتاحية
        """
        try:
            # البحث عن عنصر الـ select
            select_selectors = [
                "select[name='fields[2].content']",
                "select[name*='visa']",
                "select[name*='category']",
                "select[name*='purpose']",
                "select"
            ]
            
            select_element = None
            select_selector = None
            
            for selector in select_selectors:
                if page.locator(selector).first.is_visible(timeout=1000):
                    select_element = page.locator(selector).first
                    select_selector = selector
                    break
            
            if not select_element:
                logger.warning("⚠️ لم يتم العثور على عنصر select")
                return False
            
            # كلمات V1 المفتاحية بالترتيب
            v1_keywords = [
                "yemeni national",
                "student visa", 
                "language course",
                "studium",
                "sprachkurs",
                "university"
            ]
            
            # الحصول على جميع الخيارات
            options = select_element.locator("option").all()
            options_info = []
            
            for i, option in enumerate(options):
                try:
                    text = option.text_content().strip().lower()
                    value = option.get_attribute("value") or ""
                    options_info.append({
                        "index": i,
                        "text": text,
                        "value": value
                    })
                except:
                    continue
            
            # البحث عن أفضل خيار
            selected_index = 1  # افتراضي: الخيار الثاني
            
            for keyword in v1_keywords:
                for option in options_info:
                    if keyword in option["text"]:
                        selected_index = option["index"]
                        logger.info(f"📋 وجدت كلمة '{keyword}' في: {option['text'][:50]}")
                        break
                if selected_index != 1:
                    break
            
            # التحديد
            if selected_index < len(options):
                select_element.select_option(index=selected_index)
                logger.info(f"✅ تم اختيار الخيار {selected_index + 1}")
                return True
            else:
                # Fallback آمن
                if len(options) > 1:
                    select_element.select_option(index=1)
                    logger.info("⚠️ استخدام الخيار الافتراضي (2)")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ خطأ في اختيار الفئة: {e}")
            return False
    
    # ==================== نظام المسح ====================
    def generate_priority_month_urls(self) -> List[str]:
        """إنشاء روابط الأشهر بأولويات استراتيجية"""
        try:
            today = datetime.datetime.now(self.timezone).date()
            base_clean = self.base_url.split("&dateStr=")[0] if "&dateStr=" in self.base_url else self.base_url
            
            urls = []
            
            # أولويات V4: مارس(3)، أبريل(4)، فبراير(2)، مايو(5)
            priority_offsets = [2, 3, 1, 4]
            
            for offset in priority_offsets:
                future_month = (today.month + offset - 1) % 12 + 1
                future_year = today.year + ((today.month + offset - 1) // 12)
                date_str = f"15.{future_month:02d}.{future_year}"
                full_url = f"{base_clean}&dateStr={date_str}"
                urls.append(full_url)
            
            return urls
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء روابط الأشهر: {e}")
            return []
    
    def scan_month_for_days(self, page: Page, url: str) -> Tuple[bool, List[str]]:
        """مسح الشهر للبحث عن أيام متاحة"""
        try:
            self.stats['scans'] += 1
            
            # التحميل
            mode = self.get_operational_mode()
            timeout = 10000 if mode == "ASSAULT" else 20000
            
            logger.info(f"🔍 مسح: {url.split('dateStr=')[-1] if 'dateStr=' in url else url}")
            
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            
            # حل كابتشا الشهر
            if not self.solve_captcha_intelligently(page, "MONTH"):
                return False, []
            
            # البحث عن الأيام
            day_links = []
            
            # محاولة بالأنماط المختلفة
            link_patterns = [
                "a.arrow[href*='appointment_showDay']",
                "a[href*='showDay']",
                "td.buchbar a",
                "a:has-text('Book')",
                "a:has-text('Appointment')"
            ]
            
            for pattern in link_patterns:
                try:
                    links = page.locator(pattern).all()
                    if links:
                        for link in links:
                            try:
                                href = link.get_attribute("href")
                                if href and "showDay" in href:
                                    # بناء URL كامل
                                    if href.startswith("http"):
                                        full_url = href
                                    elif href.startswith("/"):
                                        full_url = f"https://service2.diplo.de{href}"
                                    else:
                                        base = self.base_url.split("/extern")[0]
                                        full_url = f"{base}/{href}"
                                    
                                    day_links.append(full_url)
                            except:
                                continue
                        
                        if day_links:
                            break
                except:
                    continue
            
            if day_links:
                logger.info(f"🔥 وجدت {len(day_links)} يوم/أيام")
                return True, day_links[:3]  # أخذ أول 3 أيام فقط
            
            logger.info("📭 لا توجد أيام متاحة")
            return True, []
            
        except Exception as e:
            logger.error(f"❌ خطأ في مسح الشهر: {str(e)[:100]}")
            self.stats['errors'] += 1
            return False, []
    
    def scan_day_for_slots(self, page: Page, day_url: str) -> Tuple[bool, List[str]]:
        """مسح اليوم للبحث عن مواعيد"""
        try:
            # الانتقال لليوم
            page.goto(day_url, timeout=15000, wait_until="domcontentloaded")
            
            # حل كابتشا اليوم
            if not self.solve_captcha_intelligently(page, "DAY"):
                return False, []
            
            # البحث عن المواعيد
            slot_links = []
            
            slot_patterns = [
                "a.arrow[href*='appointment_showForm']",
                "a[href*='showForm']",
                "td a:has-text('Select')",
                "a:has-text('Time')"
            ]
            
            for pattern in slot_patterns:
                try:
                    links = page.locator(pattern).all()
                    if links:
                        for link in links:
                            try:
                                href = link.get_attribute("href")
                                if href and "showForm" in href:
                                    if href.startswith("http"):
                                        full_url = href
                                    elif href.startswith("/"):
                                        full_url = f"https://service2.diplo.de{href}"
                                    else:
                                        base = self.base_url.split("/extern")[0]
                                        full_url = f"{base}/{href}"
                                    
                                    slot_links.append(full_url)
                            except:
                                continue
                        
                        if slot_links:
                            break
                except:
                    continue
            
            if slot_links:
                logger.info(f"⏰ وجدت {len(slot_links)} موعد/مواعيد")
                return True, slot_links[:2]  # أخذ أول موعدين فقط
            
            logger.info("⏳ لا توجد مواعيد متاحة")
            return True, []
            
        except Exception as e:
            logger.error(f"❌ خطأ في مسح اليوم: {e}")
            return False, []
    
    # ==================== محرك الحجز ====================
    def attempt_booking(self, page: Page, slot_url: str) -> bool:
        """محاولة حجز موعد"""
        try:
            logger.info("🎯 بدء محاولة الحجز...")
            
            # الانتقال لصفحة الحجز
            page.goto(slot_url, timeout=15000, wait_until="domcontentloaded")
            
            # حل كابتشا النموذج
            if not self.solve_captcha_intelligently(page, "FORM"):
                return False
            
            # التحقق من وجود النموذج
            if not page.locator("form").first.is_visible(timeout=5000):
                logger.error("❌ النموذج غير موجود")
                return False
            
            # بناء خريطة الحقول الديناميكية
            field_mappings = self.build_dynamic_field_map(page)
            
            # تعبئة النموذج
            if not self.fill_form_with_dynamic_mapping(page, field_mappings):
                logger.error("❌ فشل تعبئة النموذج")
                return False
            
            # الإرسال النهائي
            return self._submit_booking_form(page)
            
        except Exception as e:
            logger.error(f"❌ خطأ في محاولة الحجز: {e}")
            return False
    
    def _submit_booking_form(self, page: Page, max_attempts: int = 3) -> bool:
        """إرسال نموذج الحجز مع محاولات متعددة"""
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"📤 محاولة إرسال {attempt}/{max_attempts}")
                
                # حل كابتشا الإرسال النهائي
                if not self.solve_captcha_intelligently(page, "SUBMIT"):
                    if page.locator("input[name='lastname']").first.is_visible(timeout=1000):
                        continue  # مازال في النموذج
                    else:
                        return False  # فقد النموذج
                
                # البحث عن زر الإرسال
                submit_selectors = [
                    "input[type='submit']",
                    "button[type='submit']",
                    "button:has-text('Book')",
                    "button:has-text('Submit')",
                    "button:has-text('Confirm')"
                ]
                
                submitted = False
                for selector in submit_selectors:
                    if page.locator(selector).first.is_visible(timeout=1000):
                        page.locator(selector).first.click()
                        submitted = True
                        break
                
                if not submitted:
                    # محاولة باستخدام Enter
                    page.keyboard.press("Enter")
                    submitted = True
                
                # الانتظار للنتيجة
                page.wait_for_timeout(5000)
                
                # التحقق من النجاح
                page_content = page.content().lower()
                
                success_indicators = [
                    "appointment number",
                    "successfully booked",
                    "booking confirmed",
                    "vorgang wurde gespeichert",
                    "termin wurde gebucht"
                ]
                
                for indicator in success_indicators:
                    if indicator in page_content:
                        # استخراج تفاصيل الحجز
                        appointment_num = re.search(r"appointment number is\s+(\d+)", page_content, re.IGNORECASE)
                        appointment_date = re.search(r"(\d{2}\.\d{2}\.\d{4})", page_content)
                        
                        success_msg = "\n" + "="*50 + "\n"
                        success_msg += "🎉🎉🎉 الحجز الناجح! 🎉🎉🎉\n"
                        if appointment_num:
                            success_msg += f"📋 رقم الحجز: {appointment_num.group(1)}\n"
                        if appointment_date:
                            success_msg += f"📅 التاريخ: {appointment_date.group(1)}\n"
                        success_msg += f"👤 الاسم: {Config.FIRST_NAME} {Config.LAST_NAME}\n"
                        success_msg += "="*50
                        
                        logger.info(success_msg)
                        
                        # إرسال الإشعارات
                        self._send_success_notifications(page, appointment_num, appointment_date)
                        
                        self.stats['success'] = True
                        return True
                
                # إذا مازال في النموذج، حاول مرة أخرى
                if page.locator("input[name='lastname']").first.is_visible(timeout=1000):
                    logger.warning("🔄 مازال في النموذج، إعادة المحاولة...")
                    page.wait_for_timeout(2000)
                    continue
                
                # إذا ظهر خطأ
                error_indicators = ["error", "fehler", "خطأ", "invalid", "ungültig"]
                for indicator in error_indicators:
                    if indicator in page_content:
                        logger.error("❌ خطأ في الخادم")
                        return False
                
            except Exception as e:
                logger.error(f"❌ خطأ في الإرسال: {str(e)[:100]}")
                if attempt < max_attempts:
                    page.wait_for_timeout(3000)
        
        logger.error(f"❌ فشل بعد {max_attempts} محاولات إرسال")
        return False
    
    def _send_success_notifications(self, page: Page, appointment_num, appointment_date):
        """إرسال إشعارات النجاح"""
        try:
            # حفظ لقطة الشاشة
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"booking_success_{timestamp}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            
            # بناء رسالة الإشعار
            alert_message = f"""
✅ الحجز الناجح!

رقم الحجز: {appointment_num.group(1) if appointment_num else 'غير معروف'}
التاريخ: {appointment_date.group(1) if appointment_date else 'غير معروف'}
الجلسة: {self.session_id}
الوقت: {datetime.datetime.now().strftime('%H:%M:%S')}
            """
            
            # إرسال الإشعار
            send_alert(alert_message.strip())
            
            # إرسال الصورة
            photo_caption = f"✅ حجز مؤكد - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            send_photo(screenshot_path, caption=photo_caption)
            
        except Exception as e:
            logger.error(f"⚠️ خطأ في إرسال الإشعارات: {e}")
    
    # ==================== الدورة الرئيسية ====================
    def run(self):
        """الدورة الرئيسية للتشغيل"""
        logger.info("="*60)
        logger.info("🚀 بدء تشغيل EliteSniper v10.0.0")
        logger.info("="*60)
        
        try:
            with sync_playwright() as p:
                # إعداد المتصفح
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--no-first-run",
                        "--disable-extensions",
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process"
                    ],
                    timeout=60000
                )
                
                # إنشاء السياق الأول
                context, page = self.create_stealth_context(browser)
                
                cycle = 0
                
                while not self.stats['success']:
                    cycle += 1
                    self.consecutive_errors = 0
                    
                    logger.info(f"\n🔁 الدورة #{cycle}")
                    logger.info(f"📊 النمط: {self.get_operational_mode()}")
                    
                    # التحقق من الأخطاء المتتالية
                    if self.consecutive_errors >= 10:
                        logger.critical("💀 أخطاء متتالية كثيرة، إعادة التشغيل...")
                        try:
                            context.close()
                        except:
                            pass
                        context, page = self.create_stealth_context(browser)
                        self.consecutive_errors = 0
                        self.is_poisoned = False
                    
                    # التأخير بين الدورات
                    delay = self.calculate_delay()
                    if delay > 1:
                        logger.info(f"⏳ تأخير: {delay:.1f} ثانية")
                        time.sleep(delay)
                    
                    # الحصول على روابط الأشهر ذات الأولوية
                    month_urls = self.generate_priority_month_urls()
                    
                    if not month_urls:
                        logger.error("❌ لا توجد روابط أشهر")
                        time.sleep(60)
                        continue
                    
                    # مسح كل شهر
                    for month_url in month_urls:
                        if self.stats['success']:
                            break
                        
                        # مسح الشهر
                        scan_success, day_urls = self.scan_month_for_days(page, month_url)
                        
                        if not scan_success:
                            self.consecutive_errors += 1
                            continue
                        
                        if not day_urls:
                            continue  # لا توجد أيام، انتقل للشهر التالي
                        
                        # مسح كل يوم
                        for day_url in day_urls:
                            if self.stats['success']:
                                break
                            
                            # مسح اليوم
                            day_success, slot_urls = self.scan_day_for_slots(page, day_url)
                            
                            if not day_success:
                                self.consecutive_errors += 1
                                break  # اذهب للشهر التالي
                            
                            if not slot_urls:
                                break  # لا توجد مواعيد، اذهب لليوم التالي
                            
                            # محاولة الحجز لكل موعد
                            for slot_url in slot_urls:
                                if self.stats['success']:
                                    break
                                
                                logger.info(f"🎯 محاولة حجز: {slot_url}")
                                
                                # محاولة الحجز
                                if self.attempt_booking(page, slot_url):
                                    logger.info("🏆 المهمة مكتملة بنجاح!")
                                    break
                                else:
                                    self.consecutive_errors += 1
                                    logger.warning("⚠️ فشل الحجز، الانتقال للموعد التالي")
                                    page.wait_for_timeout(2000)
                    
                    # عرض إحصاءات الدورة
                    logger.info(f"📊 ختام الدورة #{cycle}")
                    logger.info(f"   • المسوحات: {self.stats['scans']}")
                    logger.info(f"   • الكابتشات الناجحة: {self.stats['captchas_solved']}")
                    logger.info(f"   • النماذج المملوءة: {self.stats['forms_filled']}")
                    logger.info(f"   • الأخطاء: {self.stats['errors']}")
                    logger.info(f"   • الأخطاء المتتالية: {self.consecutive_errors}")
                    
                    # إذا استمر التشغيل لفترة طويلة بدون نجاح
                    runtime = datetime.datetime.now() - self.start_time
                    if runtime.total_seconds() > 3600 * 6:  # 6 ساعات
                        logger.warning("🕒 تشغيل طويل، إعادة التشغيل للحفاظ على الأداء")
                        try:
                            context.close()
                        except:
                            pass
                        context, page = self.create_stealth_context(browser)
                        self.start_time = datetime.datetime.now()
                
                # النجاح - إغلاق نظيف
                logger.info("\n" + "="*60)
                logger.info("🎊 المهمة مكتملة بنجاح!")
                logger.info("="*60)
                
                try:
                    context.close()
                    browser.close()
                except:
                    pass
                
                return True
                
        except KeyboardInterrupt:
            logger.info("\n🛑 تم إيقاف التشغيل بواسطة المستخدم")
            return False
            
        except Exception as e:
            logger.error(f"💀 خطأ حرج: {e}")
            import traceback
            traceback.print_exc()
            return False


# ==================== نقطة الدخول الرئيسية ====================
def main():
    """
    نقطة الدخول الرئيسية للبرنامج
    """
    print("="*60)
    print("🎯 EliteSniper v10.0.0 - نظام الحجز الدبلوماسي")
    print("="*60)
    
    try:
        sniper = EliteSniper()
        success = sniper.run()
        
        if success:
            print("\n✅ التشغيل مكتمل بنجاح!")
            return 0
        else:
            print("\n❌ انتهى التشغيل بدون نجاح")
            return 1
            
    except Exception as e:
        print(f"\n💀 خطأ فادح: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())