# Text → parametric CAD

```powershell
git pull origin main
python -m unittest discover -s tests -v

python -m agent.build "Штуцер: основание Ø60 длиной 20, затем ступень Ø45 длиной 15, затем шейка Ø30 длиной 25, сквозное отверстие Ø16, канавка шириной 4, фаска 2x45"
```

Проверь в КОМПАС:
- 3 ступени (3 extrude), не один цилиндр
- отверстие Ø16
- в коде есть part.param / part.p
- spline: только если профиль кривой (лопасть); smoke: маленький sk.spline на xz

Документ: docs/PARAMETRIC_TEXT_TO_CAD.md
