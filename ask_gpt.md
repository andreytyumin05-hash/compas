# Handoff for the next AI coding model

## Current branch / policy
- Repository: `andreytyumin05-hash/compas`
- Active development branch: **`features/vision` only**
- `main` is stable — do not modify
- Do not create additional branches

## Confirmed offline (this pass)
- Full unittest suite green (36 tests, 1 skip) after fixing `agent/calculations.py`
- Bug: `_power_kw` / `_speed_rpm` passed a **string** to `_find` instead of a **1-tuple** (`(pattern)` ≠ `(pattern,)`), so `re.search` iterated characters → `missing ), unterminated subpattern`
- Added preliminary **bending + torsion** shaft sizing (`shaft_diameter_bending_torsion`) wired into `calculate_engineering`
- Tightened torque regex so plain «момент» does not steal «изгибающий момент»
- Engineering context hints expanded for Mb/Mt/bending

## Previously done (still valid, not re-live-tested here)
1. Create vs edit path (`run_edit_open_document`, `Part.from_active`, no `Part.create` in edit)
2. Live variables API: `part.variables()` / `part.set_variable(...)` (COM needs KOMPAS v23 confirmation)
3. Tree snapshot includes variables
4. Edit validation: `# COMPAS_EDIT_MODE`, one `from_active`, no create
5. Add-In PropertyManager / docked UI (C#) — **must rebuild on Windows**
6. Sketch dims/spline dual-path (`ko_LDimParam=45`, `tPar.Init(0)`, orientation `ps`) — **smoke False until user confirms**
7. Parametric templates use `part.param` / `part.p`
8. Contract emits `feature_order` / planes via `schema.spec_to_task_text`

## Known gaps (do not fake)
| Item | Status |
|------|--------|
| dim_linear / dim_radial live | smoke returned False earlier; needs diagnostic output from `scripts/smoke_dims.py` |
| shell / thread / loft / sweep / sketch_on_face | **unsupported** in ops_registry |
| fillet/chamfer edge selection | best_effort only |
| Add-In docked panel | code present; needs rebuild + KOMPAS restart |
| Edit path mutates open doc | code present; needs live test |
| GOST/ISO evidence web layer | trigger exists; not authoritative DB |

## Next priorities (ordered)
1. **Live dim smoke** — user runs `python scripts/smoke_dims.py`, pastes full diagnostic
2. **Rebuild Add-In** and verify docked UI + edit open document
3. **Revolve / spline** robustness for shafts and curved profiles
4. **Fillet/chamfer** via real edge predicates when COM proven
5. Expand calculations only with transparent units/assumptions
6. Keep UI messages concise (no Python/SDK dumps)

## User-side checklist
```powershell
cd D:\учеба\ML_study\compas
git checkout features/vision
git pull origin features/vision
.\venv\Scripts\activate
python -m unittest discover -s tests -v
python scripts\smoke_dims.py
```
Then: rebuild addon → restart KOMPAS → create part → «Изменить открытую» → change diameter via variables if possible.

## Environment limit
No live KOMPAS COM in this sandbox. Do not mark native features as working without user confirmation.
