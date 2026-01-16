import ddddocr

class CaptchaSolver:
    def __init__(self):
        # تفعيل وضع البيتا لدقة أعلى مع الكابتشا المعقدة
        self.ocr = ddddocr.DdddOcr(show_ad=False, beta=True)

    def solve(self, image_bytes):
        try:
            res = self.ocr.classification(image_bytes)
            # تنظيف النتيجة من أي مسافات
            res = res.replace(" ", "").strip()
            print(f"[AI] Captcha Solved: {res}")
            return res
        except Exception as e:
            print(f"[AI] Error solving captcha: {e}")
            return ""