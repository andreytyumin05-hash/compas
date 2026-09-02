"""Prompts for deterministic vision-to-CAD code generation."""

from .knowledge import load_patterns
from .memory import few_shot_from_memory

_API = '''
## ONLY supported core API
from core import Part
part = Part.create("Name")
with part.sketch("xy") as sk:
    sk.circle(x, y, radius)
    sk.rectangle(x, y, width, height)
    sk.rounded_rect(x, y, width, height, radius)
    sk.stadium(x, y, length, width)
    sk.polygon([(x1,y1), (x2,y2), ...], closed=True)
    sk.line(x1,y1,x2,y2)
    sk.arc(x1,y1,x2,y2,x3,y3)
    sk.slot(x1,y1,x2,y2,width)
    sk.dim_radial(x, y, radius)      # best-effort annotation
    sk.dim_linear(x1,y1,x2,y2)        # best-effort annotation
    sk.dim_rect(x,y,width,height)     # best-effort annotation
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
3. Build in dependency order: base -> added material -> cuts -> patterns -> edge finishing -> update.
4. Every requested feature must have a real corresponding core operation. Never silently omit a feature.
5. A shaft/plug is cylindrical: use circle+extrude / boss / step logic, never rectangle as the main body.
6. Repeated holes: use a pattern operation. Different hole diameters: use separate hole/hole_list operations.
7. A dashed/hidden/center line is reference information, never an outer solid contour.
8. Do not invent unreadable dimensions. Keep unknown dimensions as comments only and do not guess values.
9. Do not call `win32com`, `Dispatch`, `GetActiveObject`, `loft`, or `sweep` from generated code.
10. Do not create a fake feature by returning None; the generated code must use the supported operation that changes the model.
11. Put sketch dimensions immediately after the geometry they describe, but treat them as annotations: build must remain valid if a dim_* call returns False.
12. Prefer named Python variables for important dimensions so the generated script is easy to edit, e.g. `D_BASE = 50`, `L_BASE = 10`.
'''

_ORDER = '''
## Geometry strategy
- First choose the minimum number of additive solids needed to reproduce the visible material. For stepped cylindrical parts, each distinct diameter/length is a separate additive feature.
- Use cuts for holes, pockets, slots, grooves, counterbores and countersinks.
- Apply fillets/chamfers after the geometry they modify exists.
- If a requested edge treatment is ambiguous, apply it only to the final feature edges and keep the operation explicit.
- If the drawing contains several views, reconcile them before coding: main view gives axial lengths; top/section views give radial placement and hidden cuts.
- Prefer one coherent feature tree over many unrelated temporary sketches.
'''


def get_system_prompt(task: str = "") -> str:
    mem = few_shot_from_memory(task) if task else ""
    return (
        "You are a CAD automation engineer for KOMPAS-3D v23. "
        "The input is a canonical CAD_CONTRACT produced by a separate vision stage. "
        "Treat the contract as authoritative and deterministic; do not reinterpret measurements as prose.\n\n"
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
        "Preserve every feature and dependency. Use named dimension variables so the script is easy to edit.\n\n"
        + task.strip()
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- validation failure"
    return (
        "Repair the script against the CAD_CONTRACT. Return exactly one Python code block. "
        "Do not remove requested features. Fix every listed issue.\n\n"
        f"VALIDATION ISSUES:\n{err}\n\n"
        f"CAD_CONTRACT:\n{task.strip()}\n\n"
        f"CURRENT SCRIPT:\n```python\n{(bad_code or '')[:7000]}\n```\n"
    )
