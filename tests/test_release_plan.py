"""Public release-planning contracts; fixtures contain no actual story facts."""
import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "automation"))
from project_v13 import create_project
from validate_v13 import validate_defaults, validate_manifest, validate_release_plan, validate_shape


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def current_manifest():
    manifest = read_json(ROOT / "templates/project_manifest.template.json")
    manifest.update(project_id="planning-test", workflow_version="3.2.0", production_version="NOVEL")
    manifest["targets"].update(
        episode_count=4,
        episode_target_minutes=80,
        episode_min_runtime_seconds=4800,
        story_part_count=16,
        story_parts_per_episode=4,
        story_part_target_minutes=20,
        episode_scene_limit=200,
        script_plan_status="NOT_STARTED",
        script_chunks=None,
        allow_subchunks=True,
    )
    return manifest


def current_plan():
    return {
        "schema_version": "3.0",
        "workflow_version": "3.2.0",
        "production_version": "NOVEL",
        "project_id": "planning-test",
        "status": "NOT_STARTED",
        "public_episode_count": 4,
        "story_part_count": 16,
        "story_parts_per_episode": 4,
        "story_part_target_minutes": 20,
        "episode_scene_limit": 200,
        "episode_target_minutes": 80,
        "episode_min_runtime_seconds": 4800,
        "episodes": [
            {
                "episode_id": f"EP{number:02d}",
                "episode_number": number,
                "story_part_ids": list(range((number - 1) * 4 + 1, number * 4 + 1)),
                "planned_min_runtime_seconds": 4800,
                "runtime_seconds": None,
                "runtime_evidence": None,
                "visual_scene_count": None,
                "image_prompt_count": None,
                "video_prompt_count": None,
                "motion_scene_count": None,
            }
            for number in range(1, 5)
        ],
    }


def legacy_manifest():
    manifest = current_manifest()
    manifest["workflow_version"] = "3.0.0"
    manifest["targets"] = {
        "episode_count": 16,
        "episode_target_minutes": 15,
        "runtime_tolerance_seconds": None,
        "script_chunks": 21,
        "allow_subchunks": True,
    }
    return manifest


def file_snapshot(folder):
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in folder.rglob("*")
        if path.is_file()
    }


