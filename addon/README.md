# KOMPAS AI CAD Add-In

Native KOMPAS integration layer for the `features/vision` branch.

The add-in is a COM/ActiveX KOMPAS library written in C#/.NET Framework 4.8. KOMPAS loads it through the AddIns registry entry. The add-in exposes an **AI CAD** command and embeds a borderless WinForms panel into the KOMPAS main window. The panel is intentionally thin: all CAD/LLM logic stays in the existing Python agent.

## Architecture

```text
KOMPAS-3D v23
    |
    +-- AI CAD Add-In (addon/csharp)
    |      |
    |      +-- embedded panel
    |      +-- task/edit/save commands
    |      +-- launches Python bridge
    |
    +-- addon/bridge.py
           |
           +-- agent.build.run_task_export()
                  |
                  +-- core -> KOMPAS COM -> active .m3d
```

KOMPAS officially supports ActiveX libraries, `ExternalRunCommand`, API7 negotiation and custom property panels. The current implementation uses the supported ActiveX library route but hosts a real Win32 child panel in the KOMPAS window so the UI can use ordinary WinForms controls without making the CAD core depend on .NET UI APIs.

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

If the environment variables are omitted, the installer uses the current repository and the first `python.exe` found on PATH.

## First launch

1. Close KOMPAS-3D.
2. Run `addon/install.ps1` as a normal user.
3. Start KOMPAS-3D v23.
4. Open a 3D part document.
5. Open the library menu and choose **AI CAD / Панель AI CAD**.
6. Enter a Russian or English engineering description and press **Создать**.
7. The add-in writes the task to a temporary UTF-8 file and starts the existing Python agent. The result is saved as `.compas_tmp/latest_model.m3d`.

## Important design choice

The add-in does not duplicate the CAD kernel. `agent/`, `core/`, vision, validation, repair and KOMPAS COM operations remain the single source of truth. This prevents the native UI from becoming a second CAD implementation.

The add-in also does not claim native KOMPAS parameterization by itself. Native variable/dimension binding remains the responsibility of `core/params.py` and the generated KOMPAS sketches/features.
