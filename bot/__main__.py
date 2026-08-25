"""
Запуск: python -m bot

Нужны в .env:
  TELEGRAM_BOT_TOKEN=...
  (и ключи LLM как для agent)

КОМПАС-3D должен быть запущен на этом компьютере.
Бот вызывает agent.build.run_task — только на машине с КОМПАС.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("Задайте TELEGRAM_BOT_TOKEN в .env")
        print("Создать бота: @BotFather → /newbot → вставить токен в .env")
        sys.exit(1)

    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    except ImportError:
        print("Установите: pip install python-telegram-bot")
        sys.exit(1)

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Пришли текстовое описание детали.\n"
            "Пример: Втулка наружный 40 внутренний 20 длина 50\n"
            "КОМПАС должен быть открыт на этом ПК."
        )

    async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        task = (update.message.text or "").strip()
        if not task:
            return
        await update.message.reply_text("Строю… (LLM + КОМПАС)")

        def _work() -> str:
            from agent.build import run_task

            return run_task(task)

        try:
            code = await asyncio.to_thread(_work)
            preview = code if len(code) < 3500 else code[:3500] + "\n..."
            await update.message.reply_text(
                "Готово. Код:\n```python\n" + preview + "\n```",
                parse_mode="Markdown",
            )
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("Bot polling… Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
