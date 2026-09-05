"""Prompts for deterministic text/vision to parametric KOMPAS CAD."""

from .knowledge import load_patterns
from .memory import few_shot_from_memory, latest_edit_context

_API = '''
## ONLY supported core API
from core import Part
part = Part.create("Name")

# Named parameters. Critical dimensions must be named; derived positions use expressions.
part.param("W", 100)
part.param("HOLE_X", expr="W/2")
W = part.p("W")
HOLE_X = part.p("HOLE_X")

with part.sketch("xy") as sk:
    sk.circle(x, y, radius)
    sk.rectangle(x, y, width, height)
    sk.rounded_rect(x, y, width, height, radius)
    sk.stadium(x, y, length, width)
    sk.polygon([(x1,y1), (x2,y2), ...], closed=True)
    sk.line(x1,y1,x2,y2)
    sk.arc(x1,y1,x2,y2,x3,y3)
    sk.slot(x1,y1,x2,y2,width)
    sk.spline([(x1,y1), (x2,y2), (x3,y3), ...], closed=False, smooth=True)
    sk.bezier([(x1,y1), (x2,y2), (x3,y3), ...], closed=False, smooth=True)
    sk.dim_radial(x, y, radius)
    sk.dim_linear(x1,y1,x2,y2)
    sk.dim_rect(x,y,width,height)
part.extrude(sk, depth=H)
part.cut(sk, depth=D, through_all=False)
part.cut(sk, through_all=True)
part.revolve(sk, angle=360)
part.hole(x,y,diameter=D,through_all=True)
part.hole(x,y,diameter=D,depth=H,through_all=False)
part.pattern_holes_circular((cx,cy), pcd=P, count=N, diameter=D)
part.pattern_holes_linear((x,y), count=N, step=S, diameter=D)
part.pattern_holes_points([(x,y),...], diameter=D)
part.pattern_holes_rect(x1,y1,x2,y2,diameter=D)
part.hole_list([(x,y),...], [D1,D2,...])
part.boss(x,y,diameter=D,height=H)
part.hex_boss(x,y,diameter=D,height=H)
part.pocket(x,y,diameter=D,depth=H)
part.ring_groove(x,y,outer_diameter=Do,inner_diameter=Di,depth=H)
part.counterbore(x,y,pilot_diameter=Dp,counterbore_diameter=Db,counterbore_depth=Hb,through_all=True)
part.countersink(x,y,pilot_diameter=Dp,countersink_diameter=Ds,depth=H)
part.keyway(x,y,length=L,width=W,depth=D)
part.slot(x1,y1,x2,y2,width=W,through_all=True)
edges = part.get_edges("all")
part.fillet(edges, radius=R)
part.chamfer(edges, distance=D)
part.update()
'''

_RULES = '''
## Hard rules
1. Output exactly one Python fenced block. No prose inside the block.
2. Start with `from core import Part` and finish with `part.update()`.
3. Treat the CAD_CONTRACT as authoritative. Preserve every explicit feature, dimension and dependency.
4. Build in dependency order: base -> added material -> cuts -> patterns -> finishing -> update.
5. Every requested feature must map to a real supported core operation. Never silently omit a feature.
6. For a turned/axisymmetric part (shaft, axle, spindle, plug, fitting, turned bushing/body), PREFER ONE longitudinal half-profile + `part.revolve(...)` over a stack of independent circles/extrudes. Use separate additive extrusions only when the contract clearly requires non-axisymmetric material.
7. For a revolved shaft, draw the radial profile in a plane containing the rotation axis and make the profile describe the complete stepped outer contour. Do not model each shaft diameter as an unrelated cylinder if one profile can represent the turning operation.
8. Repeated holes use pattern operations whenever they share diameter/placement logic.
9. For a through hole/cut use `through_all=True`. Do NOT use `both_directions=True` as a synonym for through-all.
10. A dashed/hidden/center line is reference information, never outer solid geometry.
11. Never invent a missing dimension. Preserve unknown dimensions as unknown and do not guess.
12. Never call win32com/Dispatch/GetActiveObject/loft/sweep from generated code.
13. shell, thread and sketch_on_face are unsupported in the current core and MUST NOT be generated.
14. Important dimensions must be named with `part.param(name, ...)` and geometry should use `part.p(name)` rather than duplicated literals.
15. Derived positions must be expressed from parameters when a mechanical relation is stated. Example: `part.param("HOLE_X", expr="W/2")`.
16. Do not use a polyline as a substitute for a spline. `sk.spline`/`sk.bezier` must remain a real Bezier operation.
17. Put dimension calls close to the geometry they describe. Use diameter dimensions for circles and linear dimensions for lengths/offsets.
18. Dimension/constraint creation may be best-effort until the exact local API is confirmed, but never replace a requested dimension with a comment pretending that a dimension exists.
19. A sketch should be deliberately constrained: origin/axis placement, symmetry, tangency, coincidence and key dimensions where applicable. Avoid a cloud of arbitrary absolute coordinates.
20. If the user asks to edit an existing model, preserve the existing design intent and parameter names whenever they are available in the latest model context.
'''

