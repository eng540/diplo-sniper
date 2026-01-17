import ddddocr

class CaptchaSolver:
    def __init__(self):
        # نستخدم وضع البيتا (الأقوى عالمياً لهذا النوع)
        self.ocr = ddddocr.DdddOcr(show_ad=False, beta=True)

    def solve(self, image_bytes):
        try:
            # نرسل الصورة خام كما هي
            res = self.ocr.classification(image_bytes)
            # تنظيف النتيجة فقط
            res = res.replace(" ", "").strip()
            print(f"[AI] Captcha Solved: {res}")
            return res
        except Exception as e:
            print(f"[AI] Error solving captcha: {e}")
            return ""