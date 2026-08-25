# Status + collaboration notes (Grok + OpenAI analysis)

**Branch:** `agent-v2`  
**See also:** `open_ai_solve` (full static analysis from the other LLM — they could not write to the repo: GitHub 403)

---

## Agreement between LLMs

| Topic | Conclusion |
|-------|------------|
| LLM / prompts / validate | Not the blocker for solids |
| COM attach (`GetActiveObject` 5 & 7) | Works |
| Creating new document (`Document3D` / `Documents.Add`) | **Broken** — `DISP_E_MEMBERNOTFOUND` / `NoneType not callable` |
| Next step | **Localize**: `from_active` → geometry → only then fix new-doc |
| Do not | Rewrite all of `core`, swap CAD, endless `Add(n)` without interface facts |

OpenAI correctly stressed: **A/B dynamic vs gencache**, **Python 3.12 control**, **bitness**, **no proof yet that gencache is the root cause**.

Grok applied that plan without architecture rewrite:

1. Expanded `python -m core.diagnose` — raw COM, dynamic probe, **gencache probe**, wrapper tests  
2. Added `python -m core.smoke_active` — sketch+extrude on **manually opened** Part  
3. `COMPAS_DEBUG_COM=1` logging in `operations.py`  
4. Runner text: «Статическая проверка» not «Проверка API»

---

## What YOU run now (order matters)

```powershell
git pull origin agent-v2
```

### 1) Environment
```powershell
python -c "import sys,platform,struct; print(sys.version); print(platform.architecture(), platform.machine()); print(struct.calcsize('P')*8)"
```
Expect **64-bit** Python if KOMPAS is 64-bit.

### 2) Full diagnose (KOMPAS running)
```powershell
python -m core.diagnose
```
Paste **entire** output into `responce.txt`.

Look especially at:
- `CALL Document3D()` / `CALL Add(...)` under **Raw**
- **A/B Test A** (dynamic) vs **A/B Test B** (gencache)
- `Part.from_active` at the end

### 3) Geometry without creating a document
In KOMPAS: **Файл → Создать → Деталь** (leave it active).

```powershell
python -m core.smoke_active
```

| Result | Meaning |
|--------|---------|
| SUCCESS + cylinder in UI | Feature API OK — only **new document** is broken |
| from_active FAIL | Binding/`ActiveDocument3D` still wrong |
| from_active OK, extrude FAIL | Fix `sketch.py` / `operations.py` next |

### 4) Optional control: Python 3.12 x64 venv
If diagnose still fails on create:
```powershell
py -3.12 -m venv venv312
.\venv312\Scripts\activate
pip install -r requirements.txt
python -m core.diagnose
```

---

## Success criteria

1. `smoke_active` builds a solid in the open part  
2. Then `Part.create` / `agent.build` creates a **new** part document without MEMBERNOTFOUND  
3. Only then invest in more features / Telegram UI

---

## Note for the other LLM

You could not push (403). Grok pushed diagnostics on `agent-v2`. After the user pastes new `responce.txt`, review **only** whether raw vs gencache vs dynamic differ, and whether `smoke_active` succeeded — then propose a **minimal** patch to document creation, not a full rewrite.
