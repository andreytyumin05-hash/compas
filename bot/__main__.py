"""
Telegram-бот: текст / фото → очередь → КОМПАС → файлы (m3d, step) → удаление tmp.

  TELEGRAM_BOT_TOKEN=
  GROQ_API_KEY=
  GEMINI_API_KEY=          # для фото
  python -m bot
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("compas.bot")

_pending_specs: dict[int, dict] = {}


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("Задайте TELEGRAM_BOT_TOKEN в .env")
        sys.exit(1)

    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import (
            Application,
            CommandHandler,
            MessageHandler,
            CallbackQueryHandler,
            filters,
            ContextTypes,
        )
    except ImportError:
        print("pip install python-telegram-bot")
        sys.exit(1)

    from agent.schema import format_spec_for_user, spec_to_task_text
    from bot.queue import build_queue, Job
    from bot.sessions import session_workspace
    from core.export import session_dir, safe_delete_path

    async def worker(job: Job) -> None:
        def _build() -> str:
            from agent.build import run_task

            return run_task(job.description)

        try:
            code = await asyncio.wait_for(asyncio.to_thread(_build), timeout=300)
            if not job.future.done():
                job.future.set_result({"code": code, "ok": True})
        except Exception as e:
            if not job.future.done():
                job.future.set_exception(e)

    async def post_init(app: Application) -> None:
        await build_queue.start(worker)

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "compas-бот\n\n"
            "• текст — описание детали\n"
            "• фото чертежа — распознаю → подтверждение → сборка\n"
            "• пришлю .m3d (КОМПАС) и .step, локальные файлы удалю\n\n"
            "КОМПАС на этом ПК; GROQ_API_KEY; для фото — GEMINI_API_KEY."
        )

    async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        uid = update.effective_user.id
        await update.message.reply_text("Распознаю чертёж…")
        photo = update.message.photo[-1]
        tg_file = await photo.get_file()

        with session_workspace(uid) as ws:
            img_path = ws / "drawing.jpg"
            await tg_file.download_to_drive(str(img_path))

            def _vision():
                from agent.vision import analyze_drawing

                return analyze_drawing(img_path)

            try:
                spec = await asyncio.to_thread(_vision)
            except Exception as e:
                await update.message.reply_text(
                    f"Не распознал: {e}\nНужен GEMINI_API_KEY или пришлите размеры текстом."
                )
                return

            _pending_specs[uid] = spec

        text = format_spec_for_user(spec)
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Верно, строить", callback_data="spec_ok"),
                    InlineKeyboardButton("❌ Нет", callback_data="spec_no"),
                ]
            ]
        )
        await update.message.reply_text(text, reply_markup=kb)

    async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        q = update.callback_query
        await q.answer()
        uid = update.effective_user.id
        if q.data == "spec_no":
            _pending_specs.pop(uid, None)
            await q.edit_message_text("Ок, другое фото или текст.")
            return
        if q.data != "spec_ok":
            return
        spec = _pending_specs.pop(uid, None)
        if not spec:
            await q.edit_message_text("Спека устарела — фото снова.")
            return
        task = spec_to_task_text(spec)
        await q.edit_message_text("В очереди…\n" + task[:500])
        await _enqueue_build(update, context, task, reply_to=q.message)

    async def _send_exports(msg, uid: int) -> None:
        out_dir = session_dir(str(uid))
        try:

            def _exp():
                from core import Part

                p = Part.from_active()
                return p.export_formats(
                    out_dir, formats=["m3d", "step"], close=True
                )

            paths = await asyncio.to_thread(_exp)
            for path in paths:
                try:
                    with open(path, "rb") as f:
                        await msg.reply_document(
                            document=f, filename=path.name
                        )
                except Exception as e:
                    await msg.reply_text(f"Не отправил {path.name}: {e}")
            if not paths:
                await msg.reply_text("Модель в КОМПАС есть, файлы не сохранились.")
        except Exception as ex:
            await msg.reply_text(f"Экспорт: {ex}")
        finally:
            safe_delete_path(out_dir)

    async def _enqueue_build(update, context, task: str, reply_to=None) -> None:
        uid = update.effective_user.id
        job = await build_queue.submit(uid, task)
        msg = reply_to or update.message
        await msg.reply_text(f"Очередь ~{job.position}. Строю…")
        try:
            result = await asyncio.wait_for(job.future, timeout=360)
            code = result.get("code", "")
            preview = code if len(code) < 2500 else code[:2500] + "\n..."
            await msg.reply_text(
                "Готово.\n```python\n" + preview + "\n```",
                parse_mode="Markdown",
            )
            await _send_exports(msg, uid)
        except Exception as e:
            await msg.reply_text(f"Ошибка: {e}")

    async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        task = (update.message.text or "").strip()
        if not task:
            return
        low = task.lower()
        if (
            low in ("да", "yes", "ок", "ok", "верно")
            and update.effective_user.id in _pending_specs
        ):
            spec = _pending_specs.pop(update.effective_user.id)
            await _enqueue_build(update, context, spec_to_task_text(spec))
            return
        await _enqueue_build(update, context, task)

    app = Application.builder().token(token).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("Bot polling…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
