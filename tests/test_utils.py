import asyncio
import json
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
config.wled_controllers = [
    {"ip": "192.0.2.10", "start": 100, "end": 102},
]
config.hole2LEDS = {0: [100], 1: [101], 2: [102]}
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
            led_start_corner="bottom_right",
            led_direction="horizontal",
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

    def test_vertical_grid_can_start_top_right(self):
        grid = utils.generate_grid(
            (0, 0),
            (20, 0),
            (20, 10),
            (0, 10),
            2,
            3,
            led_start_corner="top_right",
            led_direction="vertical",
        )

        self.assertEqual(
            grid,
            {
                0: (20, 0),
                1: (20, 10),
                2: (10, 10),
                3: (10, 0),
                4: (0, 0),
                5: (0, 10),
            },
        )

    def test_default_cable_layout_starts_bottom_left_and_runs_vertically(self):
        grid = utils.generate_grid(
            (0, 0),
            (20, 0),
            (20, 10),
            (0, 10),
            2,
            3,
        )

        self.assertEqual(
            grid,
            {
                0: (0, 10),
                1: (0, 0),
                2: (10, 0),
                3: (10, 10),
                4: (20, 10),
                5: (20, 0),
            },
        )

    def test_all_start_corners_place_led_zero_at_requested_corner(self):
        expected_led_zero = {
            "top_left": (0, 0),
            "top_right": (20, 0),
            "bottom_left": (0, 10),
            "bottom_right": (20, 10),
        }

        for direction in ("horizontal", "vertical"):
            for corner, expected in expected_led_zero.items():
                with self.subTest(direction=direction, corner=corner):
                    grid = utils.generate_grid(
                        (0, 0),
                        (20, 0),
                        (20, 10),
                        (0, 10),
                        2,
                        3,
                        led_start_corner=corner,
                        led_direction=direction,
                    )
                    self.assertEqual(grid[0], expected)

    def test_rejects_invalid_led_cable_settings(self):
        with self.assertRaisesRegex(ValueError, "LED start corner"):
            utils.generate_grid(
                (0, 0), (20, 0), (20, 10), (0, 10), 2, 3,
                led_start_corner="center",
            )

        with self.assertRaisesRegex(ValueError, "LED direction"):
            utils.generate_grid(
                (0, 0), (20, 0), (20, 10), (0, 10), 2, 3,
                led_direction="diagonal",
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

    @patch("main.requests.get")
    def test_wall_creation_loads_saved_settings(self, get):
        wall_id = 987653
        wall = {
            "id": wall_id,
            "angle_adjustable": False,
            "created_at": "2026-01-01",
            "name": "Saved wall",
            "updated_at": "2026-01-02",
            "image_height": 400,
            "image_width": 200,
            "image_url": "https://example.com/wall.jpg",
            "maximum_angle": 40,
            "minimum_angle": 10,
            "holds": [],
        }
        response = Mock()
        response.text = json.dumps(wall)
        get.return_value = response
        db = main.SessionLocal()
        db.query(main.WallCreationDB).filter(
            main.WallCreationDB.wallid == wall_id
        ).delete(synchronize_session=False)
        db.query(main.WallDB).filter(main.WallDB.id == wall_id).delete()
        db.add(main.WallDB(**wall))
        db.add(main.WallCreationDB(
            wallid=wall_id,
            settings={
                "points": [
                    {"x": 0, "y": 0}, {"x": 200, "y": 0},
                    {"x": 200, "y": 400}, {"x": 0, "y": 400},
                ],
                "r": 18,
                "c": 11,
                "alternating": False,
                "alternating_start_column": 0,
                "led_start_corner": "top_right",
                "led_direction": "vertical",
                "excluded_position_ids": [3],
                "positions": {"0": [200, 0]},
                "position_led_ids": {"0": 0},
                "holds2led": {},
            },
        ))
        db.commit()
        db.close()

        try:
            result = asyncio.run(main.wall_creation(str(wall_id)))

            html = result.body.decode()
            self.assertIn('"r":18,"c":11', html)
            self.assertIn('"led_start_corner":"top_right"', html)
            self.assertIn('"excluded_position_ids":[3]', html)
        finally:
            db = main.SessionLocal()
            db.query(main.WallCreationDB).filter(
                main.WallCreationDB.wallid == wall_id
            ).delete(synchronize_session=False)
            db.query(main.WallDB).filter(main.WallDB.id == wall_id).delete()
            db.commit()
            db.close()


class DefineHoldsTests(unittest.TestCase):
    wall_id = 987654

    def setUp(self):
        db = main.SessionLocal()
        db.query(main.WallCreationDB).filter(
            main.WallCreationDB.wallid == self.wall_id
        ).delete(synchronize_session=False)
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
        db.query(main.WallCreationDB).filter(
            main.WallCreationDB.wallid == self.wall_id
        ).delete(synchronize_session=False)
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
        saved_creation = db.query(main.WallCreationDB).filter(
            main.WallCreationDB.wallid == self.wall_id
        ).one()
        self.assertEqual(saved_creation.settings["r"], 2)
        self.assertEqual(saved_creation.settings["c"], 3)
        self.assertEqual(saved_creation.settings["excluded_position_ids"], [1])
        self.assertEqual(saved_creation.settings["led_start_corner"], "bottom_left")
        self.assertEqual(saved_creation.settings["led_direction"], "vertical")
        self.assertEqual(saved_creation.settings["coordinate_space"], "wall_image")
        db.close()

    def test_hold_at_excluded_position_is_not_moved_to_active_position(self):
        db = main.SessionLocal()
        wall = db.query(main.WallDB).filter(main.WallDB.id == self.wall_id).one()
        wall.holds = [
            {"id": "excluded-hold", "mask": [[10, 10], [10, 10]]},
            {"id": "active-hold", "mask": [[20, 0], [20, 0]]},
        ]
        db.commit()
        db.close()

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

        self.assertEqual(result["holds2led"], {"active-hold": 1})

        db = main.SessionLocal()
        mappings = {
            mapping.holdid: mapping.ledid
            for mapping in db.query(main.Hold2ledDB).filter(
                main.Hold2ledDB.holdid.like(f"{self.wall_id}_%")
            )
        }
        db.close()
        self.assertEqual(
            mappings,
            {f"{self.wall_id}_active-hold": 1},
        )

    def test_saving_replaces_stale_hold_mappings_for_the_wall(self):
        db = main.SessionLocal()
        db.add(main.Hold2ledDB(
            holdid=f"{self.wall_id}_removed-hold",
            ledid=99,
        ))
        db.commit()
        db.close()

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
        )

        asyncio.run(main.define_holds(payload))

        db = main.SessionLocal()
        stale_mapping = db.query(main.Hold2ledDB).filter(
            main.Hold2ledDB.holdid == f"{self.wall_id}_removed-hold"
        ).first()
        self.assertIsNone(stale_mapping)
        db.close()

    def test_top_right_vertical_layout_skips_excluded_positions_in_cable_order(self):
        payload = main.WallTranslation(
            wallid=self.wall_id,
            p1x=0,
            p1y=0,
            p2x=20,
            p2y=0,
            p3x=20,
            p3y=20,
            p4x=0,
            p4y=20,
            r=3,
            c=3,
            led_start_corner="top_right",
            led_direction="vertical",
            # x o o
            # x x o
            # x x x
            excluded_position_ids=[0, 1, 5],
        )

        result = asyncio.run(main.define_holds(payload))

        self.assertEqual(
            result["grid"],
            {
                0: (20, 20),  # unten rechts
                1: (10, 20),  # unten mitte
                2: (10, 10),  # mitte mitte
                3: (0, 0),    # oben links
                4: (0, 10),   # mitte links
                5: (0, 20),   # unten links
            },
        )
        self.assertEqual(
            result["position_led_ids"],
            {2: 0, 3: 1, 4: 2, 6: 3, 7: 4, 8: 5},
        )


