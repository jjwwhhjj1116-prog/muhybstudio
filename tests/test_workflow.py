import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "automation"))
from project_v13 import create_project
from sync_workspace import inspect, start
from validate_v13 import validate_shape


def git(repo, *args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    if p.returncode:
        raise AssertionError(p.stderr)
    return p.stdout.strip()


class ProjectTests(unittest.TestCase):
    def test_external_project_has_empty_evidence_memory_and_current_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            target = create_project(Path(temp), "sample-series", "검증용 작품")
            manifest = json.loads((target / "project_manifest.json").read_text(encoding="utf-8"))
            schema = json.loads((ROOT / "schemas/project_manifest.schema.json").read_text(encoding="utf-8"))
            self.assertEqual([], validate_shape(manifest, schema))
            self.assertFalse(manifest["private_sync"]["configured"])
            self.assertEqual([], json.loads((target / "memory/knowledge.json").read_text())["items"])
            self.assertIn("05_VOICE_ALIGNMENT", json.loads((target / "stage_status.json").read_text())["stages"])

    def test_existing_project_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            target = create_project(Path(temp), "sample", "검증")
            marker = target / "PROJECT_CONTEXT.md"
            marker.write_text("Keep my manuscript", encoding="utf-8")
            with self.assertRaises(ValueError):
                create_project(Path(temp), "sample", "검증")
            self.assertEqual("Keep my manuscript", marker.read_text())

    def test_traversal_and_public_checkout_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            for slug in ["../escape", "a/b", "a\\b", "..", ""]:
                with self.assertRaises(ValueError):
                    create_project(Path(temp), slug, "검증")
        with self.assertRaises(ValueError):
            create_project(ROOT / "projects", "sample", "검증")

    def test_invalid_template_detected(self):
        data = json.loads((ROOT / "templates/project_manifest.template.json").read_text(encoding="utf-8"))
        schema = json.loads((ROOT / "schemas/project_manifest.schema.json").read_text(encoding="utf-8"))
        bad = copy.deepcopy(data)
        bad["targets"]["episode_count"] = 0
        bad["format"] = "single-feature-film"
        self.assertGreaterEqual(len(validate_shape(bad, schema)), 2)

    def test_retired_video_command_cannot_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "video.txt"
            p = subprocess.run([sys.executable, "-B", str(ROOT / "automation/build_video_from_visual.py"), "unused", str(dest)], capture_output=True)
            self.assertNotEqual(0, p.returncode)
            self.assertFalse(dest.exists())


class MultiPCSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.remote = base / "origin.git"
        git(base, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.a, self.b = base / "pc-a", base / "pc-b"
        git(base, "clone", str(self.remote), str(self.a))
        self.identity(self.a)
        self.commit(self.a, "start.txt", "initial")
        git(self.a, "push", "-u", "origin", "main")
        git(base, "clone", str(self.remote), str(self.b))
        self.identity(self.b)

    def identity(self, repo):
        git(repo, "config", "user.name", "Workflow Test")
        git(repo, "config", "user.email", "workflow@example.invalid")
        git(repo, "config", "core.autocrlf", "false")

    def commit(self, repo, filename, text):
        (repo / filename).write_text(text, encoding="utf-8")
        git(repo, "add", "--", filename)
        git(repo, "commit", "-m", "test checkpoint")

    def advance_remote(self):
        self.commit(self.a, "update.txt", "from the other PC")
        git(self.a, "push", "origin", "main")

    def test_other_pc_fast_forwards_to_shared_commit(self):
        self.advance_remote()
        before = inspect(self.b, str(self.remote))
        self.assertEqual(1, before["behind"])
        after = start(self.b, str(self.remote))
        self.assertEqual(git(self.a, "rev-parse", "HEAD"), after["head"])
        self.assertEqual("from the other PC", (self.b / "update.txt").read_text())

    def test_dirty_pc_is_not_overwritten(self):
        self.advance_remote()
        (self.b / "start.txt").write_text("unfinished local work")
        previous = git(self.b, "rev-parse", "HEAD")
        with self.assertRaises(RuntimeError):
            start(self.b, str(self.remote))
        self.assertEqual(previous, git(self.b, "rev-parse", "HEAD"))
        self.assertEqual("unfinished local work", (self.b / "start.txt").read_text())

    def test_divergence_preserved(self):
        self.commit(self.b, "local.txt", "local commit")
        previous = git(self.b, "rev-parse", "HEAD")
        self.advance_remote()
        state = inspect(self.b, str(self.remote))
        self.assertEqual((1, 1), (state["ahead"], state["behind"]))
        with self.assertRaises(RuntimeError):
            start(self.b, str(self.remote))
        self.assertEqual(previous, git(self.b, "rev-parse", "HEAD"))

    def test_work_branch_refused(self):
        git(self.b, "switch", "-c", "workflow/local")
        with self.assertRaises(RuntimeError):
            start(self.b, str(self.remote))
        self.assertEqual("workflow/local", git(self.b, "branch", "--show-current"))

    def test_wrong_remote_refused(self):
        with self.assertRaises(RuntimeError):
            inspect(self.b, "https://example.invalid/not-this-repo.git")


if __name__ == "__main__":
    unittest.main()
