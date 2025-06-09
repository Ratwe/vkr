import json
import random
import time
import subprocess

import numpy as np
import psutil
import matplotlib.pyplot as plt
from threading import Thread

RESULTS_FILE = "avg_results.txt"
START = 10_000
END = -10
STEP = -1_000
REPEATS = 1
CLICK_FILE = "clicks.json"
HEATMAP_SCRIPT = "heatmap.py"

URLS = ["http://192.168.1.102/moodle/my/"]

def generate_click_data(n_clicks):
    page_width = 1898
    page_height = 930
    url = URLS[0]
    title = f"TESTING {n_clicks}"

    try:
        with open(CLICK_FILE, "r", encoding="utf-8") as f:
            clicks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        clicks = []

    current_len = len(clicks)
    if current_len >= n_clicks:
        clicks = clicks[:n_clicks]
    else:
        for _ in range(n_clicks - current_len):
            abs_x = random.randint(0, page_width)
            abs_y = random.randint(0, page_height)
            rel_x = abs_x / page_width
            rel_y = abs_y / page_height
            clicks.append({
                "relX": round(rel_x, 14),
                "relY": round(rel_y, 14),
                "absX": abs_x,
                "absY": abs_y,
                "url": url,
                "title": title,
                "pageWidth": page_width,
                "pageHeight": page_height
            })

    with open(CLICK_FILE, "w", encoding="utf-8") as f:
        json.dump(clicks, f, ensure_ascii=False, indent=2)

def monitor_resources(proc_pid, interval, usage_data):
    process = psutil.Process(proc_pid)
    ram_samples = []
    cpu_samples = []

    while process.is_running():
        try:
            ram = process.memory_info().rss / (1024 * 1024)  # MB
            cpu = process.cpu_percent(interval=0.1)  # %
            ram_samples.append(ram)
            cpu_samples.append(cpu)
            time.sleep(interval)
        except psutil.NoSuchProcess:
            break

    usage_data["ram_max"] = max(ram_samples, default=0)
    usage_data["ram_avg"] = sum(ram_samples) / len(ram_samples) if ram_samples else 0
    usage_data["cpu_avg"] = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0

def measure_execution(n_clicks):
    gen_start = time.time()
    generate_click_data(n_clicks)
    gen_end = time.time()
    gen_time = gen_end - gen_start
    #print(f"  Время генерации данных: {gen_time:.2f} сек")

    usage_data = {}

    proc = subprocess.Popen(["python", HEATMAP_SCRIPT, str(n_clicks)], stdout=subprocess.DEVNULL)

    monitor_thread = Thread(target=monitor_resources, args=(proc.pid, 0.05, usage_data))
    start_time = time.time()
    monitor_thread.start()

    proc.wait()
    monitor_thread.join()
    end_time = time.time()

    elapsed_time = end_time - start_time
    return {
        "time": elapsed_time,
        "ram_max": usage_data.get("ram_max", 0),
        "ram_avg": usage_data.get("ram_avg", 0),
        "cpu_avg": usage_data.get("cpu_avg", 0),
    }

def plot_metric0(xs, ys, ylabel, title, filename):
    plt.figure(figsize=(10, 6))
    plt.plot(xs, ys, marker='o', linewidth=1.5)
    plt.title(title)
    plt.xlabel("Количество кликов")
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.savefig(filename)
    plt.close()

def plot_metric(xs, ys, ylabel, title, filename, fit_type="line"):
    plt.figure(figsize=(10, 6))
    xs_array = np.array(xs)
    ys_array = np.array(ys)

    # Отрисовка точек
    plt.scatter(xs_array, ys_array, color="blue", label="Замеры")

    if fit_type == "line":
        coeffs = np.polyfit(xs_array, ys_array, 1)
        poly = np.poly1d(coeffs)
        ys_fit = poly(xs_array)
        plt.plot(xs_array, ys_fit, color="red", linestyle="-", label="Линейная аппроксимация")
    elif fit_type == "poly2":
        coeffs = np.polyfit(xs_array, ys_array, 2)
        poly = np.poly1d(coeffs)
        ys_fit = poly(xs_array)
        plt.plot(xs_array, ys_fit, color="green", linestyle="-", label="Полиномиальная аппроксимация")
    elif fit_type == "log":
        # Фильтруем значения x > 0
        mask = xs_array >= 0
        xs_pos = xs_array[mask]
        ys_pos = ys_array[mask]

        if len(xs_pos) >= 2:  # Нужно минимум 2 точки
            epsilon = 1  # смещение, чтобы логарифм существовал даже при x=0
            log_xs = np.log(xs_pos + epsilon)

            coeffs = np.polyfit(log_xs, ys_pos, 1)
            poly = np.poly1d(coeffs)

            xs_fit = np.linspace(min(xs_pos), max(xs_pos), 200)
            ys_fit = poly(np.log(xs_fit + epsilon))

            plt.plot(xs_fit, ys_fit, color="purple", linestyle="-", label="Логарифмическая аппроксимация")

    plt.title(title)
    plt.xlabel("Количество кликов")
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.legend()
    plt.savefig(filename)
    plt.close()


