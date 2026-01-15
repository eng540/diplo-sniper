import time
import random
from playwright.sync_api import sync_playwright
from .config import Config
from .captcha import CaptchaSolver
from .notifier import send_alert

class DiploBot:
    def __init__(self):
        self.solver = CaptchaSolver()

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
            context = browser.new_context(user_agent="Mozilla/5.0")
            page = context.new_page()

            print(f"[*] Starting monitoring: {Config.TARGET_URL}")

            while True:
                try:
                    page.goto(Config.TARGET_URL, timeout=60000)

                    if page.locator("#captcha").is_visible():
                        captcha_bytes = page.locator("captcha_image_selector").screenshot()
                        code = self.solver.solve(captcha_bytes)
                        page.fill("input[name='captcha']", code)
                        page.click("input[type='submit']")
                        page.wait_for_load_state("networkidle")

                    content = page.content()
                    if "No appointments" in content or "keine Termine" in content:
                        time.sleep(random.randint(45, 90))
                        continue

                    send_alert("SLOT FOUND!")
                    break

                except Exception as e:
                    print(e)
                    time.sleep(10)
