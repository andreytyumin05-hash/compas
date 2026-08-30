# Лимиты и каскад LLM

Типовые детали (крышка/втулка) идут **без API** (шаблон).
Сложные — каскад, чтобы не упираться в один 429:

1. **Gemini** (тот же `GEMINI_API_KEY`, что vision)
2. **Groq light** (`gpt-oss-20b` / instant)
3. **Groq strong** (`gpt-oss-120b` / qwen)
4. **OpenRouter free** (если ключ есть)

```env
LLM_PROVIDER=cascade
GEMINI_API_KEY=AIza...
GROQ_API_KEY=gsk_...
TELEGRAM_BOT_TOKEN=...
VISION_MODEL=gemini-3.6-flash
```

```powershell
git pull origin agent-v2-vision
python -m agent.list_models
# Ctrl+C → python -m bot
```

Если Groq 429 — cascade уйдёт на Gemini сам. Подожди минуту при полном исчерпании.
