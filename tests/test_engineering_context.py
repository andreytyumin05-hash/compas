import unittest

from agent.calculations import shaft_diameter_from_torque, calculate_engineering
from agent.web_search import needs_web_research


class EngineeringContextTest(unittest.TestCase):
    def test_shaft_diameter_from_torque(self):
        result = shaft_diameter_from_torque(
            "Крутящий момент 100 Н*м, допустимое напряжение 40 МПа, коэффициент запаса 2"
        )
        self.assertIsNotNone(result)
        self.assertGreater(result.values["d_min_mm"], 0)
        self.assertEqual(result.values["T_design_Nm"], 200)

    def test_power_and_speed_to_torque(self):
        result = shaft_diameter_from_torque(
            "мощность 10 кВт, оборотов 1000, допустимое напряжение 40 МПа"
        )
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result.values["T_input_Nm"], 95.5, places=3)

    def test_missing_allowable_stress_does_not_guess(self):
        self.assertIsNone(shaft_diameter_from_torque("крутящий момент 100 Н*м"))

    def test_bending_and_torsion(self):
        results = calculate_engineering(
            "изгибающий момент 80 Н*м, крутящий момент 100 Н*м, "
            "допустимое нормальное напряжение 60 МПа"
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "shaft diameter from bending+torsion")
        self.assertAlmostEqual(results[0].values["Mb_Nm"], 80.0)
        self.assertAlmostEqual(results[0].values["Mt_Nm"], 100.0)

    def test_standards_trigger(self):
        self.assertTrue(needs_web_research("Сделай штуцер с проточкой по ГОСТ"))
        self.assertFalse(needs_web_research("Плита 100x60x10"))


if __name__ == "__main__":
    unittest.main()
