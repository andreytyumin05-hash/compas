# agent-v2-vision — что делать

```powershell
git fetch
git checkout agent-v2-vision
git pull origin agent-v2-vision
pip install -r requirements.txt
```

## Уже в ветке

| Модуль | Статус |
|--------|--------|
| `core/sketch` ellipse, rounded_rect, spline, slot | готово |
| `core/features` hole, pattern holes | готово |
| `core/export`, `mass` | готово (best-effort COM) |
| `Part.hole / pattern_* / export` | готово |
| `agent/vision.py` | Gemini → OpenRouter |
| `agent/build` COM-retry | готово |
| `bot` очередь + фото + confirm + step | готово |
| loft/sweep/boolean/сборка | **не** в стабильном API — см. ROADMAP |

## Проверки

```powershell
# КОМПАС открыт
python -m agent.build "Фланец диаметр 80 толщина 10, центр 20, 4 отверстия 9 на диаметре 55"

# vision (нужен GEMINI_API_KEY)
python -c "from agent.vision import analyze_drawing; print(analyze_drawing(r'path\\to\\drawing.jpg'))"

# бот
# .env: TELEGRAM_BOT_TOKEN + GEMINI_API_KEY + GROQ_API_KEY
python -m bot
```

## .env

```
LLM_PROVIDER=groq
GROQ_API_KEY=
GEMINI_API_KEY=
VISION_PROVIDER=auto
TELEGRAM_BOT_TOKEN=
```
