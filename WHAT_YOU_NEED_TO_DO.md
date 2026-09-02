# Локальная проверка (КОМПАС-3D v23)

```powershell
git pull origin main
python -m unittest discover -s tests -v
python -m bot
python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
```

## Детали для ручной проверки

1. **Втулка** — extrude + hole through
2. **Фланец** — extrude + center hole + pattern PCD
3. **Вал 3 ступени** — 3× circle+extrude
4. **Крышка stadium** — stadium/rounded_rect, boss, cut, pattern, fillet
5. **Пробка** — multi extrude, hex pocket cut, chamfer
6. **Штуцер** — steps + hole + ring_groove
7. **Плита+паз** — extrude + slot
8. **Цековка** — counterbore (не только hole)

Смотри дерево построения и вид сверху. shell/thread/sketch_on_face — должны падать, не silent-ok.

Подробнее: docs/AUDIT_MAIN.md
