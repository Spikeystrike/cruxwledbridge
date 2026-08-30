import asyncio
import json
import logging
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
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
import config_loader

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
import main


class ConfigLoaderTests(unittest.TestCase):
    def test_validate_config_accepts_configured_values(self):
        configured = types.SimpleNamespace(
            token="configured-token",
            wled_controllers=[{"ip": "192.168.1.50", "start": 0, "end": 399}],
        )

        self.assertIs(config_loader.validate_config(configured), configured)

    def test_validate_config_rejects_empty_token(self):
        unconfigured = types.SimpleNamespace(
            token="",
            wled_controllers=[{"ip": "192.168.1.50", "start": 0, "end": 399}],
        )

        with patch.object(config_loader.sys, "stderr") as stderr:
            with self.assertRaisesRegex(SystemExit, "1"):
                config_loader.validate_config(unconfigured)

        message = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn("token is empty", message)
        self.assertIn("Edit config/config.py", message)

    def test_validate_config_rejects_example_wled_controller(self):
        unconfigured = types.SimpleNamespace(
            token="configured-token",
            wled_controllers=[{"ip": "192.0.2.10", "start": 0, "end": 399}],
        )

        with patch.object(config_loader.sys, "stderr") as stderr:
            with self.assertRaisesRegex(SystemExit, "1"):
                config_loader.validate_config(unconfigured)

        message = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn("example controller 192.0.2.10", message)

    def test_load_config_exits_for_unmodified_example_values(self):
        unconfigured = types.SimpleNamespace(
            token="",
            wled_controllers=[{"ip": "192.0.2.10", "start": 0, "end": 399}],
        )

        with patch.object(config_loader.sys, "stderr") as stderr:
            with patch.object(
                config_loader.importlib,
                "import_module",
                return_value=unconfigured,
            ):
                with self.assertRaisesRegex(SystemExit, "1"):
                    config_loader.load_config()

        message = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn("token is empty", message)
        self.assertIn("example controller 192.0.2.10", message)

    def test_initialize_config_prefers_bundled_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mounted = root / "mounted"
            bundled = root / "bundled"
            mounted.mkdir()
            bundled.mkdir()
            (bundled / "config.py").write_text("source = 'config'\n")
            (bundled / "config.example.py").write_text("source = 'example'\n")

            target = config_loader.initialize_config(mounted, bundled)

            self.assertEqual(target, mounted / "config.py")
            self.assertEqual(target.read_text(), "source = 'config'\n")

    def test_initialize_config_falls_back_to_example(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mounted = root / "mounted"
            bundled = root / "bundled"
            mounted.mkdir()
            bundled.mkdir()
            (bundled / "config.example.py").write_text("source = 'example'\n")

            target = config_loader.initialize_config(mounted, bundled)

            self.assertEqual(target, mounted / "config.py")
            self.assertEqual(target.read_text(), "source = 'example'\n")

    def test_initialize_config_does_not_overwrite_existing_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mounted = root / "mounted"
            bundled = root / "bundled"
            mounted.mkdir()
            bundled.mkdir()
            (mounted / "config.py").write_text("source = 'mounted'\n")
            (bundled / "config.py").write_text("source = 'bundled'\n")

            config_loader.initialize_config(mounted, bundled)

            self.assertEqual(
                (mounted / "config.py").read_text(),
                "source = 'mounted'\n",
            )

    def test_missing_config_prints_error_and_exits(self):
        missing = ModuleNotFoundError("No module named 'config.config'")
        missing.name = "config.config"

        with patch.object(config_loader.sys, "stderr") as stderr:
            with patch.object(config_loader, "initialize_config", return_value=None):
                with patch.object(
                    config_loader.importlib,
                    "import_module",
                    side_effect=missing,
                ):
                    with self.assertRaisesRegex(SystemExit, "1"):
                        config_loader.load_config()

        message = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn("ERROR: config/config.py is missing", message)
        self.assertIn("No config.py or config.example.py", message)

    def test_config_dependency_import_errors_are_not_hidden(self):
        dependency_error = ModuleNotFoundError("No module named 'custom_dependency'")
        dependency_error.name = "custom_dependency"

        with patch.object(
            config_loader.importlib,
            "import_module",
            side_effect=dependency_error,
        ):
            with self.assertRaises(ModuleNotFoundError) as caught:
                config_loader.load_config()

        self.assertIs(caught.exception, dependency_error)


class AccessLoggingTests(unittest.TestCase):
    @staticmethod
    def make_request(path="/viewed", method="POST"):
        return main.Request(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "root_path": "",
                "headers": [],
                "client": ("172.29.108.2", 57358),
                "server": ("testserver", 80),
            }
        )

    def test_access_logger_places_compact_datetime_after_level(self):
        handler = next(
            handler
            for handler in main.access_logger.handlers
            if getattr(handler, "cruxwledbridge_access_handler", False)
        )
        record = logging.LogRecord(
            "cruxwledbridge.access",
            logging.INFO,
            __file__,
            1,
            "message",
            (),
            None,
        )

        self.assertRegex(
            handler.format(record),
            r"^INFO: \d{8}-\d{6} message$",
        )

    def test_lifespan_disables_uvicorn_access_log(self):
        uvicorn_access_logger = logging.getLogger("uvicorn.access")
        previous_disabled = uvicorn_access_logger.disabled
        uvicorn_access_logger.disabled = False

        async def enter_lifespan():
            async with main.app.router.lifespan_context(main.app):
                self.assertTrue(uvicorn_access_logger.disabled)

        try:
            asyncio.run(enter_lifespan())
        finally:
            uvicorn_access_logger.disabled = previous_disabled

    def test_regular_access_log_keeps_original_request_information(self):
        request = self.make_request(path="/wall_lighting", method="GET")

        self.assertEqual(
            main.format_access_log(request, 200),
            '172.29.108.2:57358 - "GET /wall_lighting HTTP/1.1" 200 OK',
        )

    def test_access_middleware_logs_completed_response(self):
        request = self.make_request(path="/", method="GET")
        response = Mock(status_code=200)

        async def call_next(received_request):
            self.assertIs(received_request, request)
            return response

        with patch.object(main.access_logger, "info") as info:
            returned_response = asyncio.run(main.log_access(request, call_next))

        self.assertIs(returned_response, response)
        info.assert_called_once_with(
            '172.29.108.2:57358 - "GET / HTTP/1.1" 200 OK'
        )

    def test_viewed_access_log_identifies_climb_after_request(self):
        request = self.make_request()
        request.state.viewed_climb = {
            "id": 321,
            "name": 'Blue "Moon"',
            "wall_id": 44,
        }

        self.assertEqual(
            main.format_access_log(request, 200),
            '172.29.108.2:57358 - "POST /viewed HTTP/1.1" '
            'climb_id=321 climb_name="Blue \\"Moon\\"" wall_id=44 200 OK',
        )

    def test_sent_access_log_identifies_climb_after_request(self):
        request = self.make_request(path="/sent")
        request.state.sent_climb = {
            "send_id": 55,
            "climb_id": 321,
            "climb_name": 'Blue "Moon"',
            "wall_id": 44,
        }

        self.assertEqual(
            main.format_access_log(request, 200),
            '172.29.108.2:57358 - "POST /sent HTTP/1.1" '
            'climb_id=321 climb_name="Blue \\"Moon\\"" wall_id=44 200 OK',
        )

    @patch("main.schedule_route_timeout")
    @patch("main.sendLightToBoulderwall")
    @patch("main.SessionLocal")
    def test_viewed_handler_adds_climb_context(
        self,
        session_local,
        send_lights,
        schedule_timeout,
    ):
        request = self.make_request()
        payload = main.PayL(
            payload=main.Climb(
                id=321,
                wall_id=44,
                angle=None,
                color=None,
                created_at=None,
                description=None,
                foot_rules=None,
                grade="6B",
                gym_name=None,
                gym_slug=None,
                holds=[],
                image_height=None,
                image_url="https://example.com/climb.jpg",
                image_width=100,
                name="Blue Moon",
                number_of_comments=0,
                number_of_sends=0,
                sends=None,
                setter_id=1,
                setter_name="Setter",
                unedited_image_url="https://example.com/climb-original.jpg",
                unset_at=None,
                updated_at="2026-08-06T00:00:00Z",
            )
        )

        asyncio.run(main.viewed(payload, request))

        self.assertEqual(
            request.state.viewed_climb,
            {"id": 321, "name": "Blue Moon", "wall_id": 44},
        )
        send_lights.assert_called_once_with({}, "dark", 20, 100)
        schedule_timeout.assert_called_once_with()
        session_local.return_value.close.assert_called_once_with()


