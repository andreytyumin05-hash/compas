# WHAT_YOU_NEED_TO_DO — status for humans + collaborating LLMs

**Branch:** `agent-v2` (do not merge to `main` without review)  
**Repo:** `andreytyumin05-hash/compas`  
**CAD:** KOMPAS-3D v23 on Windows  
**Python:** 3.14 + pywin32 in venv  
**Goal:** Text description → LLM generates Python using `core.Part` API → execute against running KOMPAS via COM and build a solid body.

Two agents work in this repo (Grok + another LLM via GitHub). Read this file + `responce.txt` + `core/connection.py` before changing COM code.

---

## 1. What already works

| Layer | Status |
|-------|--------|
| LLM code generation (`agent.runner`) | OK with models that accept the key (e.g. Qwen on Groq, or Gemini) |
| Generated scripts for bushing/flange | Correct high-level API (`Part.create`, `sketch`, `circle` with **radius**, `extrude`, `cut through_all`) |
| API validation (`agent.validate`) | OK |
| COM: process attach | OK — `GetActiveObject("Kompas.Application.5")` and `.7` both succeed |
| COM: create part + extrude | **FAILING** (see below) |

High-level wrapper API (do not invent other classes):

```python
from core import Part
part = Part.create("Name")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 20)   # radius mm, not diameter
part.extrude(sk, depth=50)
with part.sketch("xy") as sk2:
    sk2.circle(0, 0, 10)
part.cut(sk2, through_all=True)
```

---

## 2. Full problem statement (COM)

### Symptom
`python -m agent.build "..."` generates valid code then fails when creating a part:

```text
(-2147352573, 'Член группы не найден.', None, None)
# HRESULT 0x80020003 DISP_E_MEMBERNOTFOUND
```

Earlier variants also showed:
- `Property '<unknown>.Name' can not be set` on TopPart (API7 late binding without proper interface)
- Empty part document opened in UI, no solid features

### Diagnose output (authoritative, in `responce.txt`)

```text
Kompas.Application.5:
  GetActiveObject OK
  .Visible OK
  .Document3D getattr OK → CDispatch
  .ActiveDocument3D → None  (no active 3D doc)
  .Documents FAIL
  .ApplicationName FAIL

Kompas.Application.7:
  GetActiveObject OK
  .Documents OK
  .Document3D FAIL
  .ActiveDocument3D FAIL

new_part_document FAIL:
  API5 Document3D: DISP_E_MEMBERNOTFOUND
  API7 Add(1): 'NoneType' object is not callable
  API7 Add(4): DISP_E_MEMBERNOTFOUND
  API7 Add(5): DISP_E_MEMBERNOTFOUND
  ActiveDocument3D: DISP_E_MEMBERNOTFOUND
```

### Interpretation

1. **App5** is the modeling object (`Document3D` exists as a COM member on the dispatch map for getattr, but **invoking** create path fails with MEMBERNOTFOUND). This often happens when:
   - `gencache.EnsureModule` / `QueryInterface` produced a **wrong or stale typelib wrapper** for this KOMPAS build
   - or the method needs a different calling convention than early-bound wrappers assume

2. **App7** exposes `Documents` (document manager) but not `Document3D`. Creating a part must go through `Documents.Add` / `AddWithDefaultSettings`, then modeling via API5 `ActiveDocument3D().GetPart(-1)` or API7 `TopPart` with correct interface.

3. Mixing **CastTo / EnsureModule** previously caused `makepy` errors (`This COM object can not automate the makepy process`). Pure late binding is required on this machine.

4. LLM / agent side is **not** the blocker for solid geometry anymore; **COM document+feature creation** is.

### Reference patterns that work on other PCs (ASCON / Habr)

**API5 classic:**
```python
kompas = Dispatch("Kompas.Application.5")  # preferably dynamic
doc = kompas.Document3D()
doc.Create(False, True)   # visible, part
part = doc.GetPart(-1)    # pTop_Part
sketch = part.NewEntity(5)  # o3d_sketch
defn = sketch.GetDefinition()
defn.SetPlane(part.GetDefaultEntity(1))  # XOY
sketch.Create()
doc2d = defn.BeginEdit()
doc2d.ksCircle(0, 0, 20, 1)
defn.EndEdit()
feat = part.NewEntity(24)  # o3d_baseExtrusion for first feature
# SetSideParam / SetSketch / Create
```

