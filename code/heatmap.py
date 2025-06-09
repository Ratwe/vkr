import json
import os
import re
import sys
import math
from urllib.parse import urlparse
from PIL import Image, ImageDraw


def sanitize_path_part(s):
    return re.sub(r'[^a-zA-Z0-9-_]', '_', s)


def draw_clicks_on_screenshots(clicks_path="clicks.json", screenshots_root="webpages/screenshots",
                               output_root="heatmaps", last_n_clicks=None, force=True):
    os.makedirs(output_root, exist_ok=True)

    # Загрузка кликов
    with open(clicks_path, "r", encoding="utf-8") as f:
        clicks = json.load(f)

    clicks_by_url = {}
    for c in clicks:
        clicks_by_url.setdefault(c["url"], []).append(c)

    print(f"Найдены клики по {len(clicks_by_url)} URL")

    # Загрузка кэша
    cache_path = "heatmap_cache.json"
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            previous_cache = json.load(f)
    else:
        previous_cache = {}

    new_cache = {}

    for url, clicks_list in clicks_by_url.items():
        if last_n_clicks is not None:
            clicks_list = clicks_list[-last_n_clicks:]

        # Хэш текущих кликов
        click_hash = hash(tuple((c["absX"], c["absY"], c["pageWidth"], c["pageHeight"]) for c in clicks_list))
        new_cache[url] = {
            "click_hash": click_hash,
            "last_n_clicks": last_n_clicks
        }

        previous = previous_cache.get(url)

        prev_hash = None
        prev_last_n = None
        if isinstance(previous, dict):
            prev_hash = previous.get("click_hash")
            prev_last_n = previous.get("last_n_clicks")
        elif isinstance(previous, int):
            prev_hash = previous

        if prev_hash == click_hash and prev_last_n == last_n_clicks and not force:
            print(f"Пропускаем {url} — клики и количество не изменились.")
            continue

        parsed = urlparse(url)
        base_path = os.path.join(screenshots_root, sanitize_path_part(parsed.netloc))
        parts = [sanitize_path_part(p) for p in parsed.path.strip("/").split("/") if p]
        full_dir = os.path.join(base_path, *parts[:-1]) if parts else base_path

        last_part = parts[-1] if parts else "index"
        last_part = last_part.replace(".", "_")

        query = parsed.query
        if query:
            query_safe = sanitize_path_part(query)
            filename = f"{last_part}_{query_safe}.png"
        else:
            filename = f"{last_part}.png"

        original_path = os.path.join(full_dir, filename)

        if not os.path.exists(original_path):
            print(f"Скриншот не найден для: {url}, ожидается в {original_path}")
            continue

        img = Image.open(original_path).convert("RGBA")
        width, height = img.size

        # Создаем отдельный слой для тепловой карты
        heatmap_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(heatmap_layer, "RGBA")

        base_radius = 20  # Базовый радиус клика
        max_radius = 40  # Максимальный радиус при наложении

        # Собираем все точки кликов
        points = []
        for c in clicks_list:
            if c["pageWidth"] == 0 or c["pageHeight"] == 0:
                print(f"Пропущен клик с нулевым размером страницы: {c}")
                continue

            x = c["absX"] * width / c["pageWidth"]
            y = c["absY"] * height / c["pageHeight"]
            points.append((x, y))

        # Функция для определения цвета в зависимости от плотности
        def get_color_for_density(density, max_density):
            # От синего (0,0,255) к красному (255,0,0) через фиолетовый
            if density <= 1:
                return (0, 0, 255, 160)  # Синий для одиночных кликов
            elif density < max_density / 2:
                ratio = density / (max_density / 2)
                return (int(255 * ratio), 0, int(255 * (1 - ratio)), 180)
            else:
                ratio = (density - max_density / 2) / (max_density / 2)
                return (255, 0, int(255 * (1 - ratio)), 200)

        # Рассчитываем плотность кликов в каждой точке
        if points:
            # Создаем карту плотности
            density_map = [[0 for _ in range(height)] for _ in range(width)]
            max_density = 1

            for x, y in points:
                # Увеличиваем радиус в зависимости от количества кликов в области
                dynamic_radius = min(base_radius + 5 * math.sqrt(points.count((x, y))), max_radius)

                for i in range(max(0, int(x - dynamic_radius)), min(width, int(x + dynamic_radius))):
                    for j in range(max(0, int(y - dynamic_radius)), min(height, int(y + dynamic_radius))):
                        distance = math.sqrt((i - x) ** 2 + (j - y) ** 2)
                        if distance <= dynamic_radius:
                            # Гауссово распределение плотности
                            weight = math.exp(-(distance ** 2) / (2 * (dynamic_radius / 2) ** 2))
                            density_map[i][j] += weight
                            if density_map[i][j] > max_density:
                                max_density = density_map[i][j]

            # Рисуем тепловую карту
            for i in range(width):
                for j in range(height):
                    density = density_map[i][j]
                    if density > 0.1:  # Порог видимости
                        color = get_color_for_density(density, max_density)
                        draw.point((i, j), color)

        # Накладываем тепловую карту на оригинальное изображение
        img = Image.alpha_composite(img, heatmap_layer)

        output_dir = os.path.join(output_root, sanitize_path_part(parsed.netloc),
                                  *parts[:-1]) if parts else os.path.join(output_root,
                                                                          sanitize_path_part(parsed.netloc))
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)

        img.save(output_path)
        print(f"Карта кликов сохранена: {output_path}")

    # Сохраняем кэш
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(new_cache, f, indent=2, ensure_ascii=False)

    print("Все карты кликов сохранены!")


if __name__ == "__main__":
    last_n_clicks = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 100
    draw_clicks_on_screenshots(last_n_clicks=last_n_clicks)