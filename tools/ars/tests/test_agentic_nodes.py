"""Component C (contract step 4 node 4b + step 6 node 4a): the candidate->scene bridge and window_gate.

Deterministic coverage only — no real provider:
  - the bridge maps a mined candidate's fields onto build_scene_context's args (build_scene_context mocked);
  - window_gate returns a valid decision enum and surfaces the v0.3 window_negatives count;
  - the v0.3 window_negatives drive reject_window / needs_context, and an injected provider can override
    an otherwise-recommendable window while a provider failure fails safe to needs_context.
"""
import unittest
from unittest import mock

from tools.ars import deadman_agentic_nodes as nodes


class _RecordingProvider:
    """Injectable window-gate provider that returns a fixed payload and records the prompt."""
    def __init__(self, decision="reject_window", rationale="mechanism-only beat", raise_exc=False):
        self.decision, self.rationale, self.raise_exc = decision, rationale, raise_exc
        self.calls = []

    def complete_case(self, prompt, schema):
        self.calls.append((prompt, schema))
        if self.raise_exc:
            raise RuntimeError("provider down")
        return {"payload": {"window_decision": self.decision, "rationale_summary": self.rationale}}


class TestCandidateSceneBridge(unittest.TestCase):
    def test_bridge_maps_flat_mined_candidate_to_build_scene_context_args(self):
        candidate = {"drama_id": "yunmiao", "episode_id": "yunmiao_ep17",
                     "start_ms": 50000, "end_ms": 60000, "drama_title": "云渺"}
        with mock.patch("tools.ars.deadman_author_drama_heroes.build_scene_context") as bsc:
            bsc.return_value = {"whats_happening": "x"}
            out = nodes.candidate_scene_context(provider="PROV", candidate=candidate)
        # P0-B: the production-graph bridge requires fail-CLOSED context grounding.
        bsc.assert_called_once_with("PROV", "yunmiao", "yunmiao_ep17", 50000, 60000, "云渺",
                                    require_grounding=True)
        self.assertEqual(out, {"whats_happening": "x"})

    def test_bridge_accepts_moment_shape_and_scales_seconds_to_ms(self):
        # moment shape: episode_id under source_drama, *_seconds under interaction_window, no *_ms
        candidate = {"drama_id": "yunmiao",
                     "source_drama": {"episode_id": "yunmiao_ep17", "title": "云渺"},
                     "interaction_window": {"start_seconds": 50.0, "end_seconds": 60.0}}
        with mock.patch("tools.ars.deadman_author_drama_heroes.build_scene_context") as bsc:
            bsc.return_value = {}
            nodes.candidate_scene_context(provider="PROV", candidate=candidate)
        bsc.assert_called_once_with("PROV", "yunmiao", "yunmiao_ep17", 50000, 60000, "云渺",
                                    require_grounding=True)

    def test_drama_falls_back_to_episode_prefix(self):
        win = nodes.resolve_candidate_window({"episode_id": "lihun_ep03", "start_ms": 0, "end_ms": 1000})
        self.assertEqual(win["drama"], "lihun")
        self.assertEqual(win["drama_title"], "lihun")  # title falls back to drama id


class TestWindowGateDeterministic(unittest.TestCase):
    def setUp(self):
        self.scene = {"whats_happening": "她当众顶了回去", "prior_window_asr": ["前情"]}

    def test_returns_valid_enum_and_surfaces_window_negatives_count(self):
        out = nodes.window_gate(self.scene, {"item_id": "fresh_window"})
        self.assertIn(out["decision"], nodes.WINDOW_DECISIONS)
        self.assertEqual(out["decision"], "recommend_window")  # no negative match, context present
        # the v0.3 window_negatives count is surfaced (there are 53 in the committed overlay)
        self.assertEqual(out["window_negatives_count"], len(nodes.window_negatives()))
        self.assertGreater(out["window_negatives_count"], 0)
        self.assertEqual(out["direction_signal"], "window")
        self.assertEqual(out["source"], "deterministic")

    def test_v03_window_negative_drives_reject(self):
        overlay = {"window_negatives": [
            {"item_id": "neg1", "pattern": "rejected_window", "note": "duplicate in-episode beat"}]}
        out = nodes.window_gate(self.scene, {"item_id": "neg1"}, overlay=overlay)
        self.assertEqual(out["decision"], "reject_window")
        self.assertEqual(out["window_negatives_count"], 1)
        self.assertEqual(out["matched_negative"]["pattern"], "rejected_window")

    def test_context_insufficient_negative_drives_needs_context(self):
        overlay = {"window_negatives": [
            {"item_id": "neg2", "pattern": "context_insufficient", "note": "no prior ASR"}]}
        out = nodes.window_gate(self.scene, {"item_id": "neg2"}, overlay=overlay)
        self.assertEqual(out["decision"], "needs_context")

    def test_thin_scene_context_drives_needs_context(self):
        thin = {"whats_happening": "", "prior_window_asr": []}
        out = nodes.window_gate(thin, {"item_id": "fresh_window"})
        self.assertEqual(out["decision"], "needs_context")

    def test_real_overlay_window_negatives_nonempty(self):
        # the committed v0.3 overlay actually carries window-layer negatives (not just lead/display/echo)
        self.assertGreater(len(nodes.window_negatives()), 0)


class TestWindowGateProviderHook(unittest.TestCase):
    def setUp(self):
        self.scene = {"whats_happening": "她当众顶了回去", "prior_window_asr": ["前情"]}

    def test_injected_provider_can_override_recommendable_window(self):
        prov = _RecordingProvider(decision="reject_window")
        out = nodes.window_gate(self.scene, {"item_id": "fresh_window"}, provider=prov)
        self.assertEqual(out["decision"], "reject_window")
        self.assertEqual(out["source"], "llm")
        self.assertEqual(out["deterministic_decision"], "recommend_window")
        self.assertEqual(len(prov.calls), 1)  # provider actually consulted
        prompt = prov.calls[0][0]
        self.assertIn("v03_window_negatives", prompt)  # gate prompt carries the v0.3 negatives

    def test_provider_failure_fails_safe_to_needs_context(self):
        prov = _RecordingProvider(raise_exc=True)
        out = nodes.window_gate(self.scene, {"item_id": "fresh_window"}, provider=prov)
        self.assertEqual(out["decision"], "needs_context")  # never silently recommends
        self.assertEqual(out["source"], "llm_unavailable")

    def test_det_reject_is_authoritative_provider_not_consulted(self):
        overlay = {"window_negatives": [{"item_id": "neg1", "pattern": "rejected_framing"}]}
        prov = _RecordingProvider(decision="recommend_window")
        out = nodes.window_gate(self.scene, {"item_id": "neg1"}, provider=prov, overlay=overlay)
        self.assertEqual(out["decision"], "reject_window")
        self.assertEqual(len(prov.calls), 0)  # det hard-reject short-circuits the provider

    def test_normalize_gate_decision_clamps_unknown(self):
        self.assertEqual(nodes.normalize_gate_decision("recommend_window"), "recommend_window")
        self.assertEqual(nodes.normalize_gate_decision("garbage"), "needs_context")


if __name__ == "__main__":
    unittest.main()
