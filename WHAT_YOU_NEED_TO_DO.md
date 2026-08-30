# Конфликт в sketch.py — снят

В ветке были маркеры `<<<<<<< HEAD` — Python не мог нормально импортировать `core`, бот не стартовал / падал `ksLineSeg=0`.

```powershell
git pull origin agent-v2-vision

# проверка синтаксиса
python -c "from core.sketch import Sketch; print('ok')"

python -m core.smoke_rounded
python -m bot
```

Если pull снова даст конфликт — возьми версию с remote (уже чистая) или:
```powershell
git checkout --theirs core/sketch.py
git add core/sketch.py
```
