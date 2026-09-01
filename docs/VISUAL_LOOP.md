# Visual loop (замкнутый)

```
generate_checked
  → exec в КОМПАС
  → live_verify (iso + front screenshots)
  → snapshot дерева
  → VLM (Gemini / OpenRouter) по картинкам + ТЗ
  → если issues → repair LLM → exec снова
```

## Env

| Переменная | Смысл |
|------------|--------|
| `COMPAS_VISUAL_LOOP=1` | включить (по умолчанию 1) |
| `COMPAS_VISUAL_LOOP=0` | только build без VLM |
| `GEMINI_API_KEY` | VLM critic |
| `OPENROUTER_API_KEY` | fallback vision |

## Код

- `agent/visual_critic.py` — разбор скринов
- `agent/tree_snapshot.py` — дерево в repair
- `agent/build.py` — оркестрация + auto-хвост screenshot
- шаблон втулки уже с `var` + screenshot

## Проверка

```powershell
python -m unittest tests.test_visual_loop tests.test_visual_and_vars -v
python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
```
