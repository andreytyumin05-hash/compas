# КОМПАС v23 — эскиз (проверено Codex + smoke)

## Успех COM
`ksLineSeg` / `ksCircle` / `ksArcByAngle` возвращают **ненулевой** int при успехе  
(пример: `1073741855`), **0** — провал. Не путать с «0 = OK».

## Дуги
Рабочая:
```
ksArcByAngle(xc, yc, radius, ang1_deg, ang2_deg, direction, style)
direction = 1 (CCW) или -1 (CW)
```
`ksArcByPoint` на этой установке → «Параметр является обязательным» — **не использовать**.

## Stadium
При `radius = width/2` боковые отрезки нулевой длины — **не вызывать** `ksLineSeg` для них.

## Property
`BeginEdit`, `EndEdit`, `GetDefinition`, `Create` — property-style late-binding.
