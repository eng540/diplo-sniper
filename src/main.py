import threading
import time
from src.bot import DiploBot

def start_bot(instance_id):
    try:
        bot = DiploBot(instance_id)
        bot.run()
    except Exception as e:
        print(f"Unit-{instance_id} Crashed: {e}")

if __name__ == "__main__":
    print("🚀 HYDRA LAUNCHING 3 UNITS...")
    threads = []
    for i in range(1, 4):
        t = threading.Thread(target=start_bot, args=(i,))
        t.start()
        threads.append(t)
        time.sleep(1.5) # فرق زمني بسيط جداً لتجنب الحظر

    for t in threads:
        t.join()