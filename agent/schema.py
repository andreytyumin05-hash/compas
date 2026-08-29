"""JSON-схема распознанного чертежа / спецификации детали."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Описание для vision-промпта (не jsonschema-lib, чтобы не тащить зависимость)
FEATURE_SCHEMA_TEXT = """
{
  "part_type": "bushing|flange|plate|shaft|bracket|other",
  "name": "строка",
  "units": "mm",
  "overall": {"width": null, "height": null, "length": null, "outer_diameter": null, "thickness": null},
  "features": [
    {
      "type": "extrude_body|revolve_body|hole|pocket|chamfer|fillet|slot|pattern_holes",
      "params": { },
      "confidence": 0.0-1.0,
      "notes": ""
    }
  ],
  "unknown_dimensions": ["список того, что не прочитано с чертежа"],
  "warnings": []
}
""".strip()


def spec_to_task_text(spec: Dict[str, Any]) -> str:
    """Превратить JSON-спеку в текстовое ТЗ для agent.build."""
    lines: List[str] = []
    name = spec.get("name") or spec.get("part_type") or "Деталь"
    lines.append(f"Деталь: {name} (тип {spec.get('part_type', 'other')}), единицы: {spec.get('units', 'mm')}")
    overall = spec.get("overall") or {}
    bits = [f"{k}={v}" for k, v in overall.items() if v is not None]
    if bits:
        lines.append("Габариты: " + ", ".join(bits))
    for i, feat in enumerate(spec.get("features") or [], 1):
        lines.append(f"{i}. {feat.get('type')}: {feat.get('params')} {feat.get('notes') or ''}")
    unk = spec.get("unknown_dimensions") or []
    if unk:
        lines.append("НЕИЗВЕСТНЫЕ размеры (не выдумывать): " + ", ".join(str(u) for u in unk))
    return "\n".join(lines)


def format_spec_for_user(spec: Dict[str, Any]) -> str:
    """Человекочитаемое подтверждение перед построением."""
    lines = ["Я понял чертёж так:", ""]
    lines.append(f"• Тип: {spec.get('part_type', '?')}")
    if spec.get("name"):
        lines.append(f"• Имя: {spec['name']}")
    overall = spec.get("overall") or {}
    for k, v in overall.items():
        if v is not None:
            lines.append(f"• {k}: {v} {spec.get('units', 'mm')}")
    feats = spec.get("features") or []
    if feats:
        lines.append("• Элементы:")
        for f in feats:
            lines.append(f"  – {f.get('type')}: {f.get('params')}")
    unk = spec.get("unknown_dimensions") or []
    if unk:
        lines.append("")
    lines.append("⚠️ Не прочитано (нужно уточнить): " + ", ".join(str(u) for u in unk))
    for w in spec.get("warnings") or []:
        lines.append(f"⚠️ {w}")
    lines.append("")
    lines.append("Верно? Ответьте «да» / «нет» или пришлите исправление размеров.")
    return "\n".join(lines)
