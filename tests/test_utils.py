import asyncio
import os
import sys
import types
import unittest
from unittest.mock import Mock, call, patch

from fastapi import HTTPException


config_package = types.ModuleType("config")
config = types.ModuleType("config.config")
config.token = "test-token"
config.colors = {"start": "FF0000"}
config.hole2LEDS = {7: [101]}
config.wled_controllers = [
    {"ip": "192.0.2.10", "start": 100, "end": 102},
]
config_package.config = config
sys.modules["config"] = config_package
sys.modules["config.config"] = config

import utils

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
import main


class WallHoldKeyTests(unittest.TestCase):
    def test_combines_wall_and_hold_ids(self):
        self.assertEqual(
            utils.wall_hold_key(216943, "8ba97f45a6656519"),
            "216943_8ba97f45a6656519",
        )


class GridGenerationTests(unittest.TestCase):
    def test_standard_grid_keeps_all_columns(self):
        grid = utils.generate_grid((0, 0), (30, 0), (30, 10), (0, 10), 2, 4)

        self.assertEqual(len(grid), 8)
        self.assertEqual(set(grid), set(range(8)))

    def test_alternating_grid_uses_half_the_columns_per_row(self):
        grid = utils.generate_grid(
            (5, 0),
            (215, 0),
            (215, 10),
            (5, 10),
            2,
            22,
            alternating=True,
        )

        self.assertEqual(len(grid), 22)
        self.assertEqual(set(grid), set(range(22)))
        self.assertEqual(
            sorted(x for x, y in grid.values() if y == 0),
            list(range(5, 206, 20)),
        )
        self.assertEqual(
            sorted(x for x, y in grid.values() if y == 10),
            list(range(15, 216, 20)),
        )

    def test_alternating_grid_keeps_contiguous_snake_ids(self):
        grid = utils.generate_grid(
            (0, 0),
            (50, 0),
            (50, 20),
            (0, 20),
            3,
            6,
            alternating=True,
        )

        self.assertEqual(
            grid,
            {
                8: (0, 0),
                7: (20, 0),
                6: (40, 0),
                3: (10, 10),
                4: (30, 10),
                5: (50, 10),
                2: (0, 20),
                1: (20, 20),
                0: (40, 20),
            },
        )

    def test_alternating_grid_allows_odd_column_count(self):
        grid = utils.generate_grid(
            (5, 0),
            (45, 0),
            (45, 10),
            (5, 10),
            2,
            5,
            alternating=True,
        )

        self.assertEqual(set(grid), set(range(5)))
        self.assertEqual(
            sorted(x for x, y in grid.values() if y == 0),
            [5, 25, 45],
        )
        self.assertEqual(
            sorted(x for x, y in grid.values() if y == 10),
            [15, 35],
        )

    def test_alternating_grid_can_start_with_offset_row(self):
        grid = utils.generate_grid(
            (5, 0),
            (45, 0),
            (45, 10),
            (5, 10),
            2,
            5,
            alternating=True,
            alternating_start_column=1,
        )

        self.assertEqual(set(grid), set(range(5)))
        self.assertEqual(
            sorted(x for x, y in grid.values() if y == 0),
            [15, 35],
        )
        self.assertEqual(
            sorted(x for x, y in grid.values() if y == 10),
            [5, 25, 45],
        )

    def test_alternating_grid_rejects_single_column(self):
        with self.assertRaisesRegex(ValueError, "at least two columns"):
            utils.generate_grid(
                (0, 0),
                (0, 0),
                (0, 10),
                (0, 10),
                2,
                1,
                alternating=True,
            )


class WallEndpointTests(unittest.TestCase):
    @patch("main.requests.get")
    def test_list_walls_rejects_empty_gym_without_calling_crux(self, get):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(main.list_walls(""))

        self.assertEqual(raised.exception.status_code, 400)
        get.assert_not_called()

    @patch("main.requests.get")
    def test_list_walls_renders_crux_wall_list(self, get):
        response = Mock()
        response.json.return_value = [
            {
                "id": 216943,
                "name": "Kontors Keller",
                "image_url": "https://example.com/wall.jpg",
            }
        ]
        get.return_value = response

        result = asyncio.run(main.list_walls("kontors-keller"))
        html = result.body.decode()

        self.assertEqual(result.status_code, 200)
        self.assertIn("Kontors Keller", html)
        self.assertIn("/wallcreation?id=216943", html)
        get.assert_called_once_with(
            "https://www.cruxapp.ca/api/v1/gyms/kontors-keller/gym_walls",
            headers=main.auth_header,
            verify=False,
            timeout=15,
        )

    @patch("main.APP_PATH_PREFIX", "/cruxwledbridge")
    @patch("main.requests.get")
    def test_list_walls_uses_configured_path_prefix(self, get):
        response = Mock()
        response.json.return_value = [
            {
                "id": 216943,
                "name": "Kontors Keller",
                "image_url": "https://example.com/wall.jpg",
            }
        ]
        get.return_value = response

        result = asyncio.run(main.list_walls("kontors-keller"))

        self.assertIn(
            'href="/cruxwledbridge/wallcreation?id=216943"',
            result.body.decode(),
        )

    @patch("main.requests.get")
    def test_list_walls_rejects_non_list_crux_response(self, get):
        response = Mock()
        response.json.return_value = {"error": "Gym not found"}
        get.return_value = response

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(main.list_walls("does-not-exist"))

        self.assertEqual(raised.exception.status_code, 502)

    def test_wall_creation_rejects_empty_id(self):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(main.wall_creation(""))

        self.assertEqual(raised.exception.status_code, 400)