**API7 hybrid:**
```python
app7.Documents.Add(4, True)  # or AddWithDefaultSettings(ksDocumentPart, True)
# then API5 ActiveDocument3D().GetPart(-1)
```

Constants commonly used: `o3d_sketch=5`, `o3d_baseExtrusion=24`, `o3d_bossExtrusion=25`, `o3d_cutExtrusion=26`, `pTop_Part=-1`.

---

## 3. What Grok already changed (history for the other LLM)

1. High-level `core` + `agent` (prompts, validate, build).  
2. Removed hard `CastTo` after makepy error.  
3. Tried API7 collections (`Sketchs`, `Extrusions`) → MEMBERNOTFOUND.  
4. Switched modeling to API5 `NewEntity` + `ksCircle`.  
5. Document create still failed on `Document3D()` / `Documents.Add`.  
6. Tried `gencache` + `QueryInterface` for KompasObject — diagnose still failed on invoke.  
7. **Latest (this commit):** `core/connection.py` rewritten to use **only** `win32com.client.dynamic.Dispatch`, no EnsureModule for Application; try API7 Add variants first, then API5 Document3D, then attach to active part; richer errors + workaround via `Part.from_active()`.

Files that matter for the COM bug:
- `core/connection.py` — attach + create document/part  
- `core/part.py` — NewEntity sketch  
- `core/sketch.py` — BeginEdit / ksCircle  
- `core/operations.py` — baseExtrusion / cut  
- `core/diagnose.py` — run on user PC  
- `responce.txt` — latest user terminal log  

Do **not** “fix” by inventing non-existent Python APIs for the agent. Fix COM in `core/*`.

---

## 4. Suggested next experiments (for any LLM)

1. Run updated `python -m core.diagnose` after pull; paste full output to `responce.txt`.  
2. If `Documents.Add*` still MEMBERNOTFOUND under **dynamic** dispatch, try invoking via `app7._oleobj_.Invoke(...)` only as last resort; better check KOMPAS installation: API/SDK option, bitness match (64-bit KOMPAS + 64-bit Python).  
3. **Manual workaround path:** User creates empty Part in UI → `Part.from_active()` → sketch/extrude only. If that works, isolate bug to document creation, not feature API.  
4. Clear pywin32 gen_py cache: delete `%LOCALAPPDATA%\Temp\gen_py` or `win32com\gen_py` folder, retry.  
5. Confirm Python **architecture** matches KOMPAS (both x64). Python 3.14 is very new — if COM stays broken, test one 3.11/3.12 x64 venv.  
6. Optional: install/register KOMPAS SDK / “КОМПАС-Макро” components if missing.

---

## 5. What the human should check (checklist)

Copy results into `responce.txt`:

- [ ] `git checkout agent-v2 && git pull origin agent-v2`
- [ ] KOMPAS-3D **running** before commands
- [ ] `python -m core.diagnose` — full console output
- [ ] Python bitness: `python -c "import struct; print(struct.calcsize('P')*8)"` → expect **64**
- [ ] KOMPAS bitness: Task Manager → KOMPAS → 64-bit?
- [ ] Manual: in KOMPAS create **Деталь** (empty part), leave it active, then:
  ```powershell
  python -c "from core import Part; p=Part.from_active(); print('from_active OK')"
  ```
- [ ] If `from_active OK`, run a minimal feature test:
  ```powershell
  python -c "from core import Part; p=Part.from_active(); s=p.sketch('xy'); s.circle(0,0,20); p.extrude(s,50); print('feature OK')"
  ```
- [ ] Optional: delete gen_py cache, retry diagnose
- [ ] Optional: try venv with Python **3.11 or 3.12** x64 if 3.14 COM keeps failing

---

## 6. Message to the other LLM

**Please:**
1. Treat `responce.txt` + this file as source of truth.  
2. Prefer minimal patches to `core/connection.py` (document/part acquisition).  
3. Avoid reintroducing `CastTo` / `gencache.EnsureModule` for Application unless you also handle makepy failure.  
4. Keep agent prompts aligned with real `core` API.  
5. If you change COM, ask the user to re-run `python -m core.diagnose` and `Part.from_active()` tests.  
6. Success criteria: `Part.create` or `Part.from_active` + extrude produces a non-empty solid in KOMPAS UI.

**Grok’s current hypothesis:** invoke failures are typelib/cache or document-create API mismatch on this install; dynamic dispatch + API7 Add + attach-to-active-part is the most likely fix path; if Add still fails, bitness/Python 3.14/SDK install is the environmental cause.
