"""pack_store scene_context sidecar injection — runtime fetch merges it, list/summary does not.

The heavy L0–L3 scene_context card lives in a per-drama SIDECAR (scene_context.v0.1.json), never in
moments.v0.1.json. The runtime single-moment fetch (DeadmanPackStore.get_moment) re-attaches the
card to companion_exchange.scene_context in memory so runtime_echo can ground a viewer's typed line.
The public list/summary path must NOT ship the blob to the frontend, and the cached pack moment must
never be mutated. A missing/corrupt sidecar must fail safe (no scene_context, no raise).
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from Deadman.backend.api import create_app
from Deadman.backend.pack_store import DeadmanPackStore

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DRAMA_DIR = REPO_ROOT / "data" / "dramas" / "huangnian"
DRAMA_ID = "huangnian"
MOMENT_ID = "huangnian_ep12_m001"

_CARD = {
    "l0_canon": {"premise": "饥荒求生", "protagonist": {"name": "娘"}},
    "l1": {"whats_happening": "四蛋只想闻个肉味", "audience_already_knows": "全村闹饥荒",
           "relationship_state": "母子", "grounding_note": "孩子把自己排除在外"},
    "l3_series_spine": [],
    "l2_recent_events": [],
}


class PackStoreSceneContextTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_root = Path(self._tmp.name) / "dramas"
        shutil.copytree(SOURCE_DRAMA_DIR, self.data_root / DRAMA_ID)
        self.drama_dir = self.data_root / DRAMA_ID
        # The live tree now carries a real scene_context sidecar (the backfill). Drop the copied one
        # so each test controls the sidecar (or its absence) explicitly.
        sidecar = self.drama_dir / "scene_context.v0.1.json"
        if sidecar.exists():
            sidecar.unlink()

    def _write_sidecar(self, cards: dict) -> None:
        (self.drama_dir / "scene_context.v0.1.json").write_text(
            json.dumps({"schema_version": "scene_context.v0.1", "drama_id": DRAMA_ID,
                        "scene_context": cards}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _store(self) -> DeadmanPackStore:
        return DeadmanPackStore(data_root=self.data_root)

    def test_runtime_get_moment_merges_sidecar_scene_context(self) -> None:
        self._write_sidecar({MOMENT_ID: _CARD})
        store = self._store()
        moment = store.get_moment(DRAMA_ID, MOMENT_ID)
        sc = moment["companion_exchange"]["scene_context"]
        self.assertEqual(sc["l1"]["whats_happening"], "四蛋只想闻个肉味")
        self.assertEqual(sc["l0_canon"]["premise"], "饥荒求生")

    def test_get_moment_does_not_mutate_cached_pack(self) -> None:
        self._write_sidecar({MOMENT_ID: _CARD})
        store = self._store()
        store.get_moment(DRAMA_ID, MOMENT_ID)  # injects into the returned copy only
        cached = store.get_drama(DRAMA_ID).moments_by_id[MOMENT_ID]
        self.assertNotIn("scene_context", cached["companion_exchange"])

    def test_no_sidecar_yields_no_scene_context(self) -> None:
        # fail-safe: no sidecar file at all -> moment has no scene_context (runtime_echo -> template).
        store = self._store()
        moment = store.get_moment(DRAMA_ID, MOMENT_ID)
        self.assertNotIn("scene_context", moment["companion_exchange"])

    def test_corrupt_sidecar_fails_safe(self) -> None:
        (self.drama_dir / "scene_context.v0.1.json").write_text("{ not json", encoding="utf-8")
        store = self._store()
        moment = store.get_moment(DRAMA_ID, MOMENT_ID)  # must not raise
        self.assertNotIn("scene_context", moment["companion_exchange"])

    def test_moment_absent_from_sidecar_yields_no_scene_context(self) -> None:
        self._write_sidecar({"some_other_moment": _CARD})
        store = self._store()
        moment = store.get_moment(DRAMA_ID, MOMENT_ID)
        self.assertNotIn("scene_context", moment["companion_exchange"])

    def test_public_list_and_single_moment_routes_exclude_scene_context(self) -> None:
        # Even with the sidecar present, the public HTTP surface must not ship scene_context.
        self._write_sidecar({MOMENT_ID: _CARD})
        app = create_app(store=self._store())
        client = TestClient(app)

        listing = client.get(f"/api/deadman/dramas/{DRAMA_ID}/moments")
        self.assertEqual(listing.status_code, 200)
        for summary in listing.json():
            ce = summary.get("companion_exchange") or {}
            self.assertNotIn("scene_context", ce)

        single = client.get(f"/api/deadman/dramas/{DRAMA_ID}/moments/{MOMENT_ID}")
        self.assertEqual(single.status_code, 200)
        self.assertNotIn("scene_context", single.json().get("companion_exchange", {}))


if __name__ == "__main__":
    unittest.main()
