"""
Проверка сгенерированного кода перед запуском.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# Запрещённые куски (галлюцинации и COM)
_FORBIDDEN_PATTERNS = [
    (r"\bwin32com\b", "запрещён win32com"),
    (r"\bgencache\b", "запрещён gencache"),
    (r"\bDispatch\b", "запрещён Dispatch"),
    (r"\bGetActiveObject\b", "запрещён GetActiveObject"),
    (r"Part\.createSketch\b", "нет метода Part.createSketch"),
    (r"\bCircle\s*\(", "класса Circle нет — используй sk.circle"),
    (r"\bRectangle\s*\(", "класса Rectangle нет — используй sk.rectangle"),
    (r"\.move\s*\(", "метода move нет"),
    (r"diameter\s*=", "параметра diameter нет — используй radius = D/2"),
    (r"\bimport\s+(?!core\b)\w+", "разрешён только import из core"),
]

_ALLOWED_IMPORT = re.compile(
    r"^\s*from\s+core\s+import\s+Part\s*(?:#.*)?$", re.MULTILINE
)


def validate_generated_code(code: str) -> Tuple[bool, List[str]]:
    """
    Возвращает (ok, список ошибок).
    ok=True — можно исполнять.
    """
    errors: List[str] = []
    text = code.strip()
    if not text:
        return False, ["пустой код"]

    if "from core import Part" not in text and "from core import Part," not in text:
        # допускаем только `from core import Part`
        if not _ALLOWED_IMPORT.search(text):
            errors.append("нужен ровно: from core import Part")

    for pat, msg in _FORBIDDEN_PATTERNS:
        if re.search(pat, text):
            # исключение: from core import Part — уже проверили
            if pat.startswith(r"\bimport\s+") and "from core import" in text:
                # перепроверим построчно
                for line in text.splitlines():
                    s = line.strip()
                    if s.startswith("import ") and not s.startswith("import core"):
                        errors.append(f"{msg}: {s}")
                    if s.startswith("from ") and not s.startswith("from core"):
                        errors.append(f"{msg}: {s}")
                continue
            errors.append(msg)

    if "Part.create" not in text:
        errors.append("ожидается Part.create(...)")

    # убрать дубли
    uniq: List[str] = []
    for e in errors:
        if e not in uniq:
            uniq.append(e)
    return len(uniq) == 0, uniq
