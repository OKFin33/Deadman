"""P0-B (audit): the author + graph authoring cores must be fail-CLOSED — RAISE (not silently degrade
to {} / no-taste) when the v0.3 taste overlay is missing. A fresh clone / CI without the overlay must
error loudly, not produce taste-less drafts."""
import unittest
from pathlib import Path


class TestFailClosedOverlay(unittest.TestCase):
    def test_author_core_raises_on_missing_overlay(self):
        from tools.ars.deadman_author_drama_heroes import _require_overlay
        with self.assertRaises(FileNotFoundError):
            _require_overlay(Path("/nonexistent/studio_cab_taste_overlay.v0.3.json"))

    def test_graph_core_raises_on_missing_overlay(self):
        from tools.ars.deadman_run_studio_real_provider_proof import _require_overlay
        with self.assertRaises(FileNotFoundError):
            _require_overlay(Path("/nonexistent/studio_cab_taste_overlay.v0.3.json"))

    def test_present_overlay_loads_with_taste(self):
        from tools.ars.deadman_author_drama_heroes import _require_overlay, OVERLAY_PATH
        self.assertTrue(OVERLAY_PATH.exists(), "the real v0.3 overlay must be present for the core to load")
        d = _require_overlay(OVERLAY_PATH)
        self.assertIn("named_negatives", d)
        self.assertIn("named_positives", d)


class TestFailClosedGrounding(unittest.TestCase):
    """P0-B (finding #2): the committed synopsis + episode-memory grounding must be fail-CLOSED on the
    production-graph path (require=True). An absent committed input must RAISE, not silently no-op the
    layered context (empty l0_canon/l3_series_spine), so anti-spoiler grounding can't degrade on a clone."""

    def test_episode_memory_raises_when_required_and_absent(self):
        from tools.ars.deadman_author_drama_heroes import load_episode_memory
        with self.assertRaises(FileNotFoundError):
            load_episode_memory("__no_such_drama__", require=True)

    def test_synopsis_raises_when_required_and_file_absent(self):
        # require fails when the committed synopsis FILE itself is absent (a missing drama KEY inside an
        # existing file is fine). Patch Path.exists -> False to simulate the fresh-clone-missing-file case.
        import tools.ars.deadman_author_drama_heroes as m
        from unittest import mock
        with mock.patch.object(m.Path, "exists", return_value=False):
            with self.assertRaises(FileNotFoundError):
                m.load_synopsis("__no_such_drama__", require=True)

    def test_fail_open_default_preserved(self):
        # default (require=False) keeps the eval/dry-run fail-open behavior: missing -> {} / no raise.
        from tools.ars.deadman_author_drama_heroes import load_episode_memory
        self.assertEqual(load_episode_memory("__no_such_drama__"), {})

    def test_committed_grounding_inputs_present(self):
        # the load-bearing inputs the production path requires must be committed/present (P0-B acceptance).
        import tools.ars.deadman_author_drama_heroes as m
        for drama in ("huangnian", "lihun", "yunmiao"):
            self.assertTrue((m.REPO / f"data/review/context_memory/{drama}.v0.1.json").exists(),
                            f"committed episode memory for {drama} must be present")
        self.assertTrue((m.REPO / "data/review/drama_synopses.v0.1.json").exists(),
                        "committed drama synopses must be present")


if __name__ == "__main__":
    unittest.main()
