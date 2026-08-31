"""
Простое окно Windows: задача → agent.build → лог.

Запуск из корня репо (venv):
  python -m desktop.app

Обновления: не самопатчится. Кнопка открывает GitHub; обновить код — git pull
в каталоге репозитория (рекомендуется), либо скачать новый Release.
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except Exception:
    pass

VERSION_FILE = _ROOT / "VERSION"
GITHUB_BRANCH = "https://github.com/andreytyumin05-hash/compas/tree/agent-v2-vision"
GITHUB_COMMITS = "https://github.com/andreytyumin05-hash/compas/commits/agent-v2-vision"


def _version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return "dev"


def main() -> None:
    try:
        import tkinter as tk
        from tkinter import scrolledtext, messagebox
    except ImportError:
        print("tkinter недоступен")
        sys.exit(1)

    root = tk.Tk()
    root.title(f"Compas Agent {_version()}")
    root.geometry("720x520")

    frm = tk.Frame(root, padx=8, pady=8)
    frm.pack(fill=tk.BOTH, expand=True)

    tk.Label(frm, text="Задача (текст с размерами):").pack(anchor="w")
    task_box = scrolledtext.ScrolledText(frm, height=5, wrap=tk.WORD)
    task_box.pack(fill=tk.X, pady=4)
    task_box.insert("1.0", "Втулка наружный 40 внутренний 20 длина 50")

    log = scrolledtext.ScrolledText(frm, height=18, wrap=tk.WORD, state=tk.DISABLED)
    log.pack(fill=tk.BOTH, expand=True, pady=4)

    def write(msg: str) -> None:
        log.configure(state=tk.NORMAL)
        log.insert(tk.END, msg + "\n")
        log.see(tk.END)
        log.configure(state=tk.DISABLED)

    busy = {"v": False}

    def run_build() -> None:
        if busy["v"]:
            return
        task = task_box.get("1.0", tk.END).strip()
        if len(task) < 4:
            messagebox.showwarning("Compas", "Введите описание детали")
            return
        busy["v"] = True
        btn_build.configure(state=tk.DISABLED)
        write("— Сборка… (КОМПАС должен быть открыт)")

        def worker() -> None:
            try:
                from agent.build import run_task

                code = run_task(task)
                root.after(0, lambda: write("OK\n" + (code or "")[:2000]))
            except Exception as e:
                root.after(0, lambda: write(f"Ошибка: {e}"))
            finally:

                def done() -> None:
                    busy["v"] = False
                    btn_build.configure(state=tk.NORMAL)

                root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def check_updates() -> None:
        write(
            f"Версия: {_version()}\n"
            f"Обновление: git pull origin agent-v2-vision\n"
            f"или смотри коммиты: {GITHUB_COMMITS}"
        )
        webbrowser.open(GITHUB_BRANCH)

    bar = tk.Frame(frm)
    bar.pack(fill=tk.X, pady=4)
    btn_build = tk.Button(bar, text="Построить в КОМПАС", command=run_build)
    btn_build.pack(side=tk.LEFT, padx=4)
    tk.Button(bar, text="Проверить обновления", command=check_updates).pack(
        side=tk.LEFT, padx=4
    )
    tk.Button(bar, text="Выход", command=root.destroy).pack(side=tk.RIGHT, padx=4)

    write(
        f"Compas Agent {_version()}\n"
        "Рекомендуемый способ обновлений: git clone/pull, не одноразовый exe.\n"
        "Фото-чертежи удобнее через Telegram-бота (python -m bot)."
    )
    root.mainloop()


if __name__ == "__main__":
    main()
