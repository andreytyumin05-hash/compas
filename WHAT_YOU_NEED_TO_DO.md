# После чистки agent-v2-vision

```powershell
git pull origin agent-v2-vision
```

## Что починено
1. **`rounded_rect`** — настоящие **дуги** (не ломаная из отрезков).
2. **`sk.stadium(x,y,L,W)`** — овал.
3. Validate режет **английскую прозу** модели в «коде».
4. Knowledge + prompts под stadium/крышку.
5. `list_models` советует **gpt-oss / qwen**, не allam/orpheus.

## .env для кода (Groq)
```env
LLM_MODEL=openai/gpt-oss-120b
# или openai/gpt-oss-20b / qwen/qwen3.8-27b
```
`python -m agent.list_models` — сверь id.

## Проверки
```powershell
python -m agent.build "Крышка 116x80 толщина 13, rounded R40, бобышка R30 высота 18"
# в КОМПАС края базы должны быть гладкими дугами
```

Бот: перезапуск `python -m bot`.

## Не коммить
`answers.txt` очищен; ключи/токены в answers не класть.
