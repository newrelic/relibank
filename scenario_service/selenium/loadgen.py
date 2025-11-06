from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time 
from time import sleep 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
HEADLESS_MODE = True 
# ---------------------

# --- Verified Credentials/Data ---
BASE_URL = "http://relibank.westus2.cloudapp.azure.com" 
DASHBOARD_URL = f"{BASE_URL}/dashboard"
TEST_USERNAME = "demo" 
TEST_PASSWORD = "password" 
TRANSFER_AMOUNT = "1"

# --- VERIFIED LOCATORS ---
USERNAME_LOCATOR = (By.NAME, "username") 
PASSWORD_LOCATOR = (By.NAME, "password") 
LOGIN_BUTTON_LOCATOR = (By.XPATH, "//button[text()='Sign In']") 

TRANSFER_AMOUNT_FIELD_LOCATOR = (By.CSS_SELECTOR, "input[type='number']") 
TRANSFER_BUTTON_LOCATOR = (By.XPATH, "//button[text()='Complete Transfer']") 
# ---------------------------------

def automate_transfer(base_url, dashboard_url, username, password):
    # Setup
    chrome_options = Options()
    if HEADLESS_MODE:
        chrome_options.add_argument("--headless=new") 
        
    chrome_options.add_argument("--window-size=1920,1080")
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        wait = WebDriverWait(driver, 15)

        # ------------------------------------------------------------------
        # STEP 1: LOGIN
        # ------------------------------------------------------------------
        print(f"🌍 Navigating to base URL: {base_url}")
        driver.get(base_url)

        print("⏳ Waiting for login fields...")
        username_field = wait.until(EC.presence_of_element_located(USERNAME_LOCATOR))
        username_field.send_keys(username)
        password_field = wait.until(EC.presence_of_element_located(PASSWORD_LOCATOR))
        password_field.send_keys(password)
        login_button = wait.until(EC.element_to_be_clickable(LOGIN_BUTTON_LOCATOR))
        
        print("🖱️ Clicking login button...")
        login_button.click()
        
        print("Waiting 5 seconds for post-login dashboard rendering...")
        sleep(5) 
        
        # Verify dashboard access
        if driver.current_url != dashboard_url:
            driver.get(dashboard_url)
            wait.until(EC.url_to_be(dashboard_url))
            
        print(f"Successfully reached: {driver.current_url}")
        
        # ------------------------------------------------------------------
        # FIX: Simulating user focus click on the page body
        # ------------------------------------------------------------------
        print("🖱️ Simulating user focus click on the page body...")
        driver.find_element(By.TAG_NAME, "body").click()
        sleep(1) 
        
        # ------------------------------------------------------------------
        # STEP 2: TRANSFER 1 DOLLAR
        # ------------------------------------------------------------------
        print("\n--- Starting Transfer Action ---")

        # Robust wait to ensure the input field is ready
        print("⏳ Waiting for transfer amount input field...")
        amount_field = wait.until(EC.presence_of_element_located(TRANSFER_AMOUNT_FIELD_LOCATOR))
        # Changed to presence only, as the click is now handled by JavaScript
        transfer_button = wait.until(EC.presence_of_element_located(TRANSFER_BUTTON_LOCATOR)) 

        # Enter the transfer amount
        print(f"💰 Entering amount: ${TRANSFER_AMOUNT}")
        amount_field.send_keys(TRANSFER_AMOUNT)
        
        # FIX: Use JavaScript to force the click
        print("⚡️ Forcing click on 'Complete Transfer' button using JavaScript...")
        driver.execute_script("arguments[0].click();", transfer_button)
        
        # Padding time for the asynchronous transaction to complete
        print("Waiting 7 seconds for transaction confirmation/result to appear...")
        sleep(7) 

        # ------------------------------------------------------------------
        # STEP 3: FINAL CHECK
        # ------------------------------------------------------------------
        print("\n--- Final Status Check ---")
        
        SUCCESS_MESSAGE = f"Successfully transferred ${float(TRANSFER_AMOUNT):.2f}" 
        
        if SUCCESS_MESSAGE in driver.page_source:
            print(f"✅ SUCCESS: Transaction confirmed! Message found: {SUCCESS_MESSAGE}")
        else:
            print("❌ FAILURE: Could not find transaction success message on the page.")

        print(f"Final URL: {driver.current_url}")
        print(f"Page Title: {driver.title}")

    except Exception as e:
        print(f"An error occurred during the automation. Please check your network or credentials: {e}")
        
    finally:
        driver.quit()
        print("\n✅ Browser closed. Script finished.")


# ----------------------------------------------------------------
# 👇 THIS IS THE CALL THAT WAS LIKELY MISSING / CAUSING THE ISSUE!
# ----------------------------------------------------------------
automate_transfer(BASE_URL, DASHBOARD_URL, TEST_USERNAME, TEST_PASSWORD)
