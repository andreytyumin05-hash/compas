# Visual Fluent v2 подтянут в remote

Ветка: **feature/visual-fluent-v2** (и синхронизация в agent-v2-vision).

```powershell
git fetch origin
git checkout feature/visual-fluent-v2
git pull origin feature/visual-fluent-v2

python -m unittest tests.test_visual_and_vars tests.test_offline_dry_run -v
python -m agent.dry_run --self-test

# live (КОМПАС открыт)
python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
```

Смотри в сгенерированном коде: `var` / `set_properties` / `screenshot`.
COM внутри — best-effort; допилить под твою v23 после live-лога.
