# Статус: rounded_rect / stadium — ИСПРАВЛЕНО (локальный Codex + синхрон в git)

Проверено на КОМПАС v23:
- `python -m core.smoke_rounded` → OK
- `smoke_active`, `smoke_edges` 4/4, `smoke_export` OK
- `agent.build` крышка → Готово

Сигнатура: `ksArcByAngle(xc,yc,r,a1,a2,dir,style)`. Нулевые линии skip.

Дальше можно усиливать сложную геометрию / бот; core stadium закрыт.
