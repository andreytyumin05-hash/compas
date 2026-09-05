# Handoff for the next AI coding model

## Current branch / policy
- Repository: `andreytyumin05-hash/compas`
- Active development branch: **`features/vision` only**
- `main` is stable — do not modify
- Do not create additional branches

## Latest confirmed user-side state
- Add-In installer completed successfully on Windows: MSBuild, COM registration, TLB export/registration and KOMPAS AddIn registration all succeeded.
- User restarted/opened KOMPAS and can see AI CAD panel, but it is still a separate floating WinForms window over KOMPAS.
- This is considered incorrect UX. The project must not silently fall back to a top-level overlay anymore.
- User has set these environment variables before launching KOMPAS/Python:
  - `COMPAS_REPO=D:\учеба\ML_study\compas`
  - `COMPAS_PYTHON=D:\учеба\ML_study\compas\venv\Scripts\python.exe`
  - `COMPAS_BIN=D:\учеба\Bin`
  - `COMPAS_EXE=D:\учеба\Bin\kStudy.exe`
- `COMPAS_REPO` and `COMPAS_PYTHON` are explicitly consumed by the Add-In. `COMPAS_BIN`/`COMPAS_EXE` are inherited by child processes but were not previously wired into the bridge; inspect and wire them only where the runtime actually needs them.

## Latest implementation changes
1. `addon/csharp/PropertyManagerBackend.cs`
   - Reworked native initialization to use documented `IApplication::CreatePropertyManager(false)` — the standard KOMPAS PropertyManager.
   - Gets `PropertyTabs`, creates/reuses `AI CAD`, gets `PropertyControls`, adds `ksControlUserWindow` (47), then binds the WinForms HWND as the content.
   - This replaces the previous speculative `PropertyManager/CreateTab/AddControl` path.
   - Still uses late-bound COM because the project does not reference the KOMPAS type library at compile time.
   - The exact user-window handle binding remains a live KOMPAS-v23 verification point.

2. `addon/csharp/CompasAiCad.cs`
   - Removed the separate-window fallback completely.
   - If native PropertyManager integration fails, the Add-In now reports a clear error instead of opening a floating overlay.
   - When native hosting succeeds, the task box is focused immediately.
   - This is intentional: do not reintroduce the fake overlay as a fallback.

3. `agent/calculations.py`
   - Fixed a real Python syntax error in `_speed_rpm`: an invalid tuple construction caused `invalid syntax` around the calculations parser.
   - Commit containing this fix: `50c67ecf3b6137aa60ab394f3476e97b3838516b`.

## Official KOMPAS SDK facts used for the UI fix
- `CreatePropertyManager(FALSE)` accesses the standard KOMPAS-3D system PropertyManager; libraries can add their own tabs to it.
- `IPropertyManager.PropertyTabs` exposes the tab collection.
- `IPropertyControls.Add(ControlTypeEnum)` creates native PropertyManager controls.
- `ksControlUserWindow = 47` is an official v23 control type.
- Standard PropertyManager is the intended integrated UI; library-created panels otherwise have floating/side placement limitations.

## Known gaps — do not fake
| Item | Status |
|------|--------|
| Native PropertyManager panel | code changed to standard manager; needs rebuild + KOMPAS restart + visual confirmation |
| ksControlUserWindow HWND binding | late-bound; must be confirmed on actual KOMPAS v23 |
| Native PropertyManager events | not yet proven; current hosted WinForms buttons still execute through the embedded form |
| dim_linear / dim_radial live | smoke previously False; needs diagnostic output |
| shell / thread / loft / sweep / sketch_on_face | **unsupported** in ops_registry |
| fillet/chamfer edge selection | best_effort only |
| Edit path mutates open doc | code present; needs live test |
| GOST/ISO evidence web layer | trigger exists; not authoritative standards database |
| Long web/standards requests | previous user test appeared to stall ~7 min; enforce strict timeout/source budget |

## Immediate next test
After pulling/rebuilding the latest `features/vision`:
1. Close KOMPAS completely.
2. Pull branch and reinstall Add-In as Administrator.
3. Start KOMPAS normally.
4. Open `Панель AI CAD`.
5. **Expected:** AI CAD is a real tab/control inside KOMPAS PropertyManager. There must be no separate top-level AI CAD window.
6. If it still becomes a floating window, do not continue CAD tests; inspect the actual v23 `IPropertyUserWindow` interface/handle binding and COM event hookup.
7. Once embedded, first test the exact user request about the slow shaft, but standards lookup must have a strict time budget and must return explicit assumptions if GOST evidence is unavailable.

## User's current shaft test
```text
создай вал тихоходный, материал чугун, диаметры 45 40 45 и конический концевой участок 37 до 30 длина 20, могу ошибаться, посмотри госты концевых участков при начальном 37 (либо ближайший гостовский) длины 3-х наших диаметров соответственно 20 25 20
```
Interpretation must be explicit: preserve the requested 45/40/45 sequence, treat 37→30×20 as a tapered end unless standards lookup resolves a standard end, and do not silently invent dimensions. Material `чугун` is unusual for a shaft and should be flagged, not silently replaced.

## Environment limit
No live KOMPAS COM is available in this sandbox. Native KOMPAS behavior must be confirmed by the user on Windows.
