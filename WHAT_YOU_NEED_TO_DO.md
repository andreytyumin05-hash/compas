# Генерация + чистка (agent-v2-vision)

```powershell
git pull origin agent-v2-vision
python -m agent.build "Крышка length=116 width=80 thickness=13 outer_radius=40 boss_height=18 inner_radius=30"
python -m bot
```

Типовые детали идут **шаблоном** (без LLM). Успехи пишутся в `.compas_tmp/build_memory.jsonl`.

Локальному агенту: файл **`CODEX_AGENT_PROMPT.md`**.

Потом можно мержить ветку в `main`.
