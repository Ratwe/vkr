import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
from collections import Counter


def remove_png_extension(filename):
    return filename[:-4] if filename.lower().endswith('.png') else filename


def filename_to_url(name):
    base = remove_png_extension(name)
    if base.count('_') == 3 and all(part.isdigit() for part in base.split('_')):
        return base.replace('_', '.')
    parts = base.split('_')
    if len(parts) >= 2 and parts[1] == 'php':
        filename = f"{parts[0]}.php"
        if len(parts) > 2:
            params = parts[2:]
            query_parts = []
            i = 0
            while i < len(params):
                if i + 1 < len(params):
                    param = params[i].replace('.', '=')
                    if '=' not in param:
                        param = f"{param}={params[i + 1]}"
                        i += 1
                    query_parts.append(param)
                else:
                    query_parts.append(params[i])
                i += 1
            return f"{filename}?{'&'.join(query_parts)}"
        return filename
    return base.replace('_', '.')


def strip_query_params(url):
    return url.split('/')[-1].split('?')[0].split('$')[0]


class ImageViewerApp:
    def __init__(self, root, start_path):
        self.root = root
        self.start_path = start_path
        self.current_image_path = None
        self.node_paths = {}
        self.original_image = None

        self.root.title("Heatmaps Viewer")
        self.root.attributes('-fullscreen', True)
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=0)

        # --- Верхняя панель --- #
        toolbar = ttk.Frame(root)
        toolbar.grid(row=0, column=0, columnspan=3, sticky="ew")

        ttk.Button(toolbar, text="📂 Раскрыть всё", command=self.expand_all).pack(side="left", padx=5, pady=5)
        ttk.Button(toolbar, text="📁 Свернуть всё", command=self.collapse_all).pack(side="left", padx=5, pady=5)

        self.hide_query_var = tk.BooleanVar()
        ttk.Checkbutton(
            toolbar,
            text="Скрыть query параметры",
            variable=self.hide_query_var,
            command=self.refresh_tree
        ).pack(side="left", padx=10)

        # --- Поле ввода для количества кликов --- #
        ttk.Label(toolbar, text="Последние клики:").pack(side="left", padx=(20, 5))
        self.click_count_var = tk.StringVar(value="100")
        ttk.Entry(toolbar, textvariable=self.click_count_var, width=8).pack(side="left", padx=(0, 10))

        # --- Левая панель --- #
        self.left_frame = ttk.Frame(root, width=300)
        self.left_frame.grid(row=1, column=0, sticky="ns")
        self.left_frame.grid_propagate(False)

        self.tree_scroll_y = ttk.Scrollbar(self.left_frame, orient="vertical")
        self.tree_scroll_y.pack(side="right", fill="y")

        self.tree_scroll_x = ttk.Scrollbar(self.left_frame, orient="horizontal")
        self.tree_scroll_x.pack(side="bottom", fill="x")

        self.tree = ttk.Treeview(
            self.left_frame,
            yscrollcommand=self.tree_scroll_y.set,
            xscrollcommand=self.tree_scroll_x.set
        )
        self.tree.pack(fill="both", expand=True)
        self.tree.heading("#0", text="Дерево URL")
        self.tree.column("#0", width=380, stretch=False)

        self.tree_scroll_y.config(command=self.tree.yview)
        self.tree_scroll_x.config(command=self.tree.xview)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # --- Кнопка обновления --- #
        self.update_button = ttk.Button(self.left_frame, text="🔄 Обновить", command=self.run_all_scripts)
        self.update_button.pack(padx=10, pady=10, anchor="sw", fill="x")

        # --- Центральный Canvas --- #
        self.canvas = tk.Canvas(root, bg="white")
        self.canvas.grid(row=1, column=1, sticky="nsew")
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        self.image_ref = None
        self.image_on_canvas = None

        # --- Плашка со статистикой --- #
        self.stats_frame = ttk.Frame(root, relief="groove", borderwidth=2)
        self.stats_frame.grid(row=1, column=2, sticky="ns", padx=(5, 10), pady=10)

        ttk.Label(self.stats_frame, text="Статистика кликов", font=("Segoe UI", 12, "bold")).pack(pady=(5, 10))

        self.stats_text = tk.Text(self.stats_frame, width=40, height=25, wrap="word", state="disabled", bg="#fafafa")
        self.stats_text.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Нижняя консоль --- #
        self.console_frame = ttk.Frame(root)
        self.console_frame.grid(row=2, column=0, columnspan=3, sticky="ew")
        self.console_frame.columnconfigure(0, weight=1)

        self.console_text = tk.Text(
            self.console_frame,
            height=12,
            bg="#f0f0f0",
            fg="black",
            font=("Courier New", 10),
            wrap="none"
        )
        self.console_text.grid(row=0, column=0, sticky="nsew")

        self.console_scroll = ttk.Scrollbar(self.console_frame, orient="vertical", command=self.console_text.yview)
        self.console_scroll.grid(row=0, column=1, sticky="ns")
        self.console_text.config(yscrollcommand=self.console_scroll.set)

        self.insert_nodes('', self.start_path)
        self.expand_all()
        self.load_and_show_stats()

    def run_script(self, script_name, args=None, callback=None):
        if args is None:
            args = []

        def task():
            try:
                process = subprocess.Popen(
                    ["python", script_name] + args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8'
                )
                for line in process.stdout:
                    self.console_text.insert(tk.END, line)
                    self.console_text.see(tk.END)
                process.wait()
                if callback:
                    callback()
            except Exception as e:
                self.console_text.insert(tk.END, f"[ОШИБКА] {e}\n")
                self.console_text.see(tk.END)

        threading.Thread(target=task, daemon=True).start()

    def run_all_scripts(self):
        self.console_text.delete("1.0", tk.END)

        def run_next(i):
            if i >= len(scripts):
                self.refresh_tree()
                # Обновляем текущее изображение после выполнения всех скриптов
                if self.current_image_path and os.path.exists(self.current_image_path):
                    try:
                        self.original_image = Image.open(self.current_image_path)
                        self.display_image()
                        self.console_text.insert(tk.END, "\nТекущее изображение обновлено\n")
                    except Exception as e:
                        self.console_text.insert(tk.END, f"\nОшибка при обновлении изображения: {e}\n")
                # Обновляем статистику после всех скриптов
                self.load_and_show_stats()
                return

            script, args = scripts[i]
            self.console_text.insert(tk.END, f"\n--- Запуск {script} ---\n")

            # Для heatmap.py передаем дополнительный аргумент click_count_var
            if script == "heatmap.py":
                self.run_script(script, args=[self.click_count_var.get()], callback=lambda: run_next(i + 1))
            else:
                self.run_script(script, args=args, callback=lambda: run_next(i + 1))

        scripts = [
            ("clicks.py", []),
            ("webdriver.py", []),
            ("heatmap.py", [])
        ]
        run_next(0)

    def insert_nodes(self, parent, path):
        try:
            items = os.listdir(path)
        except Exception:
            return

        dirs, files = [], []
        for item in items:
            abspath = os.path.join(path, item)
            if os.path.isdir(abspath):
                dirs.append(item)
            else:
                files.append(item)

        for item in sorted(dirs):
            abspath = os.path.join(path, item)
            display_text = item.replace('_', '.')
            node = self.tree.insert(parent, 'end', text=display_text, values=[abspath])
            self.node_paths[node] = abspath
            self.insert_nodes(node, abspath)

        for item in sorted(files):
            abspath = os.path.join(path, item)
            if os.path.isfile(abspath):
                display_text = filename_to_url(item)
                if self.hide_query_var.get():
                    display_text = strip_query_params(display_text)
                display_text = remove_png_extension(display_text)
                node = self.tree.insert(parent, 'end', text=display_text, values=[abspath])
                self.node_paths[node] = abspath

    def refresh_tree(self):
        open_nodes = set()

        def collect_open_nodes(node):
            if self.tree.item(node, 'open'):
                open_nodes.add(self.node_paths.get(node, ''))
            for child in self.tree.get_children(node):
                collect_open_nodes(child)

        for node in self.tree.get_children(''):
            collect_open_nodes(node)

        self.tree.delete(*self.tree.get_children())
        self.node_paths.clear()
        self.insert_nodes('', self.start_path)

        def reopen_nodes(node):
            path = self.node_paths.get(node, '')
            if path in open_nodes:
                self.tree.item(node, open=True)
            for child in self.tree.get_children(node):
                reopen_nodes(child)

        for node in self.tree.get_children(''):
            reopen_nodes(node)

    def expand_all(self):
        def recurse(node):
            self.tree.item(node, open=True)
            for child in self.tree.get_children(node):
                recurse(child)

        for node in self.tree.get_children(''):
            recurse(node)

    def collapse_all(self):
        def recurse(node):
            self.tree.item(node, open=False)
            for child in self.tree.get_children(node):
                recurse(child)

        for node in self.tree.get_children(''):
            recurse(node)

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        filepath = self.tree.item(selected[0])['values'][0]
        if os.path.isfile(filepath) and filepath.lower().endswith('.png'):
            self.current_image_path = filepath
            self.original_image = Image.open(filepath)
            self.display_image()

    def display_image(self):
        if not self.original_image:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        img_width, img_height = self.original_image.size
        scale = min(canvas_width / img_width, canvas_height / img_height)

        new_size = (int(img_width * scale), int(img_height * scale))
        resized_image = self.original_image.resize(new_size, Image.LANCZOS)

        self.image_ref = ImageTk.PhotoImage(resized_image)
        self.canvas.delete("all")
        self.image_on_canvas = self.canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            anchor="center",
            image=self.image_ref
        )

    def on_canvas_resize(self, event):
        self.display_image()

    def load_and_show_stats(self):
        clicks_path = os.path.join("clicks.json")
        if not os.path.exists(clicks_path):
            self.set_stats_text("Файл clicks.json не найден.")
            return

        try:
            with open(clicks_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.set_stats_text(f"Ошибка чтения clicks.json:\n{e}")
            return

        total_clicks = len(data)
        urls = set()
        sum_x = 0
        sum_y = 0
        count_coords = 0
        page_widths = []
        page_heights = []
        resolutions = []

        for entry in data:
            urls.add(entry.get("url", ""))
            x = entry.get("absX", None)
            y = entry.get("absY", None)
            if x is not None and y is not None:
                sum_x += x
                sum_y += y
                count_coords += 1
            pw = entry.get("pageWidth", None)
            ph = entry.get("pageHeight", None)
            if pw is not None:
                page_widths.append(pw)
            if ph is not None:
                page_heights.append(ph)
            w = entry.get("pageWidth", None)
            h = entry.get("pageHeight", None)
            if w is not None and h is not None:
                resolutions.append(f"{w}/{h}")

        unique_urls = len(urls)
        avg_clicks_per_url = total_clicks / unique_urls if unique_urls > 0 else 0
        avg_x = sum_x / count_coords if count_coords > 0 else 0
        avg_y = sum_y / count_coords if count_coords > 0 else 0
        min_page_width = min(page_widths) if page_widths else 'N/A'
        max_page_width = max(page_widths) if page_widths else 'N/A'
        min_page_height = min(page_heights) if page_heights else 'N/A'
        max_page_height = max(page_heights) if page_heights else 'N/A'

        resolution_counter = Counter(resolutions)
        most_common_res = resolution_counter.most_common(1)
        most_common_res_str = most_common_res[0][0] if most_common_res else "N/A"

        stats = (
            f"Общее количество кликов: {total_clicks}\n"
            f"Количество уникальных URL: {unique_urls}\n"
            f"Среднее количество кликов на URL: {avg_clicks_per_url:.2f}\n"
            f"Средние координаты кликов (absX, absY): ({avg_x:.1f}, {avg_y:.1f})\n"
            f"Ширина страницы: мин = {min_page_width}, макс = {max_page_width}\n"
            f"Высота страницы: мин = {min_page_height}, макс = {max_page_height}\n"
            f"Самое популярное разрешение (Ширина/Высота): {most_common_res_str}\n"
        )

        self.set_stats_text(stats)

    def set_stats_text(self, text):
        self.stats_text.config(state="normal")
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert(tk.END, text)
        self.stats_text.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageViewerApp(root, start_path="heatmaps")
    root.mainloop()
