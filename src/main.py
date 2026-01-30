#!/usr/bin/env python3
"""
📦 MAIN LAUNCHER - King Sniper v12.0.0 (Diplo-Sniper Edition)
الإصدار: 1.0.0
الوصف: ملف التشغيل الرئيسي متكامل مع نظام Diplo-Sniper الموجود
المسار: src/main.py (بجانب bot.py في نفس المجلد)
"""

import sys
import os
import time
import logging
import json
import traceback
import random
from datetime import datetime
from typing import Optional, Dict, Any

# ------------------------------------------------------------------------------
# 1. إعداد المسارات (Path Setup) - متوافق مع هيكل Diplo-Sniper
# ------------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = current_dir
project_root = parent_dir

# إضافة المسارات المطلوبة لنظام Python
sys.path.insert(0, src_dir)       # المجلد الحالي (src)
sys.path.insert(0, project_root)  # المجلد الرئيسي

# إنشاء المجلدات المطلوبة
os.makedirs(os.path.join(project_root, "logs"), exist_ok=True)
os.makedirs(os.path.join(project_root, "evidence"), exist_ok=True)
os.makedirs(os.path.join(project_root, "crashes"), exist_ok=True)

logger = logging.getLogger("KingLauncher")

# ------------------------------------------------------------------------------
# 2. إعداد السجلات (Logging Configuration)
# ------------------------------------------------------------------------------
def setup_logging():
    """إعداد نظام السجلات المتوافق مع Diplo-Sniper"""
    
    # Formatter للنظام الحالي
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # File Handler (يومي)
    log_file = os.path.join(project_root, "logs", f"king_launcher_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # إعداد الـ Logger
    logger.handlers.clear()
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    
    return log_file

# ------------------------------------------------------------------------------
# 3. فحص النظام المتوافق مع Diplo-Sniper
# ------------------------------------------------------------------------------
def check_system_requirements() -> bool:
    """فحص متطلبات النظام لـ Diplo-Sniper"""
    
    # الملفات الأساسية المطلوبة
    required_files = {
        "config.py": os.path.join(src_dir, "config.py"),
        "bot.py": os.path.join(src_dir, "bot.py"),
        "notifier.py": os.path.join(src_dir, "notifier.py"),
        "captcha.py": os.path.join(src_dir, "captcha.py"),
    }
    
    logger.info("🔍 Diplo-Sniper System Check:")
    
    # فحص الملفات
    all_ok = True
    for file_name, file_path in required_files.items():
        exists = os.path.exists(file_path)
        status = "✅" if exists else "❌"
        logger.info(f"   {status} {file_name}")
        
        if not exists and file_name != "captcha.py":  # captcha.py قد يكون اختياري
            all_ok = False
            if file_name == "config.py":
                logger.error(f"      ملف config.py غير موجود! يجب إنشاؤه بناءً على config.example.py")
    
    # فحص المكتبات الأساسية
    try:
        import requests
        logger.info("   ✅ requests library")
    except ImportError:
        logger.error("   ❌ مكتبة requests غير مثبتة. قم بتثبيتها: pip install requests")
        all_ok = False
    
    try:
        from playwright.sync_api import sync_playwright
        logger.info("   ✅ playwright library")
    except ImportError:
        logger.error("   ❌ مكتبة playwright غير مثبتة. قم بتثبيتها: pip install playwright")
        all_ok = False
    
    # فحص متصفح Chromium
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, timeout=10000)
            browser.close()
        logger.info("   ✅ Chromium browser")
    except Exception as e:
        logger.warning(f"   ⚠️ فشل تشغيل Chromium: {e}")
        logger.info("   محاولة تثبيت المتصفح...")
        try:
            import subprocess
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            logger.info("   ✅ تم تثبيت Chromium بنجاح")
        except Exception as install_error:
            logger.error(f"   ❌ فشل تثبيت Chromium: {install_error}")
            all_ok = False
    
    # فحص تكوين التليجرام
    try:
        from config import Config
        if hasattr(Config, 'TELEGRAM_TOKEN') and hasattr(Config, 'TELEGRAM_CHAT_ID'):
            if Config.TELEGRAM_TOKEN and Config.TELEGRAM_CHAT_ID:
                logger.info("   ✅ Telegram configuration")
            else:
                logger.warning("   ⚠️ إعدادات التليجرام غير مكتملة")
        else:
            logger.warning("   ⚠️ إعدادات التليجرام غير موجودة في config.py")
    except ImportError:
        logger.error("   ❌ لا يمكن قراءة ملف config.py")
        all_ok = False
    
    return all_ok

