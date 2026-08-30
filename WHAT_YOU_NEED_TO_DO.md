# Важно: бот на телефоне — ОК, КОМПАС на ПК

`python -m bot` крутится **на том же Windows**, где открыт КОМПАС.  
Телефон только шлёт сообщения в Telegram — это нормально.

## Почему «английская проза»

Модель Groq (особенно после 429 Too Many Requests) отвечала текстом, не кодом.  
Теперь для **крышки/stadium/втулки** код берётся из **шаблона без LLM** — стабильнее.

```powershell
git pull origin agent-v2-vision
# Ctrl+C бот → снова:
python -m bot
```

Проверка без TG:
```powershell
python -m agent.runner "Крышка length=116 width=80 thickness=13 outer_radius=40 boss_height=18 inner_radius=30"
python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
```

Если Groq 429 — подожди 1–2 мин или опирайся на шаблоны (типовые детали).
