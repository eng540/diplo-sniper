"""
Elite Sniper v2.0 - Enhanced Captcha System
Integrates KingSniperV12 safe captcha checking with pre-solving capability
"""

import time
import logging
from typing import Optional, List, Tuple
from playwright.sync_api import Page

logger = logging.getLogger("EliteSniperV2.Captcha")

# Try to import ddddocr
try:
    import ddddocr
    DDDDOCR_AVAILABLE = True
except ImportError:
    DDDDOCR_AVAILABLE = False
    logger.warning("⚠️ ddddocr not available - captcha solving disabled")


class EnhancedCaptchaSolver:
    """
    Enhanced captcha solver with:
    - Multiple selector attempts (from KingSniperV12)
    - Safe checking without failures
    - Black captcha detection
    - Pre-solving capability
    - Session-aware solving
    """
    
    def __init__(self):
        """Initialize OCR engine"""
        self.ocr = None
        self._pre_solved_code: Optional[str] = None
        self._pre_solved_time: float = 0.0
        self._pre_solve_timeout: float = 30.0  # Pre-solved code expires after 30s
        
        if DDDDOCR_AVAILABLE:
            try:
                self.ocr = ddddocr.DdddOcr(beta=True)
                logger.info("✅ Captcha solver initialized (beta mode)")
            except Exception as e:
                logger.error(f"❌ Captcha solver init failed: {e}")
                self.ocr = None
        else:
            logger.warning("⚠️ ddddocr not installed - run: pip install ddddocr")
    
    def safe_captcha_check(self, page: Page, location: str = "GENERAL") -> Tuple[bool, bool]:
        """
        Safe captcha presence check (from KingSniperV12)
        
        Returns:
            (has_captcha: bool, check_successful: bool)
        """
        try:
            # Step 1: Check page content for captcha keywords
            page_content = page.content().lower()
            
            captcha_keywords = [
                "captcha", 
                "security code", 
                "verification", 
                "human check",
                "verkaptxt"  # German sites
            ]
            
            has_captcha_text = any(keyword in page_content for keyword in captcha_keywords)
            
            if not has_captcha_text:
                logger.debug(f"[{location}] No captcha keywords found")
                return False, True
            
            # Step 2: Search for captcha input (multiple selectors)
            captcha_selectors = self._get_captcha_selectors()
            
            for selector in captcha_selectors:
                try:
                    if page.locator(selector).first.is_visible(timeout=1000):
                        logger.info(f"🔍 [{location}] Captcha found: {selector}")
                        return True, True
                except:
                    continue
            
            # Found keywords but no input field
            logger.debug(f"[{location}] Captcha text found but no input field")
            return False, True
            
        except Exception as e:
            logger.error(f"❌ [{location}] Captcha check error: {e}")
            return False, False
    
    def _get_captcha_selectors(self) -> List[str]:
        """
        Get list of possible captcha selectors
        From KingSniperV12 with additions
        """
        return [
            "input[name='captchaText']",
            "input[name='captcha']",
            "input#captchaText",
            "input#captcha",
            "input[type='text'][placeholder*='code']",
            "input[type='text'][placeholder*='Code']",
            "input.verkaptxt",
            "input.captcha-input",
            "input[id*='captcha']",
            "input[name*='captcha']"
        ]
    
    def _get_captcha_image_selectors(self) -> List[str]:
        """Get list of possible captcha image selectors"""
        return [
            "captcha > div",
            "div.captcha-image",
            "div#captcha",
            "img[alt*='captcha']",
            "img[alt*='CAPTCHA']",
            "canvas.captcha"
        ]
    
    def detect_black_captcha(self, image_bytes: bytes) -> bool:
        """
        Detect poisoned/black captcha
        Black captcha = session invalid
        """
        if len(image_bytes) < 1500:
            logger.critical("⚫ BLACK CAPTCHA detected - Session poisoned")
            return True
        
        return False
    
    def solve(self, image_bytes: bytes) -> str:
        """
        Solve captcha from image bytes
        
        Returns:
            Captcha text (empty string on failure)
        """
        if not self.ocr:
            logger.error("❌ OCR engine not initialized")
            return ""
        
        try:
            # Detect black captcha first
            if self.detect_black_captcha(image_bytes):
                return ""
            
            # Solve using OCR
            result = self.ocr.predict(image_bytes)
            result = result.replace(" ", "").strip()
            
            logger.info(f"✅ Captcha solved: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Captcha solve error: {e}")
            return ""
    
    def pre_solve(self, page: Page, location: str = "PRE_SOLVE") -> Tuple[bool, Optional[str]]:
        """
        Pre-solve captcha for instant submission later
        
        Returns:
            (success: bool, captcha_code: Optional[str])
        """
        try:
            # Check if captcha exists
            has_captcha, check_ok = self.safe_captcha_check(page, location)
            
            if not check_ok:
                logger.error(f"[{location}] Pre-solve captcha check failed")
                return False, None
            
            if not has_captcha:
                logger.debug(f"[{location}] No captcha to pre-solve")
                return True, None
            
            # Find captcha image
            image_bytes = None
            for img_selector in self._get_captcha_image_selectors():
                try:
                    element = page.locator(img_selector).first
                    if element.is_visible(timeout=1000):
                        image_bytes = element.screenshot(timeout=5000)
                        break
                except:
                    continue
            
            if not image_bytes:
                logger.warning(f"[{location}] Captcha image not found for pre-solve")
                return False, None
            
            # Solve captcha
            code = self.solve(image_bytes)
            
            if not code or len(code) < 3:
                logger.warning(f"[{location}] Invalid pre-solve captcha code: '{code}'")
                return False, None
            
            # Cache the solution
            self._pre_solved_code = code
            self._pre_solved_time = time.time()
            
            logger.info(f"🔮 [{location}] Pre-solved captcha: {code}")
            return True, code
            
        except Exception as e:
            logger.error(f"[{location}] Pre-solve error: {e}")
            return False, None
    
    def get_pre_solved(self) -> Optional[str]:
        """
        Get pre-solved captcha code if still valid
        
        Returns:
            Captcha code or None if expired/unavailable
        """
        if not self._pre_solved_code:
            return None
        
        # Check if expired
        age = time.time() - self._pre_solved_time
        if age > self._pre_solve_timeout:
            logger.warning("⏰ Pre-solved captcha expired")
            self._pre_solved_code = None
            return None
        
        return self._pre_solved_code
    
    def clear_pre_solved(self):
        """Clear pre-solved captcha"""
        self._pre_solved_code = None
        self._pre_solved_time = 0.0
    
    def solve_from_page(
        self, 
        page: Page, 
        location: str = "GENERAL",
        timeout: int = 10000
    ) -> Tuple[bool, Optional[str]]:
        """
        Complete captcha solving workflow
        Uses pre-solved code if available
        
        Returns:
            (success: bool, captcha_code: Optional[str])
        """
        try:
            # Check if captcha exists
            has_captcha, check_ok = self.safe_captcha_check(page, location)
            
            if not check_ok:
                logger.error(f"[{location}] Captcha check failed")
                return False, None
            
            if not has_captcha:
                logger.debug(f"[{location}] No captcha present")
                return True, None
            
            # Find captcha input field
            input_selector = None
            for selector in self._get_captcha_selectors():
                try:
                    if page.locator(selector).first.is_visible(timeout=1000):
                        input_selector = selector
                        break
                except:
                    continue
            
            if not input_selector:
                logger.warning(f"[{location}] Captcha input not found")
                return False, None
            
            # Check for pre-solved code first
            code = self.get_pre_solved()
            
            if code:
                logger.info(f"[{location}] Using pre-solved captcha: {code}")
                self.clear_pre_solved()
            else:
                # Find captcha image and solve
                image_bytes = None
                for img_selector in self._get_captcha_image_selectors():
                    try:
                        element = page.locator(img_selector).first
                        if element.is_visible(timeout=1000):
                            image_bytes = element.screenshot(timeout=5000)
                            break
                    except:
                        continue
                
                if not image_bytes:
                    logger.warning(f"[{location}] Captcha image not found")
                    return False, None
                
                # Solve captcha
                code = self.solve(image_bytes)
                
                if not code or len(code) < 3:
                    logger.warning(f"[{location}] Invalid captcha code: '{code}'")
                    return False, None
            
            # Fill captcha
            try:
                page.fill(input_selector, code, timeout=3000)
                logger.info(f"[{location}] Captcha filled: {code}")
                return True, code
            except Exception as e:
                logger.error(f"[{location}] Failed to fill captcha: {e}")
                return False, None
            
        except Exception as e:
            logger.error(f"[{location}] Captcha solving workflow error: {e}")
            return False, None
    
    def submit_captcha(self, page: Page, method: str = "enter") -> bool:
        """
        Submit captcha (press Enter or click submit)
        
        Args:
            method: "enter" or "click"
        """
        try:
            if method == "enter":
                page.keyboard.press("Enter")
                logger.info("⏎ Captcha submitted (Enter)")
            else:
                # Try to find submit button
                submit_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "button.submit",
                    "a.submit"
                ]
                
                for selector in submit_selectors:
                    try:
                        button = page.locator(selector).first
                        if button.is_visible(timeout=1000):
                            button.click(timeout=3000)
                            logger.info("🖱️ Captcha submitted (Click)")
                            return True
                    except:
                        continue
                
                # Fallback to Enter
                page.keyboard.press("Enter")
                logger.info("⏎ Captcha submitted (Enter fallback)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Captcha submit error: {e}")
            return False


# Backward compatibility
class CaptchaSolver:
    """Original captcha solver for backward compatibility"""
    
    def __init__(self):
        if DDDDOCR_AVAILABLE:
            self.ocr = ddddocr.DdddOcr(beta=True)
        else:
            self.ocr = None
    
    def solve(self, image_bytes: bytes) -> str:
        if not self.ocr:
            return ""
        try:
            res = self.ocr.predict(image_bytes)
            res = res.replace(" ", "").strip()
            print(f"[AI] Captcha Solved: {res}")
            return res
        except Exception as e:
            print(f"[AI] Error solving captcha: {e}")
            return ""
