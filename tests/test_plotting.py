import unittest
from pathlib import Path

from quant_factor_backtest.backtest.plotting import save_dual_curve_svg
from temp_paths import cleanup_temp_dir, make_temp_dir


class DualCurveSvgTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = make_temp_dir()
        self.addCleanup(lambda: cleanup_temp_dir(self.temp_dir))

    def test_dual_curve_svg_contains_both_curves(self) -> None:
        actual = {"2024-01-01": 1.0, "2024-01-02": 1.05, "2024-01-03": 1.08}
        predicted = {"2024-01-01": 1.0, "2024-01-02": 1.03, "2024-01-03": 1.06}

        output_path = self.temp_dir / "dual_curve.svg"
        result_path = save_dual_curve_svg(
            actual, predicted, str(output_path),
            title="Test Dual Curve",
            actual_label="Actual",
            predicted_label="Predicted"
        )

        self.assertEqual(result_path, str(output_path))
        self.assertTrue(output_path.exists())

        content = output_path.read_text(encoding="utf-8")
        self.assertIn('stroke="#0f766e"', content)  # Actual curve color
        self.assertIn('stroke="#e11d48"', content)  # Predicted curve color
        self.assertIn("Test Dual Curve", content)
        self.assertIn(">Actual<", content)
        self.assertIn(">Predicted<", content)
        self.assertIn("polyline", content.lower())

    def test_dual_curve_svg_with_partial_predictions(self) -> None:
        actual = {"2024-01-01": 1.0, "2024-01-02": 1.05, "2024-01-03": 1.08}
        predicted = {"2024-01-02": 1.04, "2024-01-03": 1.07}

        output_path = self.temp_dir / "partial_curve.svg"
        result_path = save_dual_curve_svg(actual, predicted, str(output_path))

        self.assertTrue(output_path.exists())
        content = output_path.read_text(encoding="utf-8")
        self.assertIn('stroke="#0f766e"', content)
        self.assertIn('stroke="#e11d48"', content)

    def test_dual_curve_svg_empty_data(self) -> None:
        actual: dict = {}
        predicted: dict = {}

        output_path = self.temp_dir / "empty_curve.svg"
        result_path = save_dual_curve_svg(actual, predicted, str(output_path))

        self.assertTrue(output_path.exists())
        content = output_path.read_text(encoding="utf-8")
        self.assertIn("<svg", content)
        self.assertIn("</svg>", content)


if __name__ == "__main__":
    unittest.main()
