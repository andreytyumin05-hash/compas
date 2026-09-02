"""Prompts for deterministic text/vision to parametric KOMPAS CAD."""

from .knowledge import load_patterns
from .memory import few_shot_from_memory

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
    sk.spline([(x1,y1), (x2,y2), (x3,y3), ...], closed=False)
    sk.bezier([(x1,y1), (x2,y2), (x3,y3), ...], closed=False)
    sk.dim_radial(x, y, radius)
    sk.dim_linear(x1,y1,x2,y2)
    sk.dim_rect(x,y,width,height)
part.extrude(sk, depth=H)
part.cut(sk, depth=D, through_all=False)
part.cut(sk, through_all=True)
part.revolve(sk, angle=A)
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
6. A shaft/plug/fitting body is cylindrical: use circle+extrude / boss / step logic, never rectangle as the main body.
7. Repeated holes use pattern operations whenever they share diameter/placement logic.
8. A dashed/hidden/center line is reference information, never outer solid geometry.
9. Never invent a missing dimension. Preserve unknown dimensions as unknown and do not guess.
10. Never call win32com/Dispatch/GetActiveObject/loft/sweep from generated code.
11. shell, thread and sketch_on_face are unsupported in the current core and MUST NOT be generated.
12. Important dimensions must be named with `part.param(name, ...)` and geometry should use `part.p(name)` rather than duplicated literals.
13. Derived positions must be expressed from parameters when a mechanical relation is stated. Example: `part.param("HOLE_X", expr="W/2")`.
14. Do not use a polyline as a substitute for a spline. `sk.spline`/`sk.bezier` must remain a real Bezier operation.
15. Put dimension calls close to the geometry they describe. Dimension failure is not a reason to fake a successful geometry operation.
16. For complex profiles, prefer a single coherent closed sketch made of line/arc/spline elements rather than many disconnected solids.
'''

_ORDER = '''
## Geometry strategy
- First determine the design intent: body type, primary axis, sections, cuts, and edge finishing.
- For stepped cylindrical parts, each distinct diameter/length is a separate additive feature unless a revolved profile is clearly more appropriate.
- For a curved blade-like profile, build a real closed sketch from spline/arc/line segments and keep control points parameter-driven.
- Use cuts for holes, pockets, slots, grooves, counterbores and countersinks.
- Apply fillets/chamfers only after the target edges exist.
- Reuse named parameters across features. Do not duplicate the same dimension as separate magic numbers.
- When the contract states a relation such as `hole_offset = width/2`, encode the expression explicitly.
- Keep the feature tree coherent and editable; avoid unrelated temporary bodies.
'''


def get_system_prompt(task: str = "") -> str:
    mem = few_shot_from_memory(task) if task else ""
    return (
        "You are a CAD automation engineer for KOMPAS-3D v23. "
        "Generate an editable, deterministic parametric model from the supplied CAD contract. "
        "The goal is engineering intent, not merely a visually plausible solid.\n\n"
        + _API
        + _RULES
        + _ORDER
        + (("\n## Relevant memory examples\n" + mem + "\n") if mem else "")
        + "\n## Reference patterns\n"
        + load_patterns()
    )


def build_user_prompt(task: str) -> str:
    return (
        "Generate the complete KOMPAS core script from this CAD_CONTRACT. "
        "First derive the feature dependency order and parameter relations mentally; output only the final code. "
        "Use named parameters for all critical dimensions and expressions for stated relationships.\n\n"
        + task.strip()
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- validation failure"
    return (
        "Repair the script against the CAD_CONTRACT without deleting requested features. "
        "Preserve named parameters and repair the smallest failing part of the feature tree. "
        "Return exactly one Python code block.\n\n"
        f"VALIDATION ISSUES:\n{err}\n\n"
        f"CAD_CONTRACT:\n{task.strip()}\n\n"
        f"CURRENT SCRIPT:\n```python\n{(bad_code or '')[:9000]}\n```\n"
    )
