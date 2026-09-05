"""Deterministic engineering calculations used before CAD generation.

The calculator intentionally refuses to guess missing engineering inputs.  It is
small now, but structured so more validated formula families can be added later.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CalculationResult:
    name: str
    values: dict[str, float]
    formula: str
    assumptions: tuple[str, ...] = ()

    def as_text(self) -> str:
        lines = [f"CALCULATION: {self.name}", f"FORMULA: {self.formula}"]
        lines += [f"{key}={value:.6g}" for key, value in self.values.items()]
        if self.assumptions:
            lines.append("ASSUMPTIONS: " + "; ".join(self.assumptions))
        return "\n".join(lines)


def _number(value: str) -> float:
    return float(value.replace(",", "."))


def _find(patterns: tuple[str, ...], text: str) -> Optional[float]:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return _number(match.group(1))
    return None


def _torque_nm(text: str) -> Optional[float]:
    value = _find((
        r"(?:крутящ(?:ий|его)\s+момент|момент|torque)\D{0,30}(\d+(?:[\.,]\d+)?)\s*(?:н\s*[·*x]?\s*м|n\s*m|nm)\b",
        r"(?:T|M)\s*[=:]\s*(\d+(?:[\.,]\d+)?)\s*(?:н\s*[·*x]?\s*м|nm|n\s*m)\b",
    ), text)
    return value


def _stress_mpa(text: str) -> Optional[float]:
    return _find((
        r"(?:допустим(?:ое|ая)\s+(?:касательн(?:ое|ая)\s+)?напряжени(?:е|я)|допустим(?:ое|ая)\s+напряжение|tau[_ ]?allow|τ[_ ]?доп)\D{0,30}(\d+(?:[\.,]\d+)?)\s*(?:мпа|mpa)",
        r"(?:[τt]|tau)\s*[=:]\s*(\d+(?:[\.,]\d+)?)\s*(?:мпа|mpa)\b",
    ), text)
    return value


def _safety_factor(text: str) -> Optional[float]:
    return _find((
        r"(?:коэффициент\s+запаса|запас(?:а)?\s+прочности|safety\s*factor|SF)\D{0,20}(\d+(?:[\.,]\d+)?)",
        r"(?:n|k)\s*[=:]\s*(\d+(?:[\.,]\d+)?)\b",
    ), text)


def _power_kw(text: str) -> Optional[float]:
    return _find((r"(?:мощност(?:ь|и)|power)\D{0,25}(\d+(?:[\.,]\d+)?)\s*(?:квт|kw)\b"), text)


def _speed_rpm(text: str) -> Optional[float]:
    return _find((r"(?:частот(?:а|ы)\s+вращения|скорост(?:ь|и)\s+вращения|оборотов|rpm|n)\D{0,25}(\d+(?:[\.,]\d+)?)\s*(?:об/?мин|rpm)?\b"), text)


def shaft_diameter_from_torque(text: str) -> Optional[CalculationResult]:
    """Pure torsion preliminary shaft diameter estimate, d in mm.

    Uses d = cubert(16*T/(pi*tau_allow)), with T in N*mm. If a safety factor
    is supplied, torque is multiplied by it. This is a preliminary strength
    estimate, not a final shaft design (fatigue, keyway, bending, stress
    concentrations, deflection and standards still require separate checks).
    """
    torque = _torque_nm(text)
    if torque is None:
        power = _power_kw(text)
        speed = _speed_rpm(text)
        if power is not None and speed and speed > 0:
            torque = 9550.0 * power / speed
        else:
            return None

    tau = _stress_mpa(text)
    if tau is None or tau <= 0:
        return None

    sf = _safety_factor(text) or 1.0
    if sf <= 0:
        return None
    design_torque_nm = torque * sf
    torque_nmm = design_torque_nm * 1000.0
    diameter = (16.0 * torque_nmm / (math.pi * tau)) ** (1.0 / 3.0)
    return CalculationResult(
        name="shaft diameter from torsion",
        values={
            "T_input_Nm": torque,
            "tau_allow_MPa": tau,
            "safety_factor": sf,
            "T_design_Nm": design_torque_nm,
            "d_min_mm": diameter,
        },
        formula="d = (16*T_design/(pi*tau_allow))^(1/3), T_design[N*mm]",
        assumptions=(
            "pure torsion preliminary sizing",
            "solid circular shaft",
            "uniform allowable shear stress",
            "final design must also check bending, fatigue, keyway/stress concentration and deflection",
        ),
    )


def calculate_engineering(text: str) -> list[CalculationResult]:
    results: list[CalculationResult] = []
    shaft = shaft_diameter_from_torque(text)
    if shaft:
        results.append(shaft)
    return results


def calculation_context(text: str) -> str:
    results = calculate_engineering(text)
    if not results:
        return ""
    return "\n\n".join(result.as_text() for result in results)
