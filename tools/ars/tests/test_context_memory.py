"""Tests for the layered context memory's KNOWLEDGE HORIZON gating (the anti-spoiler core).

The load-bearing invariant: for a window in episode N, the assembler injects ONLY episodes < N
(L3 = all prior, L2 = previous 2) — never episode N or later. A break here = the companion spoils.
"""
import unittest

from tools.ars.deadman_author_drama_heroes import episode_num, gated_memory


class TestContextGating(unittest.TestCase):
    def setUp(self):
        self.eps = {f"d_ep{n:02d}": {"l3_one_line": f"L3-{n}", "l2_event_log": [f"E{n}a", f"E{n}b"]}
                    for n in range(1, 6)}

    def test_episode_num(self):
        self.assertEqual(episode_num("huangnian_ep03"), 3)
        self.assertEqual(episode_num("d_ep12"), 12)
        self.assertEqual(episode_num(""), 0)

    def test_l3_is_all_prior_episodes(self):
        l3, _ = gated_memory(self.eps, 4)
        self.assertEqual([x["episode"] for x in l3], ["d_ep01", "d_ep02", "d_ep03"])
        self.assertEqual(l3[0]["summary"], "L3-1")

    def test_l2_is_previous_two(self):
        _, l2 = gated_memory(self.eps, 4)
        self.assertEqual([x["episode"] for x in l2], ["d_ep02", "d_ep03"])
        self.assertEqual(l2[-1]["events"], ["E3a", "E3b"])

    def test_anti_spoiler_nothing_at_or_after_current(self):
        for cur in range(1, 7):
            l3, l2 = gated_memory(self.eps, cur)
            for x in l3 + l2:
                self.assertLess(episode_num(x["episode"]), cur)  # NEVER >= current

    def test_episode_one_has_no_prior(self):
        l3, l2 = gated_memory(self.eps, 1)
        self.assertEqual(l3, [])
        self.assertEqual(l2, [])

    def test_missing_index_is_empty_not_error(self):
        l3, l2 = gated_memory({}, 5)
        self.assertEqual((l3, l2), ([], []))


if __name__ == "__main__":
    unittest.main()
