"""Single source of truth for generated CAD operations.

Compatibility shims may exist on Part for API stability, but generation must only
see operations that produce real KOMPAS geometry. Unsupported operations remain
explicitly blocked instead of returning silent no-ops.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class OpSpec:
    name: str
    status: str  # real | best_effort | unsupported | meta
    purpose: str


OPS = {
    "create": OpSpec("create", "meta", "create one part"),
    "from_active": OpSpec("from_active", "meta", "attach to active KOMPAS part"),
    "update": OpSpec("update", "meta", "rebuild/update model"),
    "sketch": OpSpec("sketch", "real", "create base-plane sketch"),
    "extrude": OpSpec("extrude", "real", "add material by extrusion"),
    "cut": OpSpec("cut", "real", "remove material by extrusion"),
    "revolve": OpSpec("revolve", "best_effort", "revolved feature"),
    "hole": OpSpec("hole", "real", "hole feature"),
    "pattern_holes_circular": OpSpec("pattern_holes_circular", "real", "circular hole pattern"),
    "pattern_holes_rect": OpSpec("pattern_holes_rect", "real", "rectangular hole pattern"),
    "pattern_holes_points": OpSpec("pattern_holes_points", "real", "point-based hole pattern"),
    "pattern_holes_linear": OpSpec("pattern_holes_linear", "real", "linear hole pattern"),
    "hole_list": OpSpec("hole_list", "real", "explicit hole list"),
    "boss": OpSpec("boss", "real", "add cylindrical boss"),
    "hex_boss": OpSpec("hex_boss", "real", "add hexagonal boss"),
    "pocket": OpSpec("pocket", "real", "remove cylindrical pocket"),
    "ring_groove": OpSpec("ring_groove", "real", "ring groove"),
    "groove": OpSpec("groove", "real", "ring-groove compatibility alias"),
    "keyway": OpSpec("keyway", "real", "keyway"),
    "slot": OpSpec("slot", "real", "slot"),
    "step": OpSpec("step", "real", "turned step helper"),
    "counterbore": OpSpec("counterbore", "real", "counterbore"),
    "countersink": OpSpec("countersink", "real", "countersink"),
    "fillet": OpSpec("fillet", "best_effort", "edge fillet"),
    "fillet_edge": OpSpec("fillet_edge", "best_effort", "edge-selected fillet"),
    "chamfer": OpSpec("chamfer", "best_effort", "edge chamfer"),
    "chamfer_edge": OpSpec("chamfer_edge", "best_effort", "edge-selected chamfer"),
    "get_edges": OpSpec("get_edges", "best_effort", "edge query"),
    "mass_properties": OpSpec("mass_properties", "meta", "mass properties"),
    "export": OpSpec("export", "meta", "export model"),
    "export_formats": OpSpec("export_formats", "meta", "export multiple formats"),
    "close": OpSpec("close", "meta", "close document"),
    "param": OpSpec("param", "meta", "named parameter"),
    "p": OpSpec("p", "meta", "evaluate named parameter"),
    "params_dict": OpSpec("params_dict", "meta", "evaluate parameters"),
    "param_graph": OpSpec("param_graph", "meta", "parameter dependency graph"),
    "var": OpSpec("var", "meta", "KOMPAS variable bridge"),
    "set_properties": OpSpec("set_properties", "meta", "document properties"),
    "get_context": OpSpec("get_context", "meta", "document context"),
    "set_view": OpSpec("set_view", "meta", "view selection"),
    "screenshot": OpSpec("screenshot", "meta", "visual verification screenshot"),
    "sketch_on_face": OpSpec("sketch_on_face", "unsupported", "true face selection not implemented"),
    "shell": OpSpec("shell", "unsupported", "native shell not implemented"),
    "thread": OpSpec("thread", "unsupported", "native thread not implemented"),
    "sweep": OpSpec("sweep", "unsupported", "native sweep not implemented"),
    "loft": OpSpec("loft", "unsupported", "native loft not implemented"),
}


def allowed_part_methods() -> FrozenSet[str]:
    return frozenset(name for name, spec in OPS.items() if spec.status != "unsupported")


def unsupported_part_methods() -> FrozenSet[str]:
    return frozenset(name for name, spec in OPS.items() if spec.status == "unsupported")


def is_supported(name: str) -> bool:
    spec = OPS.get(name)
    return spec is not None and spec.status != "unsupported"


def is_unsupported(name: str) -> bool:
    return name in unsupported_part_methods()
