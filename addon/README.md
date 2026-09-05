# KOMPAS Add-In: AI CAD

Встраиваемая панель **AI CAD** для КОМПАС-3D v23. Не дублирует CAD-ядро: операции через `addon/bridge.py` → `agent/` + `core/`.

## Как открывается панель

1. **Предпочтительно** — `IPropertyManager` + `ksControlUserWindow` (type 47): HWND внутри панели свойств КОМПАС. **3D-вид не перекрывается.**
2. **Fallback** — узкое `SizableToolWindow` (~300×520) у **правого края** окна КОМПАС (не fullscreen, не TopMost на весь рабочий стол).

| Переменная | Значение | Эффект |
|------------|----------|--------|
| `COMPAS_NATIVE_PROPERTY_PANEL` | `1` | Только native PropertyManager |
| `COMPAS_FORCE_TOOL_PANEL` | `1` | Сразу боковая tool-панель |
| `COMPAS_REPO` | путь | Корень репозитория |
| `COMPAS_PYTHON` | путь | `python.exe` из venv |

## Сборка

```powershell
cd D:\учеба\ML_study\compas
git checkout features/vision
git pull origin features/vision
$env:COMPAS_REPO = (Get-Location).Path
$env:COMPAS_PYTHON = (Resolve-Path .\venv\Scripts\python.exe).Path
.\addon\install.ps1
```

Полностью закройте КОМПАС и откройте снова → **Панель AI CAD**.

## Интерфейс

- **Задача** — текст
- **Создать** / **Изменить** / **Сохранить** / **Очистить**
- **Статус** — короткий текст без traceback/SDK

## Проверка

1. Открыть 3D-деталь.
2. Панель сбоку или в PropertyManager — **модель видна**.
3. Создать простую деталь текстом.
4. **Изменить** без второго документа.

Удаление: `.\addon\uninstall.ps1`
