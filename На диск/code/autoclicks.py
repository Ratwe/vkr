import json
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

USERNAME = "admin"
PASSWORD = "HdrxaiGfKNvKHS6*"
TARGET_URL = "http://192.168.1.102/moodle/my"
NUM_CLICKS = 100
OUTPUT_FILE = "autoclicks.json"

# Настройка Chrome
options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=1920,1080')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=options)

try:
    # Авторизация
    driver.get("http://192.168.1.102/moodle/login/index.php")
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username")))

    driver.find_element(By.ID, "username").send_keys(USERNAME)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.ID, "loginbtn").click()

    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'logout.php')]"))
    )
    print("Login successful")

    # Переход на целевую страницу
    driver.get(TARGET_URL)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(0)

    width = driver.execute_script("return document.body.clientWidth")
    height = driver.execute_script("return document.body.scrollHeight")
    title = driver.title
    url = driver.current_url

    print(f"Page loaded: {title} ({width}×{height})")

    results = []

    for i in range(NUM_CLICKS):
        absX = random.randint(10, width - 10)
        absY = random.randint(10, height - 10)

        relX = absX / width
        relY = absY / height

        print(f"Click {i + 1}: ({absX}, {absY})")

        # Скрипт клика
        driver.execute_script("""
            const x = arguments[0], y = arguments[1];
            const el = document.elementFromPoint(x, y) || document.body;

            const evt1 = new PointerEvent('pointerdown', {
                bubbles: true,
                cancelable: true,
                clientX: x,
                clientY: y,
                pointerType: 'mouse'
            });

            const evt2 = new PointerEvent('pointerup', {
                bubbles: true,
                cancelable: true,
                clientX: x,
                clientY: y,
                pointerType: 'mouse'
            });

            const evt3 = new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                clientX: x,
                clientY: y
            });

            el.dispatchEvent(evt1);
            el.dispatchEvent(evt2);
            el.dispatchEvent(evt3);
        """, absX, absY)

        results.append({
            "relX": relX,
            "relY": relY,
            "absX": absX,
            "absY": absY,
            "url": url,
            "title": title,
            "pageWidth": width,
            "pageHeight": height
        })

        time.sleep(random.uniform(0.1, 0.2))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Saved {NUM_CLICKS} clicks to {OUTPUT_FILE}")

finally:
    driver.quit()
