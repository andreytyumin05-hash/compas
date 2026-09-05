# Что проверить после правок эскиза / размеров / сплайна

Ветка: **features/vision** (не main).

## 1. Подтянуть код
```powershell
git fetch
git checkout features/vision
git pull origin features/vision
python -m unittest discover -s tests -v
```

## 2. Размерные линии

Файл: `core/sketch_dims.py` → `sk.dim_linear` / `sk.dim_radial`.

По SDK/форуму ASCON:
- x1,y1,x2,y2 = концы **того же** отрезка, что ksLineSeg;
- dx, dy = смещение размерной линии (не координаты текста);
- ps = 2 → размер параллелен отрезку.

### Smoke
```python
from core import Part
part = Part.create("DimSmoke")
with part.sketch("xy") as sk:
    sk.line(0, 0, 50, 0)
    ok = sk.dim_linear(0, 0, 50, 0)
    sk.circle(0, 0, 20)
    ok2 = sk.dim_radial(0, 0, 20)
print(ok, ok2)
part.update()
```
Если False:
```powershell
python -c "from core.connection import get_app; a=get_app(); print(hasattr(a.k5,'GetParamStruct'))"
```

Авторазмер после circle:
```powershell
$env:COMPAS_AUTO_DIM="1"
```

## 3. Сплайн

`core/sketch_spline.py`: ksBezier + ksBezierPoint, fallback ksPoint.

```python
with part.sketch("xz") as sk:
    sk.spline([(0,0),(10,8),(20,6),(30,0)], closed=False, smooth=True)
```

## 4. Вручную в v23

1. Размер связан с геометрией.
2. Сплайн — кривая, не ломаная.
3. В коде агента после circle есть dim_radial.

## 5. Если размер не появляется — пришли

1. Версию КОМПАС
2. GetParamStruct smoke
3. Traceback
4. Скрин эскиза

## 6. Дальше

- Привязка к object ref ksLineSeg
- API7 ILineDimension
- ksConstraintParam
