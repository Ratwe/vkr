import re
import json
from collections import defaultdict
import requests


def parse_log_to_json(log_file_path, output_json_path):
    # Чтение файла
    with open(log_file_path, 'r') as file:
        log_content = file.read()

    # Регулярное выражение для нахождения всех блоков Array
    array_pattern = re.compile(r'Array\s*\(\s*(.*?)\s*\)\s*(?=Array|$)', re.DOTALL)

    # Регулярное выражение для извлечения пар ключ-значение
    field_pattern = re.compile(r'\[\s*(.*?)\s*\]\s*=>\s*(.*?)(?=\s*\[|$)', re.DOTALL)

    entries = []

    # Обработка каждого блока Array
    for array_block in array_pattern.finditer(log_content):
        block_content = array_block.group(1)
        entry = defaultdict(str)

        # Извлечение всех полей в блоке
        for field in field_pattern.finditer(block_content):
            key = field.group(1).strip()
            value = field.group(2).strip()

            # Преобразование числовых значений
            if value.isdigit():
                value = int(value)
            elif re.match(r'^-?\d+\.\d+$', value):
                value = float(value)
            elif value.lower() == 'null':
                value = None
            elif value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False

            entry[key] = value

        if entry:  # Добавляем только непустые записи
            entries.append(dict(entry))

    # Запись в JSON
    with open(output_json_path, 'w') as json_file:
        json.dump(entries, json_file, indent=2, ensure_ascii=False)

    print(f"Успешно обработано {len(entries)} записей. Результат сохранён в {output_json_path}")


def download_file_from_url(url, local_path):
    response = requests.get(url)
    response.raise_for_status()  # выбросить ошибку при неудаче
    with open(local_path, 'wb') as f:
        f.write(response.content)


if __name__ == "__main__":
    remote_url = 'http://192.168.1.102/moodle/local/logs/log.txt'
    local_log_path = 'log.txt'
    local_json_path = 'clicks.json'

    download_file_from_url(remote_url, local_log_path)
    parse_log_to_json(local_log_path, local_json_path)
