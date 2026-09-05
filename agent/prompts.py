"""Prompts for deterministic text/vision to parametric KOMPAS CAD."""

from .knowledge import load_patterns
from .memory import few_shot_from_memory, latest_edit_context

_API = '''
## ONLY supported core API
from core import Part
part = Part.create("Name")
part = Part.from_active()

part.param("W", 100)
part.param("HOLE_X", expr="W/2")
W = part.p("W")
HOLE_X = part.p("HOLE_X")
existing = part.variables()
part.set_variable("W", value=140)
part.set_variable("HOLE_X", expression="W/2")

with part.sketch("xy") as sk:
    sk.circle(x, y, radius)
    sk.rectangle(x, y, width, height)
    sk.rounded_rect(x, y, width, height, radius)
    sk.stadium(x, y, length, width)
    sk.polygon([(x1,y1), (x2,y2), ...], closed=True)
    sk.line(x1,y1,x2,y2)
    sk.axis_line(x1,y1,x2,y2)
    sk.arc(x1,y1,x2,y2,x3,y3)
    sk.slot(x1,y1,x2,y2,width)
    sk.spline([(x1,y1), (x2,y2), (x3,y3), ...], closed=False, smooth=True)
    sk.bezier([(x1,y1), (x2,y2), (x3,y3), ...], closed=False, smooth=True)
    sk.dim_radial(x, y, radius)
    sk.dim_linear(x1,y1,x2,y2)
    sk.dim_rect(x,y,width,height)
part.extrude(sk, depth=H)
part.cut(sk, through_all=True)
part.revolve(sk, angle=360)
part.hole(x,y,diameter=D,through_all=True)
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
3. Never fabricate missing dimensions, engineering values or standard values.
4. Build in dependency order: base -> added material -> cuts -> patterns -> finishing -> update.
5. Every requested feature must map to a real core operation. Never silently omit it.
6. Turned/axisymmetric part: ONE longitudinal half-profile + axis_line + revolve; never a stack of unrelated cylinders.
7. Through holes/cuts MUST use `through_all=True`.
8. Repeated holes use pattern operations where appropriate.
9. Dashed/hidden/center lines are reference geometry, not solid geometry.
10. Never call win32com/Dispatch/GetActiveObject from generated code.
11. shell/thread/sketch_on_face/loft/sweep are forbidden until their core implementations are real.
12. Important dimensions must be named with `part.param(...)` and derived positions use expressions.
13. Real spline/Bezier geometry only; no polyline substitute.
14. Visible dimensions should be placed on important editable sketches.
15. Engineering calculations are preliminary unless validated in the supplied context.
16. Standard values may be used only when supported by research context.
17. EDIT MODE uses the currently open KOMPAS detail as source of truth.
18. EDIT MODE uses exactly one `Part.from_active()` and NEVER `Part.create()`.
19. When a requested modification matches an existing model variable, use `part.set_variable(...)` before adding replacement geometry.
20. EDIT MODE must contain `# COMPAS_EDIT_MODE`.
21. An edit request returns a COMPLETE replacement script, not a patch fragment.
'''

_ORDER = '''
## Geometry strategy
- Determine design intent before coding: body type, main axis, sections, cuts, standards, relations.
- Axisymmetric turned parts: longitudinal half-profile -> axis_line -> revolve 360° -> cuts/grooves/holes -> finishing.
- Curved blades: real spline/Bezier profiles with parameterized control points.
- Use named parameters and expressions instead of duplicated magic numbers.
- EDIT MODE: inspect live variables and feature tree first; mutate an existing variable when possible; otherwise apply only the requested change to the active part.
'''


def get_system_prompt(task: str = "", *, extra_context: str = "") -> str:
    mem = few_shot_from_memory(task) if task else ""
    edit = latest_edit_context(task) if task else ""
    return (
        "You are a CAD automation engineer for KOMPAS-3D v23. Generate an editable engineering model, not a merely plausible shape.\n\n"
        + _API + _RULES + _ORDER
        + (("\n## Latest model context\n" + edit + "\n") if edit else "")
        + (("\n## Engineering calculations / standards research\n" + extra_context[:9000] + "\n") if extra_context else "")
        + (("\n## Relevant latest-model example\n" + mem + "\n") if mem else "")
        + "\n## Reference patterns\n" + load_patterns()
    )


def build_user_prompt(task: str, *, extra_context: str = "") -> str:
    prompt = (
        "Generate the complete KOMPAS core script from this CAD_CONTRACT. "
        "For EDIT MODE, inspect and modify the currently open detail rather than creating a new document. "
        "When an existing variable matches the requested change, use `part.set_variable(...)`. "
        "Include `# COMPAS_EDIT_MODE` and `Part.from_active()` for edits. Return only the final code.\n\n" + task.strip()
    )
    if extra_context:
        prompt += "\n\nENGINEERING CONTEXT (evidence only):\n" + extra_context[:9000]
    return prompt


def build_repair_prompt(task: str, bad_code: str, errors: list, *, extra_context: str = "") -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- validation failure"
    prompt = (
        "Repair the script against the CAD_CONTRACT without deleting requested features. "
        "For EDIT MODE keep `# COMPAS_EDIT_MODE`, exactly one `Part.from_active()`, no `Part.create()`, "
        "and use `part.set_variable(...)` when an existing variable is the target. "
        "Return exactly one complete Python code block.\n\n"
        f"VALIDATION ISSUES:\n{err}\n\n"
        f"CAD_CONTRACT:\n{task.strip()}\n\n"
        f"CURRENT SCRIPT:\n```python\n{(bad_code or '')[:10000]}\n```\n"
    )
    if extra_context:
        prompt += "\nENGINEERING CONTEXT:\n" + extra_context[:9000]
    return prompt