class PathPrefixTests(unittest.TestCase):
    def test_normalizes_path_prefix(self):
        self.assertEqual(main.normalize_path_prefix("cruxwledbridge/"), "/cruxwledbridge")
        self.assertEqual(main.normalize_path_prefix("/"), "")

    def test_wall_lighting_uses_path_prefix(self):
        html = main.return_wall_lighting_html("/cruxwledbridge")

        self.assertIn("fetch('/cruxwledbridge/wall_lighting_mode'", html)
        self.assertIn("Wand-Beleuchtungsmodus", html)
        self.assertIn("Dunkel – nur Boulder", html)
        self.assertIn("Hell – freie LEDs gedimmt", html)

    def test_wall_lighting_routes_replace_toggle_gui_routes(self):
        routes = {(route.path, tuple(route.methods or [])) for route in main.app.routes}

        self.assertTrue(any(path == "/wall_lighting" and "GET" in methods for path, methods in routes))
        self.assertTrue(any(path == "/wall_lighting_mode" and "POST" in methods for path, methods in routes))
        self.assertFalse(any(path in {"/toggle_gui", "/toggle_mode"} for path, _ in routes))

    def test_wall_lighting_mode_updates_server_state(self):
        original_mode = main.wall_lighting_mode
        try:
            result = asyncio.run(
                main.set_wall_lighting_mode(main.WallLightingMode(mode="bright"))
            )

            self.assertEqual(main.wall_lighting_mode, "bright")
            self.assertEqual(result, {"message": "Wall lighting mode set to bright"})
        finally:
            main.wall_lighting_mode = original_mode

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

    def test_wall_selector_offers_led_cable_layout(self):
        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
            "/cruxwledbridge",
        )

        self.assertIn('id="led-start-corner"', html)
        self.assertIn('<option value="top_right">Oben rechts</option>', html)
        self.assertIn('<option value="bottom_left" selected>Unten links</option>', html)
        self.assertIn('id="led-direction"', html)
        self.assertIn('<option value="vertical" selected>Vertikal (spaltenweise)</option>', html)
        self.assertIn("led_start_corner: ledStartCorner", html)
        self.assertIn("led_direction: ledDirection", html)

    def test_wall_selector_can_exclude_rendered_positions(self):
        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
            "/cruxwledbridge",
        )

        self.assertIn("excludedPositionIds.has(positionId)", html)
        self.assertIn("excluded_position_ids: Array.from(excludedPositionIds)", html)
        self.assertIn("Auswahl speichern", html)

    def test_wall_selector_maps_display_pixels_to_original_image_pixels(self):
        html = main.returnwallhtml(
            {
                "id": 216943,
                "image_url": "https://example.com/wall.jpg",
                "image_width": 200,
                "image_height": 400,
            },
            "/cruxwledbridge",
        )

        self.assertIn("function displayToImage(x, y)", html)
        self.assertIn("const wallImageWidth = 200", html)
        self.assertIn("const wallImageHeight = 400", html)
        self.assertIn("x * coordinateWidth() / rect.width", html)
        self.assertIn("y * coordinateHeight() / rect.height", html)
        self.assertIn("function imageToDisplay(point)", html)
        self.assertIn("point.x * rect.width / coordinateWidth()", html)
        self.assertIn("points.push(displayToImage(x, y))", html)
        self.assertIn("const rect = climbingImage.getBoundingClientRect()", html)
        self.assertIn("window.addEventListener('resize'", html)

    def test_wall_selector_migrates_saved_natural_image_coordinates(self):
        html = main.returnwallhtml(
            {
                "id": 216943,
                "image_url": "https://example.com/wall.jpg",
                "image_width": 200,
                "image_height": 400,
            },
            "/cruxwledbridge",
            {
                "points": [{"x": 100, "y": 200}],
                "positions": {0: [100, 200]},
            },
        )

        self.assertIn("savedCreation.coordinate_space === 'wall_image'", html)
        self.assertIn("wallImageWidth / climbingImage.naturalWidth", html)
        self.assertIn("wallImageHeight / climbingImage.naturalHeight", html)
        self.assertIn("normalizeSavedCreationCoordinates();", html)

    def test_wall_selector_restores_saved_creation(self):
        saved_creation = {
            "points": [
                {"x": 10, "y": 20},
                {"x": 190, "y": 20},
                {"x": 190, "y": 380},
                {"x": 10, "y": 380},
            ],
            "r": 18,
            "c": 11,
            "alternating": True,
            "alternating_start_column": 1,
            "led_start_corner": "top_right",
            "led_direction": "vertical",
            "excluded_position_ids": [2, 7],
            "positions": {0: [190, 20], 1: [190, 40]},
            "position_led_ids": {0: 0, 1: 1},
            "holds2led": {"hold-a": 1},
        }

        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
            "/cruxwledbridge",
            saved_creation,
        )

        self.assertIn('"r":18,"c":11,"alternating":true', html)
        self.assertIn('"led_start_corner":"top_right"', html)
        self.assertIn('let points = savedCreation.points || []', html)
        self.assertIn('rows.value = savedCreation.r', html)
        self.assertIn('excludedPositionIds = new Set(savedCreation.excluded_position_ids || [])', html)
        self.assertIn("climbingImage.addEventListener('load', initializeSavedCreation", html)


class WledTests(unittest.TestCase):
    def setUp(self):
        config.colors = {"start": "FF0000"}
        config.wled_controllers = [
            {"ip": "192.0.2.10", "start": 100, "end": 102},
        ]
        config.hole2LEDS = {0: [100], 1: [101], 2: [102]}

    @patch("utils.requests.post")
    def test_sends_global_led_as_controller_local_id(self, post):
        post.return_value = Mock()

        result = utils.sendLightToBoulderwall({1: "start"})

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

        utils.sendLightToBoulderwall({1: "start"}, mode="bright")

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
    def test_hole_mapping_can_skip_physical_leds_and_use_multiple_leds(self, post):
        post.return_value = Mock()
        config.hole2LEDS = {
            0: [100],
            1: [102, 103],
        }
        config.wled_controllers = [
            {"ip": "192.0.2.10", "start": 100, "end": 103},
        ]

        result = utils.sendLightToBoulderwall({1: "start"})

        self.assertEqual(result, {102: "FF0000", 103: "FF0000"})
        self.assertEqual(
            post.call_args_list[-1],
            call(
                "http://192.0.2.10/json/state",
                json={
                    "on": True,
                    "bri": 255,
                    "seg": {"i": [2, "FF0000", 3, "FF0000"]},
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
