# После answers — что делать

## 1) Почему «в питоне ничего не получилось»
В answers был **ParserError PowerShell**, не ошибка КОМПАС.
Строки `from core import Part` выполнялись как PowerShell (`>>`), а не Python.

Правильно:
```powershell
cd D:\учеба\ML_study\compas
git checkout features/vision
git pull origin features/vision
.\venv\Scripts\activate
python -m unittest discover -s tests -v
python scripts\smoke_dims.py
```

## 2) Тесты
Исправлены ожидания `part.param` (раньше тесты ждали устаревший `part.var`).

## 3) Smoke размеров
Скрипт печатает True/False. Если оба False — API размеров на машине не принимает GetParamStruct/type-id.

## 4) В answers клади вывод **python**, не PowerShell.