class AppSettingsTests(unittest.TestCase):
    keys = (
        "test_future_boolean_setting",
        "test_future_nested_setting",
        "wall_lighting_mode",
        "bright_wall_brightness_percent",
        "boulder_brightness_percent",
        "hold_lighting_direction",
        "celebration_effect",
    )

    def tearDown(self):
        db = main.SessionLocal()
        db.query(main.AppSettingDB).filter(
            main.AppSettingDB.key.in_(self.keys)
        ).delete(synchronize_session=False)
        db.commit()
        db.close()

    def test_generic_store_persists_current_and_future_settings_together(self):
        main.persist_app_settings({
            "test_future_boolean_setting": True,
            "test_future_nested_setting": {"threshold": 4},
        })

        self.assertTrue(main.load_app_setting("test_future_boolean_setting"))
        self.assertEqual(
            main.load_app_setting("test_future_nested_setting"),
            {"threshold": 4},
        )

    def test_wall_lighting_loaders_validate_persisted_values(self):
        saved = {
            "wall_lighting_mode": "bright",
            "bright_wall_brightness_percent": 73,
            "boulder_brightness_percent": 42,
            "hold_lighting_direction": "both",
        }
        with patch(
            "main.load_app_setting",
            side_effect=lambda key, default=None: saved.get(key, default),
        ):
            self.assertEqual(main.load_wall_lighting_mode(), "bright")
            self.assertEqual(
                main._load_percent_setting("bright_wall_brightness_percent", 20),
                73,
            )
            self.assertEqual(
                main._load_percent_setting("boulder_brightness_percent", 100),
                42,
            )
            self.assertEqual(main.load_hold_lighting_direction(), "both")

    def test_wall_lighting_settings_survive_database_reload(self):
        main.persist_app_settings({
            "wall_lighting_mode": "bright",
            "bright_wall_brightness_percent": 34,
            "boulder_brightness_percent": 76,
            "hold_lighting_direction": "above",
            "celebration_effect": "fireworks",
        })

        self.assertEqual(main.load_wall_lighting_mode(), "bright")
        self.assertEqual(
            main._load_percent_setting("bright_wall_brightness_percent", 20),
            34,
        )
        self.assertEqual(
            main._load_percent_setting("boulder_brightness_percent", 100),
            76,
        )
        self.assertEqual(main.load_hold_lighting_direction(), "above")
        self.assertEqual(main.load_celebration_effect(), "fireworks")

    def test_invalid_persisted_hold_lighting_direction_uses_below(self):
        with patch("main.load_app_setting", return_value="sideways"):
            self.assertEqual(main.load_hold_lighting_direction(), "below")


class CelebrationTests(unittest.TestCase):
    def setUp(self):
        self.original_effect = main.celebration_effect
        self.original_duration = main.celebration_duration_seconds
        self.original_holds = main.current_wall_holds
        self.original_pending_holds = main._pending_viewed_holds
        self.original_mode = main.wall_lighting_mode
        self.original_brightness = main.bright_wall_brightness_percent
        self.original_boulder_brightness = main.boulder_brightness_percent
        self.original_generation = main._celebration_generation
        self.original_active = main._celebration_active
        self.original_route_active = main._route_lighting_active
        self.original_route_generation = main._route_timeout_generation
        self.original_route_task = main._route_timeout_task
        self.original_route_sleep_task = main._route_timeout_sleep_task

    def tearDown(self):
        main.celebration_effect = self.original_effect
        main.celebration_duration_seconds = self.original_duration
        main.current_wall_holds = self.original_holds
        main._pending_viewed_holds = self.original_pending_holds
        main.wall_lighting_mode = self.original_mode
        main.bright_wall_brightness_percent = self.original_brightness
        main.boulder_brightness_percent = self.original_boulder_brightness
        main._celebration_generation = self.original_generation
        main._celebration_active = self.original_active
        main._route_lighting_active = self.original_route_active
        main._route_timeout_generation = self.original_route_generation
        main._route_timeout_task = self.original_route_task
        main._route_timeout_sleep_task = self.original_route_sleep_task

    @patch("main.schedule_celebration", return_value=True)
    def test_climb_sent_webhook_accepts_full_send_and_starts_effect(self, schedule):
        request = AccessLoggingTests.make_request(path="/sent")
        payload = main.SentPayL(
            payload={
                "id": 55,
                "created_at": "2026-08-06T01:00:00Z",
                "repeat": False,
                "send_date": "2026-08-06",
                "climb": {
                    "id": 321,
                    "name": "Blue Moon",
                    "grade": "6B",
                    "wall_id": 44,
                },
                "user": {"id": 99, "name": "Climber"},
            }
        )

        result = asyncio.run(main.sent(payload, request))

        schedule.assert_called_once_with()
        self.assertEqual(
            request.state.sent_climb,
            {
                "send_id": 55,
                "climb_id": 321,
                "climb_name": "Blue Moon",
                "wall_id": 44,
            },
        )
        self.assertEqual(result["message"], "Celebration started")

    def test_disabled_celebration_does_not_schedule_task(self):
        main.celebration_effect = "off"

        self.assertFalse(main.schedule_celebration())

    def test_celebration_selection_is_persisted_in_database(self):
        db = main.SessionLocal()
        previous = db.query(main.AppSettingDB).filter(
            main.AppSettingDB.key == "celebration_effect"
        ).first()
        previous_value = previous.value if previous else None
        db.close()

        try:
            main.persist_celebration_effect("pride")
            self.assertEqual(main.load_celebration_effect(), "pride")
        finally:
            db = main.SessionLocal()
            setting = db.query(main.AppSettingDB).filter(
                main.AppSettingDB.key == "celebration_effect"
            ).first()
            if previous_value is None:
                if setting:
                    db.delete(setting)
            elif setting:
                setting.value = previous_value
            else:
                db.add(main.AppSettingDB(
                    key="celebration_effect",
                    value=previous_value,
                ))
            db.commit()
            db.close()

    @patch("main.schedule_route_timeout")
    @patch("main.sendLightToBoulderwall")
    @patch("main.playCelebrationEffect")
    def test_celebration_restores_latest_wall_state(
        self,
        play_effect,
        send_lights,
        schedule_timeout,
    ):
        main.celebration_duration_seconds = 0
        main.current_wall_holds = {2: "start"}
        main._pending_viewed_holds = {1: "finish"}
        main.wall_lighting_mode = "bright"
        main.bright_wall_brightness_percent = 65
        main.boulder_brightness_percent = 70
        main._celebration_generation = 8
        main._celebration_active = True

        asyncio.run(main._run_celebration("rainbow", 8))

        play_effect.assert_called_once_with("rainbow")
        send_lights.assert_called_once_with({1: "finish"}, "bright", 65, 70)
        schedule_timeout.assert_called_once_with()
        self.assertEqual(main.current_wall_holds, {1: "finish"})
        self.assertIsNone(main._pending_viewed_holds)
        self.assertFalse(main._celebration_active)

    @patch("main.sendLightToBoulderwall")
    def test_viewed_during_celebration_is_deferred_until_it_finishes(self, send_lights):
        main.current_wall_holds = {2: "start"}
        main._pending_viewed_holds = None
        main._celebration_active = True

        hit = Mock()
        hit.ledid = 1
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = hit
        request = AccessLoggingTests.make_request(path="/viewed")
        payload = main.PayL(
            payload={
                "id": 322,
                "wall_id": 44,
                "angle": None,
                "color": None,
                "created_at": None,
                "description": None,
                "foot_rules": None,
                "grade": "6B",
                "gym_name": None,
                "gym_slug": None,
                "holds": [{"id": "hold-1", "hold_type": "start", "mask": []}],
                "image_height": None,
                "image_url": "https://example.com/climb.jpg",
                "image_width": 100,
                "name": "Next Boulder",
                "number_of_comments": 0,
                "number_of_sends": 0,
                "sends": None,
                "setter_id": 1,
                "setter_name": "Setter",
                "unedited_image_url": "https://example.com/climb-original.jpg",
                "unset_at": None,
                "updated_at": "2026-08-06T00:00:00Z",
            }
        )

        with patch("main.SessionLocal", return_value=db):
            asyncio.run(main.viewed(payload, request))

        send_lights.assert_not_called()
        self.assertEqual(main.current_wall_holds, {2: "start"})
        self.assertEqual(main._pending_viewed_holds, {1: "start"})
        db.close.assert_called_once_with()

    @patch("main._restore_current_wall")
    @patch("main.playCelebrationEffect")
    def test_older_celebration_cannot_deactivate_newer_one(self, play_effect, restore):
        main.celebration_duration_seconds = 0
        main._celebration_generation = 8
        main._celebration_active = True

        async def schedule_newer_celebration_during_restore():
            main._celebration_generation = 9
            main._celebration_active = True

        restore.side_effect = schedule_newer_celebration_during_restore

        asyncio.run(main._run_celebration("rainbow", 8))

        restore.assert_awaited_once_with()
        self.assertTrue(main._celebration_active)
        self.assertEqual(main._celebration_generation, 9)

    @patch("main.persist_celebration_effect")
    def test_celebration_selection_can_be_changed_or_disabled(self, persist):
        result = asyncio.run(
            main.set_celebration_effect(
                main.CelebrationEffectSelection(effect="fireworks")
            )
        )

        self.assertEqual(main.celebration_effect, "fireworks")
        self.assertEqual(result["effect"], "fireworks")
        persist.assert_called_once_with("fireworks")

        result = asyncio.run(
            main.set_celebration_effect(main.CelebrationEffectSelection(effect="off"))
        )
        self.assertEqual(main.celebration_effect, "off")
        self.assertEqual(result["effect"], "off")


