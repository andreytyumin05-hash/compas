# Критик кода перед КОМПАС

Перед сборкой:
1. Синтаксис + покрытие ТЗ
2. **Структура** (цилиндр ≠ rectangle, карман = cut, ступени ≥2 extrude…)
3. На сложных ТЗ — короткий **LLM-критик** (JSON ok/issues), при проблемах — перегенерация

```powershell
git pull origin agent-v2-vision
python -m bot
```
