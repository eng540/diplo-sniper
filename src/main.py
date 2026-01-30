#!/usr/bin/env python3
"""
📦 MAIN LAUNCHER - King Sniper v12.0.0
الإصدار: 1.0.0
الوصف: ملف التشغيل الرئيسي مع Auto-Recovery وحماية متقدمة
المسار: src/main.py (بجانب bot.py في نفس المجلد)
"""

import sys
import os
import time
import logging
import json
import traceback
from datetime import datetime
from typing import Optional

# ------------------------------------------------------------------------------
# 1. إعداد المسارات (Path Setup)
# حل مشكلة عدم التعرف على المجلدات عند التشغيل من خارج src
# ------------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = current_dir
project_root = parent_dir

# إضافة المسارات المطلوبة
sys.path.insert(0, src_dir)       # المجلد الحالي (src)
sys.path.insert(0, project_root)  # المجلد الرئيسي

# إنشاء المجلدات المطلوبة
os.makedirs(os.path.join(project_root, "logs"), exist_ok=True)
os.makedirs(os.path.join(project_root, "reports"), exist_ok=True)
os.makedirs(os.path.join(project_root, "backups"), exist_ok=True)

logger = logging.getLogger("KingSniperLauncher")

# ------------------------------------------------------------------------------
# 2. إعداد السجلات المتقدم (Advanced Logging)
# ------------------------------------------------------------------------------
def setup_logging():
    """إعداد نظام السجلات المتقدم"""
    
    # إنشاء formatters
    console_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    file_format = logging.Formatter(
        '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_format)
    console_handler.setLevel(logging.INFO)
    
    # File Handler (daily rotation)
    log_file = os.path.join(project_root, "logs", f"launcher_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(file_format)
    file_handler.setLevel(logging.DEBUG)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return log_file

# ------------------------------------------------------------------------------
# 3. فحص النظام (System Check)
# ------------------------------------------------------------------------------
def check_system_requirements() -> bool:
    """فحص متطلبات النظام قبل التشغيل"""
    
    requirements = {
        "Python Version": sys.version_info >= (3, 8),
        "Project Root": os.path.exists(project_root),
        "Config File": os.path.exists(os.path.join(src_dir, "config.py")),
        "Bot File": os.path.exists(os.path.join(src_dir, "bot.py")),
    }
    
    logger.info("🔍 Checking System Requirements:")
    
    all_ok = True
    for req_name, req_met in requirements.items():
        status = "✅" if req_met else "❌"
        logger.info(f"   {status} {req_name}")
        if not req_met:
            all_ok = False
    
    # فحص المكتبات
    try:
        import playwright
        import pytz
        import ntplib
        logger.info("   ✅ Python Libraries (playwright, pytz, ntplib)")
    except ImportError as e:
        logger.error(f"   ❌ Missing Python Library: {e}")
        all_ok = False
    
    # فحص Chrome/Chromium
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # محاولة تشغيل متصفح
            browser = p.chromium.launch(headless=True, timeout=5000)
            browser.close()
        logger.info("   ✅ Browser (Chromium) available")
    except Exception as e:
        logger.warning(f"   ⚠️ Browser check failed: {e}")
        logger.info("   ℹ️ Trying to install browser...")
        try:
            os.system("playwright install chromium")
            logger.info("   ✅ Browser installed successfully")
        except:
            logger.error("   ❌ Failed to install browser")
            all_ok = False
    
    return all_ok

# ------------------------------------------------------------------------------
# 4. Auto-Recovery System
# ------------------------------------------------------------------------------
class RecoverySystem:
    """نظام الاسترداد التلقائي المتقدم"""
    
    def __init__(self):
        self.crash_count = 0
        self.max_crashes = 10
        self.crash_history = []
        self.recovery_file = os.path.join(project_root, "backups", "recovery_state.json")
        self.start_time = datetime.now()
        
    def log_crash(self, exception: Exception, traceback_str: str):
        """تسجيل تفاصيل الانهيار"""
        crash_id = f"crash_{int(time.time())}"
        
        crash_info = {
            "id": crash_id,
            "timestamp": datetime.now().isoformat(),
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "crash_count": self.crash_count,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
        }
        
        self.crash_history.append(crash_info)
        self.crash_count += 1
        
        # حفظ في ملف
        self._save_crash_report(crash_info, traceback_str)
        
        return crash_info
    
    def _save_crash_report(self, crash_info: dict, traceback_str: str):
        """حفظ تقرير الانهيار"""
        report_dir = os.path.join(project_root, "reports", "crashes")
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, f"{crash_info['id']}.json")
        
        full_report = {
            **crash_info,
            "traceback": traceback_str,
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform,
                "current_directory": os.getcwd(),
                "src_directory": src_dir
            }
        }
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(full_report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📄 Crash report saved: {report_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save crash report: {e}")
    
    def should_recover(self) -> bool:
        """تحديد ما إذا كان يجب محاولة الاسترداد"""
        if self.crash_count >= self.max_crashes:
            logger.critical(f"💥 Maximum crashes reached ({self.max_crashes}). Shutting down.")
            return False
        
        # إذا كانت الانهيارات متتالية بسرعة كبيرة
        if self.crash_count >= 3:
            recent_crashes = self.crash_history[-3:]
            time_diffs = []
            
            for i in range(1, len(recent_crashes)):
                t1 = datetime.fromisoformat(recent_crashes[i-1]["timestamp"])
                t2 = datetime.fromisoformat(recent_crashes[i]["timestamp"])
                time_diffs.append((t2 - t1).total_seconds())
            
            if len(time_diffs) >= 2 and all(t < 30 for t in time_diffs):
                logger.critical("⚡ Rapid consecutive crashes detected. Emergency shutdown.")
                return False
        
        return True
    
    def calculate_wait_time(self) -> float:
        """حساب وقت الانتظار قبل إعادة المحاولة"""
        base_wait = 10  # 10 ثواني أساسية
        
        # زيادة وقت الانتظار مع زيادة الانهيارات
        if self.crash_count > 3:
            base_wait = 30
        
        if self.crash_count > 6:
            base_wait = 60
        
        if self.crash_count > 8:
            base_wait = 120
        
        # إضافة عشوائية لمنع الأنماط
        random_factor = random.uniform(0.8, 1.2)
        
        return base_wait * random_factor
    
    def get_recovery_stats(self) -> dict:
        """الحصول على إحصائيات الاسترداد"""
        return {
            "total_crashes": self.crash_count,
            "max_crashes": self.max_crashes,
            "crash_history": [c["exception_type"] for c in self.crash_history[-5:]],
            "first_crash": self.crash_history[0]["timestamp"] if self.crash_history else None,
            "uptime": (datetime.now() - self.start_time).total_seconds()
        }

# ------------------------------------------------------------------------------
# 5. نظام المراقبة (Monitoring System)
# ------------------------------------------------------------------------------
class SystemMonitor:
    """مراقبة أداء النظام والموارد"""
    
    def __init__(self):
        self.metrics = {
            "start_time": datetime.now(),
            "cycles_completed": 0,
            "total_runtime": 0,
            "peak_memory": 0,
            "exceptions_count": 0
        }
        
    def log_cycle_start(self):
        """تسجيل بداية دورة جديدة"""
        self.metrics["cycles_completed"] += 1
        self.cycle_start_time = datetime.now()
        
    def log_cycle_end(self):
        """تسجيل نهاية دورة"""
        if hasattr(self, 'cycle_start_time'):
            cycle_time = (datetime.now() - self.cycle_start_time).total_seconds()
            self.metrics["total_runtime"] += cycle_time
            
            logger.debug(f"⏱️ Cycle {self.metrics['cycles_completed']} completed in {cycle_time:.1f}s")
    
    def check_resources(self) -> bool:
        """فحص موارد النظام"""
        try:
            import psutil
            
            # فحص استخدام الذاكرة
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.metrics["peak_memory"]:
                self.metrics["peak_memory"] = memory_mb
            
            # فحص استخدام CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # فحص مساحة التخزين
            disk_usage = psutil.disk_usage(project_root)
            disk_free_gb = disk_usage.free / (1024**3)
            
            # تحذير إذا كانت الموارد منخفضة
            warnings = []
            
            if memory_mb > 500:  # أكثر من 500MB
                warnings.append(f"High memory usage: {memory_mb:.1f}MB")
            
            if cpu_percent > 80:  # أكثر من 80%
                warnings.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if disk_free_gb < 1:  # أقل من 1GB حر
                warnings.append(f"Low disk space: {disk_free_gb:.1f}GB free")
            
            if warnings:
                logger.warning(f"⚠️ Resource warnings: {', '.join(warnings)}")
                return False
            
            return True
            
        except ImportError:
            # psutil غير مثبت، تخطي فحص الموارد
            return True
        except Exception as e:
            logger.debug(f"Resource check skipped: {e}")
            return True
    
    def generate_report(self) -> dict:
        """توليد تقرير المراقبة"""
        uptime = (datetime.now() - self.metrics["start_time"]).total_seconds()
        
        report = {
            **self.metrics,
            "uptime_seconds": uptime,
            "uptime_human": self._format_time(uptime),
            "average_cycle_time": self.metrics["total_runtime"] / max(self.metrics["cycles_completed"], 1),
            "report_time": datetime.now().isoformat()
        }
        
        return report
    
    def _format_time(self, seconds: float) -> str:
        """تنسيق الوقت لصيغة مقروءة"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

# ------------------------------------------------------------------------------
# 6. Dynamic Bot Loader
# ------------------------------------------------------------------------------
def load_bot_module():
    """تحميل وحدة البوت ديناميكياً مع دعم متعدد"""
    
    bot_modules_to_try = [
        "bot",              # الافتراضي: bot.py
        "king_sniper_v12",  # النسخة المحسنة
        "elite_sniper",     # أسماء بديلة
        "sniper"            # أسماء بديلة
    ]
    
    bot_classes_to_try = [
        "EliteSniper",      # الافتراضي
        "KingSniperV12",    # النسخة المحسنة
        "KingSniper",       # أسماء بديلة
        "SniperBot"         # أسماء بديلة
    ]
    
    loaded_module = None
    loaded_class = None
    
    for module_name in bot_modules_to_try:
        try:
            module_path = os.path.join(src_dir, f"{module_name}.py")
            if not os.path.exists(module_path):
                continue
            
            # استيراد الديناميكي
            module = __import__(module_name)
            loaded_module = module_name
            
            # البحث عن الكلاس المناسب
            for class_name in bot_classes_to_try:
                if hasattr(module, class_name):
                    loaded_class = getattr(module, class_name)
                    logger.info(f"✅ Loaded: {module_name}.{class_name}")
                    return loaded_class
            
        except ImportError as e:
            continue
        except Exception as e:
            logger.debug(f"Failed to load {module_name}: {e}")
            continue
    
    # إذا لم يتم تحميل أي شيء
    raise ImportError(f"No valid bot module found. Tried: {', '.join(bot_modules_to_try)}")

# ------------------------------------------------------------------------------
# 7. الدالة الرئيسية للتشغيل
# ------------------------------------------------------------------------------
def run_king_unit():
    """
    تقوم بتشغيل البوت داخل حلقة حماية متقدمة
    مع Auto-Recovery ومراقبة الموارد
    """
    
    # إعداد السجلات
    log_file = setup_logging()
    
    # عرض معلومات البدء
    logger.info("=" * 60)
    logger.info("👑 KING SNIPER LAUNCHER v1.0.0")
    logger.info("=" * 60)
    logger.info(f"📂 Project Root: {project_root}")
    logger.info(f"📁 Source Directory: {src_dir}")
    logger.info(f"📝 Log File: {log_file}")
    logger.info("=" * 60)
    
    # فحص النظام
    if not check_system_requirements():
        logger.critical("❌ System requirements check failed. Exiting.")
        sys.exit(1)
    
    # تهيئة أنظمة الدعم
    recovery = RecoverySystem()
    monitor = SystemMonitor()
    
    # تحميل البوت
    try:
        BotClass = load_bot_module()
    except ImportError as e:
        logger.critical(f"❌ Failed to load bot module: {e}")
        logger.info("💡 Make sure bot.py exists in src/ with class EliteSniper")
        sys.exit(1)
    
    # الحلقة الرئيسية
    while True:
        try:
            monitor.log_cycle_start()
            
            logger.info("🚀 LAUNCHING KING SNIPER PROTOCOL...")
            logger.info(f"📊 Recovery Stats: {recovery.get_recovery_stats()}")
            
            # فحص الموارد قبل البدء
            if not monitor.check_resources():
                logger.warning("⚠️ Resource check failed, delaying launch...")
                time.sleep(10)
                continue
            
            # تهيئة وتشغيل البوت
            logger.info("🎯 Initializing Sniper Core...")
            bot_instance = BotClass()
            
            logger.info("▶️ Starting Execution...")
            success = bot_instance.run()
            
            # تسجيل نهاية الدورة
            monitor.log_cycle_end()
            
            if success:
                logger.info("🏆 MISSION ACCOMPLISHED - Booking Successful!")
                
                # توليد التقارير النهائية
                final_report = monitor.generate_report()
                logger.info(f"📊 Final Report: {json.dumps(final_report, indent=2)}")
                
                break  # الخروج من الحلقة بنجاح
            else:
                logger.warning("⚠️ Mission ended without booking success")
                
                # الاستمرار في المحاولة (ما لم يكن هناك أمر بالتوقف)
                continue
            
        except KeyboardInterrupt:
            logger.info("🛑 MANUAL SHUTDOWN REQUESTED")
            
            # حفظ تقرير نهائي
            final_report = monitor.generate_report()
            logger.info(f"📊 Session Report: {json.dumps(final_report, indent=2)}")
            
            sys.exit(0)
            
        except SystemExit as e:
            # خروج نظامي
            logger.info(f"🛑 System Exit: {e}")
            sys.exit(e.code)
            
        except Exception as e:
            # معالجة الانهيار
            traceback_str = traceback.format_exc()
            crash_info = recovery.log_crash(e, traceback_str)
            
            monitor.log_cycle_end()
            monitor.metrics["exceptions_count"] += 1
            
            logger.error(f"💥 SYSTEM CRASH (#{crash_info['crash_count']})")
            logger.error(f"📛 Type: {crash_info['exception_type']}")
            logger.error(f"📛 Message: {crash_info['exception_message']}")
            logger.debug(f"📋 Traceback:\n{traceback_str}")
            
            # تحديد ما إذا كان يجب الاسترداد
            if not recovery.should_recover():
                logger.critical("💀 MAXIMUM RECOVERY ATTEMPTS REACHED - SHUTTING DOWN")
                
                # تقرير نهائي
                final_report = monitor.generate_report()
                crash_report = {
                    **final_report,
                    "crash_history": recovery.crash_history,
                    "total_crashes": recovery.crash_count
                }
                
                # حفظ تقرير الانهيار النهائي
                crash_file = os.path.join(project_root, "reports", "final_crash_report.json")
                with open(crash_file, 'w', encoding='utf-8') as f:
                    json.dump(crash_report, f, indent=2, ensure_ascii=False)
                
                logger.info(f"📄 Final crash report saved: {crash_file}")
                sys.exit(1)
            
            # حساب وقت الانتظار وإعادة التشغيل
            wait_time = recovery.calculate_wait_time()
            logger.info(f"♻️ Auto-Recovery in {wait_time:.1f} seconds...")
            
            # عرض إحصائيات
            stats = recovery.get_recovery_stats()
            logger.info(f"📈 Recovery Stats: {stats['total_crashes']}/{stats['max_crashes']} crashes")
            
            # الانتظار قبل إعادة المحاولة
            for i in range(int(wait_time)):
                if i % 5 == 0:  # تحديث كل 5 ثواني
                    remaining = wait_time - i
                    logger.info(f"⏳ Waiting... {remaining:.0f}s remaining")
                time.sleep(1)
            
            logger.info("🔄 RESTARTING SYSTEM...")
            continue

# ------------------------------------------------------------------------------
# 8. نقطة الدخول (Entry Point)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # تهيئة عشوائية
    import random
    random.seed()
    
    # بدء التشغيل
    run_king_unit()