class ReleasePlanInitializationTests(unittest.TestCase):
    def test_new_project_uses_four_eighty_minute_episodes_and_deferred_chunks(self):
        with tempfile.TemporaryDirectory() as temp:
            target = create_project(Path(temp), "planning-test", "Validation fixture")
            manifest = read_json(target / "project_manifest.json")
            status = read_json(target / "stage_status.json")
            schema = read_json(ROOT / "schemas/project_manifest.schema.json")
            self.assertEqual("3.0", manifest["schema_version"])
            self.assertEqual("3.2.0", manifest["workflow_version"])
            expected = current_manifest()["targets"]
            for field in [
                "episode_count", "episode_target_minutes", "episode_min_runtime_seconds",
                "story_part_count", "story_parts_per_episode", "script_plan_status",
                "script_chunks", "allow_subchunks", "story_part_target_minutes", "episode_scene_limit",
            ]:
                with self.subTest(field=field):
                    self.assertEqual(expected[field], manifest["targets"][field])
            self.assertEqual("NOT_STARTED", status["stages"]["02_SCRIPT"]["status"])
            self.assertEqual([], validate_shape(manifest, schema))
            self.assertEqual([], validate_manifest(manifest, status))

    def test_new_project_saves_release_plan_without_claiming_measured_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            target = create_project(Path(temp), "planning-test", "Validation fixture")
            manifest = read_json(target / "project_manifest.json")
            plan = read_json(target / "synopsis/release_plan.json")
            self.assertEqual(current_plan(), plan)
            self.assertEqual([], validate_release_plan(plan, manifest))
            self.assertEqual(list(range(1, 17)), [
                part for episode in plan["episodes"] for part in episode["story_part_ids"]
            ])
            for episode in plan["episodes"]:
                self.assertEqual(4800, episode["planned_min_runtime_seconds"])
                self.assertIsNone(episode["runtime_seconds"])
                self.assertIsNone(episode["runtime_evidence"])

    def test_initializer_cli_creates_the_same_valid_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, "-B", str(ROOT / "automation/init_project.py"),
                 "planning-test", "--title", "Validation fixture", "--project-root", temp],
                capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            target = Path(temp) / "planning-test"
            manifest = read_json(target / "project_manifest.json")
            plan = read_json(target / "synopsis/release_plan.json")
            self.assertEqual([], validate_manifest(manifest))
            self.assertEqual(current_plan(), plan)
            self.assertEqual([], validate_release_plan(plan, manifest))

    def test_existing_project_is_byte_preserved_by_api_and_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            target = create_project(Path(temp), "planning-test", "Validation fixture")
            plan_path = target / "synopsis/release_plan.json"
            plan = read_json(plan_path)
            plan["episodes"][0]["runtime_seconds"] = 4860
            plan["episodes"][0]["runtime_evidence"] = "reports/EP01_runtime.json"
            plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            (target / "script/chunks/synthetic.txt").write_text("Preserve this test input.\n", encoding="utf-8")
            before = file_snapshot(target)
            with self.assertRaises(ValueError):
                create_project(Path(temp), "planning-test", "Replacement title")
            self.assertEqual(before, file_snapshot(target))
            result = subprocess.run(
                [sys.executable, "-B", str(ROOT / "automation/init_project.py"),
                 "planning-test", "--title", "Replacement title", "--project-root", temp],
                capture_output=True, text=True, encoding="utf-8",
            )
            self.assertNotEqual(0, result.returncode)
            self.assertEqual(before, file_snapshot(target))

    def test_legacy_project_is_not_silently_upgraded_by_reinitialization(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "planning-test"
            target.mkdir()
            manifest_path = target / "project_manifest.json"
            manifest_path.write_text(json.dumps(legacy_manifest(), indent=2) + "\n", encoding="utf-8")
            (target / "PROJECT_CONTEXT.md").write_text("Preserve this legacy test fixture.\n", encoding="utf-8")
            before = file_snapshot(target)
            with self.assertRaises(ValueError):
                create_project(Path(temp), "planning-test", "Replacement title")
            self.assertEqual(before, file_snapshot(target))
            self.assertFalse((target / "synopsis/release_plan.json").exists())


class ManifestPlanningTests(unittest.TestCase):
    def test_consistent_fractional_part_durations_tolerate_float_roundoff(self):
        manifest, plan = current_manifest(), current_plan()
        manifest["targets"].update(story_part_target_minutes=20.1, story_parts_per_episode=3,
                                    story_part_count=12, episode_target_minutes=60.3,
                                    episode_min_runtime_seconds=3618)
        plan.update(story_part_target_minutes=20.1, story_parts_per_episode=3,
                    story_part_count=12, episode_target_minutes=60.3, episode_min_runtime_seconds=3618)
        for index, episode in enumerate(plan["episodes"]):
            episode.update(story_part_ids=list(range(index * 3 + 1, index * 3 + 4)),
                           planned_min_runtime_seconds=3618)
        self.assertEqual([], validate_manifest(manifest))
        self.assertEqual([], validate_release_plan(plan, manifest))
        plan["story_part_target_minutes"] = 20.2
        self.assertTrue(validate_release_plan(plan))

    def test_version_default_booleans_cannot_be_numeric_aliases(self):
        version = read_json(ROOT / "VERSION.json")
        manifest = read_json(ROOT / "templates/project_manifest.template.json")
        plan = read_json(ROOT / "templates/release_plan.template.json")
        status = read_json(ROOT / "templates/stage_status.template.json")
        chunk = read_json(ROOT / "templates/script_chunk_state.template.json")
        self.assertEqual([], validate_defaults(version, manifest, plan, status, chunk))
        version["script_chunk_subdivision"] = 1
        self.assertTrue(validate_defaults(version, manifest, plan, status, chunk))

    def test_three_one_manifest_and_plan_preserve_their_sixty_minute_targets(self):
        manifest, plan = current_manifest(), current_plan()
        for value in [manifest, plan]:
            value["workflow_version"] = "3.1.0"
            del value["production_version"]
        manifest["targets"].update(episode_target_minutes=60, episode_min_runtime_seconds=3600)
        for field in ["story_part_target_minutes", "episode_scene_limit"]:
            del manifest["targets"][field]
            del plan[field]
        plan.update(episode_target_minutes=60, episode_min_runtime_seconds=3600)
        for episode in plan["episodes"]:
            episode["planned_min_runtime_seconds"] = 3600
            for field in ["visual_scene_count", "image_prompt_count", "video_prompt_count", "motion_scene_count"]:
                del episode[field]
        before = copy.deepcopy((manifest, plan))
        self.assertEqual([], validate_manifest(manifest))
        self.assertEqual([], validate_release_plan(plan, manifest))
        self.assertEqual(before, (manifest, plan))

    def test_three_two_requires_profile_part_duration_and_scene_limit(self):
        for field in ["production_version", "story_part_target_minutes", "episode_scene_limit"]:
            with self.subTest(field=field):
                manifest = current_manifest()
                parent = manifest if field == "production_version" else manifest["targets"]
                del parent[field]
                self.assertTrue(validate_manifest(manifest))

    def test_part_duration_must_match_the_public_episode_without_inventing_runtime(self):
        manifest = current_manifest()
        manifest["targets"]["story_part_target_minutes"] = 15
        self.assertTrue(validate_manifest(manifest))
        for value in [True, False, 0, -1, math.nan, math.inf, "20"]:
            with self.subTest(value=value):
                manifest = current_manifest()
                manifest["targets"]["story_part_target_minutes"] = value
                self.assertTrue(validate_manifest(manifest))

    def test_scene_limit_is_positive_integer_at_most_two_hundred(self):
        for value in [1, 199, 200]:
            with self.subTest(value=value):
                manifest = current_manifest()
                manifest["targets"]["episode_scene_limit"] = value
                self.assertEqual([], validate_manifest(manifest))
        for value in [201, 0, -1, True, 200.0, "200", math.nan, math.inf]:
            with self.subTest(value=value):
                manifest = current_manifest()
                manifest["targets"]["episode_scene_limit"] = value
                self.assertTrue(validate_manifest(manifest))

    def test_legacy_three_zero_manifest_keeps_its_original_targets(self):
        manifest = legacy_manifest()
        before = copy.deepcopy(manifest)
        schema = read_json(ROOT / "schemas/project_manifest.schema.json")
        self.assertEqual("3.0", manifest["schema_version"])
        self.assertEqual([], validate_shape(manifest, schema))
        self.assertEqual([], validate_manifest(manifest))
        self.assertEqual(before, manifest)

    def test_unplanned_chunk_count_is_valid_only_before_script_planning(self):
        manifest = current_manifest()
        self.assertEqual([], validate_manifest(manifest))
        for status in ["PLANNED", "IN_PROGRESS", "APPROVED", None]:
            with self.subTest(status=status):
                bad = copy.deepcopy(manifest)
                bad["targets"]["script_plan_status"] = status
                self.assertTrue(validate_manifest(bad))
        bad = copy.deepcopy(manifest)
        del bad["targets"]["script_plan_status"]
        self.assertTrue(validate_manifest(bad))

    def test_unplanned_chunks_require_not_started_script_stage_when_supplied(self):
        manifest = current_manifest()
        status = read_json(ROOT / "templates/stage_status.template.json")
        self.assertEqual([], validate_manifest(manifest, status))
        for state in ["IN_PROGRESS", "AWAITING_REVIEW", "APPROVED", "COMPLETED", None]:
            with self.subTest(state=state):
                bad = copy.deepcopy(status)
                bad["stages"]["02_SCRIPT"]["status"] = state
                self.assertTrue(validate_manifest(manifest, bad))

    def test_positive_planned_chunk_count_is_not_fixed_to_twenty_one(self):
        for count in [1, 21, 84]:
            with self.subTest(count=count):
                manifest = current_manifest()
                manifest["targets"].update(script_chunks=count, script_plan_status="PLANNED")
                self.assertEqual([], validate_manifest(manifest))

    def test_chunk_count_rejects_non_positive_and_non_integer_values(self):
        for count in [0, -1, False, True, 1.5, "21"]:
            with self.subTest(count=count):
                manifest = current_manifest()
                manifest["targets"].update(script_chunks=count, script_plan_status="PLANNED")
                self.assertTrue(validate_manifest(manifest))

    def test_story_part_totals_must_match_public_episode_allocation(self):
        for field, value in [
            ("episode_count", 5), ("story_part_count", 15), ("story_parts_per_episode", 3),
        ]:
            with self.subTest(field=field):
                manifest = current_manifest()
                manifest["targets"][field] = value
                self.assertTrue(validate_manifest(manifest))

    def test_planning_numbers_reject_booleans_and_nonfinite_values(self):
        for field in [
            "episode_count", "episode_target_minutes", "episode_min_runtime_seconds",
            "story_part_count", "story_parts_per_episode",
        ]:
            with self.subTest(field=field, value=True):
                manifest = current_manifest()
                manifest["targets"][field] = True
                self.assertTrue(validate_manifest(manifest))
        for field in ["episode_target_minutes", "episode_min_runtime_seconds"]:
            for value in [math.nan, math.inf, -math.inf]:
                with self.subTest(field=field, value=value):
                    manifest = current_manifest()
                    manifest["targets"][field] = value
                    self.assertTrue(validate_manifest(manifest))


class ReleasePlanValidationTests(unittest.TestCase):
    def test_two_hundred_scene_boundary_and_declared_lower_limit(self):
        plan = current_plan()
        plan["episodes"][0].update(visual_scene_count=200, image_prompt_count=200, video_prompt_count=200)
        self.assertEqual([], validate_release_plan(plan))
        for field in ["visual_scene_count", "image_prompt_count", "video_prompt_count", "motion_scene_count"]:
            with self.subTest(field=field):
                bad = copy.deepcopy(plan)
                bad["episodes"][0][field] = 201
                self.assertTrue(validate_release_plan(bad))
        plan["episode_scene_limit"] = 199
        self.assertTrue(validate_release_plan(plan))

    def test_novel_known_counts_agree_even_when_another_count_is_unknown(self):
        for counts in [
            {"visual_scene_count": 100, "image_prompt_count": 99},
            {"visual_scene_count": 100, "video_prompt_count": 99},
            {"image_prompt_count": 100, "video_prompt_count": 99},
            {"visual_scene_count": 100, "image_prompt_count": 100, "video_prompt_count": 99},
            {"video_prompt_count": 0},
        ]:
            with self.subTest(counts=counts):
                plan = current_plan()
                plan["episodes"][0].update(counts)
                self.assertTrue(validate_release_plan(plan))
        plan = current_plan()
        plan["episodes"][0].update(visual_scene_count=100, image_prompt_count=100)
        self.assertEqual([], validate_release_plan(plan))

    def test_webtoon_has_equal_base_and_motion_counts_and_optional_selected_video(self):
        for selected in [None, 0, 1, 7, 100]:
            with self.subTest(selected=selected):
                manifest, plan = current_manifest(), current_plan()
                manifest["production_version"] = plan["production_version"] = "WEBTOON_EXPERIMENT"
                plan["episodes"][0].update(visual_scene_count=100, image_prompt_count=100,
                                           motion_scene_count=100, video_prompt_count=selected)
                self.assertEqual([], validate_release_plan(plan, manifest))
        for counts in [
            {"visual_scene_count": 100, "image_prompt_count": 99},
            {"image_prompt_count": 100, "motion_scene_count": 99},
            {"visual_scene_count": 100, "video_prompt_count": 101},
            {"image_prompt_count": 100, "video_prompt_count": 101},
            {"motion_scene_count": 100, "video_prompt_count": 101},
        ]:
            with self.subTest(counts=counts):
                plan = current_plan()
                plan["production_version"] = "WEBTOON_EXPERIMENT"
                plan["episodes"][0].update(counts)
                self.assertTrue(validate_release_plan(plan))

    def test_profiles_are_explicit_and_cannot_mix_manifest_and_plan(self):
        plan = current_plan()
        plan["production_version"] = "WEBTOON_EXPERIMENT"
        self.assertTrue(validate_release_plan(plan, current_manifest()))
        for profile in [None, "WEBTOON", "novel", True]:
            with self.subTest(profile=profile):
                plan = current_plan()
                plan["production_version"] = profile
                self.assertTrue(validate_release_plan(plan))

    def test_unknown_prompt_counts_are_allowed_but_invalid_values_and_missing_keys_are_not(self):
        self.assertEqual([], validate_release_plan(current_plan()))
        for field in ["visual_scene_count", "image_prompt_count", "video_prompt_count", "motion_scene_count"]:
            with self.subTest(field=field, value="missing"):
                plan = current_plan()
                del plan["episodes"][0][field]
                self.assertTrue(validate_release_plan(plan))
            for value in [True, False, -1, 1.5, "100", math.nan, math.inf]:
                with self.subTest(field=field, value=value):
                    plan = current_plan()
                    plan["episodes"][0][field] = value
                    self.assertTrue(validate_release_plan(plan))

    def test_complete_ordered_allocation_is_valid_without_measured_runtime(self):
        plan = current_plan()
        self.assertEqual([], validate_release_plan(plan))
        self.assertEqual([], validate_release_plan(plan, current_manifest()))

    def test_missing_and_duplicate_parts_are_rejected(self):
        plans = []
        missing = current_plan()
        missing["episodes"][3]["story_part_ids"].pop()
        plans.append(missing)
        within = current_plan()
        within["episodes"][0]["story_part_ids"][-1] = 3
        plans.append(within)
        across = current_plan()
        across["episodes"][1]["story_part_ids"][-1] = 4
        plans.append(across)
        for number, plan in enumerate(plans):
            with self.subTest(case=number):
                self.assertTrue(validate_release_plan(plan))

    def test_parts_swapped_between_episodes_fail_even_with_full_unique_coverage(self):
        plan = current_plan()
        plan["episodes"][0]["story_part_ids"][0] = 5
        plan["episodes"][1]["story_part_ids"][0] = 1
        parts = [part for episode in plan["episodes"] for part in episode["story_part_ids"]]
        self.assertEqual(list(range(1, 17)), sorted(parts))
        self.assertEqual(16, len(set(parts)))
        self.assertTrue(validate_release_plan(plan))

    def test_episode_order_and_story_part_order_are_not_interchangeable(self):
        reversed_episodes = current_plan()
        reversed_episodes["episodes"].reverse()
        self.assertTrue(validate_release_plan(reversed_episodes))
        reordered_parts = current_plan()
        reordered_parts["episodes"][0]["story_part_ids"] = [2, 1, 3, 4]
        self.assertTrue(validate_release_plan(reordered_parts))

    def test_part_ids_reject_out_of_range_and_ambiguous_number_types(self):
        for part in [0, 17, -1, True, False, 1.0, "1", None]:
            with self.subTest(part=part):
                plan = current_plan()
                plan["episodes"][0]["story_part_ids"][0] = part
                self.assertTrue(validate_release_plan(plan))

    def test_duplicate_and_missing_public_episodes_are_rejected(self):
        missing = current_plan()
        missing["episodes"].pop()
        self.assertTrue(validate_release_plan(missing))
        duplicate = current_plan()
        duplicate["episodes"][1]["episode_id"] = "EP01"
        duplicate["episodes"][1]["episode_number"] = 1
        self.assertTrue(validate_release_plan(duplicate))
        extra = current_plan()
        extra["episodes"].append(copy.deepcopy(extra["episodes"][0]))
        self.assertTrue(validate_release_plan(extra))

    def test_episode_id_and_number_must_agree_with_their_position(self):
        for field, value in [
            ("episode_id", "EP02"), ("episode_id", "EP1"), ("episode_id", "EP05"),
            ("episode_number", 2), ("episode_number", True), ("episode_number", 1.0),
            ("episode_number", "1"),
        ]:
            with self.subTest(field=field, value=value):
                plan = current_plan()
                plan["episodes"][0][field] = value
                self.assertTrue(validate_release_plan(plan))

    def test_runtime_accepts_unknown_or_at_least_the_planned_minimum(self):
        for runtime in [None, 4800, 4800.5, 4860]:
            with self.subTest(runtime=runtime):
                plan = current_plan()
                plan["episodes"][0]["runtime_seconds"] = runtime
                if runtime is not None:
                    plan["episodes"][0]["runtime_evidence"] = "reports/EP01_runtime.json"
                self.assertEqual([], validate_release_plan(plan))

    def test_runtime_below_minimum_and_invalid_measurements_are_rejected(self):
        for runtime in [4799, 4799.9, 0, -1, True, False, "4800", math.nan, math.inf, -math.inf]:
            with self.subTest(runtime=runtime):
                plan = current_plan()
                plan["episodes"][0]["runtime_seconds"] = runtime
                plan["episodes"][0]["runtime_evidence"] = "reports/EP01_runtime.json"
                self.assertTrue(validate_release_plan(plan))

    def test_measured_runtime_requires_nonempty_relative_report_evidence(self):
        missing = current_plan()
        missing["episodes"][0]["runtime_seconds"] = 4800
        del missing["episodes"][0]["runtime_evidence"]
        self.assertTrue(validate_release_plan(missing))
        for evidence in [
            None, "", "   ", True, 1,
            "/runtime.json", "\\runtime.json", "C:/runtime.json", "C:runtime.json", "D:\\runtime.json",
            "\\\\server\\reports\\runtime.json", "../runtime.json",
            "reports/../../runtime.json", "reports\\..\\..\\runtime.json",
            "https://example.invalid/runtime.json", "file:///runtime.json",
            "reports/runtime\0.json", "reports/runtime\r.json", "reports/runtime\n.json",
            "reports/runtime\t.json", "reports/runtime\x1f.json",
        ]:
            with self.subTest(evidence=evidence):
                plan = current_plan()
                plan["episodes"][0]["runtime_seconds"] = 4800
                plan["episodes"][0]["runtime_evidence"] = evidence
                self.assertTrue(validate_release_plan(plan))

    def test_accepted_allocation_can_keep_actual_runtime_unknown(self):
        plan = current_plan()
        plan["status"] = "ACCEPTED"
        self.assertTrue(all(episode["runtime_seconds"] is None for episode in plan["episodes"]))
        self.assertEqual([], validate_release_plan(plan))

    def test_runtime_uses_the_declared_minimum_after_a_consistent_plan_change(self):
        plan = current_plan()
        plan["episode_target_minutes"] = 81
        plan["story_part_target_minutes"] = 20.25
        plan["episode_min_runtime_seconds"] = 4860
        for episode in plan["episodes"]:
            episode["planned_min_runtime_seconds"] = 4860
        plan["episodes"][0]["runtime_seconds"] = 4859
        plan["episodes"][0]["runtime_evidence"] = "reports/EP01_runtime.json"
        self.assertTrue(validate_release_plan(plan))
        plan["episodes"][0]["runtime_seconds"] = 4860
        self.assertEqual([], validate_release_plan(plan))

    def test_per_episode_plan_cannot_lower_the_public_minimum(self):
        for minimum in [4799, 0, -1, True, False, "4800", None, math.nan, math.inf, -math.inf]:
            with self.subTest(minimum=minimum):
                plan = current_plan()
                plan["episodes"][0]["planned_min_runtime_seconds"] = minimum
                self.assertTrue(validate_release_plan(plan))

    def test_release_plan_must_agree_with_manifest_identity_and_targets(self):
        for field, value in [
            ("project_id", "different-project"), ("public_episode_count", 5),
            ("story_part_count", 20), ("story_parts_per_episode", 5),
            ("episode_target_minutes", 81), ("episode_min_runtime_seconds", 4860),
        ]:
            with self.subTest(field=field):
                plan = current_plan()
                plan[field] = value
                self.assertTrue(validate_release_plan(plan, current_manifest()))

    def test_invalid_container_shapes_return_errors_without_crashing(self):
        for plan in [None, [], "release plan", {}, {"episodes": None}, {"episodes": [None]}]:
            with self.subTest(plan=plan):
                self.assertTrue(validate_release_plan(plan))

    def test_validation_preserves_the_supplied_plan_and_manifest(self):
        plan, manifest = current_plan(), current_manifest()
        before_plan, before_manifest = copy.deepcopy(plan), copy.deepcopy(manifest)
        self.assertEqual([], validate_release_plan(plan, manifest))
        self.assertEqual(before_plan, plan)
        self.assertEqual(before_manifest, manifest)


if __name__ == "__main__":
    unittest.main()
