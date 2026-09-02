# Vision -> CAD pipeline

## Pipeline

`drawing image -> vision JSON -> normalize_spec() -> CAD_CONTRACT v2 -> code generation -> AST validation -> structural/LLM critic -> KOMPAS execution -> export`

The vision stage and code-generation stage must not communicate through free-form prose. The shared contract is `agent/contract.py`.

## Supported modelling operations

### Base/additive
- `sketch()` on `xy/xz/yz`
- `circle`, `rectangle`, `rounded_rect`, `stadium`, `polygon`, `line`, `arc`, `ellipse`, `slot`
- `extrude`
- `step`
- `boss`
- `hex_boss`
- `revolve`

### Cuts
- `cut`
- `hole`
- `pattern_holes_circular`
- `pattern_holes_rect`
- `pattern_holes_linear`
- `pattern_holes_points`
- `hole_list`
- `pocket`
- `ring_groove` / `groove`
- `keyway`
- `slot`
- `counterbore`
- `countersink` (currently geometric approximation, not a true conical KOMPAS feature)

### Edge finishing
- `get_edges`
- `fillet`
- `chamfer`

### Drawing dimensions
- `sk.dim_radial()`
- `sk.dim_linear()`
- `sk.dim_rect()`

Dimension functions are best-effort annotations in the current core. Generated scripts also expose important values as named Python variables (`D_BASE`, `L_BASE`, etc.), which makes regeneration/editing deterministic.

## Deliberately unsupported

- `loft()` and `sweep()` are rejected by the code validator because the current core does not implement them.
- `shell()` and `thread()` exist only as compatibility placeholders and must not be treated as real modelling operations.
- Full API7 external variables / constraints are not yet wired into the core. Do not claim that a `dim_*` call alone creates a fully constrained parametric sketch.

## Vision interpretation rules

- visible thick contours -> solid material
- dashed/hidden contours -> internal/hidden geometry only
- centerlines -> axes, symmetry or PCD reference only
- dimension lines -> numbers only

The canonical contract preserves `unknown_dimensions` instead of guessing unreadable values.
