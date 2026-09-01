"""Mixin-методы Part: var, properties, view, screenshot, verify."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from . import visual as _visual


class FluentMixin:
    def var(self, name: str, value: float, *, comment: str = "") -> bool:
        return _visual.var(self, name, value, comment=comment)

    def set_properties(
        self,
        *,
        designation: str = "",
        name: str = "",
        material: str = "",
        note: str = "",
        **extra: Any,
    ) -> bool:
        return _visual.set_properties(
            self,
            designation=designation,
            name=name,
            material=material,
            note=note,
            **extra,
        )

    def get_context(self) -> Dict[str, Any]:
        return _visual.get_context(self)

    def set_view(self, orientation: str = "iso", *, zoom_all: bool = True) -> bool:
        return _visual.set_view(self, orientation, zoom_all=zoom_all)

    def screenshot(
        self, path: str | Path, *, width: int = 1280, height: int = 720
    ) -> Optional[Path]:
        return _visual.screenshot(self, path, width=width, height=height)

    def verify(
        self,
        out_dir: str | Path = "session_verify",
        *,
        views: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """После update: iso+front screenshots (live visual loop)."""
        from agent.verify import live_verify

        return live_verify(self, out_dir, views=views or ["iso", "front"])
