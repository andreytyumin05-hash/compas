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
    sk.axis_line(x1,y1,x2,y2)
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
3. Treat the CAD_CONTRACT and ENGINEERING CONTEXT as inputs, but never fabricate missing dimensions or standard values.
4. Build in dependency order: base -> added material -> cuts -> patterns -> finishing -> update.
5. Every requested feature must map to a real supported core operation. Never silently omit a feature.
6. For a turned/axisymmetric part (shaft, axle, spindle, plug, fitting, turned bushing/body), use ONE longitudinal half-profile + `part.revolve(...)` rather than a stack of independent circles/extrudes.
7. A revolved profile must contain an explicit `sk.axis_line(...)` construction line along the intended rotation axis.
8. Use separate additive extrusions only for genuinely non-axisymmetric material.
9. Repeated holes use pattern operations whenever they share diameter/placement logic.
10. Through holes/cuts MUST use `through_all=True`. Do not substitute `DT_BOTH` semantics.
11. Dashed/hidden/center lines are reference information, never outer solid geometry.
12. Never invent an unreadable drawing dimension.
13. Never call win32com/Dispatch/GetActiveObject/loft/sweep from generated code.
14. shell, thread and sketch_on_face are unsupported and MUST NOT be generated.
15. Important dimensions must be named with `part.param(...)`; derived positions must use `part.p(...)`.
16. Do not use a polyline as a spline substitute. `sk.spline`/`sk.bezier` must remain real spline geometry.
17. Put visible dimension calls near the geometry they describe.
18. Engineering calculations are preliminary unless the supplied calculation context explicitly provides a validated method and assumptions. Never present an estimate as a certified design decision.
19. If a standard/GOST result is supplied, use only dimensions actually supported by the research context. Preserve the standard identifier/source in comments only when useful for traceability.
20. For an edit request, the latest model script/tree/context is the current design. Preserve everything not explicitly changed.
21. An edit request returns a COMPLETE replacement script, not a patch fragment.
'''

_ORDER = '''
## Geometry strategy
- Determine design intent before coding: body type, main axis, sections, cuts, standards, relations.
- Axisymmetric turned parts: longitudinal half-profile -> axis_line -> revolve 360° -> cuts/grooves/holes -> finishing.
- Stepped shafts use one coherent profile whenever possible; do not create unrelated cylinders for sections that belong to one turned body.
- Curved blades use real spline/Bezier profiles with parameterized control points.
- Use cuts for holes, pockets, slots, grooves, counterbores and countersinks.
- Reuse named parameters. Never duplicate critical dimensions as magic numbers.
- Preserve stated mechanical relations as expressions.
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
        "For edits, use the latest model context as the current design and modify only the requested delta. "
        "Return only the final code.\n\n" + task.strip()
    )
    if extra_context:
        prompt += "\n\nENGINEERING CONTEXT (use as evidence, do not invent beyond it):\n" + extra_context[:9000]
    return prompt


def build_repair_prompt(task: str, bad_code: str, errors: list, *, extra_context: str = "") -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- validation failure"
    prompt = (
        "Repair the script against the CAD_CONTRACT without deleting requested features. "
        "Preserve named parameters, latest-model intent and engineering constraints. "
        "Return exactly one complete Python code block.\n\n"
        f"VALIDATION ISSUES:\n{err}\n\n"
        f"CAD_CONTRACT:\n{task.strip()}\n\n"
        f"CURRENT SCRIPT:\n```python\n{(bad_code or '')[:9000]}\n```\n"
    )
    if extra_context:
        prompt += "\nENGINEERING CONTEXT:\n" + extra_context[:9000]
    return prompt
