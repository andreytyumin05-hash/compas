# CODEX / VS Code Agent Task — Fix KOMPAS-3D COM Part Access

You are a coding agent on the **user's Windows PC** with KOMPAS-3D v23 installed and running. Work in branch **`agent-v2`** of repo `compas`. Do **not** merge to `main`.

## Goal

Make this succeed while KOMPAS is open:

```powershell
python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
```

Expected: a new part appears in KOMPAS with a hollow cylinder (OD 40, ID 20, length 50 mm).

## Confirmed runtime facts (from `responce.txt`)

| Fact | Detail |
|------|--------|
| OS / Python | Windows, Python **3.14.0 x64** |
| pywin32 | OK |
| `GetActiveObject("Kompas.Application.5")` | OK |
| `GetActiveObject("Kompas.Application.7")` | OK |
| **`app7.Documents.Add(4, True)`** | **OK** — document creation works |
| `Documents.Add` / `AddWithDefaultSettings` | methods exist |
| `gencache.EnsureModule` | **FAIL** — `Библиотека не зарегистрирована` (typelib **not registered**) |
| `App5.Document3D()` as method call | FAIL `DISP_E_MEMBERNOTFOUND` (-2147352573) |
| `App5.ActiveDocument3D` getattr | returns CDispatch; **calling `()` fails** MEMBERNOTFOUND |
| `TopPart` on ActiveDocument | often fails without proper interface |
| LLM code generation | OK — not the bug |

**Root problem:** After `Documents.Add(4, True)`, code cannot obtain a usable **`ksPart` / TopPart** COM object. Typelib is unregistered, so `CastTo` / `EnsureModule` / generated wrappers are unreliable. Must use late binding and the **document object returned by `Add`**.

## Files to fix (priority)

1. `core/connection.py` — create document + extract part  
2. `core/part.py` — `from_active` / `create`  
3. Only if part is obtained: `core/sketch.py`, `core/operations.py`

Do **not** rewrite the LLM agent unless COM works.

## Required approach

1. Prefer:
   ```python
   doc = app7.Documents.Add(4, True)  # proven OK
   part = <extract from doc>
   ```
2. Extraction attempts on `doc` (and `ActiveDocument`):
   - `doc.TopPart`
   - `doc.GetPart(-1)`
   - nested `Document3D` / property access **without** forcing `()` if property already returns dispatch
3. Never require gencache/typelib registration as the only path.
4. Optional environmental fix (if late binding cannot get TopPart):
   - Register KOMPAS type libraries / install SDK for this KOMPAS version
   - Or document how user registers typelib
5. After part works, verify:
   ```python
   part.NewEntity(5)  # sketch
   # GetDefinition, SetPlane, BeginEdit, ksCircle, EndEdit
   part.NewEntity(24)  # base extrusion
   # SetSketch, SetSideParam, Create
   ```

## Success checks (run yourself in terminal)

```powershell
# KOMPAS running
python -m core.diagnose

python -c "from core import Part; p=Part.create('T'); print('create OK', p)"

python -m core.smoke_active
# (or create empty part in UI first if from_active still needed)

python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
```

## Out of scope

- Telegram bot, GUI, Apple, rewriting prompts, changing CAD product
- Merging to `main`

## Context files

- `responce.txt` — latest diagnose log  
- `WHAT_YOU_NEED_TO_DO.md` — collaboration notes  
- `core/*` — implementation  

Ship a **minimal** patch that obtains `Part` after `Documents.Add(4, True)` and builds a solid.
