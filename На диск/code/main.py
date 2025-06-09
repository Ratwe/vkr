import subprocess
import sys

def run_script(script_name):
    print(f"\nЗапуск {script_name}...")
    result = subprocess.run(
        [sys.executable, script_name],
        capture_output=True,
        text=True,
        encoding='utf-8',  # ключевая строка
        errors='replace'   # чтобы не упасть при ошибке декодирования
    )
    print(result.stdout)
    if result.stderr:
        print(f"⚠ Ошибка при выполнении {script_name}:\n{result.stderr}")

if __name__ == "__main__":
    run_script("clicks.py")
    run_script("webdriver.py")
    run_script("heatmap.py")
