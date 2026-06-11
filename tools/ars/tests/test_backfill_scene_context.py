"""Tests for the scene_context backfill (deadman_backfill_scene_context) — SIDECAR edition.

Offline: a fake author provider supplies the L1 (this-beat) card; the static L0/L2/L3 layers come
from the committed synopsis + episode memory (huangnian has both). The backfill must:

  1. write the per-drama SIDECAR data/dramas/{id}/scene_context.v0.1.json keyed by moment_id,
     reshaped into the l0/l1/l2/l3 shape, WITHOUT touching moments.v0.1.json at all (the reviewed
     packs stay byte-stable);
  2. --dry-run recompute without writing the sidecar;
  3. degrade (l1 empty, L0/L2/L3 still present) when the provider is unavailable, never crash;
  4. skip a moment already present in the sidecar (idempotent re-run) unless force=True.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.ars import deadman_backfill_scene_context as backfill
from tools.ars.deadman_paths import find_deadman_root

REPO_ROOT = find_deadman_root(__file__)
SOURCE_DRAMA_DIR = REPO_ROOT / "data" / "dramas" / "huangnian"
DRAMA_ID = "huangnian"


class _CardProvider:
    """Fake author provider: returns a non-empty L1 beat card for build_scene_context's L1 call."""

    name = "fake"
    model = "fake"

    def complete_case(self, prompt: dict, schema: dict) -> dict:
        return {"payload": {
            "whats_happening": "这一刻的张力",
            "audience_already_knows": "饥荒背景，全村缺粮",
            "relationship_state": "母子之间",
            "grounding_note": "孩子懂事得让人鼻子发酸"}}


class BackfillSceneContextTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_root = Path(self._tmp.name) / "dramas"
        shutil.copytree(SOURCE_DRAMA_DIR, self.data_root / DRAMA_ID)
        self.drama_dir = self.data_root / DRAMA_ID
        self.addCleanup(self._tmp.cleanup)
        # Drop any sidecar copied from the live tree so each test starts from a clean (no-card) state.
        sidecar = self.drama_dir / "scene_context.v0.1.json"
        if sidecar.exists():
            sidecar.unlink()

    def _moments_text(self) -> str:
        return (self.drama_dir / "moments.v0.1.json").read_text("utf-8")

    def _sidecar(self) -> dict:
        return json.loads((self.drama_dir / "scene_context.v0.1.json").read_text("utf-8"))

    def test_backfill_writes_sidecar_and_leaves_moments_byte_stable(self) -> None:
        moments_before = self._moments_text()

        summary = backfill.backfill_drama(DRAMA_ID, _CardProvider(), data_root=self.data_root)
        self.assertEqual(len(summary["backfilled_moment_ids"]), 5)  # all 5 huangnian moments
        self.assertTrue(summary["written"])

        # moments.v0.1.json is byte-for-byte unchanged — the backfill never touches it.
        self.assertEqual(self._moments_text(), moments_before)

        sidecar = self._sidecar()
        self.assertEqual(sidecar["schema_version"], "scene_context.v0.1")
        self.assertEqual(sidecar["drama_id"], DRAMA_ID)
        cards = sidecar["scene_context"]
        self.assertEqual(len(cards), 5)
        for moment_id in summary["backfilled_moment_ids"]:
            sc = cards[moment_id]
            self.assertEqual(sc["l1"]["whats_happening"], "这一刻的张力")
            self.assertIn("l0_canon", sc)
            self.assertIn("l3_series_spine", sc)
            self.assertIn("l2_recent_events", sc)
        # and the moment packs themselves carry NO scene_context key.
        for m in json.loads(moments_before)["moments"]:
            self.assertNotIn("scene_context", m.get("companion_exchange", {}))

    def test_dry_run_does_not_write_sidecar(self) -> None:
        summary = backfill.backfill_drama(DRAMA_ID, _CardProvider(), data_root=self.data_root, write=False)
        self.assertFalse(summary["written"])
        self.assertEqual(len(summary["backfilled_moment_ids"]), 5)
        self.assertFalse((self.drama_dir / "scene_context.v0.1.json").exists())

    def test_no_provider_degrades_l1_empty_not_crash(self) -> None:
        # _NoProvider raises in complete_case -> build_scene_context swallows the L1 call -> empty l1,
        # but L0/L2/L3 static layers still written; no crash.
        summary = backfill.backfill_drama(DRAMA_ID, backfill._NoProvider(), data_root=self.data_root)
        self.assertEqual(len(summary["backfilled_moment_ids"]), 5)
        self.assertEqual(set(summary["empty_l1_moment_ids"]), set(summary["backfilled_moment_ids"]))
        cards = self._sidecar()["scene_context"]
        for moment_id in summary["backfilled_moment_ids"]:
            sc = cards[moment_id]
            self.assertEqual(sc["l1"], {})            # degraded: no fabricated beat
            self.assertIn("l0_canon", sc)             # static canon still present

    def test_skips_existing_unless_force(self) -> None:
        backfill.backfill_drama(DRAMA_ID, _CardProvider(), data_root=self.data_root)
        # second run: every moment already has a sidecar card -> all skipped, nothing rewritten.
        again = backfill.backfill_drama(DRAMA_ID, _CardProvider(), data_root=self.data_root)
        self.assertEqual(again["backfilled_moment_ids"], [])
        self.assertEqual(len(again["skipped_existing"]), 5)
        self.assertFalse(again["written"])
        # force=True recomputes them.
        forced = backfill.backfill_drama(DRAMA_ID, _CardProvider(), data_root=self.data_root, force=True)
        self.assertEqual(len(forced["backfilled_moment_ids"]), 5)


if __name__ == "__main__":
    unittest.main()
