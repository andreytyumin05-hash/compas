# KOMPAS AI CAD Add-In

Integration layer for the `features/vision` branch.

## Architecture

```text
KOMPAS-3D v23
    |
    +-- AI CAD Add-In (addon/csharp)
    |      |
    |      +-- native IPropertyManager backend (capability-driven)
    |      +-- proven WinForms fallback UI
    |      +-- task/edit/save commands
    |      +-- Python process bridge
    |
    +-- addon/bridge.py
           |
           +-- agent.build.run_task_export()
                  |
                  +-- live active-document context
                  +-- latest model context
                  +-- engineering calculation / standards research
                  +-- core -> KOMPAS COM
```

The add-in no longer treats the Win32 child panel as the only UI architecture. A native `IApplication::CreatePropertyManager(...)` backend is now present and integrated behind a capability probe. Because the exact Automation surface exposed by a user's local KOMPAS v23 installation is not available to this repository at build time, the native backend is opt-in and falls back to the known-working panel instead of risking a broken add-in.

The native backend can be tested with:

```powershell
$env:COMPAS_NATIVE_PROPERTY_PANEL = "1"
```

Then restart KOMPAS and open **Панель AI CAD**. On a machine where the v23 Automation members match the supported signatures, the add-in will use the native property-manager backend. Otherwise it silently keeps the stable WinForms panel.

## Build

Requirements on the Windows machine:

- KOMPAS-3D v23 x64.
- Visual Studio 2022 with the `.NET Framework 4.8` developer pack.
- Existing Python environment for this repository.

From PowerShell in the repository root:

```powershell
$env:COMPAS_REPO = (Get-Location).Path
$env:COMPAS_PYTHON = (Get-Command python).Source
.\addon\install.ps1
```

The installer builds `addon/csharp/CompasAiCad.csproj`, registers the COM assembly with `RegAsm`, and creates:

`HKCU\Software\ASCON\KOMPAS-3D\AddIns\CompasAiCad`

with `ProgID=CompasAiCad.Panel`, `AutoConnect=1`.

## Current edit workflow

1. Open the target **3D Деталь** in KOMPAS-3D.
2. Open **AI CAD**.
3. Create a model normally, or open an existing `.m3d` made elsewhere.
4. For a change, press **Изменить открытую** and describe the delta in ordinary language, e.g. `увеличь длину шейки до 140 мм и перенеси отверстие на ось симметрии`.
5. Before generation, the agent reads the active KOMPAS document and a best-effort feature-tree snapshot, then combines it with the latest saved generated script/context.
6. Edit scripts are required to use exactly one `Part.from_active()` and must not create a second `Part` document.
7. After a successful edit, the latest context is replaced; older generated contexts are not retained.

This makes an open KOMPAS document a first-class edit target. It does not yet guarantee that every arbitrary pre-existing native KOMPAS feature can be edited parametrically: the agent can only modify what the current core API can address. Native KOMPAS variable/constraint binding remains a separate compatibility layer under `core/params.py`.

## Engineering context

Technical standard-related tasks can trigger web research through `agent/web_search.py`; calculation-driven tasks can use `agent/calculations.py`. Research is advisory and numeric standard values are never supposed to be invented when the source context does not establish them.

## Important design choice

The add-in does not duplicate the CAD kernel. `agent/`, `core/`, vision, validation, repair and KOMPAS COM operations remain the single source of truth.