# ------------------------------------------------------------------------------
# 4. نظام الاسترداد الذكي (Smart Recovery System)
# ------------------------------------------------------------------------------
class DiploRecovery:
    """نظام الاسترداد المتوافق مع Diplo-Sniper"""
    
    def __init__(self):
        self.crash_count = 0
        self.max_crashes = 15  # زيادة الحد للأمان
        self.crash_history = []
        self.session_start = datetime.now()
        self.recovery_file = os.path.join(project_root, "crashes", "recovery.json")
        
        # إنشاء مجلد الانهيارات
        os.makedirs(os.path.join(project_root, "crashes"), exist_ok=True)
    
    def record_crash(self, error: Exception, trace: str):
        """تسجيل تفاصيل الانهيار"""
        crash_id = f"crash_{int(time.time())}"
        
        crash_info = {
            "id": crash_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "crash_number": self.crash_count + 1,
            "session_duration": (datetime.now() - self.session_start).total_seconds()
        }
        
        self.crash_history.append(crash_info)
        self.crash_count += 1
        
        # حفظ في ملف
        self._save_crash_details(crash_info, trace)
        
        return crash_info
    
    def _save_crash_details(self, info: Dict[str, Any], trace: str):
        """حفظ تفاصيل الانهيار"""
        crash_dir = os.path.join(project_root, "crashes", info["id"])
        os.makedirs(crash_dir, exist_ok=True)
        
        # حفظ معلومات الانهيار
        info_file = os.path.join(crash_dir, "crash_info.json")
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        
        # حفظ الـ traceback
        trace_file = os.path.join(crash_dir, "traceback.txt")
        with open(trace_file, 'w', encoding='utf-8') as f:
            f.write(trace)
        
        logger.info(f"📄 تم حفظ تفاصيل الانهيار: {crash_dir}")
    
    def should_recover(self) -> bool:
        """تحديد ما إذا كان يجب الاستمرار في المحاولات"""
        if self.crash_count >= self.max_crashes:
            logger.critical(f"💥 وصل للحد الأقصى من الانهيارات ({self.max_crashes})")
            return False
        
        # تحقق من الانهيارات السريعة المتتالية
        if self.crash_count >= 3:
            recent = self.crash_history[-3:]
            times = [datetime.fromisoformat(c["timestamp"]) for c in recent]
            
            # إذا كانت الانهيارات في أقل من دقيقة
            time_diffs = [(times[i] - times[i-1]).total_seconds() for i in range(1, len(times))]
            if len(time_diffs) >= 2 and all(t < 60 for t in time_diffs):
                logger.critical("⚡ اكتشاف انهيارات سريعة متتالية!")
                return False
        
        return True
    
    def get_wait_time(self) -> float:
        """حساب وقت الانتظار قبل إعادة التشغيل"""
        # وقت أساسي مع زيادة تدريجية
        base_time = 10
        
        if self.crash_count > 3:
            base_time = 30
        
        if self.crash_count > 6:
            base_time = 60
        
        if self.crash_count > 9:
            base_time = 120
        
        if self.crash_count > 12:
            base_time = 300  # 5 دقائق
        
        # إضافة عشوائية لمنع الأنماط
        random_factor = random.uniform(0.9, 1.1)
        
        return base_time * random_factor
    
    def get_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الاسترداد"""
        return {
            "total_crashes": self.crash_count,
            "max_allowed": self.max_crashes,
            "remaining_attempts": self.max_crashes - self.crash_count,
            "session_duration": (datetime.now() - self.session_start).total_seconds(),
            "last_errors": [c["error_type"] for c in self.crash_history[-3:]]
        }

# ------------------------------------------------------------------------------
# 5. محمل البوت الديناميكي
# ------------------------------------------------------------------------------
def load_diplo_bot():
    """
    تحميل البوت ديناميكياً مع دعم الأسماء المختلفة
    """
    
    # قائمة بالملفات المحتملة
    possible_files = [
        "bot.py",           # الاسم الافتراضي
        "king_sniper.py",   # النسخة المحسنة
        "elite_sniper.py",  # النسخة الأصلية
        "sniper.py",        # اسم مختصر
    ]
    
    # قائمة بالأسماء المحتملة للكلاسات
    possible_classes = [
        "EliteSniper",      # من bot.py
        "KingSniperV12",    # النسخة المحسنة
        "KingSniper",       # النسخة الملكية
        "DiploSniper",      # اسم بديل
        "SniperBot",        # اسم عام
    ]
    
    for file_name in possible_files:
        file_path = os.path.join(src_dir, file_name)
        
        if not os.path.exists(file_path):
            continue
        
        try:
            # استيراد الملف كوحدة
            module_name = file_name[:-3]  # إزالة .py
            module = __import__(module_name)
            
            # البحث عن الكلاس المناسب
            for class_name in possible_classes:
                if hasattr(module, class_name):
                    logger.info(f"✅ تم تحميل {file_name} -> {class_name}")
                    return getattr(module, class_name)
            
        except ImportError as e:
            logger.debug(f"فشل تحميل {file_name}: {e}")
            continue
        except Exception as e:
            logger.debug(f"خطأ في {file_name}: {e}")
            continue
    
    # إذا وصلنا هنا، لم يتم تحميل أي شيء
    raise ImportError("لم يتم العثور على أي ملف بوت صالح. تأكد من وجود bot.py في مجلد src/")

# ------------------------------------------------------------------------------
# 6. نظام المراقبة الذكي
# ------------------------------------------------------------------------------
class SystemWatcher:
    """مراقب أداء النظام"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.cycles = 0
        self.total_runtime = 0
        
    def start_cycle(self):
        """بدء دورة جديدة"""
        self.cycle_start = datetime.now()
        self.cycles += 1
    
    def end_cycle(self):
        """إنهاء الدورة الحالية"""
        if hasattr(self, 'cycle_start'):
            duration = (datetime.now() - self.cycle_start).total_seconds()
            self.total_runtime += duration
    
    def check_health(self) -> bool:
        """فحص صحة النظام"""
        try:
            # فحص استخدام الذاكرة
            import psutil
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > 1000:  # أكثر من 1GB
                logger.warning(f"⚠️ استخدام ذاكرة عالي: {memory_mb:.1f}MB")
                return False
            
            return True
            
        except ImportError:
            # psutil غير مثبت، تجاهل الفحص
            return True
        except Exception as e:
            logger.debug(f"تخطي فحص الصحة: {e}")
            return True
    
    def get_report(self) -> Dict[str, Any]:
        """تقرير عن أداء النظام"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "session_start": self.start_time.isoformat(),
            "total_cycles": self.cycles,
            "total_runtime_seconds": self.total_runtime,
            "session_uptime_seconds": uptime,
            "average_cycle_time": self.total_runtime / max(self.cycles, 1)
        }

# ------------------------------------------------------------------------------
# 7. الإجراءات عند النجاح
# ------------------------------------------------------------------------------
def handle_success(session_data: Dict[str, Any]):
    """معالجة النجاح وإرسال التقارير"""
    try:
        from notifier import send_alert, send_file
        
        # إرسال تنبيه النجاح
        success_msg = f"""
