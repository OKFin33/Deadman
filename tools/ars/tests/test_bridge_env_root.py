"""The producer-bridge gate must honor DEADMAN_DRAMA_DATA_ROOT.

Footgun: the gate previously hardcoded the tracked data/dramas/huangnian default and ignored
DEADMAN_DRAMA_DATA_ROOT — so with an env override set, the gate would silently validate the tracked
dir while the runtime pack_store served a DIFFERENT root. The gate now resolves the same env the
runtime reads; an explicit --drama-dir still wins.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from tools.ars import deadman_validate_producer_bridge as bridge

ENV = "DEADMAN_DRAMA_DATA_ROOT"


class BridgeEnvRootTest(unittest.TestCase):
    def test_default_root_honors_env(self) -> None:
        with mock.patch.dict(os.environ, {ENV: "/tmp/custom/dramas"}, clear=False):
            self.assertEqual(bridge.default_dramas_root(), Path("/tmp/custom/dramas"))
            self.assertEqual(bridge.default_drama_dir(), Path("/tmp/custom/dramas") / "huangnian")

    def test_default_root_falls_back_to_tracked_when_unset(self) -> None:
        env = dict(os.environ)
        env.pop(ENV, None)
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(bridge.default_dramas_root(), bridge.REPO_ROOT / "data" / "dramas")
            self.assertEqual(bridge.default_drama_dir(),
                             bridge.REPO_ROOT / "data" / "dramas" / "huangnian")

    def test_main_uses_env_root_when_drama_dir_absent(self) -> None:
        # main() with no --drama-dir resolves the env root at call time (a nonexistent dir -> the
        # validator reports it, proving the gate POINTED at the env root, not the tracked dir).
        with mock.patch.dict(os.environ, {ENV: "/tmp/does/not/exist/dramas"}, clear=False):
            with mock.patch.object(sys, "argv", ["prog"]):
                with mock.patch("builtins.print") as printed:
                    rc = bridge.main()
        self.assertEqual(rc, 1)  # nonexistent dir -> fail
        printed_text = " ".join(str(c.args[0]) for c in printed.call_args_list if c.args)
        self.assertIn("/tmp/does/not/exist/dramas/huangnian", printed_text)

    def test_explicit_drama_dir_wins_over_env(self) -> None:
        with mock.patch.dict(os.environ, {ENV: "/tmp/should/be/ignored"}, clear=False):
            with mock.patch.object(sys, "argv",
                                   ["prog", "--drama-dir", "/tmp/explicit/win/dramas/huangnian"]):
                with mock.patch("builtins.print") as printed:
                    rc = bridge.main()
        self.assertEqual(rc, 1)
        printed_text = " ".join(str(c.args[0]) for c in printed.call_args_list if c.args)
        self.assertIn("/tmp/explicit/win/dramas/huangnian", printed_text)
        self.assertNotIn("/tmp/should/be/ignored", printed_text)


if __name__ == "__main__":
    unittest.main()