class EnergySavingTests(unittest.TestCase):
    def setUp(self):
        self.original_minutes = main.route_timeout_minutes
        self.original_generation = main._route_timeout_generation
        self.original_task = main._route_timeout_task
        self.original_sleep_task = main._route_timeout_sleep_task
        self.original_active = main._route_lighting_active
        self.original_celebration_active = main._celebration_active
        self.original_brightness = main.bright_wall_brightness_percent
        self.original_boulder_brightness = main.boulder_brightness_percent
        main._route_timeout_task = None
        main._route_timeout_sleep_task = None
        main._route_timeout_generation = 0
        main._route_lighting_active = False
        main._celebration_active = False

    def tearDown(self):
        main._cancel_route_timeout()
        main.route_timeout_minutes = self.original_minutes
        main._route_timeout_generation = self.original_generation
        main._route_timeout_task = self.original_task
        main._route_timeout_sleep_task = self.original_sleep_task
        main._route_lighting_active = self.original_active
        main._celebration_active = self.original_celebration_active
        main.bright_wall_brightness_percent = self.original_brightness
        main.boulder_brightness_percent = self.original_boulder_brightness

    def test_route_timeout_is_persisted_in_database(self):
        db = main.SessionLocal()
        previous = db.query(main.AppSettingDB).filter(
            main.AppSettingDB.key == "route_timeout_minutes"
        ).first()
        previous_value = previous.value if previous else None
        db.close()

        try:
            main.persist_route_timeout_minutes(17)
            self.assertEqual(main.load_route_timeout_minutes(), 17)
        finally:
            db = main.SessionLocal()
            setting = db.query(main.AppSettingDB).filter(
                main.AppSettingDB.key == "route_timeout_minutes"
            ).first()
            if previous_value is None:
                if setting:
                    db.delete(setting)
            elif setting:
                setting.value = previous_value
            else:
                db.add(main.AppSettingDB(
                    key="route_timeout_minutes",
                    value=previous_value,
                ))
            db.commit()
            db.close()

    @patch("main.schedule_route_timeout", return_value=True)
    @patch("main.persist_route_timeout_minutes")
    def test_setting_timeout_updates_state_and_restarts_active_route(
        self,
        persist,
        schedule_timeout,
    ):
        main._route_lighting_active = True

        result = asyncio.run(main.set_route_timeout(
            main.EnergySavingSettings(route_timeout_minutes=15)
        ))

        self.assertEqual(main.route_timeout_minutes, 15)
        self.assertEqual(result["route_timeout_minutes"], 15)
        persist.assert_called_once_with(15)
        schedule_timeout.assert_called_once_with()

    def test_negative_timeout_is_rejected(self):
        with self.assertRaises(ValueError):
            main.EnergySavingSettings(route_timeout_minutes=-1)

    def test_zero_disables_automatic_switch_off(self):
        main.route_timeout_minutes = 0

        async def schedule():
            return main.schedule_route_timeout()

        self.assertFalse(asyncio.run(schedule()))
        self.assertIsNone(main._route_timeout_task)

    @patch("main.sendLightToBoulderwall")
    def test_expired_timeout_switches_route_off(self, send_lights):
        main._route_timeout_generation = 7
        main._route_lighting_active = True
        main.bright_wall_brightness_percent = 65
        main.boulder_brightness_percent = 70

        asyncio.run(main._run_route_timeout(0, 7))

        send_lights.assert_called_once_with({}, "dark", 65, 70)
        self.assertFalse(main._route_lighting_active)

    @patch("main.sendLightToBoulderwall")
    def test_outdated_timeout_cannot_switch_newer_route_off(self, send_lights):
        main._route_timeout_generation = 8
        main._route_lighting_active = True

        asyncio.run(main._run_route_timeout(0, 7))

        send_lights.assert_not_called()
        self.assertTrue(main._route_lighting_active)


class WallHoldKeyTests(unittest.TestCase):
    def test_combines_wall_and_hold_ids(self):
        self.assertEqual(
            utils.wall_hold_key(216943, "8ba97f45a6656519"),
            "216943_8ba97f45a6656519",
        )


