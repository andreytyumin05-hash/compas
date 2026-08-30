# Крышка / stadium — готово

Локальный Codex + синхрон в `agent-v2-vision`:
- `ksArcByAngle` с direction
- без нулевых `ksLineSeg`
- COM success ≠ 0

```powershell
git pull origin agent-v2-vision
python -m core.smoke_rounded
python -m bot
```

Фото крышки в TG → «Верно, строить» должно собрать деталь.
