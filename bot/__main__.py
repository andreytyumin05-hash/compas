"""
Telegram bot: drawing/text -> canonical CAD contract -> builder.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
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

_GREETING = re.compile(
    r"^(привет|здравствуй|здравствуйте|hello|hi|hey|добрый\s+(день|вечер|утро)|как дела|что умеешь)\s*[!.]?$",
    re.I,
)


def build_vision_failure_message() -> str:
    return (
        "Не удалось разобрать чертёж по фото. Пришлите более чёткое фото или размеры текстом, "
        "например: «Втулка Ø40/Ø20, длина 50 мм; 4×Ø6 на PCD 32»."
    )


def _looks_like_part_task(text: str) -> bool:
    t = text.strip()
    if len(t) < 6 or _GREETING.match(t):
        return False
    if re.search(r"\d", t):
        return True
    keys = (
        "втулк", "фланец", "плит", "вал", "отверст", "цилиндр", "куб",
        "детал", "диаметр", "толщин", "длин", "крышк", "бобыш", "канавк",
        "карман", "фаск", "скругл", "штуцер", "пробк", "паз",
    )
    low = t.lower()
    return any(k in low for k in keys)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("TELEGRAM_BOT_TOKEN в .env")
        sys.exit(1)

    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
        from telegram.request import HTTPXRequest
    except ImportError:
        print("pip install python-telegram-bot")
        sys.exit(1)

    from agent.contract import spec_to_contract_text
    from agent.schema import format_spec_for_user
    from bot.queue import build_queue, Job
    from bot.sessions import session_workspace
    from core.export import session_dir, safe_delete_path

    async def worker(job: Job) -> None:
        def _build() -> str:
            from agent.build import run_task
            return run_task(job.description)
        try:
            code = await asyncio.wait_for(asyncio.to_thread(_build), timeout=420)
            if not job.future.done():
                job.future.set_result({"code": code, "ok": True})
        except Exception as exc:
            if not job.future.done():
                job.future.set_exception(exc)

    async def post_init(app: Application) -> None:
        await build_queue.start(worker)

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Агент КОМПАС-3D\n\n"
            "Пришлите фото чертежа или описание детали с размерами.\n"
            "Для сложных деталей желательно указать все диаметры, длины, отверстия, PCD, пазы и фаски."
        )

    async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        uid = update.effective_user.id
        await update.message.reply_text("Разбираю чертёж…")
        photo = update.message.photo[-1]
        tg_file = await photo.get_file()
        with session_workspace(uid) as ws:
            img_path = ws / "drawing.jpg"
            await tg_file.download_to_drive(str(img_path))

            def _vision() -> dict:
                from agent.vision import analyze_drawing
                return analyze_drawing(img_path)

            try:
                spec = await asyncio.to_thread(_vision)
            except Exception:
                log.exception("vision")
                await update.message.reply_text(build_vision_failure_message())
                return
            _pending_specs[uid] = spec

        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Строить", callback_data="spec_ok"), InlineKeyboardButton("Неверно", callback_data="spec_no")]])
        await update.message.reply_text(format_spec_for_user(spec), reply_markup=kb)

    async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        q = update.callback_query
        try:
            await q.answer()
        except Exception as exc:
            log.warning("callback answer: %s", exc)
        uid = update.effective_user.id
        if q.data == "spec_no":
            _pending_specs.pop(uid, None)
            try:
                await q.edit_message_text("Ок. Пришлите другое фото или исправление размерами текстом.")
            except Exception:
                pass
            return
        if q.data != "spec_ok":
            return
        spec = _pending_specs.pop(uid, None)
        if not spec:
            try:
                await q.edit_message_text("Сессия устарела — пришлите фото снова.")
            except Exception:
                pass
            return
        task = spec_to_contract_text(spec)
        try:
            await q.edit_message_text("В очереди на построение…")
        except Exception:
            pass
        await _enqueue_build(update, context, task, reply_to=q.message)

    async def _send_exports(msg, uid: int) -> None:
        out_dir = session_dir(str(uid))
        try:
            def _exp():
                from core import Part
                p = Part.from_active()
                return p.export_formats(out_dir, formats=["m3d", "step"], close=True)
            paths = await asyncio.to_thread(_exp)
            for path in paths:
                try:
                    with open(path, "rb") as f:
                        await msg.reply_document(document=f, filename=path.name)
                except Exception:
                    log.exception("send file")
                    await msg.reply_text(f"Файл {path.name} не отправился.")
        except Exception:
            log.exception("export")
            await msg.reply_text("Модель создана, но экспорт не удалось отправить.")
        finally:
            safe_delete_path(out_dir)

    async def _enqueue_build(update, context, task: str, reply_to=None) -> None:
        uid = update.effective_user.id
        job = await build_queue.submit(uid, task)
        msg = reply_to or update.message
        try:
            await msg.reply_text("Строю в КОМПАС…")
        except Exception:
            pass
        try:
            result = await asyncio.wait_for(job.future, timeout=480)
            code = result.get("code") or ""
            n_lines = code.count("\n") + 1 if code else 0
            await msg.reply_text(f"Готово. Модель построена в КОМПАС.\nСкрипт: ~{n_lines} строк.")
            log.info("build ok user=%s code_lines=%s", uid, n_lines)
            await _send_exports(msg, uid)
        except Exception as exc:
            log.exception("build fail")
            brief = str(exc)
            if len(brief) > 320:
                brief = brief[:320] + "…"
            try:
                await msg.reply_text("Не удалось построить.\n" + brief)
            except Exception:
                pass

    async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        task = (update.message.text or "").strip()
        if not task:
            return
        low = task.lower()
        if low in {"да", "yes", "ок", "ok", "верно", "строить"} and update.effective_user.id in _pending_specs:
            spec = _pending_specs.pop(update.effective_user.id)
            await _enqueue_build(update, context, spec_to_contract_text(spec))
            return
        if not _looks_like_part_task(task):
            await update.message.reply_text("Нужно описание детали с размерами или фото чертежа.")
            return
        await _enqueue_build(update, context, task)

    async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        log.exception("handler: %s", context.error)

    request = HTTPXRequest(connection_pool_size=8, connect_timeout=30.0, read_timeout=60.0, write_timeout=60.0, pool_timeout=30.0)
    app = Application.builder().token(token).request(request).post_init(post_init).build()
    app.add_error_handler(on_error)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("Bot polling… (КОМПАС on this PC)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
