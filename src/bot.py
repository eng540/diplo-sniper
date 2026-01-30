"""
King Sniper v12.0.0 - النظام النهائي المسؤول 24/7
الإصدار: 12.0.0 (Production Ready - State Machine)
الوصف: نظام حجز مواعيد دبلوماسي مع State Machine ونظام Incident
الميزات: State Machine رسمية، نظام Incident، Scoring System، حفظ أدلة كاملة
التاريخ: 2024
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
from urllib.parse import urljoin, urlparse
from datetime import timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import hashlib

import pytz
import ntplib
from playwright.sync_api import sync_playwright, Page, BrowserContext, Browser

# ==================== IMPORTS الأساسية ====================
try:
    from .config import Config
    from .captcha import CaptchaSolver
    from .notifier import send_alert, send_photo, send_document
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
        logging.FileHandler('king_sniper_v12.log') if getattr(Config, 'ENABLE_FILE_LOG', False) 
        else logging.NullHandler()
    ]
)
logger = logging.getLogger("KingSniperV12")

# ==================== State Machine الأساسية ====================
class SystemState(Enum):
    """حالات النظام الرسمية"""
    ACTIVE = "ACTIVE"        # فحص، تحليل، قرار
    STANDBY = "STANDBY"      # انتظار مبرر (لا معطيات جديدة)
    BLOCKED = "BLOCKED"      # Incident يتطلب تدخل بشري

class SessionHealth(Enum):
    """صحة الجلسة"""
    CLEAN = "CLEAN"
    POISONED = "POISONED"
    SUSPECTED = "SUSPECTED"

class OperationalMode(Enum):
    """نمط التشغيل"""
    SCOUT = "SCOUT"      # مسح عادي
    WARMUP = "WARMUP"    # إحماء
    ASSAULT = "ASSAULT"  # هجوم

# ==================== فئات البيانات ====================
@dataclass
class Incident:
    """نظام Incident لتسجيل الفشل غير القابل للمعالجة"""
    id: str
    timestamp: datetime.datetime
    type: str  # CAPTCHA_FAILURE, DOM_CHANGED, UNEXPECTED_REDIRECT, NO_VALID_CATEGORY
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    evidence: Dict[str, Any]
    description: str
    resolved: bool = False
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'type': self.type,
            'severity': self.severity,
            'description': self.description,
            'resolved': self.resolved,
            'evidence_keys': list(self.evidence.keys())
        }

@dataclass
class StateTransition:
    """تسجيل انتقالات الحالة"""
    timestamp: datetime.datetime
    from_state: str
    to_state: str
    reason: str
    session_id: str

class FieldMapping:
    """تمثيل تعيين الحقل الديناميكي"""
    
    def __init__(self, field_type: str, patterns: List[str], config_value: str):
        self.field_type = field_type
        self.patterns = patterns
        self.value = config_value
        self.found_name = None
        self.found_selector = None
        self.filled = False
        self.timestamp = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'field_type': self.field_type,
            'value': self.value,
            'found_name': self.found_name,
            'found_selector': self.found_selector,
            'filled': self.filled,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class DecisionEngine:
    """محرك قرارات مع Scoring System"""
    
    def __init__(self):
        # أوزان الكلمات المفتاحية (V1 Priorities)
        self.keyword_weights = {
            # الأولوية القصوى
            "yemeni national": 20,
            "yemeni student": 18,
            
            # كلمات مفتاحية أساسية
            "yemeni": 10,
            "student": 9,
            "national": 8,
            
            # كلمات داعمة
            "studium": 9,
            "sprachkurs": 9,
            "language": 7,
            "university": 7,
            "course": 6,
            
            # كلمات عامة
            "language course": 8,
            "study": 6,
            "education": 5,
            
            # كلمات احتياطية
            "yem": 4,
            "stud": 4
        }
        
        self.threshold = 12  # الحد الأدنى للقبول
        self.absolute_threshold = 8  # الحد الأدنى المطلق
    
    def calculate_score(self, text: str) -> Tuple[int, Dict[str, int]]:
        """حساب درجة التطابق المرجّح مع تفصيل"""
        score = 0
        matches = {}
        text_lower = text.lower()
        
        # تطابق كامل أولاً (أعلى وزن)
        for keyword, weight in self.keyword_weights.items():
            if keyword in text_lower:
                score += weight
                matches[keyword] = weight
        
        # مكافآت إضافية
        if "yemeni" in text_lower and "student" in text_lower:
            score += 5  # مكافأة التطابق المركب
            matches["yemeni+student_combo"] = 5
        
        return score, matches
    
    def evaluate_option(self, option_text: str, option_value: str = "") -> Dict[str, Any]:
        """تقييم خيار مع إرجاع تفاصيل كاملة"""
        score, matches = self.calculate_score(option_text)
        
        return {
            'text': option_text,
            'value': option_value,
            'score': score,
            'matches': matches,
            'meets_threshold': score >= self.threshold,
            'meets_absolute': score >= self.absolute_threshold,
            'match_count': len(matches)
        }

# ==================== الفئة الرئيسية ====================
class KingSniperV12:
    """
    النسخة النهائية مع State Machine ونظام Incident
    - State Machine رسمية
    - نظام Incident كامل
    - Decision Engine مع Scoring
    - حفظ أدلة كاملة
    - إرسال تقارير بعد النجاح
    """
    
    def __init__(self):
        """تهيئة النظام مع State Machine"""
        self._validate_config()
        
        # المكونات الأساسية
        self.solver = CaptchaSolver()
        self.base_url = self._prepare_base_url(Config.TARGET_URL)
        self.timezone = pytz.timezone(getattr(Config, 'TIMEZONE', 'Asia/Aden'))
        
        # مزامنة الوقت
        self.ntp_offset = 0.0
        self.time_synced = False
        self._sync_ntp_time()
        
        # State Machine
        self.system_state = SystemState.ACTIVE
        self.session_health = SessionHealth.CLEAN
        self.decision_engine = DecisionEngine()
        
        # نظام Incident
        self.incidents = []
        self.state_transitions = []
        self.consecutive_blocks = 0
        
        # إدارة الجلسة
        self.session_id = f"king12_{int(time.time())}_{random.randint(1000, 9999)}"
        self.start_time = datetime.datetime.now()
        self.current_user_agent = None
        self.consecutive_errors = 0
        self.captcha_attempts = 0
        self.max_captcha_attempts = 10  # حسب متطلبات المطور الآخر
        
        # إعدادات الأداء
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
        ]
        
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
            'state_transitions': 0,
            'incidents': 0,
            'decisions_made': 0,
            'avg_decision_time_ms': 0,
            'ntp_corrections': 0,
            'standby_periods': 0,
            'active_cycles': 0
        }
        
        # تخزين البيانات للتقرير
        self.form_data_snapshot = None
        self.success_page_html = None
        self.success_screenshot = None
        self.booking_details = None
        
        # إعداد الدلائل
        self.evidence_dir = f"evidence_{self.session_id}"
        os.makedirs(self.evidence_dir, exist_ok=True)
        
        logger.info(f"👑 King Sniper v12.0.0 - Session: {self.session_id}")
        logger.info(f"🏗️  State: {self.system_state.value}, Health: {self.session_health.value}")
        logger.info(f"⏰ NTP Offset: {self.ntp_offset:.3f}s")
        
        self._log_transition("INIT", self.system_state.value, "System initialized")
    
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
    
    # ==================== State Machine Management ====================
    def _log_transition(self, from_state: str, to_state: str, reason: str):
        """تسجيل انتقال الحالة"""
        transition = StateTransition(
            timestamp=datetime.datetime.now(),
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            session_id=self.session_id
        )
        
        self.state_transitions.append(transition)
        self.stats['state_transitions'] += 1
        
        logger.info(f"🔄 State Transition: {from_state} → {to_state} ({reason})")
    
    def transition_state(self, new_state: SystemState, reason: str):
        """انتقال آمن بين حالات النظام"""
        old_state = self.system_state
        
        # التحقق من الانتقال المسموح
        if old_state == new_state:
            return
        
        # تسجيل الانتقال
        self._log_transition(old_state.value, new_state.value, reason)
        
        # تحديث الحالة
        self.system_state = new_state
        
        # معالجة خاصة للحالات
        if new_state == SystemState.BLOCKED:
            self._handle_blocked_state(reason)
        elif new_state == SystemState.STANDBY:
            self.stats['standby_periods'] += 1
            logger.info(f"⏸️  نظام في وضع STANDBY: {reason}")
        elif new_state == SystemState.ACTIVE:
            self.stats['active_cycles'] += 1
            logger.info(f"▶️  نظام في وضع ACTIVE: {reason}")
    
    def _handle_blocked_state(self, reason: str):
        """معالجة حالة BLOCKED"""
        self.consecutive_blocks += 1
        self.stats['incidents'] += 1
        
        # إنشاء Incident
        incident_id = f"inc_{self.stats['incidents']}_{int(time.time())}"
        incident = Incident(
            id=incident_id,
            timestamp=datetime.datetime.now(),
            type="SYSTEM_BLOCKED",
            severity="CRITICAL",
            evidence=self._capture_incident_evidence(),
            description=f"System blocked: {reason}"
        )
        
        self.incidents.append(incident)
        
        # إرسال تنبيه Incident
        self._send_incident_alert(incident)
        
        logger.critical(f"🚨 SYSTEM BLOCKED: {reason} (Incident #{self.stats['incidents']})")
        
        # إذا تجاوزنا الحد، توقف كامل
        if self.consecutive_blocks >= 3:
            self._emergency_shutdown()
    
    def _capture_incident_evidence(self) -> Dict[str, Any]:
        """التقاط أدلة Incident"""
        evidence = {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": self.session_id,
            "system_state": self.system_state.value,
            "session_health": self.session_health.value,
            "consecutive_blocks": self.consecutive_blocks,
            "consecutive_errors": self.consecutive_errors,
            "captcha_attempts": self.captcha_attempts,
            "stats": self.stats.copy(),
            "recent_transitions": [
                {"from": t.from_state, "to": t.to_state, "reason": t.reason}
                for t in self.state_transitions[-5:]
            ]
        }
        
        return evidence
    
    def _send_incident_alert(self, incident: Incident):
        """إرسال تنبيه Incident"""
        try:
            alert_msg = f"""
