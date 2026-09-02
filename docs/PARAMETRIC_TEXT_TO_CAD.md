# Text → parametric CAD (P0 priority)

Vision/photo is secondary.

## Flow
text → text_contract → LLM (part.param / part.p) → core → KOMPAS

## Parameters
`part.param("W", 100)` + `part.param("HOLE_OFFSET", expr="W/2")` → change W → HOLE_OFFSET follows (Python graph).

## Spline
`sk.spline(points)` uses API5 **ksBezier + ksPoint + ksEndObj** (not polyline). Live-test on v23 required.

## Honest limits
- Geometric constraints (horizontal/tangent): not claimed
- dim_linear/diameter: best-effort or explicit error; prefer part.param
- loft/sweep: unsupported