def plot_metric_0_100(xs, ys, ylabel, title, filename, fit_type="line"):
    plt.figure(figsize=(10, 6))
    xs_array = np.array(xs)
    ys_array = np.array(ys)

    # Отрисовка точек
    plt.scatter(xs_array, ys_array, color="blue", label="Замеры")

    if fit_type == "line":
        coeffs = np.polyfit(xs_array, ys_array, 1)
        poly = np.poly1d(coeffs)
        ys_fit = poly(xs_array)
        plt.plot(xs_array, ys_fit, color="red", linestyle="-", label="Линейная аппроксимация")
    elif fit_type == "poly2":
        coeffs = np.polyfit(xs_array, ys_array, 2)
        poly = np.poly1d(coeffs)
        ys_fit = poly(xs_array)
        plt.plot(xs_array, ys_fit, color="green", linestyle="-", label="Полиномиальная аппроксимация")

    plt.title(title)
    plt.xlabel("Количество кликов")
    plt.ylabel(ylabel)
    plt.ylim(0, 100)
    plt.grid(True)
    plt.legend()
    plt.savefig(filename)
    plt.close()



def main():
    total_start = time.time()

    with open(CLICK_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

    results = {}
    for count in range(START, END + 1, STEP):
        print(f"\n==> Тест для {count} кликов")
        metrics = {"time": [], "ram_max": [], "ram_avg": [], "cpu_avg": []}
        for i in range(REPEATS):
            try:
                data = measure_execution(count)
                #print(f"  Прогон {i + 1}: {data['time']:.2f} сек | ОЗУ ср: {data['ram_avg']:.2f} МБ | ОЗУ пик: {data['ram_max']:.2f} МБ | ЦПУ ср: {data['cpu_avg']:.2f}%")
                for k in metrics:
                    metrics[k].append(data[k])
            except Exception as e:
                #print(f"  Ошибка: {e}")
                break

        if len(metrics["time"]) == REPEATS:
            avg_time = sum(metrics["time"]) / REPEATS
            avg_ram = sum(metrics["ram_avg"]) / REPEATS
            max_ram = max(metrics["ram_max"])
            avg_cpu = sum(metrics["cpu_avg"]) / REPEATS

            results[count] = {
                "time_avg": avg_time,
                "ram_avg": avg_ram,
                "ram_max": max_ram,
                "cpu_avg": avg_cpu,
            }

            print(
                f"-> Средние значения | Время: {avg_time:.2f} сек | "
                f"ОЗУ ср: {avg_ram:.2f} МБ | ОЗУ пик: {max_ram:.2f} МБ | ЦПУ ср: {avg_cpu:.2f}%"
            )

            with open(RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

    xs = list(results.keys())
    plot_metric(xs, [results[k]["time_avg"] for k in xs], "Время (сек)", "Среднее время выполнения", "plots/approx/plot_time.png", fit_type="line")
    plot_metric(xs, [results[k]["ram_avg"] for k in xs], "ОЗУ среднее (МБ)", "Среднее потребление ОЗУ", "plots/approx/plot_ram_avg.png", fit_type="log")
    plot_metric(xs, [results[k]["ram_max"] for k in xs], "ОЗУ пик (МБ)", "Пиковое потребление ОЗУ", "plots/approx/plot_ram_max.png", fit_type="log")
    plot_metric(xs, [results[k]["cpu_avg"] for k in xs], "ЦПУ (%)", "Средняя загрузка ЦПУ", "plots/approx/plot_cpu_avg.png", fit_type="line")

    plot_metric0(xs, [results[k]["time_avg"] for k in xs], "Время (сек)", "Среднее время выполнения", "plots/line/plot_time.png")
    plot_metric0(xs, [results[k]["ram_avg"] for k in xs], "ОЗУ среднее (МБ)", "Среднее потребление ОЗУ", "plots/line/plot_ram_avg.png")
    plot_metric0(xs, [results[k]["ram_max"] for k in xs], "ОЗУ пик (МБ)", "Пиковое потребление ОЗУ", "plots/line/plot_ram_max.png")
    plot_metric0(xs, [results[k]["cpu_avg"] for k in xs], "ЦПУ (%)", "Средняя загрузка ЦПУ", "plots/line/plot_cpu_avg.png")

    plot_metric_0_100(xs, [results[k]["cpu_avg"] for k in xs], "ЦПУ (%)", "Средняя загрузка ЦПУ",
                "plots/approx/plot_cpu_avg.png", fit_type="line")

    print("\nГрафики сохранены: plot_time.png, plot_ram_avg.png, plot_ram_max.png, plot_cpu_avg.png")

    total_end = time.time()
    total_time = total_end - total_start
    print(f"\n⏱ Общее время работы программы: {total_time:.2f} сек")

if __name__ == "__main__":
    main()