🚨 INCIDENT REPORT - KING SNIPER V12 🚨

📋 Incident ID: {incident.id}
🕒 Time: {incident.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
⚠️ Type: {incident.type}
🔴 Severity: {incident.severity}
📝 Description: {incident.description}

📊 Session Info:
   • ID: {self.session_id}
   • State: {self.system_state.value}
   • Health: {self.session_health.value}
   • Consecutive Blocks: {self.consecutive_blocks}
   • Consecutive Errors: {self.consecutive_errors}

📈 System Stats:
   • Scans: {self.stats['scans']}
   • Captchas Solved: {self.stats['captchas_solved']}
   • Incidents: {self.stats['incidents']}
   • State Transitions: {self.stats['state_transitions']}

📍 Action Required: Manual intervention needed
            """
            
            send_alert(alert_msg.strip())
            
        except Exception as e:
            logger.error(f"❌ فشل إرسال Incident alert: {e}")
    
    def _emergency_shutdown(self):
        """إيقاف طارئ للنظام بعد 3 Incidents متتالية"""
        logger.critical("💀 EMERGENCY SHUTDOWN: 3 consecutive incidents")
        
        # إنشاء تقرير نهائي
        final_report = self._generate_final_report()
        
        # إرسال التنبيه
        send_alert(final_report)
        
        # حفظ جميع البيانات
        self._save_session_data()
        
        logger.critical("🛑 System shutdown complete")
        sys.exit(1)
    
    def update_session_health(self, new_health: SessionHealth, reason: str):
        """تحديث صحة الجلسة"""
        if self.session_health == new_health:
            return
        
        old_health = self.session_health
        self.session_health = new_health
        
        logger.info(f"🩺 Session Health: {old_health.value} → {new_health.value} ({reason})")
        
        # إذا أصبحت مسمومة، سجل Incident
        if new_health == SessionHealth.POISONED:
            self.stats['poisoned_sessions'] += 1
            self.transition_state(SystemState.BLOCKED, f"Session poisoned: {reason}")
    
    # ==================== إدارة الوقت والنمط ====================
    def get_synced_time(self) -> datetime.datetime:
        """الحصول على الوقت المصحح مع NTP"""
        if self.time_synced:
            corrected = datetime.datetime.now() + timedelta(seconds=self.ntp_offset)
            self.stats['ntp_corrections'] += 1
            return corrected
        return datetime.datetime.now()
    
    def get_operational_mode(self) -> OperationalMode:
        """تحديد نمط التشغيل مع التصحيح الزمني"""
        try:
            now = self.get_synced_time().astimezone(self.timezone)
            
            # نافذة ASSAULT الموسعة: 01:59:45 - 02:10:10
            if (now.hour == 1 and now.minute == 59 and now.second >= 45) or \
               (now.hour == 2 and now.minute <= 10) or \
               (now.hour == 2 and now.minute == 10 and now.second <= 10):
                return OperationalMode.ASSAULT
            
            # مرحلة WARMUP الموسعة: 01:40 - 01:59:44
            elif now.hour == 1 and now.minute >= 40:
                return OperationalMode.WARMUP
            
            # نمط SCOUT
            return OperationalMode.SCOUT
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحديد النمط: {e}")
            return OperationalMode.SCOUT
    
    def calculate_delay(self) -> float:
        """حساب التأخير المناسب حسب النمط"""
        mode = self.get_operational_mode()
        
        if mode == OperationalMode.ASSAULT:
            return random.uniform(0.01, 0.05)  # 10-50ms فائق السرعة
        
        elif mode == OperationalMode.WARMUP:
            return random.uniform(0.5, 1.0)    # 0.5-1 ثانية
        
        else:  # SCOUT
            return random.uniform(10.0, 20.0)  # 10-20 ثانية (مختصر للاستمرارية)
    
    # ==================== إدارة المتصفح ====================
    def create_stealth_context(self, browser: Browser) -> Tuple[BrowserContext, Page]:
        """إنشاء سياق متخفي مع هوية جديدة"""
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
                permissions=[]
            )
            
            page = context.new_page()
            
            # منع اكتشاف الأتمتة المتقدم
            stealth_script = """
            Object.defineProperty(navigator, 'webdriver', { 
                get: () => undefined,
                configurable: true
            });
            
            Object.defineProperty(navigator, 'plugins', { 
                get: () => [1, 2, 3, 4, 5],
                configurable: true
            });
            
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            """
            
            page.add_init_script(stealth_script)
            
            # تحسين الأداء
            def route_handler(route):
                resource_type = route.request.resource_type
                url = route.request.url
                
                mode = self.get_operational_mode()
                if mode == OperationalMode.ASSAULT:
                    if resource_type in ["image", "media", "font", "stylesheet"]:
                        route.abort()
                        return
                
                if resource_type in ["image", "media"] or "analytics" in url:
                    route.abort()
                else:
                    route.continue_()
            
            page.route("**/*", route_handler)
            
            # مهلات حسب النمط
            mode = self.get_operational_mode()
            if mode == OperationalMode.ASSAULT:
                context.set_default_timeout(5000)
                context.set_default_navigation_timeout(7000)
            else:
                context.set_default_timeout(15000)
                context.set_default_navigation_timeout(20000)
            
            logger.info(f"✨ New context created (UA: {self.current_user_agent[:40]}...)")
            return context, page
            
        except Exception as e:
            logger.error(f"❌ فشل إنشاء السياق: {e}")
            self.consecutive_errors += 1
            raise
    
    def emergency_session_reboot(self, page: Page, reason: str) -> bool:
        """
        إعادة تشغيل طارئة للجلسة (Hard Rebirth)
        وفقاً لمتطلبات المطور الآخر
        """
        try:
            logger.critical(f"🔄 EMERGENCY REBOOT: {reason}")
            
            # تغيير الهوية الكاملة
            new_ua_pool = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0"
            ]
            
            self.current_user_agent = random.choice(new_ua_pool)
            self.user_agents = [self.current_user_agent]
            
            # إعادة تعيين العدادات
            self.consecutive_errors = 0
            self.captcha_attempts = 0
            self.consecutive_blocks = 0
            
            # تحديث صحة الجلسة
            self.update_session_health(SessionHealth.CLEAN, "Emergency reboot completed")
            
            # إعادة مزامنة الوقت
            self._sync_ntp_time()
            
            logger.info(f"✅ Reboot completed (New UA: {self.current_user_agent[:40]}...)")
            return True
            
        except Exception as e:
            logger.error(f"❌ فشل Emergency reboot: {e}")
            return False
    
    # ==================== نظام الحقن المباشر ====================
    def dom_fill(self, page: Page, selector: str, value: str, field_type: str = "") -> bool:
        """حقن مباشر للقيمة في عنصر DOM"""
        start_time = time.time()
        
        try:
            # تنظيف القيمة
            safe_value = str(value).replace('\\', '\\\\').replace('"', '\\"')
            
            js_code = f"""
            (function() {{
                try {{
                    const el = document.querySelector(`{selector}`);
                    if (!el) return {{success: false, reason: "Element not found"}};
                    
                    el.value = "{safe_value}";
                    
                    el.dispatchEvent(new FocusEvent('focus', {{ bubbles: true }}));
                    el.dispatchEvent(new InputEvent('input', {{
                        bubbles: true,
                        inputType: 'insertText',
                        data: "{safe_value}"
                    }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    
                    return {{success: true, value: el.value}};
                }} catch(error) {{
                    return {{success: false, reason: error.message}};
                }}
            }})()
            """
            
            result = page.evaluate(js_code)
            
            elapsed = (time.time() - start_time) * 1000
            
            if result.get('success'):
                self.stats['dom_injections'] += 1
                logger.debug(f"⚡ DOM fill: {field_type} ({elapsed:.1f}ms)")
                return True
            else:
                logger.warning(f"⚠️ DOM fill failed: {result.get('reason')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ DOM fill error: {str(e)[:80]}")
            return False
    
    # ==================== نظام الكابتشا المنضبط ====================
    def solve_captcha_with_policy(self, page: Page, location: str = "GENERAL") -> bool:
        """
        حل الكابتشا مع الالتزام بالسياسة المطلوبة
        - الحد الأقصى 10 محاولات
        - شروط قبول الحل (6-8 خانات)
        - Incident عند الفشل
        """
        if self.captcha_attempts >= self.max_captcha_attempts:
            logger.error(f"❌ Max captcha attempts reached ({self.max_captcha_attempts})")
            self.update_session_health(SessionHealth.POISONED, "Max captcha attempts exceeded")
            return False
        
        try:
            # التحقق من وجود كابتشا
            captcha_input = page.locator("input[name='captchaText']").first
            if not captcha_input.is_visible(timeout=500):
                return True
            
            self.captcha_attempts += 1
            logger.info(f"🧩 [{location}] Captcha attempt {self.captcha_attempts}/{self.max_captcha_attempts}")
            
            # البحث عن عنصر الكابتشا
            captcha_element = None
            for selector in ["img[src*='captcha']", "div.captcha img", "#captcha img"]:
                try:
                    if page.locator(selector).first.is_visible(timeout=300):
                        captcha_element = page.locator(selector).first
                        break
                except:
                    continue
            
            if not captcha_element:
                logger.warning(f"⚠️ [{location}] Captcha element not found")
                self.stats['captchas_failed'] += 1
                return False
            
            # التحقق من الكابتشا السوداء
            try:
                screenshot = captcha_element.screenshot()
                if len(screenshot) < 1500:
                    logger.critical("⚫ Black captcha detected")
                    self.update_session_health(SessionHealth.POISONED, "Black captcha")
                    return False
            except:
                pass
            
            # حل الكابتشا
            try:
                start_solve = time.time()
                code = self.solver.solve(captcha_element.screenshot())
                solve_time = (time.time() - start_solve) * 1000
                
                if not code:
                    logger.warning("⚠️ No code returned from solver")
                    self.stats['captchas_failed'] += 1
                    return False
                
                # تنظيف الكود حسب السياسة
                code = str(code).replace(" ", "").replace("-", "").strip()
                
                # التحقق من الطول حسب السياسة (6-8 خانات)
                if len(code) < 6:
                    logger.warning(f"❌ Code too short: {len(code)} chars (min 6)")
                    self.stats['captchas_failed'] += 1
                    return False
                
                if len(code) > 8:
                    code = code[:8]  # اقتصار على 8 خانات كحد أقصى
                    logger.warning(f"⚠️ Code trimmed to 8 chars")
                
                logger.debug(f"🔢 Captcha code: {code} (solved in {solve_time:.0f}ms)")
                
                # حقن الكود
                if self.dom_fill(page, "input[name='captchaText']", code, "CAPTCHA"):
                    page.keyboard.press("Enter")
                    
                    wait_time = 500 if self.get_operational_mode() == OperationalMode.ASSAULT else 1000
                    page.wait_for_timeout(wait_time)
                    
                    # التحقق من النجاح
                    if not captcha_input.is_visible(timeout=500):
                        self.stats['captchas_solved'] += 1
                        self.captcha_attempts = 0  # إعادة تعيين عند النجاح
                        logger.info(f"✅ [{location}] Captcha solved successfully")
                        return True
                    else:
                        logger.warning(f"🔄 [{location}] Captcha still present")
                        return False
                
            except Exception as e:
                logger.error(f"❌ [{location}] Captcha solve error: {str(e)[:80]}")
                self.stats['captchas_failed'] += 1
                return False
                
        except Exception as e:
            logger.error(f"❌ [{location}] General captcha error: {str(e)[:80]}")
            self.stats['errors'] += 1
            return False
        
        return False
    
    # ==================== نظام القرارات (Decision Engine) ====================
    def select_visa_category_intelligent(self, page: Page) -> bool:
        """
        اختيار فئة التأشيرة باستخدام Scoring System
        بدون اختيار عشوائي - وفقاً لمتطلبات المطور الآخر
        """
        try:
            # البحث عن عنصر select
            select_info = page.evaluate("""
                () => {
                    const selects = document.querySelectorAll('select');
                    for(const select of selects) {
                        const name = (select.name || '').toLowerCase();
                        const options = select.querySelectorAll('option');
                        if(options.length > 1 && 
                           (name.includes('visa') || name.includes('category') || 
                            name.includes('purpose') || name === 'fields[2].content')) {
                            const optionData = [];
                            for(let i = 0; i < options.length; i++) {
                                optionData.push({
                                    index: i,
                                    text: options[i].textContent?.trim() || '',
                                    value: options[i].value || ''
                                });
                            }
                            return {
                                selectName: select.name,
                                options: optionData
                            };
                        }
                    }
                    return null;
                }
            """)
            
            if not select_info:
                logger.warning("⚠️ No visa category select found")
                return False
            
            # تقييم جميع الخيارات
            evaluated_options = []
            for option in select_info['options']:
                evaluation = self.decision_engine.evaluate_option(option['text'], option['value'])
                evaluated_options.append({
                    **option,
                    **evaluation
                })
            
            # ترتيب حسب النقاط
            evaluated_options.sort(key=lambda x: x['score'], reverse=True)
            
            # تسجيل التفاصيل
            logger.info(f"📊 Decision Engine evaluated {len(evaluated_options)} options")
            for opt in evaluated_options[:3]:  # أفضل 3 فقط للـ log
                logger.debug(f"   • Score {opt['score']}: {opt['text'][:50]}...")
            
            # اتخاذ القرار وفقاً للسياسة
            best_option = evaluated_options[0] if evaluated_options else None
            
            if best_option and best_option['meets_threshold']:
                # الاختيار إذا وصل للحد الأدنى
                select_selector = f"select[name='{select_info['selectName']}']"
                page.select_option(select_selector, index=best_option['index'])
                
                self.stats['decisions_made'] += 1
                logger.info(f"✅ Selected: {best_option['text'][:50]}... (Score: {best_option['score']})")
                return True
            
            elif best_option and best_option['meets_absolute']:
                # استخدام إذا وصل للحد الأدنى المطلق (لكن ليس المثالي)
                select_selector = f"select[name='{select_info['selectName']}']"
                page.select_option(select_selector, index=best_option['index'])
                
                logger.warning(f"⚠️ Selected suboptimal: {best_option['text'][:50]}... (Score: {best_option['score']})")
                return True
            
            else:
                # لا يوجد خيار مقبول - Incident
                logger.error("❌ No acceptable visa category found")
                
                # حفظ أدلة
                evidence = {
                    "select_name": select_info['selectName'],
                    "evaluated_options": evaluated_options,
                    "threshold": self.decision_engine.threshold,
                    "absolute_threshold": self.decision_engine.absolute_threshold
                }
                
                # إنشاء Incident
                incident = Incident(
                    id=f"visa_cat_{int(time.time())}",
                    timestamp=datetime.datetime.now(),
                    type="NO_VALID_VISA_CATEGORY",
                    severity="HIGH",
                    evidence=evidence,
                    description="No visa category meets the scoring threshold"
                )
                
                self.incidents.append(incident)
                self.transition_state(SystemState.BLOCKED, "No valid visa category")
                
                return False
                
        except Exception as e:
            logger.error(f"❌ Visa category selection error: {e}")
            self.stats['errors'] += 1
            return False
    
    # ==================== نظام التعيين الديناميكي ====================
    def build_dynamic_field_map(self, page: Page) -> List[FieldMapping]:
        """بناء خريطة الحقول الديناميكية"""
        field_mappings = [
            FieldMapping("LAST_NAME", ["last name", "family name", "surname"], Config.LAST_NAME),
            FieldMapping("FIRST_NAME", ["first name", "given name"], Config.FIRST_NAME),
            FieldMapping("EMAIL", ["email", "e-mail"], Config.EMAIL),
            FieldMapping("PASSPORT", ["passport", "passport number"], Config.PASSPORT),
            FieldMapping("PHONE", ["phone", "telephone"], Config.PHONE.replace("+", "00").strip())
        ]
        
        try:
            labels_info = page.evaluate("""
                () => {
                    const results = [];
                    const elements = document.querySelectorAll('label, span, div, td, th');
                    
                    for(const el of elements) {
                        const text = (el.textContent || '').trim().toLowerCase();
                        if(text && text.length < 100 && text.length > 1) {
                            let input = null;
                            
                            if(el.htmlFor) {
                                input = document.getElementById(el.htmlFor);
                            }
                            
                            if(!input) {
                                let next = el.nextElementSibling;
                                while(next && !input) {
                                    if(next.matches('input, select, textarea')) {
                                        input = next;
                                    }
                                    next = next.nextElementSibling;
                                }
                            }
                            
                            if(!input) {
                                input = el.querySelector('input, select, textarea');
                            }
                            
                            if(input) {
                                results.push({
                                    text: text,
                                    inputName: input.name || '',
                                    inputId: input.id || '',
                                    tagName: input.tagName
                                });
                            }
                        }
                    }
                    return results;
                }
            """)
            
            for mapping in field_mappings:
                for label in labels_info:
                    for pattern in mapping.patterns:
                        if pattern in label['text']:
                            if label['inputName']:
                                mapping.found_name = label['inputName']
                                mapping.found_selector = f"input[name='{label['inputName']}']"
                            elif label['inputId']:
                                mapping.found_selector = f"#{label['inputId']}"
                            break
                    
                    if mapping.found_selector:
                        break
            
            return field_mappings
            
        except Exception as e:
            logger.error(f"❌ Field mapping error: {e}")
            return field_mappings
    
    def fill_form_intelligently(self, page: Page, field_mappings: List[FieldMapping]) -> bool:
        """تعبئة النموذج مع تسجيل البيانات"""
        try:
            success_count = 0
            
            # تسجيل snapshot للبيانات
            form_snapshot = {
                "timestamp": datetime.datetime.now().isoformat(),
                "fields": [],
                "expected_values": {},
                "actual_values": {}
            }
            
            for mapping in field_mappings:
                filled = False
                
                if mapping.found_selector:
                    if self.dom_fill(page, mapping.found_selector, mapping.value, mapping.field_type):
                        filled = True
                        mapping.filled = True
                        mapping.timestamp = datetime.datetime.now()
                
                if not filled:
                    # Fallback للأسماء الثابتة
                    fallback_map = {
                        "LAST_NAME": ["input[name='lastname']"],
                        "FIRST_NAME": ["input[name='firstname']"],
                        "EMAIL": ["input[name='email']"],
                        "PASSPORT": ["input[name='passportNumber']"],
                        "PHONE": ["input[name='phone']"]
                    }
                    
                    for selector in fallback_map.get(mapping.field_type, []):
                        if self.dom_fill(page, selector, mapping.value, mapping.field_type):
                            filled = True
                            mapping.filled = True
                            mapping.timestamp = datetime.datetime.now()
                            break
                
                # تسجيل في snapshot
                field_data = mapping.to_dict()
                form_snapshot["fields"].append(field_data)
                form_snapshot["expected_values"][mapping.field_type] = mapping.value
                
                if filled:
                    success_count += 1
                    # الحصول على القيمة الفعلية
                    try:
                        actual_value = page.evaluate(f"""
                            document.querySelector('{mapping.found_selector or selector}')?.value || ''
                        """)
                        form_snapshot["actual_values"][mapping.field_type] = actual_value
                    except:
                        form_snapshot["actual_values"][mapping.field_type] = "UNKNOWN"
            
            # اختيار فئة التأشيرة
            if self.select_visa_category_intelligent(page):
                success_count += 1
            
            # حقل تكرار الإيميل
            if self._fill_email_repeat(page, Config.EMAIL):
                success_count += 1
            
            # حفظ snapshot
            self.form_data_snapshot = form_snapshot
            
            self.stats['forms_filled'] += 1
            logger.info(f"📝 Form filled: {success_count}/{len(field_mappings)+2} fields")
            
            return success_count >= len(field_mappings)
            
        except Exception as e:
            logger.error(f"❌ Form filling error: {e}")
            return False
    
    def _fill_email_repeat(self, page: Page, email: str) -> bool:
        """تعبئة حقل تكرار الإيميل"""
        for selector in ["input[name='emailrepeat']", "input[name='emailRepeat']", "#emailRepeat"]:
            try:
                if page.locator(selector).first.is_visible(timeout=300):
                    return self.dom_fill(page, selector, email, "EMAIL_REPEAT")
            except:
                continue
        return False
    
    # ==================== نظام المسح والبحث ====================
    def generate_priority_month_urls(self) -> List[str]:
        """إنشاء روابط الأشهر بأولويات"""
        try:
            today = self.get_synced_time().astimezone(self.timezone).date()
            base_clean = self.base_url.split("&dateStr=")[0] if "&dateStr=" in self.base_url else self.base_url
            
            urls = []
            priority_months = [2, 3, 1, 4, 5, 6]  # مارس، أبريل، فبراير، مايو، يونيو، يوليو
            
            for offset in priority_months:
                future_month = (today.month + offset - 1) % 12 + 1
                future_year = today.year + ((today.month + offset - 1) // 12)
                date_str = f"15.{future_month:02d}.{future_year}"
                urls.append(f"{base_clean}&dateStr={date_str}")
            
            return urls[:8]  # حد أقصى 8 أشهر
            
        except Exception as e:
            logger.error(f"❌ Month URL generation error: {e}")
            return []
    
    def scan_month_for_days(self, page: Page, url: str) -> Tuple[bool, List[str]]:
        """مسح الشهر للبحث عن أيام"""
        try:
            self.stats['scans'] += 1
            
            page.goto(url, timeout=8000, wait_until="domcontentloaded")
            
            if not self.solve_captcha_with_policy(page, "MONTH"):
                return False, []
            
            # البحث عن الأيام
            day_links = []
            links = page.evaluate("""
                () => {
                    const results = [];
                    const anchors = document.querySelectorAll('a[href*="showDay"], td.buchbar a');
                    for(const a of anchors) {
                        if(a.href && a.href.includes('showDay')) {
                            results.push(a.href);
                        }
                    }
                    return results.slice(0, 3);
                }
            """)
            
            for href in links:
                full_url = urljoin(url, href)
                day_links.append(full_url)
            
            if day_links:
                logger.info(f"📅 Found {len(day_links)} days")
            else:
                logger.info("📭 No days available")
            
            return True, day_links
            
        except Exception as e:
            logger.error(f"❌ Month scan error: {e}")
            self.stats['errors'] += 1
            return False, []
    
    def scan_day_for_slots(self, page: Page, day_url: str) -> Tuple[bool, List[str]]:
        """مسح اليوم للبحث عن مواعيد"""
        try:
            page.goto(day_url, timeout=7000, wait_until="domcontentloaded")
            
            if not self.solve_captcha_with_policy(page, "DAY"):
                return False, []
            
            # البحث عن المواعيد
            slot_links = []
            slots = page.evaluate("""
                () => {
                    const results = [];
                    const anchors = document.querySelectorAll('a[href*="showForm"], td a:has-text("Select")');
                    for(const a of anchors) {
                        if(a.href && a.href.includes('showForm')) {
                            results.push({
                                href: a.href,
                                text: a.textContent?.trim() || ''
                            });
                        }
                    }
                    return results.slice(0, 2);
                }
            """)
            
            for slot in slots:
                full_url = urljoin(day_url, slot['href'])
                slot_links.append(full_url)
                logger.debug(f"⏰ Slot: {slot['text'][:30]}")
            
            if slot_links:
                logger.info(f"⏰ Found {len(slot_links)} slots")
            else:
                logger.info("⏳ No slots available")
            
            return True, slot_links
            
        except Exception as e:
            logger.error(f"❌ Day scan error: {e}")
            return False, []
    
    # ==================== محرك الحجز النهائي ====================
    def attempt_booking(self, page: Page, slot_url: str) -> bool:
        """محاولة حجز مع الالتزام بالسياسة"""
        try:
            logger.info("🎯 Attempting booking...")
            
            page.goto(slot_url, timeout=6000, wait_until="domcontentloaded")
            
            if not self.solve_captcha_with_policy(page, "FORM"):
                return False
            
            if not page.locator("form").first.is_visible(timeout=3000):
                logger.error("❌ Form not found")
                return False
            
            # بناء وتعبئة النموذج
            field_mappings = self.build_dynamic_field_map(page)
            if not self.fill_form_intelligently(page, field_mappings):
                logger.error("❌ Form filling failed")
                return False
            
            # التقاط صورة الفورم قبل الإرسال
            form_screenshot = os.path.join(self.evidence_dir, f"form_before_submit_{int(time.time())}.png")
            page.screenshot(path=form_screenshot, full_page=True)
            logger.info(f"📸 Form screenshot saved: {form_screenshot}")
            
            # الإرسال النهائي
            return self._submit_booking_final(page)
            
        except Exception as e:
            logger.error(f"❌ Booking attempt error: {e}")
            return False
    
    def _submit_booking_final(self, page: Page) -> bool:
        """إرسال الحجز النهائي"""
        try:
            logger.info("📤 Final submission...")
            
            if not self.solve_captcha_with_policy(page, "SUBMIT"):
                return False
            
            # البحث عن زر الإرسال
            submit_result = page.evaluate("""
                () => {
                    const buttons = [
                        'input[type="submit"]',
                        'button[type="submit"]',
                        'button:contains("Book")',
                        'button:contains("Submit")'
                    ];
                    
                    for(const selector of buttons) {
                        const btn = document.querySelector(selector);
                        if(btn && btn.offsetParent !== null) {
                            btn.click();
                            return {success: true, selector: selector};
                        }
                    }
                    return {success: false};
                }
            """)
            
            if not submit_result.get('success'):
                page.keyboard.press("Enter")
            
            page.wait_for_timeout(3000)
            
            # التحقق من النجاح
            page_content = page.content().lower()
            
            success_keywords = [
                "appointment number",
                "successfully booked",
                "booking confirmed",
                "vorgang wurde gespeichert"
            ]
            
            for keyword in success_keywords:
                if keyword in page_content:
                    # استخراج التفاصيل
                    appointment_num = re.search(r"appointment number is\s+(\d+)", page_content, re.IGNORECASE)
                    appointment_date = re.search(r"(\d{2}\.\d{2}\.\d{4})", page_content)
                    
                    self.booking_details = {
                        "appointment_number": appointment_num.group(1) if appointment_num else "UNKNOWN",
                        "appointment_date": appointment_date.group(1) if appointment_date else "UNKNOWN",
                        "confirmation_time": datetime.datetime.now().isoformat()
                    }
                    
                    # حفظ الصفحة الناجحة
                    self.success_page_html = page.content()
                    self.success_screenshot = os.path.join(self.evidence_dir, f"success_page_{int(time.time())}.png")
                    page.screenshot(path=self.success_screenshot, full_page=True)
                    
                    # تسجيل النجاح
                    self._log_success()
                    
                    self.stats['success'] = True
                    return True
            
            logger.error("❌ Booking submission failed - no success indicators")
            return False
            
        except Exception as e:
            logger.error(f"❌ Submission error: {e}")
            return False
    
    def _log_success(self):
        """تسجيل النجاح وإرسال التقارير"""
        try:
            success_msg = f"""
🎉🎉🎉 BOOKING SUCCESSFUL! 🎉🎉🎉

📋 Appointment Number: {self.booking_details['appointment_number']}
📅 Appointment Date: {self.booking_details['appointment_date']}
🕒 Confirmation Time: {self.booking_details['confirmation_time']}

👤 Personal Details:
   • Name: {Config.FIRST_NAME} {Config.LAST_NAME}
   • Passport: {Config.PASSPORT}
   • Email: {Config.EMAIL}
   • Phone: {Config.PHONE}

📊 Session Statistics:
   • Session ID: {self.session_id}
   • Total Scans: {self.stats['scans']}
   • Captchas Solved: {self.stats['captchas_solved']}
   • Forms Filled: {self.stats['forms_filled']}
   • Decisions Made: {self.stats['decisions_made']}
   • Runtime: {(datetime.datetime.now() - self.start_time).total_seconds():.0f}s

🏗️ System State:
   • Final State: {self.system_state.value}
   • Session Health: {self.session_health.value}
   • Incidents: {len(self.incidents)}
   • State Transitions: {self.stats['state_transitions']}
            """
            
            # إرسال التنبيه
            send_alert(success_msg.strip())
            
            # إرسال الصور والتقارير بعد النجاح (لتجنب إعاقة الأداء)
            self._send_post_success_reports()
            
        except Exception as e:
            logger.error(f"❌ Success logging error: {e}")
    
    def _send_post_success_reports(self):
        """إرسال التقارير والصور بعد النجاح (بدون إعاقة الأداء)"""
        try:
            # 1. إرسال صورة الفورم
            form_screenshots = [f for f in os.listdir(self.evidence_dir) if "form_before_submit" in f]
            if form_screenshots:
                latest_form = os.path.join(self.evidence_dir, sorted(form_screenshots)[-1])
                send_photo(latest_form, caption="📋 Form before submission")
            
            # 2. إرسال صفحة النجاح
            if self.success_screenshot and os.path.exists(self.success_screenshot):
                send_photo(self.success_screenshot, caption="✅ Success confirmation page")
            
            # 3. إرسال تقرير البيانات
            if self.form_data_snapshot:
                report_data = {
                    "booking_details": self.booking_details,
                    "form_data": self.form_data_snapshot,
                    "session_stats": self.stats,
                    "config_used": {
                        "first_name": Config.FIRST_NAME,
                        "last_name": Config.LAST_NAME,
                        "email": Config.EMAIL,
                        "passport": Config.PASSPORT[:4] + "******",  # جزئي للأمان
                        "phone": Config.PHONE[:6] + "****"
                    }
                }
                
                report_file = os.path.join(self.evidence_dir, "booking_report.json")
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(report_data, f, indent=2, ensure_ascii=False)
                
                send_document(report_file, caption="📄 Booking Report")
            
            # 4. إرسال تقرير State Machine
            state_report = {
                "session_id": self.session_id,
                "state_transitions": [
                    {"from": t.from_state, "to": t.to_state, "reason": t.reason}
                    for t in self.state_transitions
                ],
                "incidents": [inc.to_dict() for inc in self.incidents],
                "final_state": self.system_state.value
            }
            
            state_file = os.path.join(self.evidence_dir, "state_machine_report.json")
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state_report, f, indent=2, ensure_ascii=False)
            
            logger.info("📤 Success reports sent successfully")
            
        except Exception as e:
            logger.error(f"❌ Error sending post-success reports: {e}")
    
    # ==================== نظام STANDBY المنضبط ====================
    def standby_if_justified(self) -> bool:
        """
        الانتقال لـ STANDBY فقط إذا مبرر
        وفقاً لمتطلبات المطور الآخر
        """
        # شروط STANDBY
        standby_conditions = [
            self.system_state == SystemState.ACTIVE,  # فقط من ACTIVE
            self.session_health == SessionHealth.CLEAN,  # جلسة نظيفة
            self.consecutive_errors < 3,  # ليس هناك أخطاء متتالية كثيرة
            self.get_operational_mode() != OperationalMode.ASSAULT,  # خارج نافذة الهجوم
        ]
        
        if not all(standby_conditions):
            return False
        
        # أسباب مبررة للانتظار
        standby_reasons = [
            "Waiting for next scan cycle",
            "No appointments available",
            "Outside operational window"
        ]
        
        reason = random.choice(standby_reasons)
        self.transition_state(SystemState.STANDBY, reason)
        
        # تأخير ذكي حسب النمط
        delay = self._calculate_standby_delay()
        logger.info(f"⏸️  STANDBY: {reason} for {delay:.1f}s")
        time.sleep(delay)
        
        # العودة لـ ACTIVE
        self.transition_state(SystemState.ACTIVE, "STANDBY period completed")
        return True
    
    def _calculate_standby_delay(self) -> float:
        """حساب تأخير STANDBY"""
        mode = self.get_operational_mode()
        
        if mode == OperationalMode.WARMUP:
            return random.uniform(30.0, 60.0)  # 30-60 ثانية
        else:  # SCOUT
            return random.uniform(60.0, 180.0)  # 1-3 دقائق
    
    # ==================== الدورة الرئيسية ====================
    def run(self):
        """الدورة الرئيسية مع State Machine"""
        logger.info("="*60)
        logger.info("👑 King Sniper v12.0.0 - State Machine System")
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
                        "--single-process",
                        "--disable-web-security"
                    ],
                    timeout=30000
                )
                
                # إنشاء السياق الأول
                context, page = self.create_stealth_context(browser)
                self.context = context
                
                cycle = 0
                
                while not self.stats['success']:
                    cycle += 1
                    
                    # التحقق من حالة النظام
                    if self.system_state == SystemState.BLOCKED:
                        logger.critical("💀 System is BLOCKED - requires manual intervention")
                        break
                    
                    if self.session_health == SessionHealth.POISONED:
                        logger.critical("☠️ Session is POISONED - performing emergency reboot")
                        self.emergency_session_reboot(page, "Session poisoned")
                        
                        # إعادة إنشاء السياق
                        try:
                            context.close()
                        except:
                            pass
                        context, page = self.create_stealth_context(browser)
                        continue
                    
                    logger.info(f"\n🔄 Cycle #{cycle} - State: {self.system_state.value}")
                    
                    # تأخير ذكي (لا نوم عشوائي)
                    if self.system_state == SystemState.ACTIVE:
                        delay = self.calculate_delay()
                        if delay > 0.1:
                            logger.debug(f"⏳ Active delay: {delay:.2f}s")
                            time.sleep(delay)
                    
                    # مسح الأشهر
                    month_urls = self.generate_priority_month_urls()
                    found_appointment = False
                    
                    for month_url in month_urls:
                        if self.stats['success'] or found_appointment:
                            break
                        
                        # مسح الشهر
                        scan_ok, day_urls = self.scan_month_for_days(page, month_url)
                        if not scan_ok:
                            self.consecutive_errors += 1
                            continue
                        
                        self.consecutive_errors = 0
                        
                        if not day_urls:
                            continue
                        
                        # مسح الأيام
                        for day_url in day_urls:
                            if self.stats['success'] or found_appointment:
                                break
                            
                            day_ok, slot_urls = self.scan_day_for_slots(page, day_url)
                            if not day_ok or not slot_urls:
                                continue
                            
                            # محاولة الحجز
                            for slot_url in slot_urls:
                                if self.attempt_booking(page, slot_url):
                                    found_appointment = True
                                    break
                                else:
                                    self.consecutive_errors += 1
                    
                    # إذا لم يتم العثور على موعد
                    if not found_appointment and not self.stats['success']:
                        # الانتقال لـ STANDBY إذا مبرر
                        if not self.standby_if_justified():
                            logger.info("🔄 Continuing active scanning")
                    
                    # إحصاءات الدورة
                    if cycle % 5 == 0:
                        self._log_cycle_stats(cycle)
                
                # النجاح - إنهاء نظيف
                if self.stats['success']:
                    self._handle_success_shutdown(context, browser)
                else:
                    self._handle_failure_shutdown(context, browser)
                
                return self.stats['success']
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Stopped by user")
            self._save_session_data()
            return False
            
        except Exception as e:
            logger.error(f"💀 Critical error: {e}")
            logger.exception("Error details:")
            self._save_session_data()
            return False
    
    def _log_cycle_stats(self, cycle: int):
        """تسجيل إحصاءات الدورة"""
        logger.info(f"📊 Cycle #{cycle} Statistics:")
        logger.info(f"   • System State: {self.system_state.value}")
        logger.info(f"   • Session Health: {self.session_health.value}")
        logger.info(f"   • Scans: {self.stats['scans']}")
        logger.info(f"   • Captchas Solved: {self.stats['captchas_solved']}")
        logger.info(f"   • Forms Filled: {self.stats['forms_filled']}")
        logger.info(f"   • Decisions Made: {self.stats['decisions_made']}")
        logger.info(f"   • Incidents: {len(self.incidents)}")
        logger.info(f"   • Consecutive Errors: {self.consecutive_errors}")
    
    def _handle_success_shutdown(self, context, browser):
        """معالجة الإغلاق بعد النجاح"""
        logger.info("\n" + "="*60)
        logger.info("🎊 MISSION ACCOMPLISHED - BOOKING SUCCESSFUL!")
        logger.info("="*60)
        
        # حفظ جميع البيانات
        self._save_session_data()
        
        # إغلاق الموارد
        try:
            context.close()
            browser.close()
        except:
            pass
        
        logger.info("✅ System shutdown complete")
    
    def _handle_failure_shutdown(self, context, browser):
        """معالجة الإغلاق بعد الفشل"""
        logger.info("\n" + "="*60)
        logger.info("❌ Mission ended without booking")
        logger.info("="*60)
        
        # حفظ البيانات
        self._save_session_data()
        
        # إرسال تقرير الفشل
        failure_report = self._generate_failure_report()
        send_alert(failure_report)
        
        # إغلاق الموارد
        try:
            context.close()
            browser.close()
        except:
            pass
        
        logger.info("🛑 System shutdown complete")
    
    def _save_session_data(self):
        """حفظ جميع بيانات الجلسة"""
        try:
            session_data = {
                "session_id": self.session_id,
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.datetime.now().isoformat(),
                "stats": self.stats,
                "system_state": self.system_state.value,
                "session_health": self.session_health.value,
                "incidents": [inc.to_dict() for inc in self.incidents],
                "state_transitions": [
                    {
                        "timestamp": t.timestamp.isoformat(),
                        "from": t.from_state,
                        "to": t.to_state,
                        "reason": t.reason
                    }
                    for t in self.state_transitions
                ],
                "form_snapshot": self.form_data_snapshot,
                "booking_details": self.booking_details
            }
            
            data_file = os.path.join(self.evidence_dir, "session_data.json")
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Session data saved: {data_file}")
            
        except Exception as e:
            logger.error(f"❌ Error saving session data: {e}")
    
    def _generate_final_report(self) -> str:
        """توليد تقرير نهائي"""
        runtime = datetime.datetime.now() - self.start_time
        
        report = f"""
📊 FINAL SYSTEM REPORT - KING SNIPER V12 📊

Session: {self.session_id}
Runtime: {runtime.total_seconds():.0f} seconds
Final State: {self.system_state.value}
Session Health: {self.session_health.value}

📈 Statistics:
• Total Scans: {self.stats['scans']}
• Captchas Solved: {self.stats['captchas_solved']}
• Forms Filled: {self.stats['forms_filled']}
• Decisions Made: {self.stats['decisions_made']}
• Incidents: {len(self.incidents)}
• State Transitions: {self.stats['state_transitions']}

🚨 Incidents: {len(self.incidents)}
"""
        
        for i, inc in enumerate(self.incidents[-3:], 1):  # آخر 3 incidents
            report += f"  {i}. {inc.type} - {inc.severity}\n"
        
        if self.stats['success']:
            report += f"\n🎉 SUCCESS: Booking #{self.booking_details.get('appointment_number', 'UNKNOWN')}"
        else:
            report += "\n❌ No booking made"
        
        return report
    
    def _generate_failure_report(self) -> str:
        """توليد تقرير الفشل"""
        runtime = datetime.datetime.now() - self.start_time
        
        return f"""
❌ FAILURE REPORT - KING SNIPER V12 ❌

Session: {self.session_id}
Runtime: {runtime.total_seconds():.0f} seconds
Final State: {self.system_state.value}
Session Health: {self.session_health.value}

📈 Statistics:
• Scans: {self.stats['scans']}
• Captchas: {self.stats['captchas_solved']}/{self.stats['captchas_failed']}
• Errors: {self.stats['errors']}
• Consecutive Errors: {self.consecutive_errors}
• Incidents: {len(self.incidents)}

🔍 Last State Transition: {self.state_transitions[-1].to_state if self.state_transitions else 'N/A'}
💡 Recommendation: Check incidents and session health
"""

# ==================== نقطة الدخول الرئيسية ====================
if __name__ == "__main__":
    """
    نقطة الدخول الرئيسية
    """
    
    print("="*60)
    print("👑 King Sniper v12.0.0 - State Machine System")
    print("="*60)
    print("الميزات الرئيسية:")
    print("  🏗️  State Machine رسمية (ACTIVE, STANDBY, BLOCKED)")
    print("  🚨 نظام Incident كامل مع تنبيهات")
    print("  🧠 Decision Engine مع Scoring System")
    print("  📸 حفظ أدلة كاملة (Forms + Success Pages)")
    print("  📤 إرسال تقارير بعد النجاح (لا تعيق الأداء)")
    print("="*60)
    
    try:
        sniper = KingSniperV12()
        success = sniper.run()
        
        if success:
            print("\n✅ Mission accomplished!")
            sys.exit(0)
        else:
            print("\n❌ Mission ended without booking")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n💀 Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)