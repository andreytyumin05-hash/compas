# KOMPAS Add-In: AI CAD

Панель **только внутри** Панели свойств КОМПАС (`CreatePropertyManager` + `ksControlUserWindow`).
Отдельное окно Windows **не используется**.

## Установка

```powershell
cd D:\учеба\ML_study\compas
git checkout features/vision
git pull origin features/vision
$env:COMPAS_REPO = (Get-Location).Path
$env:COMPAS_PYTHON = (Resolve-Path .\venv\Scripts\python.exe).Path
.\addon\install.ps1
```

Полностью закройте КОМПАС → откройте → **Панель AI CAD**.

Если ошибка — пришлите **полный текст** MessageBox (там диагностика API).
