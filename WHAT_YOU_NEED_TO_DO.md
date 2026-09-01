# Visual loop max — pull

```powershell
git fetch origin
git checkout feature/visual-fluent-v2
git pull origin feature/visual-fluent-v2

python -m unittest tests.test_visual_loop tests.test_visual_and_vars tests.test_offline_dry_run -v

# КОМПАС + GEMINI_API_KEY в .env
python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
```

В логе ищи `👁 VLM critic` или `visual loop: ok`.
Отключить VLM: `$env:COMPAS_VISUAL_LOOP=0`
