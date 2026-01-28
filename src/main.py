import time
import logging
import sys
import os

# Add the parent directory to sys.path to allow running from src directly or root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# استيراد كود النخبة الذي جهزناه
try:
    from src.elite_sniper import EliteSniper
except ImportError:
    # Fallback if run from inside src
    from elite_sniper import EliteSniper

# إعداد السجلات للملف الرئيسي
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("MainLauncher")

def run_royal_unit():
    """تشغيل وحدة ملكية واحدة مع نظام استعادة تلقائي"""
    retry_count = 0
    max_retries = 5 # عدد محاولات إعادة التشغيل في حال الانهيار الكلي

    while retry_count < max_retries:
        try:
            logger.info(f"👑 KING SNIPER PROTOCOL: Launching Royal Unit (Attempt {retry_count + 1})...")
            
            # إنشاء كائن البوت وتشغيله
            bot = EliteSniper()
            bot.run()
            
            # إذا انتهت الدالة بنجاح (تحقق النصر)
            logger.info("🏆 Mission Accomplished. Unit shutting down gracefully.")
            break

        except Exception as e:
            retry_count += 1
            logger.error(f"⚠️ Unit Crashed: {e}")
            
            if retry_count < max_retries:
                wait_time = 10  # انتظر 10 ثوانٍ قبل محاولة الولادة من جديد
                logger.info(f"♻️ Re-initiating protocol in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.critical("🚨 MAX RETRIES REACHED. Manual intervention required.")

if __name__ == "__main__":
    print("""
    *****************************************
    * KING SNIPER - ELITE EDITION      *
    * Target: Muscat Appointment       *
    * Status: Single Unit (Heavy)      *
    *****************************************
    """)
    run_royal_unit()