class GridGenerationTests(unittest.TestCase):
    def test_nearby_hold_detection_uses_local_grid_spacing(self):
        occupied = utils.positions_near_holds(
            [
                {"id": "near", "mask": [[4, 0], [4, 0]]},
                {"id": "far", "mask": [[100, 0], [100, 0]]},
            ],
            [{0: (0, 0), 1: (10, 0), 2: (20, 0)}],
        )

        self.assertEqual(occupied, {(0, 0)})

    def test_nearby_hold_is_assigned_to_only_one_of_multiple_grids(self):
        occupied = utils.positions_near_holds(
            [{"id": "hold", "mask": [[0, 0], [0, 0]]}],
            [{0: (0, 0)}, {0: (1, 0)}],
        )

        self.assertEqual(occupied, {(0, 0)})

    def test_standard_grid_keeps_all_columns(self):
        grid = utils.generate_grid((0, 0), (30, 0), (30, 10), (0, 10), 2, 4)

        self.assertEqual(len(grid), 8)
        self.assertEqual(set(grid), set(range(8)))

    def test_perspective_grid_uses_projective_row_spacing(self):
        grid = utils.generate_grid(
            (0, 0),
            (100, 0),
            (80, 100),
            (20, 100),
            3,
            3,
            led_start_corner="top_left",
            led_direction="horizontal",
        )

        self.assertEqual(grid[0], (0, 0))
        self.assertEqual(grid[2], (100, 0))
        self.assertEqual(grid[4], (50, 62))
        self.assertEqual(grid[6], (20, 100))
        self.assertEqual(grid[8], (80, 100))
        self.assertNotEqual(grid[4][1], 50)

    def test_rejects_degenerate_grid_corners(self):
        with self.assertRaisesRegex(ValueError, "non-degenerate quadrilateral"):
            utils.generate_grid(
                (0, 0),
                (10, 0),
                (20, 0),
                (30, 0),
                3,
                3,
            )

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
        self.assertIn('<html lang="en">', html)
        self.assertIn('id="language-toggle"', html)
        self.assertIn('data-i18n="page.heading">Wall selector</h1>', html)
        self.assertIn('data-gym-slug="kontors-keller"', html)
        self.assertIn("window.localStorage.setItem(", html)
        self.assertIn("'cruxwledbridge.favoriteGymSlug'", html)
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

    @patch("main.requests.get")
    def test_wall_creation_preserves_coordinate_basis_across_image_refresh(self, get):
        wall_id = 987652
        old_wall = {
            "id": wall_id,
            "angle_adjustable": False,
            "created_at": "2026-01-01",
            "name": "Resized wall",
            "updated_at": "2026-01-01",
            "image_height": 400,
            "image_width": 200,
            "image_url": "https://example.com/old-wall.jpg",
            "maximum_angle": 40,
            "minimum_angle": 10,
            "holds": [],
        }
        refreshed_wall = {
            **old_wall,
            "updated_at": "2026-01-02",
            "image_height": 800,
            "image_width": 400,
            "image_url": "https://example.com/new-wall.jpg",
        }
        response = Mock()
        response.text = json.dumps(refreshed_wall)
        get.return_value = response
        db = main.SessionLocal()
        db.query(main.WallCreationDB).filter(
            main.WallCreationDB.wallid == wall_id
        ).delete(synchronize_session=False)
        db.query(main.WallDB).filter(main.WallDB.id == wall_id).delete()
        db.add(main.WallDB(**old_wall))
        db.add(main.WallCreationDB(
            wallid=wall_id,
            settings={
                "coordinate_space": "wall_image",
                "points": [{"x": 100, "y": 200}],
                "positions": {"0": [100, 200]},
            },
        ))
        db.commit()
        db.close()

        try:
            result = asyncio.run(main.wall_creation(str(wall_id)))

            html = result.body.decode()
            self.assertIn('"coordinate_width":200', html)
            self.assertIn('"coordinate_height":400', html)
            self.assertIn("const wallImageWidth = 400", html)
            self.assertIn("const wallImageHeight = 800", html)

            db = main.SessionLocal()
            saved = db.query(main.WallCreationDB).filter(
                main.WallCreationDB.wallid == wall_id
            ).one()
            self.assertEqual(saved.settings["coordinate_width"], 200)
            self.assertEqual(saved.settings["coordinate_height"], 400)
            db.close()
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
        self.assertEqual(saved_creation.settings["coordinate_width"], 20)
        self.assertEqual(saved_creation.settings["coordinate_height"], 10)
        db.close()

    def test_new_grid_auto_excludes_empty_positions(self):
        db = main.SessionLocal()
        wall = db.query(main.WallDB).filter(main.WallDB.id == self.wall_id).one()
        wall.holds = [
            {"id": "left-hold", "mask": [[0, 0], [0, 0]]},
            {"id": "right-hold", "mask": [[20, 0], [20, 0]]},
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
            r=1,
            c=3,
            auto_exclude_empty=True,
            apply_auto_exclusions=True,
        )

        result = asyncio.run(main.define_holds(payload))

        self.assertEqual(result["excluded_position_ids"], [1])
        self.assertEqual(result["position_led_ids"], {0: 0, 2: 1})
        self.assertEqual(
            result["holds2led"],
            {"left-hold": 0, "right-hold": 1},
        )
        self.assertTrue(result["grids"][0]["auto_exclude_empty"])

    def test_grid_can_disable_automatic_empty_position_exclusion(self):
        db = main.SessionLocal()
        wall = db.query(main.WallDB).filter(main.WallDB.id == self.wall_id).one()
        wall.holds = [
            {"id": "left-hold", "mask": [[0, 0], [0, 0]]},
            {"id": "right-hold", "mask": [[20, 0], [20, 0]]},
        ]
        db.commit()
        db.close()

        result = asyncio.run(main.define_holds(main.WallTranslation(
            wallid=self.wall_id,
            p1x=0,
            p1y=0,
            p2x=20,
            p2y=0,
            p3x=20,
            p3y=10,
            p4x=0,
            p4y=10,
            r=1,
            c=3,
            auto_exclude_empty=False,
            apply_auto_exclusions=True,
        )))

        self.assertEqual(result["excluded_position_ids"], [])
        self.assertEqual(result["position_led_ids"], {0: 0, 1: 1, 2: 2})
        self.assertFalse(result["grids"][0]["auto_exclude_empty"])

        db = main.SessionLocal()
        saved = db.query(main.WallCreationDB).filter(
            main.WallCreationDB.wallid == self.wall_id
        ).one()
        self.assertFalse(saved.settings["auto_exclude_empty"])
        db.close()

    def test_fully_empty_grid_is_returned_for_manual_reactivation(self):
        db = main.SessionLocal()
        wall = db.query(main.WallDB).filter(main.WallDB.id == self.wall_id).one()
        wall.holds = []
        db.commit()
        db.close()

        result = asyncio.run(main.define_holds(main.WallTranslation(
            wallid=self.wall_id,
            p1x=0,
            p1y=0,
            p2x=20,
            p2y=0,
            p3x=20,
            p3y=10,
            p4x=0,
            p4y=10,
            r=1,
            c=2,
            auto_exclude_empty=True,
            apply_auto_exclusions=True,
        )))

        self.assertEqual(result["excluded_position_ids"], [0, 1])
        self.assertEqual(result["position_led_ids"], {})
        self.assertEqual(result["holds2led"], {})

    def test_auto_excluded_position_can_be_manually_reactivated(self):
        db = main.SessionLocal()
        wall = db.query(main.WallDB).filter(main.WallDB.id == self.wall_id).one()
        wall.holds = [
            {"id": "left-hold", "mask": [[0, 0], [0, 0]]},
            {"id": "right-hold", "mask": [[20, 0], [20, 0]]},
        ]
        db.commit()
        db.close()

        base_payload = {
            "wallid": self.wall_id,
            "p1x": 0,
            "p1y": 0,
            "p2x": 20,
            "p2y": 0,
            "p3x": 20,
            "p3y": 10,
            "p4x": 0,
            "p4y": 10,
            "r": 1,
            "c": 3,
        }
        asyncio.run(main.define_holds(main.WallTranslation(
            **base_payload,
            auto_exclude_empty=True,
            apply_auto_exclusions=True,
        )))

        result = asyncio.run(main.define_holds(main.WallTranslation(
            **base_payload,
            excluded_position_ids=[],
            auto_exclude_empty=True,
            apply_auto_exclusions=False,
        )))

        self.assertEqual(result["excluded_position_ids"], [])
        self.assertEqual(result["position_led_ids"], {0: 0, 1: 1, 2: 2})
        self.assertEqual(
            result["holds2led"],
            {"left-hold": 0, "right-hold": 2},
        )

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

    def test_multiple_grids_continue_global_led_ids_in_tab_order(self):
        db = main.SessionLocal()
        wall = db.query(main.WallDB).filter(main.WallDB.id == self.wall_id).one()
        wall.holds = [
            {"id": "left-hold", "mask": [[0, 0], [0, 0]]},
            {"id": "right-hold", "mask": [[100, 0], [100, 0]]},
        ]
        db.commit()
        db.close()

        payload = main.MultiGridWallTranslation(
            wallid=self.wall_id,
            grids=[
                main.GridTranslation(
                    id="left-wall",
                    p1x=0, p1y=0, p2x=10, p2y=0,
                    p3x=10, p3y=10, p4x=0, p4y=10,
                    r=1, c=2,
                ),
                main.GridTranslation(
                    id="right-wall",
                    p1x=100, p1y=0, p2x=110, p2y=0,
                    p3x=110, p3y=10, p4x=100, p4y=10,
                    r=1, c=2,
                ),
            ],
        )

        result = asyncio.run(main.define_holds(payload))

        self.assertEqual(result["grids"][0]["position_led_ids"], {0: 0, 1: 1})
        self.assertEqual(result["grids"][0]["led_start"], 0)
        self.assertEqual(result["grids"][0]["led_end"], 1)
        self.assertEqual(result["grids"][1]["position_led_ids"], {0: 2, 1: 3})
        self.assertEqual(result["grids"][1]["led_start"], 2)
        self.assertEqual(result["grids"][1]["led_end"], 3)
        self.assertEqual(result["holds2led"], {"left-hold": 0, "right-hold": 2})

        db = main.SessionLocal()
        saved = db.query(main.WallCreationDB).filter(
            main.WallCreationDB.wallid == self.wall_id
        ).one()
        self.assertEqual([grid["id"] for grid in saved.settings["grids"]], [
            "left-wall", "right-wall",
        ])
        self.assertEqual(saved.settings["holds2led"], {
            "left-hold": 0,
            "right-hold": 2,
        })
        db.close()

    def test_reordering_grids_reassigns_global_led_ranges(self):
        db = main.SessionLocal()
        wall = db.query(main.WallDB).filter(main.WallDB.id == self.wall_id).one()
        wall.holds = [
            {"id": "left-hold", "mask": [[0, 0], [0, 0]]},
            {"id": "right-hold", "mask": [[100, 0], [100, 0]]},
        ]
        db.commit()
        db.close()

        right_grid = main.GridTranslation(
            id="right-wall",
            p1x=100, p1y=0, p2x=110, p2y=0,
            p3x=110, p3y=10, p4x=100, p4y=10,
            r=1, c=2,
        )
        left_grid = main.GridTranslation(
            id="left-wall",
            p1x=0, p1y=0, p2x=10, p2y=0,
            p3x=10, p3y=10, p4x=0, p4y=10,
            r=1, c=2,
        )

        result = asyncio.run(main.define_holds(main.MultiGridWallTranslation(
            wallid=self.wall_id,
            grids=[right_grid, left_grid],
        )))

        self.assertEqual(result["holds2led"], {"left-hold": 2, "right-hold": 0})
        self.assertEqual(result["grids"][0]["id"], "right-wall")
        self.assertEqual(result["grids"][0]["led_start"], 0)
        self.assertEqual(result["grids"][1]["id"], "left-wall")
        self.assertEqual(result["grids"][1]["led_start"], 2)

    def test_each_grid_must_keep_an_active_position(self):
        payload = main.MultiGridWallTranslation(
            wallid=self.wall_id,
            grids=[main.GridTranslation(
                id="disabled-grid",
                p1x=0, p1y=0, p2x=10, p2y=0,
                p3x=10, p3y=10, p4x=0, p4y=10,
                r=1, c=2,
                excluded_position_ids=[0, 1],
            )],
        )

        with self.assertRaises(main.HTTPException) as raised:
            asyncio.run(main.define_holds(payload))

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("Grid 1", raised.exception.detail)
        self.assertIn("at least one", raised.exception.detail)


