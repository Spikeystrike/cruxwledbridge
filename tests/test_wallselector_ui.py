import shutil
import subprocess
import unittest
from pathlib import Path

from templates.wallselector import returnwallhtml


class ManualHoleUITests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is required for UI behavior tests")
    def test_manual_hole_browser_interactions(self):
        grid = {
            "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 50}, {"x": 0, "y": 50}],
            "r": 1, "c": 3,
            "positions": {"0": [0, 0], "1": [50, 0], "2": [100, 0]},
            "position_led_ids": {"0": 0, "1": 1, "2": 2},
        }
        html = returnwallhtml(
            {"id": 1, "image_url": "/wall.jpg", "image_width": 100, "image_height": 50},
            "/bridge",
            {"coordinate_space": "wall_image", "coordinate_width": 100, "coordinate_height": 50,
             "holds2led": {"hold-b": 1}, "grids": [{"id": "a", **grid}, {"id": "b", **grid}]},
        )
        result = subprocess.run(
            [shutil.which("node"), str(Path(__file__).with_name("wallselector_manual.cjs"))],
            input=html, text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Manual-hole UI behavior passed", result.stdout)
