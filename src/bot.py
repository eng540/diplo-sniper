"""
EliteSniper - النسخة المُحسنة لبيئة Railway
إصدار: 10.1.0 (Railway Optimized)
"""

import time
import random
import datetime
import logging
import re
import sys
import json
import os
from typing import Optional, List, Dict, Tuple, Any

import pytz
from playwright.sync_api import sync_playwright, Page, BrowserContext, Browser

# ==================== IMPORTS الأساسية ====================
try:
    from src.config import Config
    from src.captcha import CaptchaSolver
    from sec.notifier import send_alert, send_photo
except ImportError:
    try:
        from sec.config import Config
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
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("EliteSniper")

# ==================== إعدادات Railway ====================
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') == 'production' or os.getenv('RAILWAY_ENVIRONMENT') == 'development'
IS_CONTAINER = os.getenv('CONTAINER') == 'true' or os.path.exists('/.dockerenv')

# ==================== الفئة الرئيسية ====================
class EliteSniper:
    """
    EliteSniper - النسخة المُحسنة لبيئة Railway
    """
    
    def __init__(self):
        """تهيئة النظام مع إعدادات Railway"""
        self._validate_config()
        
        # المكونات الأساسية
        self.solver = CaptchaSolver()
        self.base_url = self._prepare_base_url(Config.TARGET_URL)
        self.timezone = pytz.timezone(getattr(Config, 'TIMEZONE', 'Asia/Aden'))
        
        # إعدادات متقدمة لـ Railway
        self.is_railway = IS_RAILWAY
        self.is_container = IS_CONTAINER
        
        # إعدادات المهلات الخاصة بـ Railway
        if self.is_railway or self.is_container:
            self.timeout_settings = {
                'navigation': 45000,  # 45 ثانية للتنقل في Railway
                'default': 30000,     # 30 ثانية للعمليات العامة
                'captcha': 10000,     # 10 ثوانٍ للكابتشا
                'loading': 25000      # 25 ثانية لتحميل الصفحات
            }
            logger.info("⚙️ تم تحميل إعدادات Railway المتقدمة")
        else:
            self.timeout_settings = {
                'navigation': 30000,
                'default': 20000,
                'captcha': 8000,
                'loading': 20000
            }
        
        # إعدادات الأداء
        self.user_agents = getattr(Config, 'USER_AGENTS', [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
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
            'success': False,
            'timeouts': 0
        }
        
        logger.info(f"🚀 EliteSniper v10.1.0 - Session: {self.session_id}")
        logger.info(f"🌐 البيئة: {'Railway' if self.is_railway else 'Local'} | {'Container' if self.is_container else 'Native'}")
    
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
    
    # ==================== إدارة المتصفح لـ Railway ====================
    def create_railway_context(self, browser: Browser) -> Tuple[BrowserContext, Page]:
        """إنشاء سياق محسّن لـ Railway"""
        try:
            # إعدادات متقدمة لـ Railway
            context_args = {
                'user_agent': random.choice(self.user_agents),
                'viewport': {
                    "width": 1366 + random.randint(-30, 30),
                    "height": 768 + random.randint(-30, 30)
                },
                'locale': "en-US",
                'timezone_id': "Asia/Aden",
                'java_script_enabled': True,
                'ignore_https_errors': True,
            }
            
            # إعدادات إضافية لـ Railway
            if self.is_railway:
                context_args.update({
                    'bypass_csp': True,
                    'accept_downloads': False,
                    'has_touch': False,
                    'is_mobile': False,
                    'device_scale_factor': 1,
                })
            
            context = browser.new_context(**context_args)
            
            page = context.new_page()
            
            # scripts إخفاء متقدمة لـ Railway
            stealth_script = """
            // إخفاء WebDriver
            Object.defineProperty(navigator, 'webdriver', { 
                get: () => undefined,
                configurable: true
            });
            
            // تعديل خصائص المتصفح
            Object.defineProperty(navigator, 'plugins', { 
                get: () => [1, 2, 3, 4, 5],
                configurable: true
            });
            
            Object.defineProperty(navigator, 'languages', { 
                get: () => ['en-US', 'en'],
                configurable: true
            });
            
            // إخفاء Chrome في Railway
            if (window.chrome) {
                Object.defineProperty(window, 'chrome', {
                    get: () => undefined,
                    configurable: true
                });
            }
            
            // إخفاء علامات الأتمتة
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // منع اكتشاف Playwright
            window.__playwright = undefined;
            window.playwright = undefined;
            
            // إخفاء الـ permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            """
            
            page.add_init_script(stealth_script)
            
            # معالجة الطلبات لـ Railway
            def railway_route_handler(route):
                request = route.request
                url = request.url
                resource_type = request.resource_type
                
                # حظر الموارد غير الضرورية في Railway
                blocked_resources = ["image", "media", "font"]
                
                # في Railway، نحتاج للسماح بـ CSS والخطوط لمنع المشاكل
                if resource_type in blocked_resources:
                    if any(ext in url for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.mp4', '.webm']):
                        route.abort()
                        return
                
                # السماح بجميع الطلبات الأخرى
                route.continue_()
            
            page.route("**/*", railway_route_handler)
            
            # مهلات Railway المطوّلة
            context.set_default_timeout(self.timeout_settings['default'])
            context.set_default_navigation_timeout(self.timeout_settings['navigation'])
            
            logger.info(f"✨ سياق Railway جاهز | المهلات: {self.timeout_settings}")
            return context, page
            
        except Exception as e:
            logger.error(f"❌ فشل إنشاء سياق Railway: {e}")
            raise
    
    # ==================== نظام المسح المُحسّن ====================
    def smart_page_goto(self, page: Page, url: str, description: str = "الصفحة") -> bool:
        """
        تنقل ذكي مع معالجة مهلات Railway
        """
        max_retries = 2
        base_timeout = self.timeout_settings['loading']
        
        for retry in range(max_retries):
            try:
                # زيادة المهلة في Railway
                timeout_multiplier = 1.5 if self.is_railway else 1.0
                current_timeout = int(base_timeout * timeout_multiplier * (retry + 1))
                
                logger.info(f"🌐 {description} | محاولة {retry+1}/{max_retries} | مهلة: {current_timeout}ms")
                
                # استخدام wait_until مختلفة بناءً على المحاولة
                wait_until = "domcontentloaded" if retry == 0 else "load"
                
                # إضافة headers لتحسين الأداء في Railway
                extra_headers = {}
                if self.is_railway:
                    extra_headers = {
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    }
                
                response = page.goto(
                    url,
                    timeout=current_timeout,
                    wait_until=wait_until,
                    referer=self.base_url if 'diplo' in url else None
                )
                
                if response and response.status >= 400:
                    logger.warning(f"⚠️ {description} | حالة HTTP: {response.status}")
                    if retry < max_retries - 1:
                        page.wait_for_timeout(2000 * (retry + 1))
                        continue
                    else:
                        return False
                
                # الانتظار الإضافي للاستقرار في Railway
                if self.is_railway:
                    page.wait_for_timeout(1500)
                
                logger.info(f"✅ {description} | تحميل ناجح")
                return True
                
            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower():
                    self.stats['timeouts'] += 1
                    logger.warning(f"⏰ {description} | مهلة في المحاولة {retry+1}")
                    
                    if retry < max_retries - 1:
                        # استراتيجيات التعافي
                        recovery_strategies = [
                            lambda: page.wait_for_timeout(3000),
                            lambda: page.reload() if page.url == url else None,
                            lambda: page.evaluate("location.reload()") if page.url == url else None
                        ]
                        
                        if retry < len(recovery_strategies):
                            try:
                                recovery_strategies[retry]()
                            except:
                                pass
                        
                        logger.info(f"🔄 {description} | إعادة المحاولة بعد {3000 * (retry + 1)}ms")
                        page.wait_for_timeout(3000 * (retry + 1))
                        continue
                else:
                    logger.error(f"❌ {description} | خطأ: {error_msg[:100]}")
                
                if retry == max_retries - 1:
                    logger.error(f"💀 {description} | فشل بعد {max_retries} محاولات")
                    return False
        
        return False
    
    # ==================== نظام الكابتشا المُحسّن ====================
    def solve_captcha_railway(self, page: Page, location: str = "GENERAL") -> bool:
        """
        حل كابتشا مُحسّن لـ Railway
        """
        max_attempts = 3
        
        for attempt in range(1, max_attempts + 1):
            try:
                # التحقق من وجود كابتشا مع مهلة Railway
                captcha_timeout = self.timeout_settings['captcha']
                if not page.locator("input[name='captchaText']").first.is_visible(timeout=captcha_timeout):
                    return True
                
                logger.info(f"🧩 [{location}] محاولة كابتشا {attempt}/{max_attempts}")
                
                # البحث بطريقة أكثر مرونة في Railway
                captcha_selectors = [
                    "captcha > div",
                    "div.captcha",
                    ".captcha-image",
                    "img[src*='captcha']",
                    "div[class*='captcha']",
                    "form img",
                    "img[alt*='captcha']",
                    "img[alt*='code']"
                ]
                
                captcha_element = None
                for selector in captcha_selectors:
                    try:
                        if page.locator(selector).first.is_visible(timeout=2000):
                            captcha_element = page.locator(selector).first
                            logger.debug(f"🔍 [{location}] وجدت كابتشا بـ: {selector}")
                            break
                    except:
                        continue
                
                if not captcha_element:
                    # محاولة البحث بـ JavaScript
                    try:
                        captcha_element = page.evaluate_handle("""
                            () => {
                                const images = document.querySelectorAll('img');
                                for(const img of images) {
                                    if(img.src.includes('captcha') || img.alt.includes('captcha') || 
                                       img.src.includes('security') || img.alt.includes('security')) {
                                        return img;
                                    }
                                }
                                return null;
                            }
                        """)
                    except:
                        pass
                
                if not captcha_element:
                    logger.warning(f"⚠️ [{location}] عنصر الكابتشا غير موجود")
                    self.stats['captchas_failed'] += 1
                    return False
                
                # الانتظار لتحميل الصورة في Railway
                page.wait_for_timeout(500 if self.is_railway else 300)
                
                # التقاط لقطة الشاشة مع معالجة أخطاء Railway
                try:
                    screenshot = captcha_element.screenshot()
                    if len(screenshot) < 500:  # صورة صغيرة جداً (تالفة)
                        logger.warning("⚫ كابتشا تالفة محتملة")
                        
                        # محاولة تحديث الكابتشا في Railway
                        refresh_selectors = [
                            "input[name*='refresh']",
                            "button:has-text('Refresh')",
                            "a:has-text('New')",
                            "img[src*='refresh']"
                        ]
                        
                        for selector in refresh_selectors:
                            try:
                                if page.locator(selector).first.is_visible(timeout=1000):
                                    page.locator(selector).first.click()
                                    page.wait_for_timeout(1500)
                                    logger.info("🔄 تحديث الكابتشا")
                                    break
                            except:
                                continue
                        
                        page.wait_for_timeout(1000)
                        continue
                except Exception as e:
                    logger.warning(f"⚠️ خطأ في التقاط لقطة الشاشة: {e}")
                    continue
                
                # حل الكابتشا
                try:
                    code = self.solver.solve(captcha_element.screenshot())
                    if not code:
                        logger.warning("⚠️ فشل حل الكابتشا")
                        continue
                    
                    # تنظيف الكود
                    code = str(code).replace(" ", "").strip().upper()[:8]
                    
                    if len(code) < 4:
                        logger.warning(f"⚠️ كود قصير جداً: {len(code)} أحرف")
                        continue
                    
                    # إدخال الكود بطريقة أكثر مرونة
                    try:
                        page.fill("input[name='captchaText']", code)
                    except:
                        # محاولة بديلة
                        page.evaluate(f"""
                            (code) => {{
                                const input = document.querySelector("input[name='captchaText']");
                                if(input) {{
                                    input.value = code;
                                    input.dispatchEvent(new Event('input', {{bubbles: true}}));
                                }}
                            }}
                        """, code)
                    
                    # إرسال النموذج
                    submit_strategies = [
                        lambda: page.keyboard.press("Enter"),
                        lambda: page.locator("input[type='submit']").first.click(),
                        lambda: page.locator("button[type='submit']").first.click(),
                        lambda: page.evaluate("document.querySelector('form').submit()")
                    ]
                    
                    submitted = False
                    for strategy in submit_strategies:
                        try:
                            strategy()
                            submitted = True
                            break
                        except:
                            continue
                    
                    if not submitted:
                        page.keyboard.press("Enter")
                    
                    # الانتظار للنتيجة مع مهلة Railway
                    wait_time = 3000 if self.is_railway else 2000
                    page.wait_for_timeout(wait_time)
                    
                    # التحقق من النجاح
                    if not page.locator("input[name='captchaText']").first.is_visible(timeout=2000):
                        self.stats['captchas_solved'] += 1
                        logger.info(f"✅ [{location}] كابتشا محلولة بنجاح")
                        return True
                    else:
                        logger.warning(f"⚠️ [{location}] الكابتشا مازالت موجودة")
                        page.wait_for_timeout(1500)
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
    
    # ==================== نظام المسح الرئيسي ====================
    def scan_month_for_days_railway(self, page: Page, url: str) -> Tuple[bool, List[str]]:
        """مسح الشهر مُحسّن لـ Railway"""
        try:
            self.stats['scans'] += 1
            
            logger.info(f"🔍 مسح: {url.split('dateStr=')[-1] if 'dateStr=' in url else url}")
            
            # تحميل الصفحة بطريقة Railway
            if not self.smart_page_goto(page, url, f"شهر {url.split('dateStr=')[-1] if 'dateStr=' in url else 'غير معروف'}"):
                self.stats['errors'] += 1
                self.consecutive_errors += 1
                return False, []
            
            # حل كابتشا الشهر
            if not self.solve_captcha_railway(page, "MONTH"):
                self.stats['errors'] += 1
                return False, []
            
            # البحث عن الأيام بطرق متعددة
            day_links = []
            
            # استراتيجيات البحث المختلفة
            search_strategies = [
                # الاستراتيجية 1: البحث بـ CSS Selectors
                lambda: page.locator("a.arrow[href*='appointment_showDay']").all(),
                # الاستراتيجية 2: البحث بـ JavaScript
                lambda: page.evaluate("""
                    () => {
                        const links = [];
                        const allLinks = document.querySelectorAll('a');
                        for(const link of allLinks) {
                            if(link.href && link.href.includes('showDay')) {
                                links.push(link);
                            }
                        }
                        return links;
                    }
                """),
                # الاستراتيجية 3: البحث بالنص
                lambda: page.locator("a:has-text('Book'), a:has-text('Appointment'), a:has-text('Termin')").all(),
            ]
            
            for strategy in search_strategies:
                try:
                    result = strategy()
                    if result and len(result) > 0:
                        if isinstance(result, list):
                            for element in result[:5]:  # أخذ أول 5 عناصر فقط
                                try:
                                    if hasattr(element, 'get_attribute'):
                                        href = element.get_attribute("href")
                                    else:
                                        href = element.get('href') if isinstance(element, dict) else None
                                    
                                    if href:
                                        # بناء URL كامل
                                        if href.startswith("http"):
                                            full_url = href
                                        elif href.startswith("/"):
                                            full_url = f"https://service2.diplo.de{href}"
                                        elif href.startswith("appointment_"):
                                            base = self.base_url.split("/extern")[0]
                                            full_url = f"{base}/extern/{href}"
                                        else:
                                            continue
                                        
                                        day_links.append(full_url)
                                except:
                                    continue
                        
                        if day_links:
                            break
                except Exception as e:
                    logger.debug(f"⚠️ استراتيجية بحث فشلت: {e}")
                    continue
            
            if day_links:
                logger.info(f"🔥 وجدت {len(day_links)} يوم/أيام")
                return True, list(set(day_links))[:3]  # إزالة التكرارات وأخذ أول 3
            
            logger.info("📭 لا توجد أيام متاحة")
            return True, []
            
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                self.stats['timeouts'] += 1
                logger.error(f"⏰ مهلة في مسح الشهر")
            else:
                logger.error(f"❌ خطأ في مسح الشهر: {error_msg[:100]}")
            
            self.stats['errors'] += 1
            self.consecutive_errors += 1
            return False, []
    
    # ==================== توليد روابط الأشهر ====================
    def generate_priority_month_urls(self) -> List[str]:
        """إنشاء روابط الأشهر"""
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
    
    # ==================== الدورة الرئيسية المُحسّنة ====================
    def run_railway_optimized(self):
        """الدورة الرئيسية المُحسّنة لـ Railway"""
        logger.info("="*60)
        logger.info("🚀 بدء تشغيل EliteSniper v10.1.0 (Railway Optimized)")
        logger.info("="*60)
        
        try:
            # إعدادات متقدمة لـ Railway
            launch_args = {
                'headless': True,
                'args': [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-first-run",
                    "--disable-extensions",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--window-size=1366,768",
                    "--start-maximized",
                ]
            }
            
            # إضافة إعدادات خاصة لـ Railway
            if self.is_railway:
                launch_args['args'].extend([
                    "--single-process",
                    "--no-zygote",
                    "--disable-accelerated-2d-canvas",
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                ])
                launch_args['timeout'] = 90000  # 90 ثانية لـ Railway
            
            with sync_playwright() as p:
                logger.info("🌐 بدء تشغيل المتصفح...")
                
                browser = p.chromium.launch(**launch_args)
                
                logger.info("✅ المتصفح جاهز")
                
                # إنشاء السياق
                context, page = self.create_railway_context(browser)
                
                cycle = 0
                max_cycles_without_success = 50  # زيادة عدد الدورات لـ Railway
                
                while not self.stats['success'] and cycle < max_cycles_without_success:
                    cycle += 1
                    
                    logger.info(f"\n{'='*50}")
                    logger.info(f"🔁 الدورة #{cycle}")
                    logger.info(f"📊 النمط: {self.get_operational_mode()}")
                    logger.info(f"📈 الإحصاءات: Scans={self.stats['scans']}, Errors={self.stats['errors']}, Timeouts={self.stats['timeouts']}")
                    logger.info(f"{'='*50}")
                    
                    # إعادة التعافي إذا كانت الأخطاء كثيرة
                    if self.consecutive_errors >= 5:
                        logger.warning(f"⚠️ أخطاء متتالية: {self.consecutive_errors}")
                        logger.info("🔄 محاولة التعافي...")
                        
                        try:
                            page.wait_for_timeout(5000)
                            
                            # محاولة إعادة تحميل الصفحة الرئيسية
                            if page.url and 'diplo' in page.url:
                                page.reload()
                            else:
                                page.goto(self.base_url, timeout=30000)
                            
                            page.wait_for_timeout(3000)
                            self.consecutive_errors = 0
                            logger.info("✅ تمت إعادة التعافي")
                        except:
                            logger.warning("⚠️ فشل التعافي، المتابعة...")
                    
                    # التأخير بين الدورات
                    delay = self.calculate_delay()
                    if delay > 1:
                        logger.info(f"⏳ تأخير: {delay:.1f} ثانية")
                        time.sleep(delay)
                    
                    # الحصول على روابط الأشهر
                    month_urls = self.generate_priority_month_urls()
                    
                    if not month_urls:
                        logger.error("❌ لا توجد روابط أشهر")
                        time.sleep(60)
                        continue
                    
                    logger.info(f"📅 عدد الأشهر للمسح: {len(month_urls)}")
                    
                    # مسح كل شهر
                    for month_index, month_url in enumerate(month_urls):
                        if self.stats['success']:
                            break
                        
                        logger.info(f"📊 الشهر {month_index+1}/{len(month_urls)}")
                        
                        # مسح الشهر
                        scan_success, day_urls = self.scan_month_for_days_railway(page, month_url)
                        
                        if not scan_success:
                            self.consecutive_errors += 1
                            logger.warning(f"⚠️ فشل مسح الشهر {month_index+1}")
                            continue
                        
                        if not day_urls:
                            logger.info(f"📭 الشهر {month_index+1}: لا توجد أيام")
                            continue
                        
                        logger.info(f"🎯 الشهر {month_index+1}: وجدت {len(day_urls)} يوم/أيام")
                        
                        # هنا يمكن إضافة منطق مسح الأيام والمحاولة (مختصر للتركيز على Railway)
                        # في النسخة الكاملة، سيتم إضافة باقي المنطق هنا
                        
                        # مؤقت: فقط لتجربة Railway
                        logger.info("⏸️ توقف للاختبار (في النسخة الكاملة سيتم متابعة الحجز)")
                        page.wait_for_timeout(5000)
                        break  # خروج من الحلقة للاختبار
                    
                    # إحصاءات نهاية الدورة
                    logger.info(f"\n📊 إحصاءات الدورة #{cycle}")
                    logger.info(f"   • المسوحات: {self.stats['scans']}")
                    logger.info(f"   • المهلات: {self.stats['timeouts']}")
                    logger.info(f"   • الأخطاء: {self.stats['errors']}")
                    logger.info(f"   • الأخطاء المتتالية: {self.consecutive_errors}")
                    logger.info(f"   • وقت التشغيل: {(datetime.datetime.now() - self.start_time).total_seconds():.1f} ثانية")
                    
                    # إعادة التشغيل إذا استمرت المشاكل
                    if self.stats['timeouts'] > 10 or self.consecutive_errors > 8:
                        logger.warning("🔄 مشاكل متكررة، إعادة التشغيل...")
                        try:
                            context.close()
                        except:
                            pass
                        context, page = self.create_railway_context(browser)
                        self.consecutive_errors = 0
                        self.stats['timeouts'] = 0
                
                # إنهاء التشغيل
                logger.info("\n" + "="*60)
                if self.stats['success']:
                    logger.info("🎊 المهمة مكتملة بنجاح!")
                else:
                    logger.info(f"⏹️ انتهى التشغيل بعد {cycle} دورات")
                logger.info("="*60)
                
                # إغلاق نظيف
                try:
                    context.close()
                    browser.close()
                except:
                    pass
                
                return self.stats['success']
                
        except KeyboardInterrupt:
            logger.info("\n🛑 تم إيقاف التشغيل بواسطة المستخدم")
            return False
            
        except Exception as e:
            logger.error(f"💀 خطأ حرج: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ==================== الدوال المساعدة ====================
    def get_operational_mode(self) -> str:
        """تحديد نمط التشغيل"""
        try:
            now = datetime.datetime.now(self.timezone)
            
            if (now.hour == 1 and now.minute == 59 and now.second >= 50) or \
               (now.hour == 2 and now.minute <= 10):
                return "ASSAULT"
            
            elif now.hour == 1 and now.minute >= 45:
                return "WARMUP"
            
            return "SCOUT"
            
        except Exception as e:
            return "SCOUT"
    
    def calculate_delay(self) -> float:
        """حساب التأخير"""
        mode = self.get_operational_mode()
        
        if mode == "ASSAULT":
            return random.uniform(0.05, 0.15)
        
        elif mode == "WARMUP":
            return random.uniform(1.0, 2.0)
        
        else:
            return random.uniform(30.0, 90.0)  # زيادة المهلة لـ Railway
    
    # ==================== نقطة الدخول الرئيسية ====================
    def run(self):
        """نقطة الدخول الرئيسية (متوافقة مع Railway)"""
        return self.run_railway_optimized()


# ==================== الدالة الرئيسية ====================
def main():
    """الدالة الرئيسية للتشغيل"""
    print("="*60)
    print("🎯 EliteSniper v10.1.0 - Railway Optimized")
    print("="*60)
    
    try:
        sniper = EliteSniper()
        success = sniper.run()
        
        if success:
            print("\n✅ التشغيل مكتمل بنجاح!")
            return 0
        else:
            print("\n⏹️ انتهى التشغيل")
            return 0  # إرجاع 0 حتى في حالة الفشل لعدم إعادة التشغيل المستمر
            
    except Exception as e:
        print(f"\n💀 خطأ فادح: {e}")
        import traceback
        traceback.print_exc()
        return 1  # إرجاع 1 لإعادة التشغيل في Railway

if __name__ == "__main__":
    sys.exit(main())