class PathPrefixTests(unittest.TestCase):
    def test_normalizes_path_prefix(self):
        self.assertEqual(main.normalize_path_prefix("cruxwledbridge/"), "/cruxwledbridge")
        self.assertEqual(main.normalize_path_prefix("/"), "")

    def test_wall_lighting_uses_path_prefix(self):
        html = main.return_wall_lighting_html(
            "/cruxwledbridge",
            "fireworks",
            65,
            "bright",
            45,
            "both",
        )

        self.assertIn("fetch('/cruxwledbridge/wall_lighting_settings'", html)
        self.assertNotIn("fetch('/cruxwledbridge/wall_lighting_mode'", html)
        self.assertNotIn("fetch('/cruxwledbridge/celebration_effect'", html)
        self.assertIn("celebrationSelect.value = 'fireworks'", html)
        self.assertIn("Wandbeleuchtungs-Einstellungen", html)
        self.assertIn("Dunkel – nur Boulder", html)
        self.assertIn("Hell – freie LEDs gedimmt", html)
        self.assertEqual(html.count('type="range" min="10" max="100"'), 2)
        self.assertIn('value="65"', html)
        self.assertIn('value="45"', html)
        self.assertIn('name="mode" value="bright" checked', html)
        self.assertIn(
            "bright_brightness_percent: Number(brightBrightnessInput.value)",
            html,
        )
        self.assertIn(
            "boulder_brightness_percent: Number(boulderBrightnessInput.value)",
            html,
        )
        self.assertIn(
            "hold_lighting_direction: form.elements.hold_lighting_direction.value",
            html,
        )
        self.assertIn('name="hold_lighting_direction" value="both" checked', html)
        self.assertIn("genau eine Reihe höher in derselben Spalte", html)
        self.assertIn("Helligkeit freier LEDs: {value}%", html)
        self.assertIn("Helligkeit der Boulder-LEDs: {value}%", html)
        self.assertEqual(html.count('id="save-settings"'), 1)
        self.assertGreater(
            html.index('id="save-settings"'),
            html.index('id="celebration-effect"'),
        )

    def test_overview_links_to_user_pages_with_path_prefix(self):
        html = main.return_overview_html("/cruxwledbridge")

        self.assertIn('action="/cruxwledbridge/listwalls"', html)
        self.assertIn('name="gym"', html)
        self.assertIn('href="/cruxwledbridge/wall_lighting"', html)
        self.assertIn('href="/cruxwledbridge/settings"', html)
        self.assertIn("map its holds to the physical LEDs", html)
        self.assertIn("configure the celebration", html)
        self.assertIn("Configure energy saving", html)

    def test_overview_is_localized(self):
        html = main.return_overview_html()

        self.assertIn('<html lang="en">', html)
        self.assertIn('id="language-toggle"', html)
        self.assertIn("Wall setup", html)
        self.assertIn("Wand einrichten", html)
        self.assertIn("Wall lighting", html)
        self.assertIn("Wandbeleuchtung", html)
        self.assertIn("Energy saving", main.return_settings_html())
        self.assertIn("Energiesparmodus", main.return_settings_html())

    def test_settings_page_uses_path_prefix_and_current_timeout(self):
        html = main.return_settings_html("/cruxwledbridge", 15)

        self.assertIn("fetch('/cruxwledbridge/route_timeout'", html)
        self.assertIn('type="number" min="0" step="1" value="15"', html)
        self.assertIn("Mit 0 bleibt die Route an", html)
        self.assertIn("route_timeout_minutes: Number(timeoutInput.value)", html)

    def test_overview_shows_and_removes_saved_gym_favorite(self):
        html = main.return_overview_html("/cruxwledbridge")

        self.assertIn('id="favorite-gym"', html)
        self.assertIn('id="favorite-gym-link"', html)
        self.assertIn('id="favorite-gym-remove"', html)
        self.assertIn("window.localStorage.getItem(storageKey)", html)
        self.assertIn("encodeURIComponent(slug)", html)
        self.assertIn("const listWallsPath = \"/cruxwledbridge/listwalls\"", html)
        self.assertIn("window.localStorage.removeItem(storageKey)", html)
        self.assertIn("Favorisierte Halle entfernen", html)

    def test_root_returns_overview_html(self):
        response = asyncio.run(main.root())

        self.assertEqual(response.status_code, 200)
        self.assertIn("CRUX WLED Bridge", response.body.decode())

    def test_wall_lighting_routes_replace_toggle_gui_routes(self):
        routes = {(route.path, tuple(route.methods or [])) for route in main.app.routes}

        self.assertTrue(any(path == "/wall_lighting" and "GET" in methods for path, methods in routes))
        self.assertTrue(any(path == "/wall_lighting_settings" and "POST" in methods for path, methods in routes))
        self.assertTrue(any(path == "/wall_lighting_mode" and "POST" in methods for path, methods in routes))
        self.assertTrue(any(path == "/celebration_effect" and "POST" in methods for path, methods in routes))
        self.assertTrue(any(path == "/sent" and "POST" in methods for path, methods in routes))
        self.assertTrue(any(path == "/settings" and "GET" in methods for path, methods in routes))
        self.assertTrue(any(path == "/route_timeout" and "POST" in methods for path, methods in routes))
        self.assertFalse(any(path in {"/toggle_gui", "/toggle_mode"} for path, _ in routes))

    def test_wall_lighting_mode_updates_server_state(self):
        original_mode = main.wall_lighting_mode
        original_brightness = main.bright_wall_brightness_percent
        try:
            with patch("main.persist_app_settings") as persist:
                result = asyncio.run(
                    main.set_wall_lighting_mode(
                        main.WallLightingMode(mode="bright", brightness=65)
                    )
                )

            self.assertEqual(main.wall_lighting_mode, "bright")
            self.assertEqual(main.bright_wall_brightness_percent, 65)
            persist.assert_called_once_with({
                "wall_lighting_mode": "bright",
                "bright_wall_brightness_percent": 65,
            })
            self.assertEqual(
                result,
                {
                    "message": "Wall lighting mode set to bright",
                    "brightness": 65,
                },
            )
        finally:
            main.wall_lighting_mode = original_mode
            main.bright_wall_brightness_percent = original_brightness

    def test_all_wall_lighting_settings_are_saved_together(self):
        original_values = (
            main.wall_lighting_mode,
            main.bright_wall_brightness_percent,
            main.boulder_brightness_percent,
            main.celebration_effect,
            main.hold_lighting_direction,
        )
        try:
            with patch("main.persist_app_settings") as persist:
                result = asyncio.run(main.set_wall_lighting_settings(
                    main.WallLightingSettings(
                        mode="bright",
                        bright_brightness_percent=35,
                        boulder_brightness_percent=70,
                        celebration_effect="pride",
                        hold_lighting_direction="above",
                    )
                ))

            persist.assert_called_once_with({
                "wall_lighting_mode": "bright",
                "bright_wall_brightness_percent": 35,
                "boulder_brightness_percent": 70,
                "celebration_effect": "pride",
                "hold_lighting_direction": "above",
            })
            self.assertEqual(result, {
                "message": "Wall lighting settings updated",
                "mode": "bright",
                "bright_brightness_percent": 35,
                "boulder_brightness_percent": 70,
                "celebration_effect": "pride",
                "hold_lighting_direction": "above",
            })
            self.assertEqual(main.wall_lighting_mode, "bright")
            self.assertEqual(main.bright_wall_brightness_percent, 35)
            self.assertEqual(main.boulder_brightness_percent, 70)
            self.assertEqual(main.celebration_effect, "pride")
            self.assertEqual(main.hold_lighting_direction, "above")
        finally:
            (
                main.wall_lighting_mode,
                main.bright_wall_brightness_percent,
                main.boulder_brightness_percent,
                main.celebration_effect,
                main.hold_lighting_direction,
            ) = original_values

    def test_wall_lighting_settings_reject_invalid_hold_direction(self):
        with patch("main.persist_app_settings") as persist:
            response = asyncio.run(main.set_wall_lighting_settings(
                main.WallLightingSettings(
                    mode="dark",
                    bright_brightness_percent=20,
                    boulder_brightness_percent=100,
                    celebration_effect="rainbow",
                    hold_lighting_direction="sideways",
                )
            ))

        self.assertEqual(response.status_code, 400)
        persist.assert_not_called()

    def test_wall_lighting_brightness_rejects_values_outside_range(self):
        for brightness in (9, 101):
            with self.subTest(brightness=brightness):
                with self.assertRaises(ValueError):
                    main.WallLightingMode(mode="bright", brightness=brightness)

                with self.assertRaises(ValueError):
                    main.WallLightingSettings(
                        mode="bright",
                        bright_brightness_percent=50,
                        boulder_brightness_percent=brightness,
                        celebration_effect="rainbow",
                    )

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

        self.assertIn('<label for="rows" data-i18n="form.rows">Rows:</label>', html)
        self.assertIn('<label for="columns" data-i18n="form.columns">Columns:</label>', html)
        self.assertNotIn('<label for="rows">R:', html)
        self.assertNotIn('<label for="columns">C:', html)
        self.assertGreaterEqual(html.count('<div class="form-row">'), 3)
        self.assertIn('id="alternating"', html)
        self.assertIn("alternating: Boolean(grid.alternating)", html)
        self.assertIn('id="alternating-start"', html)
        self.assertIn(
            '<option value="0" data-i18n="form.not_offset">Not offset</option>',
            html,
        )
        self.assertIn(
            '<option value="1" data-i18n="form.offset">Offset</option>',
            html,
        )
        self.assertIn(
            "alternating_start_column: Number(grid.alternating_start_column || 0)",
            html,
        )

    def test_wall_selector_reset_clears_all_rendered_points(self):
        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
            "/cruxwledbridge",
        )

        self.assertIn('id="reset-btn"', html)
        self.assertLess(html.index('id="reset-btn"'), html.index('id="submit-btn"'))
        self.assertIn("resetBtn.addEventListener('click'", html)
        self.assertIn("points = [];", html)
        self.assertIn("renderedPositions = null;", html)
        self.assertIn("excludedPositionIds.clear();", html)

    def test_wall_selector_keeps_hold_labels_bound_to_grid_positions(self):
        html = main.returnwallhtml(
            {
                "id": "wall-1",
                "image_url": "https://example.com/wall.jpg",
                "image_width": 100,
                "image_height": 200,
            },
            saved_creation={
                "holds2led": {"hold-a": 1},
                "grids": [{
                    "id": "grid-1",
                    "positions": {"0": [0, 0], "1": [10, 0], "2": [20, 0]},
                    "position_led_ids": {"0": 0, "1": 1, "2": 2},
                    "excluded_position_ids": [],
                }],
            },
        )

        self.assertIn("function bindHoldsToPositions()", html)
        self.assertIn("grid.position_hold_ids[positionId] = holdId", html)
        self.assertIn(
            "const positionHoldIds = grids[activeGridIndex].position_hold_ids || {}",
            html,
        )
        self.assertIn("else if (positionHoldIds[positionIdText])", html)
        self.assertNotIn("else if (led2holds[ledId])", html)

    def test_wall_selector_offers_led_cable_layout(self):
        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
            "/cruxwledbridge",
        )

        self.assertIn('id="led-start-corner"', html)
        self.assertIn(
            '<option value="top_right" data-i18n="form.top_right">Top right</option>',
            html,
        )
        self.assertIn(
            '<option value="bottom_left" data-i18n="form.bottom_left" selected>Bottom left</option>',
            html,
        )
        self.assertIn('id="led-direction"', html)
        self.assertIn(
            '<option value="vertical" data-i18n="form.vertical" selected>Vertical (column by column)</option>',
            html,
        )
        self.assertIn("led_start_corner: grid.led_start_corner", html)
        self.assertIn("led_direction: grid.led_direction", html)

    def test_pages_default_to_english_and_offer_opposite_flag(self):
        wall_selector = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
        )
        wall_lighting = main.return_wall_lighting_html()

        for html in (wall_selector, wall_lighting):
            with self.subTest(page=html[:80]):
                self.assertIn('<html lang="en">', html)
                self.assertIn('id="language-toggle"', html)
                self.assertIn('>🇩🇪</button>', html)
                self.assertIn(
                    "toggle.textContent = targetLanguage === 'de' ? '🇩🇪' : '🇬🇧';",
                    html,
                )

        self.assertIn("Climbing wall – select points", wall_selector)
        self.assertIn("Kletterwand – Punkte auswählen", wall_selector)
        self.assertIn("Wall lighting settings", wall_lighting)
        self.assertIn("Wandbeleuchtungs-Einstellungen", wall_lighting)
        self.assertIn("Moving rainbow", wall_lighting)
        self.assertIn("Laufender Regenbogen", wall_lighting)
        self.assertIn('<option value="off"', wall_lighting)

    def test_language_choice_is_loaded_and_persisted_in_browser_storage(self):
        html = main.return_wall_lighting_html()

        self.assertIn("const storageKey = 'cruxwledbridge.language';", html)
        self.assertIn("window.localStorage.getItem(storageKey)", html)
        self.assertIn(": 'en';", html)
        self.assertIn("window.localStorage.setItem(storageKey, currentLanguage)", html)
        self.assertIn("document.documentElement.lang = currentLanguage", html)

    def test_wall_selector_retranslates_dynamic_content(self):
        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
        )

        self.assertIn("window.addEventListener('crux-language-change'", html)
        self.assertIn("t('status.grid'", html)
        self.assertIn("t('grid.excluded_title')", html)
        self.assertIn("alert(t('alert.incomplete_grid'", html)

    def test_wall_selector_can_exclude_rendered_positions(self):
        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
            "/cruxwledbridge",
        )

        self.assertIn("excludedPositionIds.has(positionId)", html)
        self.assertIn("grid.excluded_position_ids = Array.from(excludedPositionIds)", html)
        self.assertIn("Alle Raster speichern", html)

    def test_wall_selector_controls_auto_exclusion_per_grid(self):
        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
            "/cruxwledbridge",
        )

        self.assertIn('id="auto-exclude-empty" checked', html)
        self.assertIn("auto_exclude_empty: true", html)
        self.assertIn(
            "grid.auto_exclude_empty = autoExcludeEmptyCheckbox.checked",
            html,
        )
        self.assertIn(
            "autoExcludeEmptyCheckbox.checked = grid.auto_exclude_empty !== false",
            html,
        )
        self.assertIn("grid.apply_auto_exclusions = Boolean(grid.auto_exclude_empty", html)
        self.assertIn(
            "auto_exclude_empty: Boolean(grid.auto_exclude_empty)",
            html,
        )
        self.assertIn(
            "apply_auto_exclusions: Boolean(grid.apply_auto_exclusions)",
            html,
        )
        self.assertIn(
            "Positionen ohne Griff in der Nähe automatisch abwählen",
            html,
        )

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
        self.assertIn(
            "points.push(displayToImage(event.clientX - rect.left, event.clientY - rect.top))",
            html,
        )
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
        self.assertIn("savedCreation.coordinate_width || climbingImage.naturalWidth", html)
        self.assertIn("savedCreation.coordinate_height || climbingImage.naturalHeight", html)
        self.assertIn("const scaleX = targetWidth / sourceWidth", html)
        self.assertIn("const scaleY = targetHeight / sourceHeight", html)
        self.assertIn("normalizeSavedCreationCoordinates();", html)

    def test_wall_selector_restores_against_saved_coordinate_dimensions(self):
        html = main.returnwallhtml(
            {
                "id": 216943,
                "image_url": "https://example.com/wall.jpg",
                "image_width": 400,
                "image_height": 800,
            },
            "/cruxwledbridge",
            {
                "coordinate_space": "wall_image",
                "coordinate_width": 200,
                "coordinate_height": 400,
                "points": [{"x": 100, "y": 200}],
                "positions": {0: [100, 200]},
            },
        )

        self.assertIn('"coordinate_width":200,"coordinate_height":400', html)
        self.assertIn("savedCreation.coordinate_width || wallImageWidth", html)
        self.assertIn("savedCreation.coordinate_height || wallImageHeight", html)
        self.assertIn("savedCreation.coordinate_width = targetWidth", html)
        self.assertIn("savedCreation.coordinate_height = targetHeight", html)

    def test_wall_selector_repositions_overlay_when_image_layout_changes(self):
        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
        )

        self.assertIn("new ResizeObserver(() =>", html)
        self.assertIn("if (savedCreationInitialized) redraw()", html)
        self.assertIn(".observe(climbingImage)", html)

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
        self.assertIn(
            "const savedGrids = Array.isArray(savedCreation.grids)",
            html,
        )
        self.assertIn(
            "const savedGrids = Array.isArray(savedCreation.grids) && savedCreation.grids.length ? savedCreation.grids : [savedCreation]",
            html,
        )
        self.assertIn("rows.value = grid.r ?? ''", html)
        self.assertIn(
            "excludedPositionIds = new Set((grid.excluded_position_ids || []).map(Number))",
            html,
        )
        self.assertIn("climbingImage.addEventListener('load', initializeSavedCreation", html)

    def test_wall_selector_manages_ordered_grid_tabs(self):
        html = main.returnwallhtml(
            {"id": 216943, "image_url": "https://example.com/wall.jpg"},
            "/cruxwledbridge",
        )

        self.assertIn('id="grid-tabs"', html)
        self.assertIn("add.id = 'add-grid-btn'", html)
        self.assertIn("grids.push(createEmptyGrid())", html)
        self.assertIn("tab.draggable = true", html)
        self.assertIn("moveGrid(Number(event.dataTransfer.getData('text/plain')), index)", html)
        self.assertIn("remove.className = 'grid-tab-delete'", html)
        self.assertIn("grids.splice(index, 1)", html)
        self.assertIn("grids: grids.map((grid) => ({", html)
        self.assertIn("let offset = 0", html)
        self.assertIn("grid.led_start = offset", html)
        self.assertIn("offset += activeIds.length", html)


