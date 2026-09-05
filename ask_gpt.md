# Handoff for the next AI coding model

## Current branch / policy
- Repository: `andreytyumin05-hash/compas`
- Active development branch: **`features/vision` only**
- `main` is stable — do not modify
- Do not create additional branches

## Confirmed in this pass
- Windows installer was actually run from an elevated `cmd.exe` and reached MSBuild successfully.
- Visual Studio/MSBuild path is valid: `D:\VS_INST\PROGRAM\MSBuild\Current\Bin\MSBuild.exe`.
- The Add-In build failed only because `PositionBesideKompas(Form form)` accessed `Form.PreferredWidth` / `Form.PreferredHeight`, which do not exist on WinForms `Form`.
- Fixed `addon/csharp/CompasAiCad.cs` to use the already initialized `Form.Width` / `Form.Height` values instead.
- Commit: `cc000c4538b6995fae5fa679d3c3c324710c23d0`.

## Previously done (still valid, not live-verified here)
1. Create vs edit path (`run_edit_open_document`, `Part.from_active`, no `Part.create` in edit generation/validation)
2. Live variables API: `part.variables()` / `part.set_variable(...)` (KOMPAS v23 still requires live confirmation)
3. Tree snapshot includes variables
4. Edit validation: `# COMPAS_EDIT_MODE`, one `from_active`, no create
5. Add-In PropertyManager integration probe exists in C# (`PropertyManagerBackend.cs`)
6. Sketch dims/spline dual-path (`ko_LDimParam=45`, `tPar.Init(0)`, orientation `ps`) — smoke False until user confirms
7. Parametric templates use `part.param` / `part.p`
8. Contract emits `feature_order` / planes via `schema.spec_to_task_text`

## Important UI status
- `CompasAiCad.cs` still contains a WinForms fallback path when native PropertyManager initialization fails.
- Therefore the native/docked panel is **not yet proven** on the user's KOMPAS v23 installation.
- Do not describe the panel as fully native/docked until the user confirms it visually after rebuild/restart.
- `COMPAS_NATIVE_PROPERTY_PANEL=1` remains a diagnostic switch in the current code; it is not intended as the final UX.

## Known gaps (do not fake)
| Item | Status |
|------|--------|
| dim_linear / dim_radial live | smoke returned False earlier; needs diagnostic output from `scripts/smoke_dims.py` |
| shell / thread / loft / sweep / sketch_on_face | **unsupported** in ops_registry |
| fillet/chamfer edge selection | best_effort only |
| Add-In native docked panel | **needs fresh rebuild + KOMPAS restart + visual confirmation** |
| Edit path mutates open doc | code present; needs live test |
| GOST/ISO evidence web layer | trigger exists; not an authoritative standards database |
| Long web/standards requests | must have strict timeout/budget; previous user test appeared to stall for ~7 minutes |

## Next priorities (ordered)
1. Rebuild Add-In and verify whether the panel is truly integrated into KOMPAS rather than a separate WinForms window.
2. Verify create → edit on the same active document and confirm active-document identity is unchanged.
3. Add native feature resolver/mutation for real edits such as `diameter 30 -> 35` instead of reconstructing the part.
4. Verify revolve/spline robustness for shafts and curved profiles.
5. Harden standards/GOST web lookup with strict timeout, source limit, one retry maximum, and explicit fallback/assumption reporting.
6. Clean `docs` / `knowledge` and remove stale or misleading implementation notes only after auditing references.

## Exact user-side test after pulling this commit
```powershell
cd D:\учеба\ML_study\compas
git checkout features/vision
git pull origin features/vision
.\venv\Scripts\activate
```
Then from an **Administrator cmd.exe**:
```cmd
cd /d "D:\учеба\ML_study\compas"
venv\Scripts\activate
powershell -ExecutionPolicy Bypass -File ".\addon\install.ps1"
```
If the build succeeds: completely restart KOMPAS-3D and open `Панель AI CAD`.
First report only whether the panel is inside/docked in KOMPAS or appears as a separate floating window. Then test:
```text
создай цилиндр диаметром 50 длиной 100
```
followed by:
```text
измени диаметр на 60
```

## Environment limit
No live KOMPAS COM is available in this sandbox. Native KOMPAS behavior must be confirmed by the user on Windows.