🎉 نجاح الحجز! - King Sniper v12

📋 جلسة: {session_data.get('session_id', 'N/A')}
⏰ مدة التشغيل: {session_data.get('uptime_seconds', 0):.0f} ثانية
🔄 عدد الدورات: {session_data.get('cycles', 0)}
📊 الحالات: {session_data.get('state_changes', 0)}

🏆 المهمة مكتملة بنجاح!
        """
        
        send_alert(success_msg.strip())
        
        # إرسال ملف السجلات إذا كان موجوداً
        log_file = os.path.join(project_root, "logs", f"king_launcher_{datetime.now().strftime('%Y%m%d')}.log")
        if os.path.exists(log_file):
            send_file(log_file, "📋 سجلات التشغيل الكاملة")
        
        logger.info("✅ تم إرسال تقارير النجاح")
        
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال تقارير النجاح: {e}")

# ------------------------------------------------------------------------------
# 8. الدالة الرئيسية للتشغيل
# ------------------------------------------------------------------------------
def launch_diplo_sniper():
    """
    الدالة الرئيسية لتشغيل Diplo-Sniper مع نظام استرداد ذكي
    """
    
    # إعداد السجلات
    log_file = setup_logging()
    
    # شاشة البدء
    logger.info("=" * 60)
    logger.info("👑 DIPLO-SNIPER KING LAUNCHER v12.0.0")
    logger.info("=" * 60)
    logger.info(f"📁 المسار الرئيسي: {project_root}")
    logger.info(f"📂 مجلد المصادر: {src_dir}")
    logger.info(f"📝 ملف السجلات: {log_file}")
    logger.info("=" * 60)
    
    # فحص النظام
    if not check_system_requirements():
        logger.critical("❌ فشل فحص النظام. الخروج...")
        sys.exit(1)
    
    # تهيئة الأنظمة المساعدة
    recovery = DiploRecovery()
    watcher = SystemWatcher()
    
    # تحميل البوت
    try:
        BotClass = load_diplo_bot()
    except ImportError as e:
        logger.critical(f"❌ فشل تحميل البوت: {e}")
        logger.info("💡 تأكد من وجود ملف bot.py في مجلد src/ يحتوي على class EliteSniper")
        sys.exit(1)
    
    # الحلقة الرئيسية
    while True:
        try:
            watcher.start_cycle()
            
            logger.info("🚀 بدء تشغيل بروتوكول Diplo-Sniper...")
            
            # عرض إحصائيات الاسترداد
            stats = recovery.get_stats()
            logger.info(f"📊 إحصائيات: {stats['total_crashes']} انهيارات، {stats['remaining_attempts']} محاولات متبقية")
            
            # فحص صحة النظام
            if not watcher.check_health():
                logger.warning("⚠️ فحص الصحة فشل، تأخير التشغيل...")
                time.sleep(30)
                continue
            
            # تهيئة وتشغيل البوت
            logger.info("🎯 تهيئة نواة Sniper...")
            bot_instance = BotClass()
            
            logger.info("▶️ بدء التنفيذ...")
            success = bot_instance.run()
            
            # تسجيل نهاية الدورة
            watcher.end_cycle()
            
            if success:
                logger.info("🏆 إنجاز المهمة - نجاح الحجز!")
                
                # توليد تقرير النجاح
                session_report = watcher.get_report()
                session_report["session_id"] = getattr(bot_instance, 'session_id', 'unknown')
                session_report["success"] = True
                
                # معالجة النجاح
                handle_success(session_report)
                
                # حفظ التقرير النهائي
                final_report_file = os.path.join(project_root, "logs", "final_success.json")
                with open(final_report_file, 'w', encoding='utf-8') as f:
                    json.dump(session_report, f, indent=2, ensure_ascii=False)
                
                logger.info(f"📄 تم حفظ التقرير النهائي: {final_report_file}")
                break  # الخروج من الحلقة بنجاح
                
            else:
                logger.warning("⚠️ انتهت المهمة بدون نجاح الحجز")
                watcher.end_cycle()
                continue
                
        except KeyboardInterrupt:
            logger.info("🛑 طلب إيقاف يدوي")
            
            # حفظ تقرير الجلسة
            session_report = watcher.get_report()
            session_report["stopped_by_user"] = True
            
            report_file = os.path.join(project_root, "logs", "user_stopped.json")
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(session_report, f, indent=2, ensure_ascii=False)
            
            sys.exit(0)
            
        except SystemExit as e:
            logger.info(f"🛑 خروج نظامي: {e}")
            sys.exit(e.code)
            
        except Exception as e:
            # معالجة الانهيار
            trace_str = traceback.format_exc()
            crash_info = recovery.record_crash(e, trace_str)
            
            watcher.end_cycle()
            
            logger.error(f"💥 انهيار النظام (#{crash_info['crash_number']})")
            logger.error(f"📛 النوع: {crash_info['error_type']}")
            logger.error(f"📛 الرسالة: {crash_info['error_message']}")
            
            # التحقق مما إذا كان يجب الاستمرار
            if not recovery.should_recover():
                logger.critical("💀 وصل للحد الأقصى من محاولات الاسترداد")
                
                # تقرير فشل نهائي
                failure_report = {
                    **watcher.get_report(),
                    "crash_history": recovery.crash_history,
                    "total_crashes": recovery.crash_count,
                    "final_status": "MAX_CRASHES_REACHED"
                }
                
                failure_file = os.path.join(project_root, "crashes", "final_failure.json")
                with open(failure_file, 'w', encoding='utf-8') as f:
                    json.dump(failure_report, f, indent=2, ensure_ascii=False)
                
                logger.info(f"📄 تقرير الفشل النهائي: {failure_file}")
                sys.exit(1)
            
            # حساب وقت الانتظار
            wait_time = recovery.get_wait_time()
            logger.info(f"♻️ استرداد تلقائي خلال {wait_time:.1f} ثانية...")
            
            # عرض العد التنازلي
            for remaining in range(int(wait_time), 0, -5):
                if remaining % 30 == 0 or remaining <= 10:
                    logger.info(f"⏳ متبقي: {remaining} ثانية")
                time.sleep(5)
            
            logger.info("🔄 إعادة تشغيل النظام...")
            continue

# ------------------------------------------------------------------------------
# 9. نقطة الدخول الرئيسية
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # بدء التشغيل
    launch_diplo_sniper()