_ORDER = '''
## Geometry strategy
- First determine the design intent: body type, primary axis, sections, cuts, and edge finishing.
- For axisymmetric turned parts, the default strategy is: one longitudinal profile sketch -> revolve 360° -> cuts -> grooves/holes -> edge finishing.
- Use a revolved profile for stepped shafts, plugs, turned fittings and similar rotational bodies. The profile should include all diameter transitions, shoulders and chamfers that can be represented in the turning profile.
- For a curved blade-like profile, build a real closed sketch from spline/arc/line segments and keep control points parameter-driven. Do not approximate a spline with many line segments.
- Use cuts for holes, pockets, slots, grooves, counterbores and countersinks.
- Apply fillets/chamfers only after the target edges exist.
- Reuse named parameters across features. Do not duplicate the same dimension as separate magic numbers.
- When the contract states a relation such as `hole_offset = width/2`, encode the expression explicitly.
- Keep the feature tree coherent and editable; avoid unrelated temporary bodies.
'''


def get_system_prompt(task: str = "") -> str:
    mem = few_shot_from_memory(task) if task else ""
    edit = latest_edit_context(task) if task else ""
    return (
        "You are a CAD automation engineer for KOMPAS-3D v23. "
        "Generate an editable, deterministic parametric model from the supplied CAD contract. "
        "The goal is engineering intent, not merely a visually plausible solid.\n\n"
        + _API
        + _RULES
        + _ORDER
        + (("\n## Relevant memory examples\n" + mem + "\n") if mem else "")
        + (("\n## Latest model context for an edit request\n" + edit + "\n") if edit else "")
        + "\n## Reference patterns\n"
        + load_patterns()
    )


def build_user_prompt(task: str) -> str:
    return (
        "Generate the complete KOMPAS core script from this CAD_CONTRACT. "
        "First derive the feature dependency order and parameter relations mentally; output only the final code. "
        "Use named parameters for all critical dimensions and expressions for stated relationships. "
        "For rotationally symmetric shafts/fittings/plugs, prefer one longitudinal profile and revolve 360 degrees.\n\n"
        + task.strip()
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- validation failure"
    return (
        "Repair the script against the CAD_CONTRACT without deleting requested features. "
        "Preserve named parameters and repair the smallest failing part of the feature tree. "
        "If the task describes a turned axisymmetric body, do not regress from a revolved profile to unrelated cylinders. "
        "For through-all holes/cuts, preserve through_all=True. "
        "Return exactly one Python code block.\n\n"
        f"VALIDATION ISSUES:\n{err}\n\n"
        f"CAD_CONTRACT:\n{task.strip()}\n\n"
        f"CURRENT SCRIPT:\n```python\n{(bad_code or '')[:9000]}\n```\n"
    )