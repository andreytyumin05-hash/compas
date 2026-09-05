# Handoff for the next AI coding model

## Current branch / policy
- Repository: `andreytyumin05-hash/compas`
- Active development branch: `features/vision`
- `main` is stable and must not be modified.
- Do not create additional branches.

## What was done in this stage

### 1. Active-document edit path was separated from creation
- `agent/build.py` now has a strict create/edit split.
- Added `run_edit_open_document(...)`.
- Edit execution requires the active KOMPAS 3D document and uses `Part.from_active()`.
- Edit code is forbidden from calling `Part.create()`.
- Edit output is saved only after the active document has been modified successfully.
- The current active document name is checked before/after the edit as a safety guard.
- `addon/bridge.py` now routes `edit` directly to `run_edit_open_document()` instead of treating edit as a normal export task.

### 2. Live KOMPAS variables are now exposed to the Python core
- `core/params.py` now has:
  - `list_kompas_variables(part)`
  - `set_kompas_variable(part, name, value=..., expression=...)`
  - safe variable collection iteration helpers.
- `core/__init__.py` exposes:
  - `part.variables()`
  - `part.set_variable(...)`
- The goal is to modify existing KOMPAS variables instead of rebuilding geometry when the user's request is a parameter change.
- IMPORTANT: exact native COM behavior still requires live KOMPAS v23 testing.

### 3. Model snapshot now includes live variable information
- `agent/tree_snapshot.py` includes model variables alongside feature-tree information.
- Edit prompts therefore receive both the current tree and available live variables.

### 4. Prompt/validation rules were strengthened
- `agent/prompts.py` documents `part.variables()` and `part.set_variable(...)`.
- Edit-mode rules explicitly prefer mutation of an existing variable.
- `agent/validate.py` recognizes `variables` and `set_variable`.
- Edit scripts are required to have `# COMPAS_EDIT_MODE`, exactly one `Part.from_active()`, and no `Part.create()`.

### 5. Add-In UI architecture was changed
The old WinForms window used to sit on top of KOMPAS and obstruct the CAD workspace. This is no longer the intended UI architecture.

- `addon/csharp/PropertyManagerBackend.cs` now targets KOMPAS `IPropertyManager` and creates a `ksControlUserWindow` (control type 47).
- The existing WinForms surface is intended to be hosted inside that KOMPAS property panel, not as a floating overlay.
- `addon/csharp/CompasAiCad.cs` now opens the native property panel as the normal path.
- Automatic fallback to the old floating overlay was removed.
- The Add-In UI no longer displays raw Python stdout/stderr.
- The C# side parses the final JSON result and only shows a compact status such as `Готово.` / `Модель обновлена.` / a concise error.
- `addon/csharp/CompasAiCad.csproj` references `System.Web.Extensions` for compact JSON parsing.

### 6. Existing engineering layer remains active
- Engineering calculations: `agent/calculations.py`.
- Standards/technical web research: `agent/web_search.py` + `agent/engineering_context.py`.
- Legacy `google.generativeai` usage was removed earlier; project uses `google-genai`.
- `ddgs` is used for technical/standards research triggers.

## What remains to be finished

### A. Native KOMPAS property panel needs real v23 verification
This is the most important immediate test.

The current implementation uses late-bound COM and probes possible host-window handle properties/methods because the exact local `IPropertyUserWindow` Automation surface has not been live-tested in this environment.

Need to verify on the user's KOMPAS-3D v23:
1. `CreatePropertyManager(false)` succeeds.
2. `PropertyTabs.Add("AI CAD")` succeeds.
3. `PropertyControls.Add(47)` succeeds.
4. The WinForms handle can actually be hosted in `IPropertyUserWindow`.
5. The panel docks correctly without covering the modeling workspace.
6. Closing/reopening KOMPAS does not leak the property manager or child window.

Do not reintroduce a floating overlay as the normal solution.

### B. Native panel interactions should become fully KOMPAS-native where practical
The current hosted WinForms surface solves the physical UI placement problem, but the next architectural improvement should be to use native KOMPAS property controls/events where useful:
- text editor
- text buttons
- status field
- mode selector
- parameter grid
- eventually `IPropertyManagerNotify` event handling

Use official KOMPAS v23 SDK behavior rather than guessed signatures whenever possible.

