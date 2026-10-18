import asyncio
import copy
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from test_utils import config, main, utils
from led_layout import (LEDLayout, active_associations, calculate_layout, grip_positions,
                        led_positions, physical_route, seed_layout)
from templates.led_mapping import return_led_mapping_html


def grip_grid(identity="grips", points=None, r=3, c=2, **options):
    points = points or [(100, 100), (200, 100), (200, 300), (100, 300)]
    opts = {"led_start_corner": "top_left", "led_direction": "horizontal", **options}
    positions = utils.generate_grid(*points, r, c, **opts)
    return {"id": identity, "r": r, "c": c, "points": [{"x": x, "y": y} for x, y in points],
            "positions": positions, "position_led_ids": {key: key for key in positions}, **opts}


def settings_fixture():
    return {"coordinate_width": 500, "coordinate_height": 500, "grids": [grip_grid()],
            "holds2led": {"grip-a": 0}}


def layout_fixture():
    return {"coordinate_width": 500, "coordinate_height": 500,
            "grids": [{"id": "lights", "name": "Lights", "r": 4, "c": 2,
                       "points": [{"x": 100, "y": 50}, {"x": 200, "y": 50},
                                  {"x": 200, "y": 350}, {"x": 100, "y": 350}],
                       "physical_start": 100, "led_start_corner": "top_left", "led_direction": "horizontal"}],
            "skipped_physical_ids": [102]}


