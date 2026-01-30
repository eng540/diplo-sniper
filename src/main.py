#!/usr/bin/env python3
"""
📦 DIPLO SNIPER MAIN LAUNCHER - VERSION 3.0
الإصدار: 3.0.0 (Final Production)
الوصف: المحمل الرئيسي المتوافق مع جميع إصدارات Diplo-Sniper
المميزات: Auto-Recovery, Health Checks, Compatibility Mode
"""

import sys
import os
import time
import logging
import json
import traceback
import random
import signal
from datetime import datetime
from typing import Optional, Dict, Any, List, Type

# ===================================================================
# 1. إعداد المسارات الأساسية
# ===================================================================
def setup_paths() -> tuple:
    """إعداد المسارات الأساسية للنظام"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    src_dir = current_dir
    project_root = parent_dir
    
    # إضافة المسارات للنظام
    sys.path.insert(0, src_dir)
    sys.path.insert(0, project_root)
    
    # إنشاء المجلدات الأساسية
    essential_dirs = ["logs", "evidence", "debug", "backups"]
    for dir_name in essential_dirs:
        os.makedirs(os.path.join(project_root, dir_name), exist_ok=True)
    
    return src_dir, project_root

# ===================================================================
# 2. إعداد نظام السجلات المتقدم
# ===================================================================
class AdvancedLogger:
    """نظام سجلات متقدم مع تلوين ومراقبة"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[41m', # Red background
        'RESET': '\033[0m'      # Reset
    }
    
    def __init__(self):
        self.logger = logging.getLogger("DiploMain")
        self.setup_logging()
        
    def setup_logging(self):
        """إعداد نظام السجلات المتقدم"""
        self.logger.handlers.clear()
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        
        # Formatter ملون
        class ColoredFormatter(logging.Formatter):
            def format(self, record):
                levelname = record.levelname
                if levelname in AdvancedLogger.COLORS:
                    record.levelname = f"{AdvancedLogger.COLORS[levelname]}{levelname}{AdvancedLogger.COLORS['RESET']}"
                return super().format(record)
        
        # Console Handler (ملون)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # File Handler (تفصيلي)
        file_handler = logging.FileHandler(
            f"logs/main_launcher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
        return file_handler.baseFilename
    
    def get_logger(self):
        """الحصول على كائن الـ logger"""
        return self.logger

# ===================================================================
# 3. نظام فحص الصحة والموارد
# ===================================================================
class SystemHealthChecker:
    """فحص صحة النظام والموارد"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.requirements_met = False
        
    def check_all_requirements(self) -> tuple:
        """فحص جميع متطلبات النظام"""
        checks = {
            "Python Version": self.check_python_version(),
            "Essential Files": self.check_essential_files(),
            "Dependencies": self.check_dependencies(),
            "Browser": self.check_browser(),
            "Disk Space": self.check_disk_space(),
            "Memory": self.check_memory(),
            "Network": self.check_network(),
        }
        
        all_passed = all(checks.values())
        self.requirements_met = all_passed
        
        return all_passed, checks
    
    def check_python_version(self) -> bool:
        """فحص إصدار Python"""
        return sys.version_info >= (3, 8)
    
    def check_essential_files(self) -> bool:
        """فحص الملفات الأساسية"""
        essential_files = {
            "config.py": os.path.join(self.project_root, "src", "config.py"),
            "bot.py": os.path.join(self.project_root, "src", "bot.py"),
        }
        
        missing_files = []
        for name, path in essential_files.items():
            if not os.path.exists(path):
                missing_files.append(name)
        
        return len(missing_files) == 0
    
    def check_dependencies(self) -> bool:
        """فحص المكتبات المطلوبة"""
        required_libs = ["playwright", "requests"]
        
        for lib in required_libs:
            try:
                __import__(lib)
            except ImportError:
                return False
        
        return True
    
    def check_browser(self) -> bool:
        """فحص متصفح Chromium"""
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                # محاولة تشغيل متصفح بسيط
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                    timeout=10000
                )
                browser.close()
            
            return True
        except Exception as e:
            print(f"Browser check failed: {e}")
            return False
    
    def check_disk_space(self, min_gb: float = 0.5) -> bool:
        """فحص مساحة التخزين"""
        try:
            import shutil
            
            stat = shutil.disk_usage(self.project_root)
            free_gb = stat.free / (1024 ** 3)
            
            return free_gb >= min_gb
        except:
            return True  # تجاهل الفحص إذا فشل
    
    def check_memory(self, min_mb: int = 500) -> bool:
        """فحص الذاكرة"""
        try:
            import psutil
            
            available_mb = psutil.virtual_memory().available / (1024 ** 2)
            return available_mb >= min_mb
        except ImportError:
            return True  # تجاهل إذا psutil غير مثبت
    
    def check_network(self) -> bool:
        """فحص الاتصال بالشبكة"""
        try:
            import socket
            import urllib.request
            
            # فحص DNS
            socket.gethostbyname("google.com")
            
            # فحص اتصال بالإنترنت
            urllib.request.urlopen("http://www.google.com", timeout=5)
            
            return True
        except:
            return False

# ===================================================================
# 4. نظام الاسترداد الذكي (Smart Recovery)
# ===================================================================
class SmartRecoverySystem:
    """نظام استرداد ذكي مع تعلم من الأخطاء"""
    
    def __init__(self):
        self.crash_history = []
        self.session_start = datetime.now()
        self.successful_cycles = 0
        
        # إعدادات مرنة للتشغيل السحابي
        self.max_crashes = 20
        self.rapid_crash_threshold = 5  # 5 انهيارات في 5 دقائق
        self.rapid_crash_window = 300   # 5 دقائق بالثواني
        
    def record_crash(self, error: Exception, traceback_str: str, context: dict = None):
        """تسجيل تفاصيل الانهيار مع السياق"""
        crash_id = f"crash_{int(time.time())}_{random.randint(1000, 9999)}"
        
        crash_info = {
            "id": crash_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "crash_number": len(self.crash_history) + 1,
            "session_duration": (datetime.now() - self.session_start).total_seconds(),
            "context": context or {},
            "successful_cycles_before": self.successful_cycles
        }
        
        self.crash_history.append(crash_info)
        
        # حفظ تقرير الانهيار
        self._save_crash_report(crash_info, traceback_str)
        
        return crash_info
    
    def _save_crash_report(self, crash_info: dict, traceback_str: str):
        """حفظ تقرير الانهيار"""
        try:
            report_dir = os.path.join("debug", "crashes")
            os.makedirs(report_dir, exist_ok=True)
            
            report_file = os.path.join(report_dir, f"{crash_info['id']}.json")
            
            full_report = {
                **crash_info,
                "traceback": traceback_str,
                "system_info": {
                    "python_version": sys.version,
                    "platform": sys.platform,
                    "current_dir": os.getcwd(),
                    "argv": sys.argv
                }
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(full_report, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Failed to save crash report: {e}")
    
    def should_recover(self) -> bool:
        """تحديد ما إذا كان يجب الاستمرار في الاسترداد"""
        if len(self.crash_history) >= self.max_crashes:
            return False
        
        # تحقق من الانهيارات السريعة المتتالية
        if len(self.crash_history) >= self.rapid_crash_threshold:
            recent_crashes = self.crash_history[-self.rapid_crash_threshold:]
            timestamps = [datetime.fromisoformat(c["timestamp"]) for c in recent_crashes]
            
            # حساب الوقت بين الانهيارات
            time_diffs = []
            for i in range(1, len(timestamps)):
                diff = (timestamps[i] - timestamps[i-1]).total_seconds()
                time_diffs.append(diff)
            
            # إذا كانت جميع الانهيارات في نافذة زمنية قصيرة
            if all(diff < self.rapid_crash_window for diff in time_diffs):
                print(f"⚠️ Rapid consecutive crashes detected")
                return False
        
        return True
    
    def calculate_wait_time(self) -> float:
        """حساب وقت الانتظار الذكي"""
        crash_count = len(self.crash_history)
        
        # استراتيجية الانتظار المرنة
        wait_strategies = [
            (0, 5, 10),    # 0-4 crashes: 5-10 ثواني
            (5, 10, 30),   # 5-9 crashes: 10-30 ثواني
            (10, 30, 60),  # 10-14 crashes: 30-60 ثواني
            (15, 60, 120), # 15+ crashes: 1-2 دقائق
        ]
        
        for threshold, min_wait, max_wait in wait_strategies:
            if crash_count >= threshold:
                base_min, base_max = min_wait, max_wait
        
        # إضافة عشوائية لمنع الأنماط
        wait_time = random.uniform(base_min, base_max)
        
        # زيادة وقت الانتظار في الليل (مفترض)
        hour = datetime.now().hour
        if 0 <= hour < 6:  # منتصف الليل إلى 6 صباحاً
            wait_time *= 1.5
        
        return wait_time
    
    def record_success(self):
        """تسجيل دورة ناجحة"""
        self.successful_cycles += 1
    
    def get_stats(self) -> dict:
        """الحصول على إحصائيات الاسترداد"""
        return {
            "total_crashes": len(self.crash_history),
            "successful_cycles": self.successful_cycles,
            "session_duration": (datetime.now() - self.session_start).total_seconds(),
            "recovery_rate": self.successful_cycles / max(len(self.crash_history), 1),
            "last_crash_type": self.crash_history[-1]["error_type"] if self.crash_history else None
        }

# ===================================================================
# 5. محمل البوت الذكي (Smart Bot Loader)
# ===================================================================
class SmartBotLoader:
    """محمل ذكي للبوت مع دعم متعدد"""
    
    def __init__(self, src_dir: str):
        self.src_dir = src_dir
        self.bot_versions = []
        
    def discover_bots(self) -> List[dict]:
        """اكتشاف جميع إصدارات البوت المتاحة"""
        bot_files = [
            ("bot.py", ["EliteSniper", "DiploSniper", "SniperBot"]),
            ("king_sniper_v12.py", ["KingSniperV12", "KingSniper"]),
            ("elite_sniper.py", ["EliteSniper"]),
            ("sniper.py", ["Sniper"]),
        ]
        
        discovered = []
        for filename, class_names in bot_files:
            filepath = os.path.join(self.src_dir, filename)
            
            if os.path.exists(filepath):
                for class_name in class_names:
                    discovered.append({
                        "file": filename,
                        "class": class_name,
                        "path": filepath,
                        "exists": True
                    })
        
        self.bot_versions = discovered
        return discovered
    
    def load_best_bot(self) -> Type:
        """تحميل أفضل إصدار متاح من البوت"""
        discovered = self.discover_bots()
        
        if not discovered:
            raise ImportError("No bot files found in src/ directory")
        
        # محاولة تحميل بالترتيب
        for bot_info in discovered:
            try:
                BotClass = self._load_specific_bot(bot_info["file"], bot_info["class"])
                return BotClass
            except Exception as e:
                continue
        
        raise ImportError(f"Failed to load any bot class. Tried: {[b['class'] for b in discovered]}")
    
    def _load_specific_bot(self, filename: str, classname: str) -> Type:
        """تحميل إصدار محدد من البوت"""
        try:
            # إزالة .py
            module_name = filename[:-3]
            
            # استيراد الديناميكي
            module = __import__(module_name)
            
            # البحث عن الكلاس
            if hasattr(module, classname):
                return getattr(module, classname)
            
            # البحث في جميع السمات
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and attr_name.lower() == classname.lower():
                    return attr
            
            raise AttributeError(f"Class {classname} not found in {filename}")
            
        except Exception as e:
            raise ImportError(f"Failed to load {classname} from {filename}: {e}")

# ===================================================================
# 6. نظام المراقبة في الوقت الحقيقي
# ===================================================================
class RealTimeMonitor:
    """مراقبة النظام في الوقت الحقيقي"""
    
    def __init__(self):
        self.metrics = {
            "start_time": datetime.now(),
            "cycles_completed": 0,
            "total_runtime": 0,
            "peak_memory_mb": 0,
            "captcha_attempts": 0,
            "pages_scanned": 0,
            "forms_filled": 0,
            "errors_encountered": 0,
            "state_changes": 0
        }
        
    def start_cycle(self):
        """بدء دورة جديدة"""
        self.cycle_start = datetime.now()
        self.metrics["cycles_completed"] += 1
    
    def end_cycle(self):
        """إنهاء الدورة الحالية"""
        if hasattr(self, 'cycle_start'):
            cycle_time = (datetime.now() - self.cycle_start).total_seconds()
            self.metrics["total_runtime"] += cycle_time
    
    def update_metric(self, metric: str, value: Any = 1):
        """تحديث مقياس معين"""
        if metric in self.metrics:
            if isinstance(self.metrics[metric], (int, float)):
                self.metrics[metric] += value
            else:
                self.metrics[metric] = value
    
    def check_resources(self) -> bool:
        """فحص موارد النظام"""
        try:
            import psutil
            
            # فحص الذاكرة
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / (1024 ** 2)
            
            if memory_mb > self.metrics["peak_memory_mb"]:
                self.metrics["peak_memory_mb"] = memory_mb
            
            # فحص CPU
            cpu_percent = psutil.cpu_percent(interval=0.5)
            
            # تحذيرات
            warnings = []
            if memory_mb > 800:  # أكثر من 800MB
                warnings.append(f"High memory: {memory_mb:.1f}MB")
            
            if cpu_percent > 85:  # أكثر من 85%
                warnings.append(f"High CPU: {cpu_percent:.1f}%")
            
            if warnings:
                print(f"⚠️ Resource warnings: {', '.join(warnings)}")
            
            return len(warnings) == 0
            
        except ImportError:
            return True  # تجاهل إذا psutil غير مثبت
        except Exception as e:
            print(f"Resource check failed: {e}")
            return True
    
    def generate_report(self) -> dict:
        """توليد تقرير المراقبة"""
        uptime = (datetime.now() - self.metrics["start_time"]).total_seconds()
        
        report = {
            **self.metrics,
            "uptime_seconds": uptime,
            "uptime_formatted": self._format_time(uptime),
            "average_cycle_time": self.metrics["total_runtime"] / max(self.metrics["cycles_completed"], 1),
            "efficiency_score": self._calculate_efficiency(),
            "report_time": datetime.now().isoformat(),
            "health_status": self._get_health_status()
        }
        
        return report
    
    def _calculate_efficiency(self) -> float:
        """حساب كفاءة النظام"""
        if self.metrics["cycles_completed"] == 0:
            return 0.0
        
        # معادلة كفاءة مبسطة
        cycles = self.metrics["cycles_completed"]
        errors = self.metrics["errors_encountered"]
        runtime = self.metrics["total_runtime"]
        
        if runtime == 0:
            return 0.0
        
        efficiency = (cycles * 100) / (errors + 1) / runtime
        return min(efficiency, 100.0)
    
    def _get_health_status(self) -> str:
        """تحديد حالة صحة النظام"""
        efficiency = self._calculate_efficiency()
        
        if efficiency > 80:
            return "EXCELLENT"
        elif efficiency > 60:
            return "GOOD"
        elif efficiency > 40:
            return "FAIR"
        elif efficiency > 20:
            return "POOR"
        else:
            return "CRITICAL"
    
    def _format_time(self, seconds: float) -> str:
        """تنسيق الوقت بشكل مقروء"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

# ===================================================================
# 7. نظام معالجة الإشارات (Signal Handler)
# ===================================================================
class SignalHandler:
    """معالجة إشارات النظام للإنهاء النظيف"""
    
    def __init__(self, logger):
        self.logger = logger
        self.shutdown_requested = False
        self.setup_handlers()
    
    def setup_handlers(self):
        """إعداد معالجات الإشارات"""
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
    
    def handle_signal(self, signum, frame):
        """معالجة إشارة النظام"""
        signals = {
            signal.SIGINT: "SIGINT (Ctrl+C)",
            signal.SIGTERM: "SIGTERM"
        }
        
        signal_name = signals.get(signum, f"Signal {signum}")
        self.logger.info(f"📡 Received {signal_name}, initiating graceful shutdown...")
        
        self.shutdown_requested = True
    
    def is_shutdown_requested(self) -> bool:
        """التحقق مما إذا تم طلب الإيقاف"""
        return self.shutdown_requested

# ===================================================================
# 8. الدالة الرئيسية للتشغيل
# ===================================================================
def main():
    """الدالة الرئيسية للتشغيل"""
    
    # ============== المرحلة 1: الإعدادات الأولية ==============
    src_dir, project_root = setup_paths()
    
    # إعداد السجلات
    logger_system = AdvancedLogger()
    logger = logger_system.get_logger()
    log_file = logger_system.setup_logging()
    
    # شاشة البدء
    logger.info("=" * 70)
    logger.info("🚀 DIPLO-SNIPER MAIN LAUNCHER v3.0 - PRODUCTION READY")
    logger.info("=" * 70)
    logger.info(f"📁 Project Root: {project_root}")
    logger.info(f"📂 Source Directory: {src_dir}")
    logger.info(f"📝 Log File: {log_file}")
    logger.info(f"🐍 Python Version: {sys.version}")
    logger.info(f"🖥️  Platform: {sys.platform}")
    logger.info("=" * 70)
    
    # ============== المرحلة 2: فحص النظام ==============
    logger.info("🔍 Running comprehensive system check...")
    
    health_checker = SystemHealthChecker(project_root)
    all_passed, checks = health_checker.check_all_requirements()
    
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        logger.info(f"   {status} {check_name}")
    
    if not all_passed:
        logger.critical("❌ System requirements not met. Exiting.")
        sys.exit(1)
    
    logger.info("✅ All system checks passed successfully!")
    
    # ============== المرحلة 3: تحميل البوت ==============
    logger.info("🤖 Loading bot system...")
    
    bot_loader = SmartBotLoader(src_dir)
    discovered_bots = bot_loader.discover_bots()
    
    logger.info(f"📊 Found {len(discovered_bots)} potential bot configurations:")
    for bot in discovered_bots:
        logger.info(f"   • {bot['file']} -> {bot['class']}")
    
    try:
        BotClass = bot_loader.load_best_bot()
        bot_name = BotClass.__name__
        logger.info(f"✅ Successfully loaded: {bot_name}")
    except Exception as e:
        logger.critical(f"❌ Failed to load any bot: {e}")
        logger.info("💡 Make sure bot.py exists in src/ with a valid bot class")
        sys.exit(1)
    
    # ============== المرحلة 4: تهيئة الأنظمة المساعدة ==============
    logger.info("⚙️ Initializing support systems...")
    
    recovery = SmartRecoverySystem()
    monitor = RealTimeMonitor()
    signal_handler = SignalHandler(logger)
    
    # ============== المرحلة 5: الحلقة الرئيسية للتشغيل ==============
    logger.info("🚀 Starting main execution loop...")
    
    cycle = 0
    session_success = False
    
    while not session_success:
        cycle += 1
        
        # التحقق من طلب الإيقاف
        if signal_handler.is_shutdown_requested():
            logger.info("🛑 Shutdown requested, stopping gracefully...")
            break
        
        try:
            monitor.start_cycle()
            
            logger.info(f"\n{'='*50}")
            logger.info(f"🔄 EXECUTION CYCLE #{cycle}")
            logger.info(f"{'='*50}")
            
            # عرض إحصائيات الاسترداد
            recovery_stats = recovery.get_stats()
            logger.info(f"📈 Recovery Stats: {recovery_stats['total_crashes']} crashes, "
                       f"{recovery_stats['successful_cycles']} successful cycles")
            
            # فحص الموارد
            if not monitor.check_resources():
                logger.warning("⚠️ Resource check failed, waiting before retry...")
                time.sleep(30)
                continue
            
            # ============== تشغيل البوت ==============
            logger.info(f"🎯 Initializing {bot_name}...")
            
            bot_instance = BotClass()
            
            logger.info("▶️ Starting bot execution...")
            success = bot_instance.run()
            
            monitor.end_cycle()
            
            if success:
                logger.info("🏆 MISSION ACCOMPLISHED - BOOKING SUCCESSFUL!")
                
                recovery.record_success()
                session_success = True
                
                # توليد تقرير النجاح
                final_report = monitor.generate_report()
                logger.info(f"📊 Final Report:")
                logger.info(f"   • Cycles: {final_report['cycles_completed']}")
                logger.info(f"   • Total Runtime: {final_report['uptime_formatted']}")
                logger.info(f"   • Efficiency Score: {final_report['efficiency_score']:.1f}")
                logger.info(f"   • Health Status: {final_report['health_status']}")
                
                # إرسال تنبيه النجاح
                try:
                    from notifier import send_alert
                    success_message = (
                        f"🎉 Diplo-Sniper: MISSION ACCOMPLISHED!\n"
                        f"✅ Booking successful!\n"
                        f"⏱️ Runtime: {final_report['uptime_formatted']}\n"
                        f"🔄 Cycles: {final_report['cycles_completed']}\n"
                        f"📊 Efficiency: {final_report['efficiency_score']:.1f}"
                    )
                    send_alert(success_message)
                except Exception as e:
                    logger.warning(f"Could not send success alert: {e}")
                
                break  # الخروج من الحلقة بنجاح
                
            else:
                logger.warning("⚠️ Bot execution completed without booking success")
                
                recovery.record_success()  # حتى بدون حجز، تعتبر دورة ناجحة
                
                # الاستمرار في المحاولة بعد تأخير قصير
                retry_delay = 60  # 60 ثانية
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                
                # التأخير مع إمكانية الإيقاف
                for i in range(retry_delay):
                    if signal_handler.is_shutdown_requested():
                        logger.info("🛑 Shutdown during retry delay")
                        break
                    time.sleep(1)
                
                if signal_handler.is_shutdown_requested():
                    break
                
                continue  # الاستمرار في الحلقة
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Manual shutdown requested by user")
            break
            
        except SystemExit as e:
            logger.info(f"🛑 System exit with code: {e.code}")
            sys.exit(e.code)
            
        except Exception as e:
            # ============== معالجة الانهيار ==============
            trace_str = traceback.format_exc()
            crash_context = {
                "cycle": cycle,
                "bot_class": bot_name,
                "monitor_metrics": monitor.metrics.copy()
            }
            
            crash_info = recovery.record_crash(e, trace_str, crash_context)
            
            monitor.end_cycle()
            monitor.update_metric("errors_encountered", 1)
            
            logger.error(f"💥 SYSTEM CRASH #{crash_info['crash_number']}")
            logger.error(f"📛 Error Type: {crash_info['error_type']}")
            logger.error(f"📛 Error Message: {crash_info['error_message'][:200]}")
            
            # تحقق مما إذا كان يجب الاستمرار
            if not recovery.should_recover():
                logger.critical(f"💀 MAXIMUM RECOVERY ATTEMPTS REACHED ({recovery.max_crashes})")
                
                # توليد تقرير الفشل النهائي
                failure_report = monitor.generate_report()
                failure_report.update({
                    "final_status": "MAX_CRASHES_REACHED",
                    "crash_history_count": len(recovery.crash_history),
                    "session_duration": recovery_stats['session_duration']
                })
                
                failure_file = os.path.join("debug", "final_failure_report.json")
                with open(failure_file, 'w', encoding='utf-8') as f:
                    json.dump(failure_report, f, indent=2, ensure_ascii=False)
                
                logger.info(f"📄 Final failure report saved: {failure_file}")
                
                # إرسال تنبيه الفشل
                try:
                    from notifier import send_alert
                    failure_message = (
                        f"🔴 Diplo-Sniper: CRITICAL FAILURE\n"
                        f"❌ Max crashes reached: {recovery.max_crashes}\n"
                        f"💥 Last error: {crash_info['error_type']}\n"
                        f"⏱️ Session duration: {recovery_stats['session_duration']:.0f}s\n"
                        f"🔄 Successful cycles: {recovery_stats['successful_cycles']}"
                    )
                    send_alert(failure_message)
                except:
                    pass
                
                sys.exit(1)
            
            # حساب وقت الانتظار وإعادة التشغيل
            wait_time = recovery.calculate_wait_time()
            logger.info(f"♻️ Auto-recovery in {wait_time:.1f} seconds...")
            
            # عرض العد التنازلي مع إمكانية الإيقاف
            for remaining in range(int(wait_time), 0, -5):
                if signal_handler.is_shutdown_requested():
                    logger.info("🛑 Shutdown during recovery wait")
                    break
                    
                if remaining % 30 == 0 or remaining <= 10:
                    logger.info(f"⏳ Recovery in {remaining}s...")
                
                time.sleep(5)
            
            if signal_handler.is_shutdown_requested():
                break
            
            logger.info("🔄 Restarting system...")
            continue
    
    # ============== المرحلة 6: الإنهاء النظيف ==============
    logger.info("\n" + "=" * 70)
    
    if session_success:
        logger.info("🎊 SESSION COMPLETED SUCCESSFULLY!")
    else:
        logger.info("🛑 SESSION TERMINATED")
    
    # عرض الإحصائيات النهائية
    final_stats = monitor.generate_report()
    logger.info(f"📊 FINAL STATISTICS:")
    logger.info(f"   • Total Cycles: {final_stats['cycles_completed']}")
    logger.info(f"   • Total Runtime: {final_stats['uptime_formatted']}")
    logger.info(f"   • Peak Memory: {final_stats['peak_memory_mb']:.1f}MB")
    logger.info(f"   • Errors Encountered: {final_stats['errors_encountered']}")
    logger.info(f"   • Efficiency Score: {final_stats['efficiency_score']:.1f}")
    logger.info(f"   • Health Status: {final_stats['health_status']}")
    
    # إحصائيات الاسترداد
    recovery_final = recovery.get_stats()
    logger.info(f"🔄 RECOVERY STATISTICS:")
    logger.info(f"   • Total Crashes: {recovery_final['total_crashes']}")
    logger.info(f"   • Successful Cycles: {recovery_final['successful_cycles']}")
    logger.info(f"   • Recovery Rate: {recovery_final['recovery_rate']:.1%}")
    
    logger.info("=" * 70)
    logger.info("👋 System shutdown complete")
    
    if session_success:
        sys.exit(0)
    else:
        sys.exit(1)

# ===================================================================
# 9. نقطة الدخول
# ===================================================================
if __name__ == "__main__":
    main()