# Ошибка rounded_rect — исправлено

```
Параметр является обязательным
```

В КОМПАС у `ksArcByPoint` нужен **direction** (1 / -1), без него COM падает.  
Теперь дуги через `ksArcByAngle` + fallback с direction.

```powershell
git pull origin agent-v2-vision

# КОМПАС открыт:
python -m core.smoke_rounded

# или
python -m agent.build "Крышка length=116 width=80 thickness=13 outer_radius=40 boss_height=18 inner_radius=30"
```

Ждём `OK` / `Готово`. Потом `python -m bot` и фото снова.
