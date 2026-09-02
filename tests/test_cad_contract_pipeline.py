from agent.contract import normalize_spec, spec_to_contract_text
from agent.runner import Agent
from agent.validate import validate_generated_code


def test_plan_only_spec_becomes_features():
    spec = {
        "part_type": "plug",
        "name": "Штуцер",
        "build_plan": [
            {"id": "S01", "type": "step", "params": {"diameter": 40, "length": 12}},
            {"id": "S02", "type": "step", "params": {"diameter": 28, "length": 25}, "depends_on": "S01"},
            {"id": "S03", "type": "pattern_holes", "params": {"pcd": 32, "count": 4, "diameter": 6}, "depends_on": "S02"},
        ],
    }
    normalized = normalize_spec(spec)
    assert [f["type"] for f in normalized["features"]] == ["step", "step", "pattern_holes"]
    assert normalized["features"][2]["params"]["count"] == 4
    text = spec_to_contract_text(normalized)
    assert "CAD_CONTRACT v2" in text
    assert "body_style=cylindrical_steps" in text
    assert "F03: feature=pattern_holes" in text


def test_validator_rejects_unknown_core_method():
    code = '''
from core import Part
part = Part.create("X")
part.magic_operation(10)
part.update()
'''
    ok, errors = validate_generated_code(code)
    assert not ok
    assert any("unknown part.magic_operation" in e for e in errors)


def test_validator_accepts_real_parameter_friendly_script():
    code = '''
from core import Part
D = 50
L = 20
part = Part.create("X")
with part.sketch("xy") as sk:
    sk.circle(0, 0, D / 2)
    sk.dim_radial(0, 0, D / 2)
part.extrude(sk, depth=L)
part.update()
'''
    ok, errors = validate_generated_code(code)
    assert ok, errors


def test_code_extractor_ignores_prose():
    raw = '''Here is the final script:\n```python\nfrom core import Part\npart = Part.create("X")\npart.update()\n```\nDone.'''
    extracted = Agent._extract_code(raw)
    assert extracted.startswith("from core import Part")
    assert "Done" not in extracted
