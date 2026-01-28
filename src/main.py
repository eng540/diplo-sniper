import sys
import os
import time
import logging

# --- حل مشكلة المسارات في الحاويات (Docker/Container Path Fix) ---
# إضافة المسار الحالي ومسار مجلد src لضمان رؤية جميع الملفات
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'src'))

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("MainLauncher")

# --- استيراد البوت بمرونة عالية ---
try:
    # المحاولة الأولى: الاستيراد كحزمة من src
    from src.bot import DiploBot
    logger.info("✅ Unit identified: DiploBot found in src.bot")
except ImportError:
    try:
        # المحاولة الثانية: الاستيراد المباشر (إذا كان main داخل src)
        from bot import DiploBot
        logger.info("✅ Unit identified: DiploBot found in direct path")
    except ImportError as e:
        logger.critical(f"❌ Failed to find Bot module. Error: {e}")
        sys.exit(1)

def run_king_unit():
    """تشغيل الوحدة الملكية مع نظام الاستعادة التلقائي"""
    while True:
        try:
            logger.info("👑 KING SNIPER PROTOCOL: Launching Royal Unit...")
            
            # تشغيل نسخة واحدة فقط كما طلبت
            bot = DiploBot()
            bot.run()
            
            # إذا وصل الكود هنا، فهذا يعني أن عملية الحجز تمت بنجاح
            logger.info("🏆 MISSION ACCOMPLISHED: Appointment Secured.")
            break 

        except Exception as e:
            logger.error(f"⚠️ Unit Crashed: {e}")
            wait_time = 15
            logger.info(f"♻️ Re-initiating protocol in {wait_time} seconds...")
            time.sleep(wait_time)

if __name__ == "__main__":
    run_king_unit()
