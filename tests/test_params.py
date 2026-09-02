import unittest

from core.params import ParamStore, ParamError


class ParamStoreTest(unittest.TestCase):
    def test_hole_offset_follows_width(self):
        s = ParamStore()
        s.set("W", 100)
        s.set("HOLE_OFFSET", expr="W / 2")
        self.assertAlmostEqual(s.eval("HOLE_OFFSET"), 50.0)
        s.set("W", 140)
        self.assertAlmostEqual(s.eval("HOLE_OFFSET"), 70.0)

    def test_inner_from_outer(self):
        s = ParamStore()
        s.set("D", 60)
        s.set("D_inner", expr="D - 44")
        self.assertAlmostEqual(s.eval("D_inner"), 16.0)

    def test_cycle_raises(self):
        s = ParamStore()
        s.set("A", expr="B + 1")
        s.set("B", expr="A + 1")
        with self.assertRaises(ParamError):
            s.eval("A")

    def test_dependency_graph(self):
        s = ParamStore()
        s.set("D", 50)
        s.set("R", expr="D / 2")
        self.assertIn("D", s.dependency_graph()["R"])


class TextContractTest(unittest.TestCase):
    def test_fitting_steps(self):
        from agent.text_contract import parse_technical_text

        t = (
            "Штуцер: основание Ø60 длиной 20, затем ступень Ø45 длиной 15, "
            "затем шейка Ø30 длиной 25, сквозное отверстие Ø16, "
            "канавка шириной 4, фаска 2x45"
        )
        c = parse_technical_text(t)
        self.assertEqual(c["part_type"], "fitting")
        types = [f["type"] for f in c["features"]]
        self.assertTrue(any(x in types for x in ("extrude_body", "step")))
        self.assertIn("hole", types)


class SplineNotPolylineTest(unittest.TestCase):
    def test_spline_source_uses_ksBezier(self):
        import inspect
        from core.sketch import Sketch

        src = inspect.getsource(Sketch.spline)
        self.assertIn("ksBezier", src)
        self.assertNotIn("return self.polyline", src)


if __name__ == "__main__":
    unittest.main()
