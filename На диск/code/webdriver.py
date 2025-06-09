import json
import os
import tempfile
import base64
import time
import re
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def sanitize_path_part(s):
    # Оставляем только буквы, цифры, дефисы и подчеркивания, заменяем остальное на _
    return re.sub(r'[^a-zA-Z0-9-_]', '_', s)


def take_fullpage_screenshot(driver, path):
    driver.execute_script("window.scrollTo(0, 0);")
    screenshot = driver.execute_cdp_cmd("Page.captureScreenshot", {
        "fromSurface": True,
        "captureBeyondViewport": True
    })
    with open(path, "wb") as f:
        f.write(base64.b64decode(screenshot['data']))


# Распарсить и выделить уникальные URL
with open('clicks.json', 'r', encoding='utf-8') as f:
    all_points = json.load(f)

unique_urls = sorted(set(entry["url"] for entry in all_points))

# Настройки Chrome
options = Options()
options.add_argument('--headless=new')  # Раскомментируй, если нужно без GUI
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')
options.add_experimental_option('excludeSwitches', ['enable-automation'])
options.add_experimental_option("useAutomationExtension", False)

# Временный профиль
user_data_dir = os.path.join(tempfile.gettempdir(), 'chrome_temp_profile')
os.makedirs(user_data_dir, exist_ok=True)
options.add_argument(f'--user-data-dir={user_data_dir}')

USERNAME = "admin"
PASSWORD = "HdrxaiGfKNvKHS6*"

print("Setting up driver...")
try:
    driver = webdriver.Chrome(options=options)
    print("Driver is ready")

    # Вход в Moodle
    login_url = "http://192.168.1.102/moodle/login/index.php"
    driver.get(login_url)

    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username")))
    time.sleep(1)
    driver.find_element(By.ID, "username").clear()
    driver.find_element(By.ID, "username").send_keys(USERNAME)
    driver.find_element(By.ID, "password").clear()
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.ID, "loginbtn").click()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'logout.php')]"))
    )
    print("Login successful.")

    for i, url in enumerate(unique_urls, 1):
        print(f"[{i}/{len(unique_urls)}] Visiting {url}")
        try:
            driver.get(url)
            time.sleep(0)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            parsed = urlparse(url)
            base_path = os.path.join("webpages/screenshots", sanitize_path_part(parsed.netloc))
            parts = [sanitize_path_part(p) for p in parsed.path.strip("/").split("/") if p]
            full_dir = os.path.join(base_path, *parts[:-1]) if parts else base_path
            os.makedirs(full_dir, exist_ok=True)

            last_part = parts[-1] if parts else "index"
            last_part = last_part.replace(".", "_")

            if parsed.query:
                query_safe = sanitize_path_part(parsed.query)
                filename = f"{last_part}_{query_safe}.png"
            else:
                filename = f"{last_part}.png"

            filepath = os.path.join(full_dir, filename)

            take_fullpage_screenshot(driver, filepath)
            print(f"Saved screenshot: {filepath}")
        except Exception as page_error:
            print(f"Failed to load or screenshot {url}: {page_error}")

except Exception as e:
    print(f"Critical error: {str(e)}")
finally:
    if 'driver' in locals():
        driver.quit()
    try:
        os.rmdir(user_data_dir)
    except Exception:
        pass