### C. Active-document editing is structurally prepared but not yet a full feature mutator
Current code can target `Part.from_active()` and can change existing model variables where the variables are exposed.

Still needed:
- robust feature resolver: map user language (`шейка`, `ступень`, `отверстие`, `канавка`, `фланец`, etc.) to actual KOMPAS features/objects;
- robust native feature parameter mutation (extrusion length, revolve profile dimensions, hole diameter/depth, chamfer/fillet values, etc.);
- preserve feature dependencies and rebuild only what is affected;
- reject accidental creation of a second document;
- verify document identity more reliably than just comparing name.

The desired behavior is:
`open detail -> AI reads live model -> user says “изменить X” -> existing feature/variable changes -> KOMPAS rebuilds -> visual verification -> latest context replaced.`

### D. Native parametric relationships still need live KOMPAS implementation
The Python `ParamStore` is not enough by itself.

Need a verified native workflow for:
- variables
- dimension constraints
- expressions
- dependency graph
- rebuild

Target example:
`W=100`, hole at `W/2` -> change `W=140` -> hole moves from 50 to 70 automatically.

Do not claim this works until tested inside KOMPAS v23.

### E. CAD core cleanup / single source of truth
`core/ops_registry.py` exists, but additional duplicate capability lists/helpers still need to be removed where possible.

In particular:
- derive validation from the registry instead of maintaining duplicate method allowlists;
- remove misleading dead/stub methods in `core/part.py` that conflict with registry/runtime behavior;
- keep unsupported operations (`shell`, `thread`, `loft`, `sweep`, real face-based sketching) explicitly unsupported until real implementations exist.

### F. Complex CAD operations need to be upgraded
Priority:
1. revolve robustness for shafts/fittings/turned bodies;
2. real spline/Bezier profiles;
3. native face selection;
4. robust fillet/chamfer selection;
5. thread geometry;
6. sweep;
7. loft;
8. shell.

For blades especially, spline/Bezier geometry must remain real curve geometry and not be replaced with polyline approximations.

### G. Standards resolver should become evidence-based
Current web search is a useful trigger, but exact standards work should prefer authoritative sources and retain traceability.

Need:
- authoritative GOST/ISO/DIN lookup where possible;
- extract exact supported dimensions/requirements;
- preserve standard identifier and source in engineering context;
- never invent missing standard dimensions.

### H. Engineering calculation layer should expand
Current deterministic calculation support includes shaft torsion diameter and power/speed -> torque.

Potential next modules:
- combined bending + torsion;
- shaft stress/concentration checks;
- bearing life;
- bolts;
- keys/splines;
- gears;
- preliminary fits.

Every formula should expose units and assumptions and should not be presented as certified design.

### I. UI output / diagnostics policy
The user explicitly does not want internal logs such as:
- model loading details;
- Python imports;
- SDK warnings;
- host/provider messages;
- raw stdout/stderr.

Normal UI must show only a concise human result.
Detailed diagnostics should be available only through an explicit developer/diagnostic mode.

### J. `ask_gpt.md` policy
This file is the persistent handoff between coding AIs.

Every substantive implementation pass must update this file with:
1. what was changed;
2. what is confirmed vs. not live-tested;
3. known bugs/regressions;
4. what should be done next;
5. any exact user-side tests required.

Keep it technical and selective. Do not copy the whole repository or dump arbitrary logs.

## Immediate user-side verification after rebuilding the Add-In

1. Checkout and update `features/vision`.
2. Rebuild/reinstall `addon` because C# changed.
3. Restart KOMPAS-3D v23 completely.
4. Open a 3D part.
5. Launch `AI CAD`.
6. Confirm the AI CAD UI is docked inside KOMPAS property area and no floating overlay appears.
7. Create a simple stepped shaft/part.
8. Without closing the part, use `Изменить открытую` and request an additive change such as a through hole.
9. Then request a parameter change such as changing an existing diameter.
10. Confirm that the original document changes instead of a second document appearing.
11. Confirm that the UI contains only concise statuses, not internal Python/GPT logs.

## Known limitation
The repository can be inspected and edited here, but KOMPAS-3D itself is not available for live COM execution in this environment. Therefore native property-panel hosting and real feature mutation must be confirmed on the user's Windows/KOMPAS v23 installation.
