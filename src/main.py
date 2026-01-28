import sys
import os
import time
import logging

# ------------------------------------------------------------------------------
# 1. إعداد المسارات (Path Setup)
# حل مشكلة عدم التعرف على المجلدات عند التشغيل من خارج src
# ------------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)  # إضافة src للمسار
sys.path.append(parent_dir)   # إضافة المجلد الرئيسي للمسار

# ------------------------------------------------------------------------------
# 2. إعداد السجلات (Logging Configuration)
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MainLauncher")

# ------------------------------------------------------------------------------
# 3. استيراد البوت (Dynamic Import)
# محاولة استيراد EliteSniper من ملف bot.py
# ------------------------------------------------------------------------------
try:
    # يفترض أن ملف البوت اسمه bot.py والكلاس داخله اسمه EliteSniper
    from bot import EliteSniper
    logger.info("✅ Core System Loaded: EliteSniper Class found.")
except ImportError as e:
    logger.critical(f"❌ Failed to load bot module: {e}")
    logger.critical("Make sure 'bot.py' exists in 'src/' and contains class 'EliteSniper'.")
    sys.exit(1)

# ------------------------------------------------------------------------------
# 4. دالة التشغيل الرئيسية (Execution Loop)
# ------------------------------------------------------------------------------
def run_king_unit():
    """
    تقوم بتشغيل البوت داخل حلقة حماية (Safety Loop)
    لضمان إعادة التشغيل التلقائي في حال انهيار البرنامج لأي سبب خارجي.
    """
    crash_count = 0
    
    while True:
        try:
            logger.info("👑 SYSTEM STARTUP: Initializing Elite Sniper Protocol...")
            
            # تهيئة وتشغيل البوت
            bot = EliteSniper()
            bot.run()

            # إذا وصل الكود هنا (عاد من دالة run)، فهذا يعني انتهاء المهمة بنجاح
            logger.info("🏆 MISSION ACCOMPLISHED. System shutting down.")
            break 

        except KeyboardInterrupt:
            logger.info("🛑 Manual Shutdown Requested.")
            sys.exit(0)
            
        except Exception as e:
            crash_count += 1
            wait_time = 10  # وقت الانتظار قبل إعادة المحاولة
            
            logger.error(f"⚠️ SYSTEM CRASH (#{crash_count}): {e}")
            logger.info(f"♻️ Auto-Recovery initiated in {wait_time} seconds...")
            
            time.sleep(wait_time)

# ------------------------------------------------------------------------------
# 5. نقطة الدخول (Entry Point)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    run_king_unit()