import unittest

from agent.schema import spec_to_task_text


class SpecToTaskTextComplexSpecTest(unittest.TestCase):
    def test_complex_feature_tree_is_explicit(self):
        spec = {
            "part_type": "cover",
            "name": "Крышка",
            "overall": {"length": 116, "width": 80, "thickness": 13},
            "construction": {
                "feature_order": ["base", "boss", "pocket", "pattern_holes", "fillet"],
                "planes_used": ["xy", "xz"],
                "notes": "Основание на xy, карман и паз в xz",
            },
            "features": [
                {
                    "type": "extrude_body",
                    "params": {"shape": "stadium", "length": 116, "width": 80, "thickness": 13},
                    "notes": "base body",
                },
                {
                    "type": "boss",
                    "params": {"shape": "circle", "diameter": 60, "boss_height": 18},
                    "notes": "center boss",
                },
                {
                    "type": "pocket",
                    "params": {"shape": "circle", "diameter": 50, "depth": 8},
                    "notes": "blind pocket",
                },
                {
                    "type": "pattern_holes",
                    "params": {"pcd": 60, "count": 4, "diameter": 8},
                    "notes": "4 holes",
                },
                {
                    "type": "fillet",
                    "params": {"radius": 2},
                    "notes": "edge blend",
                },
            ],
            "unknown_dimensions": [],
            "warnings": [],
        }

        text = spec_to_task_text(spec)

        self.assertIn("feature_order=base->boss->pocket->pattern_holes->fillet", text)
        self.assertIn("plane=xy", text)
        self.assertIn("plane=xz", text)
        self.assertIn("boss_height=18", text)
        self.assertIn("pocket_depth=8", text)
        self.assertIn("fillet_radius=2", text)


if __name__ == "__main__":
    unittest.main()
