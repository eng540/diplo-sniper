"""
📡 NOTIFIER SYSTEM - PRODUCTION VERSION
الإصدار: 2.0.0
الوصف: نظام الإشعارات المتكامل والمتوافق
المميزات: Telegram, Retry Logic, Error Handling
"""

import requests
import os
import time
import logging
from typing import Optional, Tuple
from src.config import Config

logger = logging.getLogger("Notifier")

# ==================== إعدادات التليجرام ====================
TELEGRAM_TOKEN = getattr(Config, 'TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = getattr(Config, 'TELEGRAM_CHAT_ID', '')

# ==================== دوال الإرسال الرئيسية ====================
def send_alert(message: str, max_retries: int = 3) -> Tuple[bool, str]:
    """
    إرسال رسالة نصية مع إعادة المحاولة
    
    Args:
        message: نص الرسالة
        max_retries: الحد الأقصى للمحاولات
        
    Returns:
        tuple: (نجاح العملية, رسالة الخطأ إن وجدت)
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("⚠️ Telegram credentials not configured")
        return False, "Telegram credentials not configured"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, data=data, timeout=15)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                logger.debug(f"✅ Alert sent successfully (attempt {attempt})")
                return True, ""
            else:
                error_msg = result.get("description", "Unknown error")
                logger.error(f"❌ Telegram error: {error_msg}")
                
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout sending alert (attempt {attempt})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # Exponential backoff
            continue
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request error: {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            continue
            
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False, str(e)
    
    return False, "Max retries exceeded"

def send_photo(photo_path: str, caption: str = "", max_retries: int = 3) -> Tuple[bool, str]:
    """
    إرسال صورة مع إعادة المحاولة
    
    Args:
        photo_path: مسار الصورة
        caption: وصف الصورة
        max_retries: الحد الأقصى للمحاولات
        
    Returns:
        tuple: (نجاح العملية, رسالة الخطأ إن وجدت)
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("⚠️ Telegram credentials not configured")
        return False, "Telegram credentials not configured"
    
    if not os.path.exists(photo_path):
        logger.error(f"❌ Photo file not found: {photo_path}")
        return False, f"File not found: {photo_path}"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    
    for attempt in range(1, max_retries + 1):
        try:
            with open(photo_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
                
                response = requests.post(url, files=files, data=data, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                if result.get("ok"):
                    logger.debug(f"✅ Photo sent successfully (attempt {attempt})")
                    return True, ""
                else:
                    error_msg = result.get("description", "Unknown error")
                    logger.error(f"❌ Telegram photo error: {error_msg}")
                    
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout sending photo (attempt {attempt})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            continue
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request error: {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            continue
            
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False, str(e)
    
    return False, "Max retries exceeded"

def send_file(file_path: str, caption: str = "", max_retries: int = 3) -> Tuple[bool, str]:
    """
    إرسال ملف مع إعادة المحاولة
    
    Args:
        file_path: مسار الملف
        caption: وصف الملف
        max_retries: الحد الأقصى للمحاولات
        
    Returns:
        tuple: (نجاح العملية, رسالة الخطأ إن وجدت)
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("⚠️ Telegram credentials not configured")
        return False, "Telegram credentials not configured"
    
    if not os.path.exists(file_path):
        logger.error(f"❌ File not found: {file_path}")
        return False, f"File not found: {file_path}"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    
    for attempt in range(1, max_retries + 1):
        try:
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
                
                response = requests.post(url, files=files, data=data, timeout=45)
                response.raise_for_status()
                
                result = response.json()
                if result.get("ok"):
                    logger.info(f"📤 File sent successfully: {os.path.basename(file_path)}")
                    return True, ""
                else:
                    error_msg = result.get("description", "Unknown error")
                    logger.error(f"❌ Telegram file error: {error_msg}")
                    
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout sending file (attempt {attempt})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            continue
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request error: {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            continue
            
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False, str(e)
    
    return False, "Max retries exceeded"

def send_document(document_path: str, caption: str = "", max_retries: int = 3) -> Tuple[bool, str]:
    """
    إرسال مستند - توافق مع King Sniper v12
    
    Args:
        document_path: مسار المستند
        caption: وصف المستند
        max_retries: الحد الأقصى للمحاولات
        
    Returns:
        tuple: (نجاح العملية, رسالة الخطأ إن وجدت)
    """
    # هذه مجرد wrapper لـ send_file للحفاظ على التوافق
    return send_file(document_path, caption, max_retries)

# ==================== دوال المساعدة ====================
def send_multipart_message(parts: List[Tuple[str, str]], max_retries: int = 3) -> bool:
    """
    إرسال رسالة متعددة الأجزاء
    
    Args:
        parts: قائمة من (نوع_الجزء, المحتوى)
               أنواع الأجزاء: 'text', 'photo', 'file'
        max_retries: الحد الأقصى للمحاولات
        
    Returns:
        bool: نجاح العملية
    """
    all_success = True
    
    for part_type, content in parts:
        if part_type == 'text':
            success, error = send_alert(content, max_retries)
        elif part_type == 'photo':
            success, error = send_photo(content, "", max_retries)
        elif part_type == 'file':
            success, error = send_file(content, "", max_retries)
        else:
            logger.warning(f"⚠️ Unknown part type: {part_type}")
            continue
        
        if not success:
            all_success = False
            logger.error(f"❌ Failed to send {part_type}: {error}")
        
        # تأخير بسيط بين الأجزاء
        if len(parts) > 1:
            time.sleep(1)
    
    return all_success

def send_status_update(status_data: dict) -> bool:
    """
    إرسال تحديث حالة
    
    Args:
        status_data: بيانات الحالة
        
    Returns:
        bool: نجاح العملية
    """
    try:
        message = "📊 SYSTEM STATUS UPDATE\n\n"
        
        for key, value in status_data.items():
            if isinstance(value, dict):
                message += f"🔹 {key}:\n"
                for sub_key, sub_value in value.items():
                    message += f"   • {sub_key}: {sub_value}\n"
            else:
                message += f"🔸 {key}: {value}\n"
        
        success, error = send_alert(message)
        return success
        
    except Exception as e:
        logger.error(f"❌ Failed to send status update: {e}")
        return False

# ==================== اختبار النظام ====================
def test_notification_system() -> bool:
    """
    اختبار نظام الإشعارات
    
    Returns:
        bool: نجاح الاختبار
    """
    logger.info("🔔 Testing notification system...")
    
    tests_passed = 0
    total_tests = 3
    
    # اختبار 1: رسالة نصية
    logger.info("📝 Testing text message...")
    success, error = send_alert("🔔 TEST: Notification system is working!", 1)
    if success:
        logger.info("✅ Text message test passed")
        tests_passed += 1
    else:
        logger.error(f"❌ Text message test failed: {error}")
    
    # اختبار 2: إنشاء وإرسال ملف تجريبي
    logger.info("📄 Testing file upload...")
    try:
        test_file = "test_notification.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("This is a test file for notification system\n")
            f.write(f"Generated at: {time.ctime()}\n")
        
        success, error = send_file(test_file, "📄 Test file", 1)
        
        if os.path.exists(test_file):
            os.remove(test_file)
        
        if success:
            logger.info("✅ File upload test passed")
            tests_passed += 1
        else:
            logger.error(f"❌ File upload test failed: {error}")
            
    except Exception as e:
        logger.error(f"❌ File test error: {e}")
    
    # اختبار 3: send_document (التوافق)
    logger.info("📋 Testing document compatibility...")
    success, error = send_document(__file__, "📋 Test document (notifier.py)", 1)
    if success:
        logger.info("✅ Document compatibility test passed")
        tests_passed += 1
    else:
        logger.warning(f"⚠️ Document test warning: {error}")
    
    # النتيجة النهائية
    logger.info(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    return tests_passed >= 2  # نجاح إذا مرت 2 على الأقل

# ==================== نقطة الدخول للاختبار ====================
if __name__ == "__main__":
    # إعداد السجلات
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # اختبار النظام
    if test_notification_system():
        print("\n✅ NOTIFICATION SYSTEM IS OPERATIONAL")
    else:
        print("\n⚠️ NOTIFICATION SYSTEM HAS SOME ISSUES")
        print("   Check your TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in config.py")