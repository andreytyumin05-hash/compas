"""
Telegram-бот: текст или фото чертежа → подтверждение → очередь → КОМПАС → файл.

  TELEGRAM_BOT_TOKEN=...
  GEMINI_API_KEY=...   # для vision
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

# user_id -> pending spec dict
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
            "• текст: описание детали\n"
            "• фото: чертёж → распознаю → подтвердите → строю в КОМПАС\n\n"
            "КОМПАС должен быть открыт на этом ПК."
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
                await update.message.reply_text(f"Не удалось распознать: {e}")
                return

            # spec держим в памяти; файл рисунка удалится с ws
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
            await q.edit_message_text("Ок, пришлите другое фото или текст с размерами.")
            return
        if q.data != "spec_ok":
            return
        spec = _pending_specs.pop(uid, None)
        if not spec:
            await q.edit_message_text("Спецификация устарела — пришлите фото снова.")
            return
        task = spec_to_task_text(spec)
        await q.edit_message_text("В очереди на построение…\n" + task[:500])
        await _enqueue_build(update, context, task, reply_to=q.message)

    async def _enqueue_build(update, context, task: str, reply_to=None) -> None:
        uid = update.effective_user.id
        job = await build_queue.submit(uid, task)
        msg = reply_to or update.message
        await msg.reply_text(
            f"Позиция в очереди: ~{job.position}. Строю (один КОМПАС — по очереди)…"
        )
        try:
            result = await asyncio.wait_for(job.future, timeout=360)
            code = result.get("code", "")
            preview = code if len(code) < 3000 else code[:3000] + "\n..."
            await msg.reply_text(
                "Готово.\n```python\n" + preview + "\n```",
                parse_mode="Markdown",
            )
            # экспорт best-effort
            try:

                def _exp():
                    from core import Part
                    from bot.sessions import session_workspace as sw
                    # already cleaned; new short session for file
                    return None

                # отдельная сессия под файл
                from core import Part
                from core.export import session_dir, safe_delete_path

                out_dir = session_dir(str(uid))
                try:
                    p = Part.from_active()
                    out = p.export(out_dir / "part.step", fmt="step")
                    await msg.reply_document(document=open(out, "rb"), filename="part.step")
                finally:
                    safe_delete_path(out_dir)
            except Exception as ex:
                await msg.reply_text(
                    f"Модель в КОМПАС готова; экспорт файла не удался: {ex}"
                )
        except Exception as e:
            await msg.reply_text(f"Ошибка построения: {e}")

    async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        task = (update.message.text or "").strip()
        if not task:
            return
        # если ждём правку спеки — можно расширить позже
        low = task.lower()
        if low in ("да", "yes", "ок", "ok", "верно") and update.effective_user.id in _pending_specs:
            spec = _pending_specs.pop(update.effective_user.id)
            await _enqueue_build(update, context, spec_to_task_text(spec))
            return
        await _enqueue_build(update, context, task)

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("Bot polling… КОМПАС должен быть запущен.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
