"""
Elite Sniper v2.0 - Main Entry Point
Production-grade 24/7 appointment booking system

Usage:
    python -m src.main
    
Features:
    - 3 parallel sessions (1 Scout + 2 Attackers)
    - NTP-synchronized Zero-Hour precision at 2:00 AM Aden time
    - Automatic recovery and session management
    - Telegram notifications with screenshots
"""

import time
import logging
import sys
import os
import signal

# Add the parent directory to sys.path to allow running from src directly or root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Elite Sniper v2.0
try:
    from src.elite_sniper_v2 import EliteSniperV2
except ImportError:
    # Fallback if run from inside src
    from elite_sniper_v2 import EliteSniperV2

# Logging setup
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("MainLauncher")


def run_elite_sniper_v2():
    """
    Run Elite Sniper v2.0 with automatic recovery
    Implements supervisor pattern for 24/7 operation
    """
    retry_count = 0
    max_retries = 10  # Maximum restart attempts
    min_runtime = 60  # Minimum runtime before counting as failed start
    
    while retry_count < max_retries:
        start_time = time.time()
        
        try:
            logger.info("=" * 60)
            logger.info(f"👑 ELITE SNIPER V2.0 - LAUNCHING (Attempt {retry_count + 1})")
            logger.info("=" * 60)
            
            # Create and run sniper
            sniper = EliteSniperV2()
            success = sniper.run()
            
            if success:
                # Mission accomplished!
                logger.info("🏆 MISSION ACCOMPLISHED! System shutting down gracefully.")
                return True
            else:
                # Completed without success - normal termination
                runtime = time.time() - start_time
                
                if runtime < min_runtime:
                    # Quick failure - something is wrong
                    retry_count += 1
                    logger.warning(f"⚠️ Quick exit after {runtime:.0f}s - possible issue")
                else:
                    # Normal completion - reset retry count
                    retry_count = 0
                    logger.info(f"🔄 Session completed after {runtime:.0f}s - restarting...")
                
                # Wait before restart
                wait_time = min(30 * (retry_count + 1), 300)  # Max 5 minutes
                logger.info(f"⏳ Waiting {wait_time}s before restart...")
                time.sleep(wait_time)

        except KeyboardInterrupt:
            logger.info("\n🛑 Shutdown requested by user")
            return False
            
        except Exception as e:
            retry_count += 1
            logger.error(f"💀 Critical crash: {e}")
            
            if retry_count < max_retries:
                wait_time = min(30 * retry_count, 300)
                logger.info(f"♻️ Restarting in {wait_time}s (attempt {retry_count + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                logger.critical("🚨 MAX RETRIES REACHED! Manual intervention required.")
                return False
    
    logger.critical("🚨 System stopped after exhausting retry attempts")
    return False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"\n🛑 Received signal {signum} - initiating graceful shutdown")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("""
    ==============================================================
    ||                                                          ||
    ||     ELITE SNIPER v2.0 - PRODUCTION EDITION               ||
    ||                                                          ||
    ||     Architecture: 1 Scout + 2 Attackers                  ||
    ||     Target Time: 02:00 AM Aden (GMT+3)                   ||
    ||     Mode: 24/7 Autonomous Operation                      ||
    ||                                                          ||
    ||     Features:                                            ||
    ||     [+] NTP-synchronized Zero-Hour Precision             ||
    ||     [+] Multi-session parallel execution                 ||
    ||     [+] Hard-kill session management (60s max)           ||
    ||     [+] Double-captcha detection                         ||
    ||     [+] Telegram notifications with screenshots          ||
    ||     [+] Automatic recovery and self-healing              ||
    ||                                                          ||
    ==============================================================
    """)
    
    success = run_elite_sniper_v2()
    sys.exit(0 if success else 1)