class HoldLightingDirectionTests(unittest.TestCase):
    def setUp(self):
        positions = utils.generate_grid(
            (0, 0),
            (10, 0),
            (10, 20),
            (0, 20),
            3,
            1,
            led_start_corner="bottom_left",
            led_direction="vertical",
        )
        self.saved_settings = {
            "r": 3,
            "c": 1,
            "alternating": False,
            "alternating_start_column": 0,
            "led_start_corner": "bottom_left",
            "led_direction": "vertical",
            "positions": positions,
            "position_led_ids": {0: 0, 1: 1, 2: 2},
        }

    def test_grid_layout_retains_rows_independent_of_cable_order(self):
        self.assertEqual(
            utils.generate_grid_position_layout(
                3,
                1,
                led_start_corner="bottom_left",
                led_direction="vertical",
            ),
            {0: (2, 0), 1: (1, 0), 2: (0, 0)},
        )

    def test_above_direction_uses_the_next_rows_light(self):
        self.assertEqual(
            main.apply_hold_lighting_direction(
                {0: "start", 1: "finish"},
                self.saved_settings,
                "above",
            ),
            {1: "start", 2: "finish"},
        )

    def test_both_direction_keeps_lights_above_and_below(self):
        self.assertEqual(
            main.apply_hold_lighting_direction(
                {0: "start"},
                self.saved_settings,
                "both",
            ),
            {0: "start", 1: "start"},
        )

    def test_highest_hold_always_uses_its_below_light(self):
        self.assertEqual(
            main.apply_hold_lighting_direction(
                {2: "finish"},
                self.saved_settings,
                "above",
            ),
            {2: "finish"},
        )

    def test_highest_hold_fallback_wins_shared_led_color(self):
        self.assertEqual(
            main.apply_hold_lighting_direction(
                {1: "start", 2: "finish"},
                self.saved_settings,
                "above",
            ),
            {2: "finish"},
        )

    def test_above_direction_never_uses_a_sideways_light(self):
        layout = utils.generate_grid_position_layout(
            2,
            2,
            led_start_corner="bottom_left",
            led_direction="vertical",
        )
        position_ids = {
            coordinates: position_id
            for position_id, coordinates in layout.items()
        }
        bottom_left = position_ids[(1, 0)]
        top_right = position_ids[(0, 1)]
        saved_settings = {
            "r": 2,
            "c": 2,
            "alternating": False,
            "alternating_start_column": 0,
            "led_start_corner": "bottom_left",
            "led_direction": "vertical",
            "position_led_ids": {
                bottom_left: 10,
                top_right: 11,
            },
        }

        self.assertEqual(
            main.apply_hold_lighting_direction(
                {10: "start"},
                saved_settings,
                "above",
            ),
            {10: "start"},
        )

    def test_above_direction_never_skips_over_an_excluded_row(self):
        saved_settings = {
            **self.saved_settings,
            # The middle position is excluded. The top LED must not be used
            # as a substitute for the missing LED immediately above LED 0.
            "position_led_ids": {0: 0, 2: 2},
        }
        self.assertEqual(
            main.apply_hold_lighting_direction(
                {0: "start"},
                saved_settings,
                "above",
            ),
            {0: "start"},
        )

    def test_multiple_grids_do_not_share_above_lights(self):
        second_grid = {
            **self.saved_settings,
            "position_led_ids": {0: 3, 1: 4, 2: 5},
        }
        self.assertEqual(
            main.apply_hold_lighting_direction(
                {0: "start", 3: "finish"},
                {"grids": [self.saved_settings, second_grid]},
                "above",
            ),
            {1: "start", 4: "finish"},
        )

    def test_default_below_direction_keeps_existing_mapping(self):
        holds = {0: "start", 2: "finish"}
        self.assertEqual(
            main.apply_hold_lighting_direction(
                holds,
                self.saved_settings,
                "below",
            ),
            holds,
        )


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
                        "seg": {"fx": 0, "i": [1, "FF0000"]},
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
                        "fx": 0,
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
    def test_bright_mode_background_strength_is_adjustable(self, post):
        post.return_value = Mock()

        utils.sendLightToBoulderwall(
            {1: "start"},
            mode="bright",
            bright_brightness_percent=10,
        )
        ten_percent_pixels = post.call_args_list[-1].kwargs["json"]["seg"]["i"]

        utils.sendLightToBoulderwall(
            {1: "start"},
            mode="bright",
            bright_brightness_percent=100,
        )
        full_brightness_pixels = post.call_args_list[-1].kwargs["json"]["seg"]["i"]

        self.assertEqual(ten_percent_pixels, [0, "1A1A1A", 1, "FF0000", 2, "1A1A1A"])
        self.assertEqual(full_brightness_pixels, [0, "FFFFFF", 1, "FF0000", 2, "FFFFFF"])

    @patch("utils.requests.post")
    def test_boulder_brightness_scales_route_colors_independently(self, post):
        post.return_value = Mock()
        config.colors = {"start": "FF8000"}

        result = utils.sendLightToBoulderwall(
            {1: "start"},
            mode="bright",
            bright_brightness_percent=20,
            boulder_brightness_percent=50,
        )

        self.assertEqual(result, {101: "804000"})
        self.assertEqual(
            post.call_args_list[-1].kwargs["json"]["seg"]["i"],
            [0, "333333", 1, "804000", 2, "333333"],
        )

    def test_boulder_brightness_rejects_values_outside_range(self):
        for brightness in (9, 101):
            with self.subTest(brightness=brightness):
                with self.assertRaisesRegex(ValueError, "Boulder brightness"):
                    utils.sendLightToBoulderwall(
                        {1: "start"},
                        boulder_brightness_percent=brightness,
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
                    "seg": {"fx": 0, "i": [2, "FF0000", 3, "FF0000"]},
                },
            ),
        )

    @patch("utils.requests.post")
    def test_celebration_effect_uses_complete_controller_range(self, post):
        post.return_value = Mock()

        utils.playCelebrationEffect("rainbow")

        self.assertEqual(
            post.call_args_list,
            [
                call(
                    "http://192.0.2.10/json/state",
                    json={"on": False, "tt": 0},
                    timeout=2,
                ),
                call(
                    "http://192.0.2.10/json/state",
                    json={
                        "on": True,
                        "bri": 255,
                        "tt": 0,
                        "seg": {
                            "id": 0,
                            "start": 0,
                            "stop": 3,
                            "on": True,
                            "bri": 255,
                            "frz": False,
                            "fx": 9,
                            "sx": 180,
                            "ix": 180,
                        },
                    },
                    timeout=2,
                ),
            ],
        )

    @patch("utils.requests.post")
    def test_celebration_resets_each_controller_before_starting_effect(self, post):
        post.return_value = Mock()
        config.wled_controllers = [
            {"ip": "192.0.2.10", "start": 100, "end": 102},
            {"ip": "192.0.2.11", "start": 200, "end": 203},
        ]

        utils.playCelebrationEffect("fireworks")

        self.assertEqual(len(post.call_args_list), 4)
        for reset_call, effect_call in zip(
            post.call_args_list[::2], post.call_args_list[1::2]
        ):
            self.assertEqual(reset_call.kwargs["json"], {"on": False, "tt": 0})
            self.assertTrue(effect_call.kwargs["json"]["on"])
            self.assertEqual(effect_call.kwargs["json"]["bri"], 255)
            self.assertEqual(effect_call.kwargs["json"]["tt"], 0)
            self.assertFalse(effect_call.kwargs["json"]["seg"]["frz"])
            self.assertEqual(effect_call.kwargs["json"]["seg"]["fx"], 42)

    @patch("utils.requests.post")
    def test_unknown_celebration_effect_is_rejected(self, post):
        with self.assertRaisesRegex(ValueError, "Unknown celebration effect"):
            utils.playCelebrationEffect("unknown")

        post.assert_not_called()

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
