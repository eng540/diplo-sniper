import ddddocr
import cv2
import numpy as np

class CaptchaSolver:
    def __init__(self):
        # تفعيل وضع البيتا (الأذكى)
        self.ocr = ddddocr.DdddOcr(show_ad=False, beta=True)

    def preprocess_image(self, image_bytes):
        """
        معمل معالجة الصور: تنظيف وتجهيز الصورة قبل القراءة
        """
        try:
            # 1. تحويل البايتات إلى مصفوفة صور
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # 2. تحويل للرمادي
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 3. إزالة التشويش (Denoising)
            # يزيل النقاط الصغيرة دون التأثير على الحروف
            denoised = cv2.fastNlMeansDenoising(gray, h=30)

            # 4. تحويل للأبيض والأسود الصارم (Thresholding)
            # أي شيء ليس أسود داكن سيصبح أبيضاً (إزالة الخطوط الرمادية الباهتة)
            _, binary = cv2.threshold(denoised, 150, 255, cv2.THRESH_BINARY)

            # 5. فحص "نظافة" الصورة (Cherry Picking Strategy)
            # نحسب عدد النقاط السوداء (الحبر)
            total_pixels = binary.size
            black_pixels = total_pixels - cv2.countNonZero(binary)
            density = black_pixels / total_pixels

            # إذا كانت الصورة سوداء جداً (أكثر من 25% حبر)، فهي معقدة جداً
            # نرفضها ليقوم البوت بتحديثها
            if density > 0.25:
                print(f"[AI] Image too noisy (Density: {density:.2f}). Rejecting.")
                return None

            # إعادة تحويل الصورة المعالجة إلى بايتات
            _, encoded_img = cv2.imencode('.png', binary)
            return encoded_img.tobytes()

        except Exception as e:
            print(f"[AI] Preprocessing error: {e}")
            return image_bytes # في حال الخطأ، نستخدم الصورة الأصلية

    def solve(self, image_bytes):
        try:
            # مرحلة المعالجة الأولية
            clean_bytes = self.preprocess_image(image_bytes)
            
            if clean_bytes is None:
                return "REFRESH" # إشارة للبوت بتغيير الصورة

            # القراءة بالذكاء الاصطناعي
            res = self.ocr.classification(clean_bytes)
            
            # تنظيف النص الناتج
            res = res.replace(" ", "").strip()
            
            print(f"[AI] Captcha Solved: {res}")
            return res
        except Exception as e:
            print(f"[AI] Error solving captcha: {e}")
            return ""