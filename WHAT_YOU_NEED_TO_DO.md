# Catch-up готов на remote

```powershell
git fetch origin
git checkout feature/visual-fluent-v2
git pull origin feature/visual-fluent-v2

python -m agent.dry_run --self-test
python -m unittest tests.test_visual_and_vars tests.test_offline_dry_run -v

# live
python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
```

Смотри сгенерированный код: `var`, `set_properties`, `set_view`, `screenshot`.
После build можно в скрипте: `part.verify("out")`.

Подробности: `docs/HABR_MCP_CATCHUP.md`