class DefineHoldsTests(unittest.TestCase):
    wall_id = 987654

    def setUp(self):
        db = main.SessionLocal()
        db.query(main.Hold2ledDB).filter(
            main.Hold2ledDB.holdid.like(f"{self.wall_id}_%")
        ).delete(synchronize_session=False)
        db.query(main.WallDB).filter(main.WallDB.id == self.wall_id).delete()
        db.add(
            main.WallDB(
                id=self.wall_id,
                angle_adjustable=False,
                created_at="2026-01-01",
                name="Test wall",
                updated_at="2026-01-01",
                image_height=10,
                image_width=20,
                image_url="https://example.com/wall.jpg",
                holds=[{"id": "hold-a", "mask": [[0, 0], [0, 0]]}],
            )
        )
        db.commit()
        db.close()

    def tearDown(self):
        db = main.SessionLocal()
        db.query(main.Hold2ledDB).filter(
            main.Hold2ledDB.holdid.like(f"{self.wall_id}_%")
        ).delete(synchronize_session=False)
        db.query(main.WallDB).filter(main.WallDB.id == self.wall_id).delete()
        db.commit()
        db.close()

    def test_excluded_position_is_not_used_for_mapping(self):
        payload = main.WallTranslation(
            wallid=self.wall_id,
            p1x=0,
            p1y=0,
            p2x=20,
            p2y=0,
            p3x=20,
            p3y=10,
            p4x=0,
            p4y=10,
            r=2,
            c=3,
            alternating=True,
            alternating_start_column=0,
            excluded_position_ids=[1],
        )

        result = asyncio.run(main.define_holds(payload))

        self.assertEqual(set(result["positions"]), {0, 1, 2})
        self.assertEqual(set(result["grid"]), {0, 1})
        self.assertEqual(result["position_led_ids"], {0: 0, 2: 1})
        self.assertEqual(result["excluded_position_ids"], [1])
        self.assertEqual(result["holds2led"], {"hold-a": 0})

        db = main.SessionLocal()
        mapping = db.query(main.Hold2ledDB).filter(
            main.Hold2ledDB.holdid == f"{self.wall_id}_hold-a"
        ).first()
        self.assertEqual(mapping.ledid, 0)
        db.close()


class PathPrefixTests(unittest.TestCase):
    def test_normalizes_path_prefix(self):
        self.assertEqual(main.normalize_path_prefix("cruxwledbridge/"), "/cruxwledbridge")
        self.assertEqual(main.normalize_path_prefix("/"), "")

    def test_toggle_gui_uses_path_prefix(self):
        html = main.returntogglehtml("/cruxwledbridge")

        self.assertIn("fetch('/cruxwledbridge/toggle_mode'", html)

    def test_wall_selector_uses_path_prefix(self):
        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
            "/cruxwledbridge",
        )

        self.assertIn("fetch('/cruxwledbridge/defineholds'", html)

    def test_wall_selector_offers_alternating_grid(self):
        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
            "/cruxwledbridge",
        )

        self.assertIn('id="alternating"', html)
        self.assertIn("alternating: alternating", html)
        self.assertIn('id="alternating-start"', html)
        self.assertIn('<option value="0">Nicht eingerückt</option>', html)
        self.assertIn('<option value="1">Eingerückt</option>', html)
        self.assertIn("alternating_start_column: alternatingStartColumn", html)

    def test_wall_selector_can_exclude_rendered_positions(self):
        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
            "/cruxwledbridge",
        )

        self.assertIn("excludedPositionIds.has(positionId)", html)
        self.assertIn("excluded_position_ids: Array.from(excludedPositionIds)", html)
        self.assertIn("Auswahl speichern", html)


class WledTests(unittest.TestCase):
    def setUp(self):
        config.colors = {"start": "FF0000"}
        config.hole2LEDS = {7: [101]}
        config.wled_controllers = [
            {"ip": "192.0.2.10", "start": 100, "end": 102},
        ]

    @patch("utils.requests.post")
    def test_sends_global_led_as_controller_local_id(self, post):
        post.return_value = Mock()

        result = utils.sendLightToBoulderwall({7: "start"})

        self.assertEqual(result, {101: "FF0000"})
        self.assertEqual(
            post.call_args_list,
            [
                call(
                    "http://192.0.2.10/json/state",
                    json={"on": False, "bri": 255},
                ),
                call(
                    "http://192.0.2.10/json/state",
                    json={
                        "on": True,
                        "bri": 255,
                        "seg": {"i": [1, "FF0000"]},
                    },
                ),
            ],
        )

    @patch("utils.requests.post")
    def test_bright_mode_sets_unselected_leds_to_dim_white(self, post):
        post.return_value = Mock()

        utils.sendLightToBoulderwall({7: "start"}, mode="bright")

        self.assertEqual(
            post.call_args_list[-1],
            call(
                "http://192.0.2.10/json/state",
                json={
                    "on": True,
                    "bri": 255,
                    "seg": {
                        "i": [
                            0,
                            "333333",
                            1,
                            "FF0000",
                            2,
                            "333333",
                        ],
                    },
                },
            ),
        )

    @patch("utils.requests.post")
    def test_light_id_uses_matching_controller_range(self, post):
        response = Mock()
        post.return_value = response

        result = utils.lightUpHoldId(102, "00FF00")

        self.assertIs(result, response)
        self.assertEqual(
            post.call_args_list[-1],
            call(
                "http://192.0.2.10/json/state",
                json={
                    "on": True,
                    "bri": 255,
                    "seg": {"i": [2, "00FF00"]},
                },
            ),
        )

    @patch("utils.requests.post")
    def test_rejects_led_outside_all_controller_ranges(self, post):
        post.return_value = Mock()

        with self.assertRaisesRegex(ValueError, "LED ID 99"):
            utils.lightUpHoldId(99, "00FF00")


if __name__ == "__main__":
    unittest.main()