class IndependentLEDGeometryTests(unittest.TestCase):
    def test_independent_grip_and_led_rows_with_extra_top_bottom_and_skips(self):
        result = calculate_layout(settings_fixture(), layout_fixture())
        self.assertEqual([p["physical_id"] for p in result["leds"]], [100, 101, 103, 104, 105, 106, 107, 108])
        first = next(p for p in result["grips"] if p["logical_id"] == 0)
        self.assertEqual((first["above"], first["below"]), (100, 104))
        self.assertEqual(first["key"], "grips:r0c0")
        self.assertTrue(all(p["below"] is not None and p["above"] is not None for p in result["grips"]))

    def test_missing_bottom_has_no_fallback_and_top_led_without_grip_is_used(self):
        layout = layout_fixture()
        layout["grids"][0]["excluded_position_ids"] = [6, 7]
        result = calculate_layout(settings_fixture(), layout)
        bottom = [p for p in result["grips"] if p["y"] == 300]
        self.assertTrue(all(p["below"] is None for p in bottom))
        self.assertTrue(all(p["above"] is not None for p in bottom))
        self.assertEqual(result["grips"][0]["above"], 100)

    def test_crosses_grid_boundary_but_not_wall_surface(self):
        layout = layout_fixture()
        first = layout["grids"][0]
        second = copy.deepcopy(first)
        first["r"] = second["r"] = 2
        first["points"][2]["y"] = first["points"][3]["y"] = 150
        second.update(id="lower", physical_start=None)
        second["points"][0]["y"] = second["points"][1]["y"] = 250
        layout["grids"].append(second)
        settings = settings_fixture()
        result = calculate_layout(settings, layout)
        self.assertTrue(all(p["below"] is not None for p in result["grips"]))
        second["surface"] = "other-plane"
        result = calculate_layout(settings, layout)
        self.assertTrue(all(p["below"] is None for p in result["grips"] if p["y"] >= 200))
        self.assertEqual(result["grips"][0]["above"], 100)

    def test_grip_references_do_not_depend_on_cable_order(self):
        settings = settings_fixture()
        for corner in ("top_left", "bottom_left", "top_right", "bottom_right"):
            for direction in ("horizontal", "vertical"):
                settings["grids"] = [grip_grid(led_start_corner=corner, led_direction=direction)]
                result = calculate_layout(settings, layout_fixture())
                left_top = next(p for p in result["grips"] if p["x"] == p["y"] == 100)
                self.assertEqual((left_top["key"], left_top["above"], left_top["below"]), ("grips:r0c0", 100, 104))

    def test_real_staggered_grip_geometry_both_cable_directions(self):
        # Actual grid 15 geometry from the reported horizontal-cable failure.
        corners = [(715,159),(952,169),(909,467),(703,466)]
        for direction in ("horizontal", "vertical"):
            for corner in ("top_left", "top_right", "bottom_left", "bottom_right"):
                g = grip_grid(points=corners, r=8, c=6, alternating=True,
                              alternating_start_column=1, led_start_corner=corner, led_direction=direction)
                settings = {"coordinate_width":1600,"coordinate_height":1200,"grids":[g]}
                # LED bores are below grips, not the next staggered grip row.
                led_corners = [{"x":x, "y":y+18} for x,y in corners]
                layout = {"coordinate_width":1600,"coordinate_height":1200,"grids":[{
                    "id":"leds", "points":led_corners, "r":8,"c":6,"alternating":True,
                    "alternating_start_column":1,"led_start_corner":corner,"led_direction":direction,
                    "physical_start":323}], "skipped_physical_ids":[330]}
                result = calculate_layout(settings, layout)
                visible = [p for p in result["leds"] if p["physical_id"] is not None]
                self.assertEqual(len(result["grips"]),24)
                for grip, led in zip(result["grips"], visible):
                    self.assertEqual(grip["below"], led["physical_id"], (corner, direction, grip))

    def test_perspective_and_coordinate_resize(self):
        # Vertical on the plane is diagonal in the photograph.
        points = [(100,100),(250,150),(400,400),(200,350)]
        g = grip_grid(points=points, r=3, c=2)
        settings = {"coordinate_width":500,"coordinate_height":500,"grids":[g]}
        h = utils._grid_homography(*points)
        def project(s,t):
            import numpy as np
            p = h @ np.array([s,t,1.0]); return {"x":float(p[0]/p[2])*2,"y":float(p[1]/p[2])*2}
        layout = {"coordinate_width":1000,"coordinate_height":1000,"grids":[{
            "id":"leds","r":3,"c":2,"points":[project(0,.15),project(1,.15),project(1,1.15),project(0,1.15)],
            "physical_start":100,"led_start_corner":"top_left","led_direction":"horizontal"}]}
        result = calculate_layout(settings, layout)
        self.assertEqual([p["below"] for p in result["grips"]], list(range(100,106)))

    def test_ambiguity_requires_override_and_null_means_no_led(self):
        layout = layout_fixture()
        layout["grids"][0]["manual_positions"] = [{"id":-1,"x":101,"y":150}]
        result = calculate_layout(settings_fixture(), layout)
        first = result["grips"][0]
        self.assertEqual(first["below_status"], "ambiguous")
        self.assertIsNone(first["below"])
        layout["overrides"] = {first["key"]:{"below":104,"above":None}}
        first = calculate_layout(settings_fixture(), layout)["grips"][0]
        self.assertEqual((first["below"],first["below_status"]),(104,"manual"))
        self.assertEqual((first["above"],first["above_status"]),(None,"disabled"))
        layout["overrides"][first["key"]]["below"] = 999
        with self.assertRaisesRegex(ValueError,"missing LED"):
            calculate_layout(settings_fixture(), layout)

    def test_disabled_position_is_distinct_from_hidden_cable_led(self):
        layout = layout_fixture()
        layout["grids"][0]["excluded_position_ids"] = [1]
        layout["grids"][0]["manual_positions"] = [{"id":-1,"x":150,"y":150,"before_position_id":2}]
        points = led_positions(LEDLayout.model_validate(layout))
        self.assertEqual([(p["position_id"],p["physical_id"]) for p in points[:4]],[(0,100),(1,None),(-1,101),(2,103)])

    def test_duplicate_addresses_and_invalid_skips_rejected(self):
        layout = layout_fixture()
        extra = copy.deepcopy(layout["grids"][0]); extra["id"]="overlap"
        layout["grids"].append(extra)
        with self.assertRaisesRegex(ValueError,"assigned more than once"):
            calculate_layout(settings_fixture(),layout)
        for bad in ([True],[-1],[1.5]):
            layout["skipped_physical_ids"] = bad
            with self.assertRaises(ValueError):
                LEDLayout.model_validate(layout)

    def test_seed_preserves_grips_and_imports_physical_gaps_without_activation(self):
        settings = settings_fixture(); before=copy.deepcopy(settings)
        seed = seed_layout(settings,{i:[100+i+(i>=2)] for i in range(6)},500,500)
        self.assertEqual(seed["skipped_physical_ids"],[102])
        self.assertEqual(seed["grids"][0]["physical_start"],100)
        self.assertEqual(settings,before)
        self.assertIsNone(active_associations(settings))

    def test_route_and_moonboard_share_physical_addresses_without_double_mapping(self):
        settings=settings_fixture(); settings["led_layout"]=layout_fixture()
        spatial=active_associations(settings)
        for direction in ("below","above","both"):
            route=physical_route({0:"start"},spatial,direction)
            virtual=utils.map_virtual_grid_to_physical_leds({0:(100,100)},settings,{0:[999],100:[900],104:[901]},direction=direction)
            self.assertEqual(set(route),set(virtual["physical_led_ids"]))
            with patch.object(utils,"_turn_off",return_value=True), patch.object(utils,"_send_individual_pixels",return_value=True):
                output=utils.sendLightToBoulderwall({utils.PhysicalLED(led):value for led,value in route.items()})
            self.assertEqual(set(output),set(route))
        # Upper light for a lower grip and lower light for its upper neighbour share a LED.
        combined=physical_route({0:"start",3:"end"},spatial,"both")
        self.assertEqual(combined[104],"start")

    def test_missing_led_preserves_moonboard_position(self):
        settings=settings_fixture(); layout=layout_fixture()
        layout["grids"][0]["excluded_position_ids"]=[6,7]; settings["led_layout"]=layout
        result=utils.map_virtual_grid_to_physical_leds({0:(100,300),1:(100,100)},settings,{})
        self.assertEqual(len(result["matches"]),2)
        self.assertEqual(result["matches"][0]["physical_led_ids"],[])
        self.assertEqual(result["matches"][1]["physical_led_ids"],[104])


class LEDLayoutPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.wallid=976121
        db=main.SessionLocal()
        db.add(main.WallDB(id=self.wallid,name="LED test wall",created_at="now",updated_at="now",image_width=500,image_height=500,holds=[]))
        db.add(main.WallCreationDB(wallid=self.wallid,settings=settings_fixture()))
        db.commit(); db.close()

    def tearDown(self):
        db=main.SessionLocal()
        db.query(main.WallCreationDB).filter_by(wallid=self.wallid).delete()
        db.query(main.WallDB).filter_by(id=self.wallid).delete()
        db.commit();db.close()

    def call(self,action,layout=None):
        with patch.object(main,"_wled_controllers",return_value=[{"start":0,"end":1000}]):
            return asyncio.run(main.edit_led_mapping(main.LEDLayoutRequest(wallid=self.wallid,action=action,layout=layout)))

    def stored(self):
        db=main.SessionLocal()
        result=copy.deepcopy(db.query(main.WallCreationDB).filter_by(wallid=self.wallid).first().settings)
        db.close();return result

    def test_draft_activation_edit_and_rollback_are_separate(self):
        layout=layout_fixture()
        self.call("calculate",layout)
        self.assertNotIn("led_layout_draft",self.stored())
        self.call("draft",layout)
        self.assertNotIn("led_layout",self.stored())
        self.call("activate",layout)
        active=self.stored()["led_layout"]
        layout["skipped_physical_ids"].append(105)
        self.call("draft",layout)
        self.assertEqual(self.stored()["led_layout"],active)
        self.call("deactivate")
        self.assertNotIn("led_layout",self.stored())
        self.assertIn(105,self.stored()["led_layout_draft"]["skipped_physical_ids"])
        self.assertEqual(self.stored()["holds2led"],{"grip-a":0})

    def test_activation_rejects_ambiguity_and_unconfigured_controller_ids(self):
        layout=layout_fixture()
        layout["grids"][0]["manual_positions"]=[{"id":-1,"x":101,"y":150}]
        with self.assertRaises(main.HTTPException) as exc:
            self.call("activate",layout)
        self.assertIn("ambiguous",exc.exception.detail)
        layout=layout_fixture();layout["grids"][0]["physical_start"]=2000
        with self.assertRaises(main.HTTPException) as exc:
            self.call("activate",layout)
        self.assertIn("outside configured",exc.exception.detail)
        self.assertNotIn("led_layout",self.stored())

    def test_saving_grip_grids_keeps_led_layer_and_draft(self):
        self.call("activate",layout_fixture())
        before=self.stored()["led_layout"]
        payload=main.MultiGridWallTranslation(wallid=self.wallid,grids=[main.GridTranslation(
            id="grips",p1x=100,p1y=100,p2x=200,p2y=100,p3x=200,p3y=300,p4x=100,p4y=300,
            r=3,c=2,auto_exclude_empty=False)])
        asyncio.run(main.define_holds(payload))
        self.assertEqual(self.stored()["led_layout"],{**before,"overrides":{},"grip_surfaces":{}})
        self.assertIn("led_layout_draft",self.stored())

    def test_viewed_uses_physical_addresses_and_saved_restore_state(self):
        self.call("activate",layout_fixture())
        db=main.SessionLocal();db.add(main.Hold2ledDB(holdid=f"{self.wallid}_grip-a",ledid=0));db.commit();db.close()
        try:
            payload=SimpleNamespace(payload=SimpleNamespace(id=121,name="Route",wall_id=self.wallid,
                image_url="https://example.test/wall",holds=[SimpleNamespace(id="grip-a",hold_type="start")]))
            request=SimpleNamespace(state=SimpleNamespace())
            with patch.object(main,"sendLightToBoulderwall",return_value={}) as send, patch.object(main,"schedule_route_timeout"), patch.object(main,"hold_lighting_direction","below"), patch.object(main,"_celebration_active",False), patch.object(main,"current_wall_holds",{}):
                asyncio.run(main.viewed(payload,request))
                self.assertEqual(send.call_args.args[0],{utils.PhysicalLED(104):"start"})
                self.assertEqual(main.current_wall_holds,{utils.PhysicalLED(104):"start"})
                with patch.object(main,"_route_lighting_active",True), patch.object(main,"_pending_viewed_holds",None):
                    asyncio.run(main.preview_virtual_mapping(main.VirtualMappingPreviewRequest(enabled=False)))
                self.assertEqual(send.call_args.args[0],{utils.PhysicalLED(104):"start"})
        finally:
            db=main.SessionLocal();db.query(main.Hold2ledDB).filter_by(holdid=f"{self.wallid}_grip-a").delete();db.commit();db.close()


class IndependentLEDUIBehaviorTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"),"Node.js is required for UI behavior tests")
    def test_saved_moonboard_refresh_cannot_preview_stale_addresses(self):
        from templates.virtual_mapping import return_virtual_mapping_html
        html=return_virtual_mapping_html(
            {"id":1,"image_url":"/wall.jpg","image_width":500,"image_height":500},
            "/bridge", [], main.MOONBOARD_SETUPS, recalculate_on_load=True)
        result=subprocess.run([shutil.which("node"),str(Path(__file__).with_name("virtual_mapping_refresh.cjs"))],
                              input=html,text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which("node"),"Node.js is required for UI behavior tests")
    def test_editor_interactions_and_draft_requests(self):
        settings=settings_fixture();layout=layout_fixture()
        data={"wallid":1,"layout":layout,"active":False,"grip_grids":settings["grids"],"coordinate_width":500,"coordinate_height":500}
        html=return_led_mapping_html(data,"/wall.jpg","/bridge")
        self.assertNotIn("__DATA__",html)
        result={**calculate_layout(settings,layout),"active":False,"unconfigured_led_ids":[]}
        completed=subprocess.run([shutil.which("node"),str(Path(__file__).with_name("led_mapping_ui.cjs"))],
                                 input=json.dumps({"html":html,"result":result}),text=True,capture_output=True,timeout=15)
        self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)
        self.assertIn("Independent LED UI passed",completed.stdout)

    def test_script_embedded_data_is_escaped(self):
        settings=settings_fixture();layout=layout_fixture();layout["grids"][0]["name"]="</script><b>unsafe __LANGUAGE__"
        html=return_led_mapping_html({"wallid":1,"layout":layout,"active":False,"grip_grids":settings["grids"],"coordinate_width":500,"coordinate_height":500},'" onerror="unsafe')
        self.assertNotIn("</script><b>unsafe",html)
        self.assertIn("unsafe __LANGUAGE__",html)
        self.assertIn("&quot; onerror=&quot;unsafe",html)
