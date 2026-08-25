"""
Smoke test на УЖЕ открытой детали (Этап 2–3 из open_ai_solve).

1) В КОМПАСе: Файл → Создать → Деталь
2) python -m core.smoke_active

Не создаёт документ — только sketch + extrude в активной детали.
"""

from __future__ import annotations

import os
import sys
import traceback

# Включить подробные ошибки в core (если поддерживается)
os.environ.setdefault("COMPAS_DEBUG_COM", "1")


def main() -> None:
    print("=== smoke_active: geometry on existing Part ===")
    try:
        from core import Part

        p = Part.from_active()
        print("from_active OK", p)

        with p.sketch("xy") as sk:
            sk.circle(0, 0, 20.0)
        print("sketch+circle OK")

        p.extrude(sk, depth=50.0)
        print("extrude OK")

        p.update()
        print("SUCCESS — check KOMPAS for a cylinder Ø40 x 50")
    except Exception:
        print("FAIL:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
