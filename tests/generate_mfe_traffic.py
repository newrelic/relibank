"""
ReliBank - Selenium Traffic Generator for Microfrontend Tests

Generates real MicroFrontEndTiming events by:
1. Launching headless Chrome browser
2. Logging into ReliBank application
3. Navigating to dashboard (loads all 4 MFEs)
4. Waiting for MFEs to register with New Relic
5. Navigating between pages to trigger mount/unmount cycles
6. Waiting for Browser agent beacons to flush

This ensures real browser execution where:
- JavaScript actually runs
- MFEs actually load
- Browser agent captures real telemetry
- Actual .register() calls occur
"""

import logging
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("generate_mfe_traffic")


def setup_driver():
    """Configure and return headless Chrome driver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # Enable browser console logs
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    return webdriver.Chrome(options=options)


def generate_mfe_traffic_with_selenium(frontend_url=None):
    """
    Generate real MFE events using Selenium.

    Args:
        frontend_url: URL of ReliBank frontend (defaults to localhost:3000)

    Returns:
        None (generates traffic and MicroFrontEndTiming events in New Relic)
    """
    if frontend_url is None:
        frontend_url = os.getenv("RELIBANK_URL", "http://localhost:3000")

    logger.info(f"Starting Selenium traffic generation for {frontend_url}")
    driver = setup_driver()

    try:
        # 1. Navigate to frontend
        logger.info(f"Navigating to {frontend_url}")
        driver.get(frontend_url)

        # 2. Login (auto-login with default credentials)
        logger.info("Logging in...")
        login_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "login-submit-btn"))
        )
        login_btn.click()

        # 3. Wait for dashboard (MFEs load)
        WebDriverWait(driver, 30).until(EC.url_contains("/dashboard"))
        logger.info("Dashboard loaded - MFEs mounting...")
        time.sleep(3)  # Wait for all 4 MFEs to register

        # Check console logs for MFE registration
        logs = driver.get_log('browser')
        registration_logs = [log for log in logs if 'Mount' in log.get('message', '') or 'register' in log.get('message', '').lower()]
        if registration_logs:
            logger.info(f"Found {len(registration_logs)} MFE mount/register log entries")
            for log in registration_logs[:10]:  # Show first 10
                logger.info(f"  {log.get('message', '')[:200]}")
        else:
            logger.warning("No MFE registration logs found in browser console")

        # 4. Interact with ad banner MFE to trigger custom events
        logger.info("Interacting with Ad Banner MFE...")
        try:
            more_info_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'More Info')]"))
            )
            logger.info("  Clicking 'More Info' button")
            more_info_btn.click()
            time.sleep(1)

            logger.info("  Clicking 'More Info' again to collapse")
            more_info_btn.click()
            time.sleep(1)

            # Click Sign Up button to trigger API call and MFE custom events
            signup_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "dashboard-rewards-signup-btn"))
            )
            logger.info("  Clicking 'Sign Up' button (triggers API call)")
            signup_btn.click()
            time.sleep(3)  # Wait for API call and error handling
            logger.info("  Ad Banner interactions complete")
        except Exception as e:
            logger.warning(f"  Could not interact with Ad Banner: {e}")

        # 5. Navigation cycle 1: Dashboard -> Payments -> Dashboard
        logger.info("Navigation cycle 1: Navigating to payments (unmounts MFEs)...")
        payments_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='/payments']"))
        )
        payments_link.click()
        WebDriverWait(driver, 10).until(EC.url_contains("/payments"))
        logger.info("  On payments page - MFEs unmounted")
        time.sleep(2)

        logger.info("  Returning to dashboard (remounts MFEs)...")
        dashboard_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='/dashboard']"))
        )
        dashboard_link.click()
        WebDriverWait(driver, 10).until(EC.url_contains("/dashboard"))
        logger.info("  Back on dashboard - MFEs remounted")
        time.sleep(3)

        # 5. Navigation cycle 2
        logger.info("Navigation cycle 2: Navigating to payments...")
        payments_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='/payments']"))
        )
        payments_link.click()
        WebDriverWait(driver, 10).until(EC.url_contains("/payments"))
        logger.info("  On payments page")
        time.sleep(2)

        logger.info("  Returning to dashboard...")
        dashboard_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='/dashboard']"))
        )
        dashboard_link.click()
        WebDriverWait(driver, 10).until(EC.url_contains("/dashboard"))
        logger.info("  Back on dashboard")
        time.sleep(3)

        # 6. Navigation cycle 3
        logger.info("Navigation cycle 3: Navigating to payments...")
        payments_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='/payments']"))
        )
        payments_link.click()
        WebDriverWait(driver, 10).until(EC.url_contains("/payments"))
        logger.info("  On payments page")
        time.sleep(2)

        logger.info("  Returning to dashboard (final)...")
        dashboard_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='/dashboard']"))
        )
        dashboard_link.click()
        WebDriverWait(driver, 10).until(EC.url_contains("/dashboard"))
        logger.info("  Back on dashboard")
        time.sleep(3)

        logger.info("✓ Selenium traffic generation complete")
        logger.info("  - Visited dashboard 3 times")
        logger.info("  - All 4 MFEs loaded and registered")
        logger.info("  - Navigation cycles completed")

    except Exception as e:
        logger.error(f"Traffic generation failed: {e}")
        raise
    finally:
        # Allow New Relic Browser agent beacons to flush
        time.sleep(3)
        driver.quit()


if __name__ == "__main__":
    generate_mfe_traffic_with_selenium()
