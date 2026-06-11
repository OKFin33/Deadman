"""Tests for the drama-generic companion_exchange promote node (contract step 8 / P0-1).

The promote node owns the `companion_exchange` block on an existing reviewed-window
moment. These tests prove:
  1. an accepted draft promoted with an approve token produces a moment whose
     companion_exchange passes `deadman_validate_producer_bridge`'s checks;
  2. without an approve token the node refuses to stamp owner_reviewed (P1-A) and
     the bridge gate rejects the unreviewed exchange;
  3. it is drama-generic (no DRAMA_CONFIG / huangnian pin).
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from Deadman.tools.ars.deadman_paths import find_deadman_root
from Deadman.tools.ars.deadman_promote_companion_pack import (
    PromoteError,
    is_approve_token,
    promote_pack,
    reshape_scene_context,
    resolved_review_status,
)
from Deadman.tools.ars.deadman_validate_producer_bridge import BridgeValidator

REPO_ROOT = find_deadman_root(__file__)
SOURCE_DRAMA_DIR = REPO_ROOT / "data" / "dramas" / "huangnian"
DRAMA_ID = "huangnian"
TARGET_MOMENT_ID = "huangnian_ep12_m001"


def _minimal_draft() -> dict:
    """One accepted per-window draft in the loop/author output shape."""
    return {
        "moment_id": TARGET_MOMENT_ID,
        "companion_lead": "我刚刚真想替四蛋说一句。",
        "reply_candidates": [
            {
                "display_text": "四蛋该吃肉",
                "viewer_motivation": "心疼这个懂事到把自己排除的孩子",
                "selected_echo": "对，这孩子都懂事到先把自己排除出去了，这口肉不能再让他干闻着。",
                "emotion_role": "心疼孩子",
                "semantic_role": "include_child_first",
            },
            {
                "display_text": "别让娃白懂事",
                "viewer_motivation": "想先保住孩子这份心意",
                "selected_echo": "嗯，孩子不是来交差的，他这点心意得被看见。",
                "emotion_role": "不忍亏待",
                "semantic_role": "preserve_child_contribution",
            },
            {
                "display_text": "功劳算孩子的",
                "viewer_motivation": "想让家里人认这份功劳",
                "selected_echo": "这句我懂，孩子出力了，就该让他被家里人认真看见一次。",
                "emotion_role": "给孩子撑腰",
                "semantic_role": "name_child_contribution",
            },
        ],
    }


class PromoteCompanionPackTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_root = Path(self._tmp.name) / "dramas"
        # Copy the full reviewed-window scaffold so the bridge gate has everything it
        # needs (manifest/context/media_registry/reviewed nodes); the promote node only
        # rewrites the companion_exchange + mouthpiece alias on top of it.
        shutil.copytree(SOURCE_DRAMA_DIR, self.data_root / DRAMA_ID)
        self.drama_dir = self.data_root / DRAMA_ID
        self.addCleanup(self._tmp.cleanup)
        # The live tree now carries a scene_context sidecar (the real backfill). Drop the copied one
        # so these tests exercise promote's sidecar writes from a clean (no-card) starting state.
        _sidecar = self.drama_dir / "scene_context.v0.1.json"
        if _sidecar.exists():
            _sidecar.unlink()

    def _bridge_result(self) -> dict:
        return BridgeValidator(self.drama_dir).validate()

    def _exchange_errors(self, result: dict) -> list[str]:
        return [e for e in result["errors"] if "companion_exchange" in e]

    def test_promote_with_approve_token_passes_bridge_companion_exchange(self) -> None:
        result = promote_pack(
            DRAMA_ID,
            [_minimal_draft()],
            review_token="approve",
            data_root=self.data_root,
        )
        self.assertEqual(result["review_status"], "reviewed")
        self.assertTrue(result["owner_reviewed"])
        self.assertEqual(result["promoted_moment_ids"], [TARGET_MOMENT_ID])

        bridge = self._bridge_result()
        # The companion_exchange (+ mouthpiece alias) checks must be clean.
        self.assertEqual(
            self._exchange_errors(bridge),
            [],
            msg=f"companion_exchange bridge errors: {self._exchange_errors(bridge)}",
        )
        # And the full bridge gate passes on the promoted pack.
        self.assertEqual(bridge["status"], "pass", msg=f"bridge errors: {bridge['errors']}")

    def test_refuses_owner_reviewed_without_approve_token(self) -> None:
        # No token: must NOT stamp reviewed (P1-A); stays draft.
        result = promote_pack(
            DRAMA_ID,
            [_minimal_draft()],
            review_token=None,
            data_root=self.data_root,
        )
        self.assertEqual(result["review_status"], "draft")
        self.assertFalse(result["owner_reviewed"])

        bridge = self._bridge_result()
        self.assertEqual(bridge["status"], "fail")
        self.assertTrue(
            any("review_status is not reviewed" in e for e in self._exchange_errors(bridge)),
            msg=f"expected review_status failure, got: {self._exchange_errors(bridge)}",
        )

    def test_non_approve_token_does_not_grant_review(self) -> None:
        # A non-approve token (e.g. reject/random) is treated as no approval.
        for token in ("reject", "needs_review", "pending", "yes-please"):
            self.assertFalse(is_approve_token(token), token)
            self.assertEqual(resolved_review_status(token), "draft", token)
        for token in ("approve", "approved", "owner_reviewed", "OWNER_APPROVE"):
            self.assertTrue(is_approve_token(token), token)
            self.assertEqual(resolved_review_status(token), "reviewed", token)

    def test_drama_generic_no_huangnian_pin(self) -> None:
        # Re-home the same scaffold under a different drama id and promote there: the
        # node must not be pinned to huangnian / DRAMA_CONFIG.
        other_id = "demo_other_drama"
        shutil.copytree(self.drama_dir, self.data_root / other_id)
        result = promote_pack(
            other_id,
            [_minimal_draft()],
            review_token="approve",
            data_root=self.data_root,
        )
        self.assertEqual(result["promoted_moment_ids"], [TARGET_MOMENT_ID])
        bridge = BridgeValidator(self.data_root / other_id).validate()
        self.assertEqual(self._exchange_errors(bridge), [], msg=str(bridge["errors"]))

    def test_dry_run_does_not_write(self) -> None:
        path = self.drama_dir / "moments.v0.1.json"
        before = path.read_text(encoding="utf-8")
        result = promote_pack(
            DRAMA_ID,
            [_minimal_draft()],
            review_token="approve",
            data_root=self.data_root,
            write=False,
        )
        self.assertFalse(result["written"])
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_rejects_draft_without_three_candidates(self) -> None:
        draft = _minimal_draft()
        draft["reply_candidates"] = draft["reply_candidates"][:2]
        with self.assertRaises(PromoteError):
            promote_pack(DRAMA_ID, [draft], review_token="approve", data_root=self.data_root)

    def test_rejects_unknown_moment_id(self) -> None:
        draft = _minimal_draft()
        draft["moment_id"] = "huangnian_ep99_m999"
        with self.assertRaises(PromoteError):
            promote_pack(DRAMA_ID, [draft], review_token="approve", data_root=self.data_root)

    def test_reshape_scene_context_layers_the_card(self) -> None:
        # the flat build_scene_context() card -> the persisted l0/l1/l2/l3 shape.
        card = {
            "whats_happening": "这一刻的张力",
            "audience_already_knows": "饥荒背景",
            "relationship_state": "母子",
            "grounding_note": "孩子把自己排除在外",
            "l0_canon": {"premise": "饥荒求生", "protagonist": {"name": "娘"}},
            "l3_series_spine": [{"episode": "ep01", "summary": "开场"}],
            "l2_recent_events": [{"episode": "ep11", "events": ["分粮"]}],
            "prior_window_asr": ["前情对白"],
            "knowledge_horizon": "只知道到 ep12",
        }
        shaped = reshape_scene_context(card)
        self.assertEqual(set(shaped["l1"]),
                         {"whats_happening", "audience_already_knows", "relationship_state", "grounding_note"})
        self.assertEqual(shaped["l0_canon"], card["l0_canon"])
        self.assertEqual(shaped["l3_series_spine"], card["l3_series_spine"])
        self.assertEqual(shaped["l2_recent_events"], card["l2_recent_events"])
        self.assertEqual(shaped["prior_window_asr"], card["prior_window_asr"])
        # the four l1 fields no longer float at the card root.
        self.assertNotIn("whats_happening", shaped)
        # None / empty card -> None (so callers never write an empty scene_context).
        self.assertIsNone(reshape_scene_context(None))
        self.assertIsNone(reshape_scene_context({}))

    def test_promote_persists_scene_context_to_sidecar(self) -> None:
        # a draft carrying a build_scene_context() card -> the SIDECAR scene_context.v0.1.json keyed
        # by moment_id, reshaped, WITHOUT putting it into the promoted companion_exchange and WITHOUT
        # changing the reviewed lead/display_text/echo.
        draft = _minimal_draft()
        draft["scene_context"] = {
            "whats_happening": "四蛋只想闻个肉味",
            "audience_already_knows": "全村闹饥荒",
            "relationship_state": "母子",
            "grounding_note": "孩子懂事到先把自己排除",
            "l0_canon": {"premise": "饥荒求生", "protagonist": {}},
            "l3_series_spine": [],
            "l2_recent_events": [],
        }
        result = promote_pack(DRAMA_ID, [draft], review_token="approve", data_root=self.data_root)
        import json

        # The sidecar carries the reshaped card keyed by moment_id.
        sidecar_path = self.drama_dir / "scene_context.v0.1.json"
        self.assertEqual(result["scene_context_sidecar"], str(sidecar_path))
        sidecar = json.loads(sidecar_path.read_text("utf-8"))
        self.assertEqual(sidecar["schema_version"], "scene_context.v0.1")
        self.assertEqual(sidecar["drama_id"], DRAMA_ID)
        card = sidecar["scene_context"][TARGET_MOMENT_ID]
        self.assertEqual(card["l1"]["whats_happening"], "四蛋只想闻个肉味")
        self.assertEqual(card["l0_canon"]["premise"], "饥荒求生")

        # The promoted moment must NOT gain a scene_context key; reviewed copy untouched, bridge passes.
        pack = json.loads((self.drama_dir / "moments.v0.1.json").read_text("utf-8"))
        moment = next(m for m in pack["moments"] if m["moment_id"] == TARGET_MOMENT_ID)
        ce = moment["companion_exchange"]
        self.assertNotIn("scene_context", ce)
        self.assertEqual(ce["companion_lead"], draft["companion_lead"])
        self.assertEqual(ce["reply_candidates"][0]["display_text"], "四蛋该吃肉")
        self.assertEqual(self._bridge_result()["status"], "pass")

    def test_promote_without_card_writes_no_sidecar(self) -> None:
        # a draft with no scene_context card -> no scene_context key on the moment AND no sidecar.
        result = promote_pack(DRAMA_ID, [_minimal_draft()], review_token="approve", data_root=self.data_root)
        import json

        self.assertIsNone(result["scene_context_sidecar"])
        self.assertFalse((self.drama_dir / "scene_context.v0.1.json").exists())
        pack = json.loads((self.drama_dir / "moments.v0.1.json").read_text("utf-8"))
        moment = next(m for m in pack["moments"] if m["moment_id"] == TARGET_MOMENT_ID)
        self.assertNotIn("scene_context", moment["companion_exchange"])

    def test_promote_sidecar_merges_other_moments(self) -> None:
        # promoting moment A then moment B must keep A's card (merge, not clobber the sidecar).
        import json

        draft_a = _minimal_draft()
        draft_a["scene_context"] = {"whats_happening": "A 节拍", "l0_canon": {}, "l3_series_spine": [], "l2_recent_events": []}
        promote_pack(DRAMA_ID, [draft_a], review_token="approve", data_root=self.data_root)

        other_id = "huangnian_ep03_m001"
        draft_b = _minimal_draft()
        draft_b["moment_id"] = other_id
        draft_b["scene_context"] = {"whats_happening": "B 节拍", "l0_canon": {}, "l3_series_spine": [], "l2_recent_events": []}
        promote_pack(DRAMA_ID, [draft_b], review_token="approve", data_root=self.data_root)

        sidecar = json.loads((self.drama_dir / "scene_context.v0.1.json").read_text("utf-8"))["scene_context"]
        self.assertEqual(sidecar[TARGET_MOMENT_ID]["l1"]["whats_happening"], "A 节拍")
        self.assertEqual(sidecar[other_id]["l1"]["whats_happening"], "B 节拍")


if __name__ == "__main__":
    unittest.main()
