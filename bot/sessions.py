"""Временные папки на пользователя + гарантированная очистка."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from core.export import safe_delete_path, session_dir

log = logging.getLogger("compas.bot")


@contextmanager
session_workspace(user_id: int) -> Iterator[Path]:
    path = session_dir(str(user_id))
    try:
        yield path
    finally:
        safe_delete_path(path)
        log.info("session cleaned user=%s path=%s", user_id, path)
