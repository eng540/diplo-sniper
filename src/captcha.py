import ddddocr

class CaptchaSolver:
    def __init__(self):
        self.ocr = ddddocr.DdddOcr(show_ad=False)

    def solve(self, image_bytes):
        try:
            res = self.ocr.classification(image_bytes)
            print(f"[AI] Captcha Solved: {res}")
            return res
        except Exception as e:
            print(f"[AI] Error solving captcha: {e}")
            return ""
