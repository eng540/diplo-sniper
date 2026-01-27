import threading
import time
# التغيير الجوهري: استيراد KingSniper بدلاً من DiploBot
from src.bot import KingSniper 

def start_bot(instance_id):
    try:
        print(f"⚔️ Launching King Unit-{instance_id}...")
        # إنشاء نسخة جديدة من الملك
        bot = KingSniper()
        # تشغيل البوت
        bot.run()
    except Exception as e:
        print(f"⚠️ King Unit-{instance_id} Crashed: {e}")

if __name__ == "__main__":
    print("👑 KING HYDRA PROTOCOL INITIATED: Launching 3 Royal Units...")
    
    threads = []
    # تشغيل 3 وحدات متوازية (يمكنك زيادة الرقم إذا كان السيرفر يتحمل)
    for i in range(1, 4):
        t = threading.Thread(target=start_bot, args=(i,))
        t.start()
        threads.append(t)
        # فاصل زمني بسيط جداً عند التشغيل لتجنب خنق المعالج لحظة الإقلاع
        time.sleep(2) 

    # إبقاء البرنامج الرئيسي يعمل طالما الوحدات تعمل
    for t in threads:
        t.join()