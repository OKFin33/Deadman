from __future__ import annotations

import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import Deadman.tools.ars.deadman_run_producer_graph as producer_graph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from Deadman.tools.ars.deadman_run_producer_graph import (
    LLM_CANDIDATE_JUDGMENT_SCHEMA,
    LLM_BATCH_MANIFEST_SCHEMA,
    LLM_DRAMA_CONTEXT_DRAFT_SCHEMA,
    LLM_MOMENT_PACK_DRAFTS_SCHEMA,
    LLM_SEMANTIC_CANDIDATES_SCHEMA,
    REVIEW_REQUEST_SCHEMA,
    ProducerConfig,
    append_errors,
    build_spike_graph,
    command_plan,
    command_log_path,
    graph_node_order,
    is_interrupt_result,
    llm_cache_key_hash,
    manifest_path,
    merge_dict,
    read_json,
    repo_relative,
    resume_config_from_manifest,
    run_child,
    run_llm_candidate_judge,
    run_llm_drama_context_draft,
    run_llm_json_node,
    run_llm_moment_pack_draft,
    run_llm_semantic_miner,
    stable_review_payload,
    validate_json_schema,
    verify_command_plan,
    write_json,
)
from Deadman.tools.ars.deadman_producer_graph_llm import (
    ArkCandidateJudgeProvider,
    LlmProviderError,
    build_candidate_judge_prompt,
    normalize_context_draft,
)


@contextmanager
def patched_env(values: dict[str, str], *, clear: bool = False):
    previous = os.environ.copy()
    try:
        if clear:
            os.environ.clear()
        os.environ.update(values)
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


@contextmanager
def patched_attr(obj: object, name: str, value: object):
    previous = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, previous)


class ProducerGraphTests(unittest.TestCase):
    def test_reducers_preserve_existing_state(self) -> None:
        self.assertEqual(merge_dict({"a": 1}, {"b": 2, "a": 3}), {"a": 3, "b": 2})
        self.assertEqual(
            append_errors([{"node": "a", "code": "old"}], [{"node": "b", "code": "new"}]),
            [{"node": "a", "code": "old"}, {"node": "b", "code": "new"}],
        )

    def test_review_request_hash_is_stable_and_schema_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="hash_stable")
            self._write_candidate_inputs(config)

            payload_a, hash_a = stable_review_payload(config)
            payload_b, hash_b = stable_review_payload(config)

            self.assertEqual(hash_a, hash_b)
            self.assertEqual(payload_a, payload_b)
            ok, message = validate_json_schema(payload_a, REVIEW_REQUEST_SCHEMA)
            self.assertTrue(ok, message)

    def test_mock_llm_candidate_judge_writes_schema_valid_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="llm_mock", enable_llm=True, mock_provider=True)
            self._write_candidate_inputs(config)

            ok, message = run_llm_candidate_judge(config)

            self.assertTrue(ok, message)
            output = read_json(config.run_dir / "llm_candidate_judgment.json")
            schema_ok, schema_message = validate_json_schema(output, LLM_CANDIDATE_JUDGMENT_SCHEMA)
            self.assertTrue(schema_ok, schema_message)
            self.assertEqual(output["task"], "llm_candidate_judge")
            self.assertEqual(output["provider"]["mock_provider"], True)
            self.assertEqual(output["judgment_count"], 3)
            self.assertEqual(output["input_candidate_count"], 3)
            self.assertEqual(output["shortlist_policy"]["shortlist_target"], 3)
            self.assertEqual(output["decisions_summary"]["recommend"], 1)

    def test_mock_all_llm_nodes_write_schema_valid_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="llm_all_mock", enable_llm=True, mock_provider=True)
            self._write_candidate_inputs(config)

            checks = [
                (run_llm_semantic_miner, "llm_semantic_candidates.json", LLM_SEMANTIC_CANDIDATES_SCHEMA),
                (run_llm_candidate_judge, "llm_candidate_judgment.json", LLM_CANDIDATE_JUDGMENT_SCHEMA),
                (run_llm_drama_context_draft, "llm_drama_context_draft.json", LLM_DRAMA_CONTEXT_DRAFT_SCHEMA),
                (run_llm_moment_pack_draft, "llm_moment_pack_drafts.json", LLM_MOMENT_PACK_DRAFTS_SCHEMA),
            ]
            for runner, artifact_name, schema in checks:
                ok, message = runner(config)
                self.assertTrue(ok, f"{artifact_name}: {message}")
                output = read_json(config.run_dir / artifact_name)
                schema_ok, schema_message = validate_json_schema(output, schema)
                self.assertTrue(schema_ok, f"{artifact_name}: {schema_message}")

            semantic = read_json(config.run_dir / "llm_semantic_candidates.json")
            judgment = read_json(config.run_dir / "llm_candidate_judgment.json")
            context_draft = read_json(config.run_dir / "llm_drama_context_draft.json")
            moment_drafts = read_json(config.run_dir / "llm_moment_pack_drafts.json")
            self.assertGreaterEqual(semantic["candidate_count"], 3)
            self.assertEqual(judgment["judgment_count"], judgment["shortlist_policy"]["shortlist_target"])
            self.assertLessEqual(judgment["judgment_count"], judgment["input_candidate_count"])
            self.assertIn("context_draft", context_draft)
            self.assertEqual(moment_drafts["draft_count"], 1)
            review_payload, _ = stable_review_payload(config)
            review_ok, review_message = validate_json_schema(review_payload, REVIEW_REQUEST_SCHEMA)
            self.assertTrue(review_ok, review_message)
            self.assertIn("llm_candidate_shortlist", review_payload)
            self.assertIn("c1", review_payload["llm_candidate_shortlist"]["candidate_ids"])
            self.assertEqual(
                review_payload["llm_candidate_shortlist"]["shortlist_policy"]["shortlist_target"],
                3,
            )

    def test_llm_graph_order_contains_all_extension_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="llm_order", enable_llm=True, mock_provider=True)
            order = graph_node_order(config)
            self.assertLess(order.index("mine_candidates"), order.index("llm_semantic_miner"))
            self.assertLess(order.index("llm_semantic_miner"), order.index("cluster_candidates"))
            self.assertLess(order.index("cluster_candidates"), order.index("llm_candidate_judge"))
            self.assertLess(order.index("human_review_gate"), order.index("llm_drama_context_draft"))
            self.assertLess(order.index("llm_drama_context_draft"), order.index("llm_moment_pack_draft"))
            self.assertLess(order.index("llm_moment_pack_draft"), order.index("build_drama_context"))

    def test_candidate_judge_prompt_uses_pool_with_shortlist_policy(self) -> None:
        candidate_data = {"candidates": [self._candidate(f"c{i}", rank=i, score=100 - i) for i in range(20)]}
        semantic_data = {
            "candidates": [
                {
                    "semantic_candidate_id": f"s{i}",
                    "origin": "llm_discovered",
                    "confidence": 0.7,
                    "evidence_excerpt": "semantic evidence",
                }
                for i in range(10)
            ]
        }

        with patched_env(
            {
                "LLM_CANDIDATE_JUDGE_POOL_LIMIT": "15",
                "LLM_CANDIDATE_JUDGE_SEMANTIC_POOL_LIMIT": "4",
                "LLM_CANDIDATE_JUDGE_SHORTLIST_LIMIT": "6",
            }
        ):
            prompt = build_candidate_judge_prompt(
                run_id="r",
                drama_id="d",
                drama_title="D",
                source_candidate_ref="candidates.json",
                candidate_data=candidate_data,
                semantic_candidate_data=semantic_data,
            )

        self.assertEqual(len(prompt["candidates"]), 19)
        self.assertEqual(prompt["selection_policy"]["deterministic_total"], 20)
        self.assertEqual(prompt["selection_policy"]["deterministic_pool_size"], 15)
        self.assertEqual(prompt["selection_policy"]["semantic_pool_size"], 4)
        self.assertEqual(prompt["selection_policy"]["shortlist_target"], 6)
        self.assertEqual(prompt["selection_policy"]["shortlist_policy"]["mode"], "override")
        self.assertIn("不吐不快", prompt["selection_policy"]["semantic_filter"])
        self.assertEqual(prompt["shortlist_limit"], 6)

    def test_candidate_judge_shortlist_budget_scales_with_source_count(self) -> None:
        candidates = []
        for index in range(100):
            candidate = self._candidate(f"c{index}", rank=index + 1, score=100 - index)
            candidate["episode_id"] = f"ep{index % 40:02d}"
            candidates.append(candidate)
        source_window_data = {
            "windows": [
                {"episode_id": f"ep{index:02d}", "window_id": f"w{index:02d}"}
                for index in range(40)
            ]
        }

        with patched_env({}, clear=True):
            prompt = build_candidate_judge_prompt(
                run_id="r",
                drama_id="d",
                drama_title="D",
                source_candidate_ref="candidates.json",
                candidate_data={"candidates": candidates},
                source_window_data=source_window_data,
            )

        self.assertEqual(prompt["selection_policy"]["deterministic_pool_size"], 100)
        self.assertEqual(prompt["selection_policy"]["source_count"], 40)
        self.assertEqual(prompt["selection_policy"]["shortlist_policy"]["mode"], "dynamic")
        self.assertEqual(prompt["selection_policy"]["shortlist_policy"]["source_budget"], 20)
        self.assertEqual(prompt["selection_policy"]["shortlist_target"], 20)
        self.assertEqual(prompt["shortlist_limit"], 20)

    def test_verify_command_plan_checks_runner_argv(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="verify_argv")
            result = verify_command_plan(config)

            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["errors"], [])

    def test_candidate_recall_budget_scales_from_media_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="recall_budget")
            write_json(
                config.analysis_dir / "media_index.json",
                [{"episode_id": f"ep{index:02d}"} for index in range(50)],
            )

            with patched_env({}, clear=True):
                commands = command_plan(config)

            mine_command = next(item for item in commands if item["node"] == "mine_candidates")
            max_index = mine_command["argv"].index("--max-candidates") + 1
            self.assertEqual(mine_command["argv"][max_index], "200")

    def test_llm_cache_hit_writes_current_run_artifact_without_provider_call(self) -> None:
        class CountingProvider:
            name = "fake"
            model = "fake-model"
            mock_provider = False

            def __init__(self) -> None:
                self.calls = 0

            def complete_json(self, prompt: dict[str, object], schema: dict[str, object]) -> dict[str, object]:
                self.calls += 1
                return self._output(prompt)

            def _output(self, prompt: dict[str, object]) -> dict[str, object]:
                return {
                    "schema_version": "deadman_llm_candidate_judgment.v0.1",
                    "task": "llm_candidate_judge",
                    "run_id": prompt["run_id"],
                    "drama_id": prompt["drama_id"],
                    "drama_title": prompt["drama_title"],
                    "provider": {
                        "name": self.name,
                        "model": self.model,
                        "mock_provider": False,
                        "latency_ms": 0,
                        "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                    },
                    "source_candidate_ref": "fake",
                    "input_candidate_count": 0,
                    "shortlist_policy": {},
                    "judgment_count": 0,
                    "decisions_summary": {"recommend": 0, "keep_for_review": 0, "reject": 0},
                    "judgments": [],
                }

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache_root = root / "cache"
            first_config = self._config(root, run_id="cache_first", enable_llm=True)
            second_config = self._config(root, run_id="cache_second", enable_llm=True)
            first_provider = CountingProvider()
            prompt = {
                "run_id": first_config.run_id,
                "drama_id": first_config.drama_id,
                "drama_title": first_config.drama_title,
            }
            with patched_attr(
                producer_graph,
                "make_llm_provider",
                lambda *args, **kwargs: first_provider,
            ), patched_env(
                {
                    "ARK_MODEL": "fake-model",
                    "DEADMAN_LLM_CACHE_MODE": "read_write",
                    "DEADMAN_LLM_CACHE_ROOT": str(cache_root),
                },
            ):
                ok, message = run_llm_json_node(
                    config=first_config,
                    node="llm_candidate_judge",
                    output_key="llm_candidate_judgment",
                    schema_path=LLM_CANDIDATE_JUDGMENT_SCHEMA,
                    prompt=prompt,
                )
            self.assertTrue(ok, message)
            self.assertEqual(first_provider.calls, 1)

            def fail_provider_factory(*args, **kwargs):
                raise LlmProviderError("provider should not be constructed on cache hit")

            prompt["run_id"] = second_config.run_id
            with patched_attr(
                producer_graph,
                "make_llm_provider",
                fail_provider_factory,
            ), patched_env(
                {
                    "ARK_MODEL": "fake-model",
                    "DEADMAN_LLM_CACHE_MODE": "read",
                    "DEADMAN_LLM_CACHE_ROOT": str(cache_root),
                },
            ):
                ok, message = run_llm_json_node(
                    config=second_config,
                    node="llm_candidate_judge",
                    output_key="llm_candidate_judgment",
                    schema_path=LLM_CANDIDATE_JUDGMENT_SCHEMA,
                    prompt=prompt,
                )

            self.assertTrue(ok, message)
            output = read_json(second_config.run_dir / "llm_candidate_judgment.json")
            self.assertEqual(output["run_id"], second_config.run_id)
            trace = (second_config.run_dir / "provider_trace_redacted.jsonl").read_text(encoding="utf-8")
            self.assertIn("cache_hit", trace)
            self.assertNotIn("ARK_API_KEY", trace)

    def test_llm_cache_key_normalizes_run_scoped_artifact_refs(self) -> None:
        left_ref = "tmp/deadman_producer_runs/cache_key_norm_left/llm_candidate_judgment.json"
        right_ref = "tmp/deadman_producer_runs/cache_key_norm_right/llm_candidate_judgment.json"
        write_json(
            Path(left_ref),
            {
                "same": True,
                "run_id": "cache_key_norm_left",
                "provider": {
                    "name": "mock",
                    "model": "deadman-mock-candidate-judge-v0.1",
                    "latency_ms": 1,
                    "token_usage": {"total_tokens": 11},
                },
            },
        )
        write_json(
            Path(right_ref),
            {
                "same": True,
                "run_id": "cache_key_norm_right",
                "provider": {
                    "name": "mock",
                    "model": "deadman-mock-candidate-judge-v0.1",
                    "latency_ms": 9,
                    "token_usage": {"total_tokens": 99},
                },
            },
        )

        left_hash, _ = llm_cache_key_hash(
            node="llm_drama_context_draft",
            chunk_id="single",
            provider="mock",
            model="deadman-mock-drama-context-draft-v0.1",
            schema_path=LLM_DRAMA_CONTEXT_DRAFT_SCHEMA,
            prompt={
                "run_id": "cache_key_norm_left",
                "drama_id": "testdrama",
                "source_refs": {"llm_candidate_judgment": left_ref},
                "nested": {"run_id": "cache_key_norm_left", "artifact": left_ref},
            },
        )
        right_hash, _ = llm_cache_key_hash(
            node="llm_drama_context_draft",
            chunk_id="single",
            provider="mock",
            model="deadman-mock-drama-context-draft-v0.1",
            schema_path=LLM_DRAMA_CONTEXT_DRAFT_SCHEMA,
            prompt={
                "run_id": "cache_key_norm_right",
                "drama_id": "testdrama",
                "source_refs": {"llm_candidate_judgment": right_ref},
                "nested": {"run_id": "cache_key_norm_left", "artifact": left_ref},
            },
        )

        self.assertEqual(left_hash, right_hash)

    def test_candidate_judge_batch_merge_writes_manifest_and_review_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="judge_batch", enable_llm=True, mock_provider=True)
            self._write_candidate_inputs(config)
            candidate_dir = config.analysis_dir / "candidates"
            write_json(
                candidate_dir / f"{config.drama_id}_candidates.v0.1.json",
                {
                    "version": "v0.1",
                    "candidates": [
                        self._candidate(f"c{index}", rank=index + 1, score=100 - index)
                        for index in range(9)
                    ],
                },
            )

            with patched_env(
                {
                    "LLM_CANDIDATE_JUDGE_BATCH_SIZE": "3",
                    "LLM_CHUNK_CONCURRENCY": "2",
                    "DEADMAN_LLM_CACHE_MODE": "off",
                },
            ):
                ok, message = run_llm_candidate_judge(config)

            self.assertTrue(ok, message)
            output = read_json(config.run_dir / "llm_candidate_judgment.json")
            self.assertEqual(output["input_candidate_count"], 9)
            self.assertEqual(output["judgment_count"], output["shortlist_policy"]["shortlist_target"])
            self.assertEqual(output["shortlist_policy"]["batch_policy"]["chunk_count"], 3)
            chunk_paths = sorted((config.run_dir / "llm_candidate_judge_chunks").glob("*.json"))
            self.assertEqual(len(chunk_paths), 3)
            manifest = read_json(config.run_dir / "llm_batch_manifest.json")
            ok_schema, schema_message = validate_json_schema(manifest, LLM_BATCH_MANIFEST_SCHEMA)
            self.assertTrue(ok_schema, schema_message)
            self.assertEqual(manifest["nodes"]["llm_candidate_judge"]["chunk_count"], 3)
            review_payload, _ = stable_review_payload(config)
            self.assertIn("llm_batch_manifest", review_payload["hash_inputs"])

    def test_semantic_miner_batch_merge_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="semantic_batch", enable_llm=True, mock_provider=True)
            self._write_candidate_inputs(config)
            candidate_dir = config.analysis_dir / "candidates"
            write_json(
                candidate_dir / f"{config.drama_id}_windows.v0.1.json",
                {
                    "version": "v0.1",
                    "windows": [
                        {
                            "window_id": f"w{index}",
                            "episode_id": f"ep{index // 2}",
                            "start_ms": index * 1000,
                            "end_ms": index * 1000 + 500,
                            "transcript_text": "A tense source window where a viewer may want to intervene.",
                            "source_quality": "asr",
                        }
                        for index in range(4)
                    ],
                },
            )

            with patched_env(
                {
                    "LLM_SEMANTIC_MINER_BATCH_MODE": "on",
                    "LLM_SEMANTIC_MINER_WINDOW_CAP": "1",
                    "LLM_CHUNK_CONCURRENCY": "2",
                    "DEADMAN_LLM_CACHE_MODE": "off",
                },
            ):
                ok, message = run_llm_semantic_miner(config)

            self.assertTrue(ok, message)
            output = read_json(config.run_dir / "llm_semantic_candidates.json")
            schema_ok, schema_message = validate_json_schema(output, LLM_SEMANTIC_CANDIDATES_SCHEMA)
            self.assertTrue(schema_ok, schema_message)
            self.assertGreaterEqual(output["candidate_count"], 1)
            chunk_paths = sorted((config.run_dir / "llm_semantic_miner_chunks").glob("*.json"))
            self.assertEqual(len(chunk_paths), 4)
            manifest = read_json(config.run_dir / "llm_batch_manifest.json")
            self.assertEqual(manifest["nodes"]["llm_semantic_miner"]["chunk_count"], 4)

    def test_candidate_judge_batch_parallel_matches_serial_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            serial_config = self._config(root, run_id="judge_batch_serial", enable_llm=True, mock_provider=True)
            parallel_config = self._config(root, run_id="judge_batch_parallel", enable_llm=True, mock_provider=True)
            self._write_candidate_inputs(serial_config)
            self._write_candidate_inputs(parallel_config)
            candidate_dir = serial_config.analysis_dir / "candidates"
            write_json(
                candidate_dir / f"{serial_config.drama_id}_candidates.v0.1.json",
                {
                    "version": "v0.1",
                    "candidates": [
                        self._candidate(f"c{index}", rank=index + 1, score=100 - index)
                        for index in range(12)
                    ],
                },
            )
            with patched_env(
                {"LLM_CANDIDATE_JUDGE_BATCH_SIZE": "4", "LLM_CHUNK_CONCURRENCY": "1", "DEADMAN_LLM_CACHE_MODE": "off"},
            ):
                ok, message = run_llm_candidate_judge(serial_config)
            self.assertTrue(ok, message)
            serial_ids = [
                item["candidate_id"]
                for item in read_json(serial_config.run_dir / "llm_candidate_judgment.json")["judgments"]
            ]
            with patched_env(
                {"LLM_CANDIDATE_JUDGE_BATCH_SIZE": "4", "LLM_CHUNK_CONCURRENCY": "2", "DEADMAN_LLM_CACHE_MODE": "off"},
            ):
                ok, message = run_llm_candidate_judge(parallel_config)
            self.assertTrue(ok, message)
            parallel_ids = [
                item["candidate_id"]
                for item in read_json(parallel_config.run_dir / "llm_candidate_judgment.json")["judgments"]
            ]
            self.assertEqual(serial_ids, parallel_ids)

    def test_candidate_judge_batch_failure_blocks_parent_output(self) -> None:
        class FailingChunkProvider:
            name = "fake"
            model = "fake-model"
            mock_provider = False

            def complete_json(self, prompt: dict[str, object], schema: dict[str, object]) -> dict[str, object]:
                candidates = prompt.get("candidates")
                candidate_ids = [
                    str(candidate.get("candidate_id"))
                    for candidate in candidates
                    if isinstance(candidate, dict)
                ]
                if "c2" in candidate_ids:
                    raise LlmProviderError("ark request failed: HTTP 500")
                return {
                    "schema_version": "deadman_llm_candidate_judgment.v0.1",
                    "task": "llm_candidate_judge",
                    "run_id": prompt["run_id"],
                    "drama_id": prompt["drama_id"],
                    "drama_title": prompt["drama_title"],
                    "provider": {
                        "name": self.name,
                        "model": self.model,
                        "mock_provider": False,
                        "latency_ms": 0,
                        "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                    },
                    "source_candidate_ref": prompt.get("source_candidate_ref", ""),
                    "input_candidate_count": len(candidate_ids),
                    "shortlist_policy": prompt.get("selection_policy", {}),
                    "judgment_count": len(candidate_ids),
                    "decisions_summary": {
                        "recommend": len(candidate_ids),
                        "keep_for_review": 0,
                        "reject": 0,
                    },
                    "judgments": [
                        {
                            "candidate_id": candidate_id,
                            "decision": "recommend",
                            "confidence": 0.8,
                            "rationale": "Immediate pressure.",
                            "failure_modes": [],
                            "source_refs": {},
                        }
                        for candidate_id in candidate_ids
                    ],
                }

        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="judge_batch_failure", enable_llm=True)
            self._write_candidate_inputs(config)
            candidate_dir = config.analysis_dir / "candidates"
            write_json(
                candidate_dir / f"{config.drama_id}_candidates.v0.1.json",
                {
                    "version": "v0.1",
                    "candidates": [
                        self._candidate(f"c{index}", rank=index + 1, score=100 - index)
                        for index in range(5)
                    ],
                },
            )
            provider = FailingChunkProvider()
            with patched_attr(
                producer_graph,
                "make_llm_provider",
                lambda *args, **kwargs: provider,
            ), patched_env(
                {
                    "LLM_CANDIDATE_JUDGE_BATCH_SIZE": "2",
                    "LLM_CHUNK_CONCURRENCY": "1",
                    "DEADMAN_LLM_CACHE_MODE": "off",
                    "LLM_PROVIDER_MAX_ATTEMPTS": "1",
                    "LLM_PROVIDER_RETRY_BASE_SECONDS": "0",
                }
            ):
                ok, message = run_llm_candidate_judge(config)

            self.assertFalse(ok)
            self.assertIn("chunk judge_candidates_0002_0004 failed", message)
            self.assertFalse((config.run_dir / "llm_candidate_judgment.json").exists())
            trace = (config.run_dir / "provider_trace_redacted.jsonl").read_text(encoding="utf-8")
            self.assertIn("provider_failed", trace)

    def test_resume_config_restores_llm_mode_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            start_config = self._config(root, run_id="resume_restore", enable_llm=True, mock_provider=True)
            write_json(
                manifest_path(start_config),
                {
                    "run_id": start_config.run_id,
                    "thread_id": start_config.thread_id,
                    "drama_id": start_config.drama_id,
                    "drama_title": start_config.drama_title,
                    "paths": {
                        "analysis_dir": repo_relative(start_config.analysis_dir),
                        "video_dir": repo_relative(start_config.video_dir),
                        "drama_dir": repo_relative(start_config.drama_dir),
                        "run_dir": repo_relative(start_config.run_dir),
                    },
                    "artifacts": {
                        "reviewed_demo_nodes": repo_relative(start_config.reviewed_demo_nodes),
                        "reviewed_candidates": repo_relative(start_config.reviewed_candidates),
                    },
                    "graph": {"mode": "llm"},
                    "llm": {"enabled": True, "mock_provider": True, "allow_skip": False},
                },
            )
            resume_cli_config = self._config(root, run_id="resume_restore")

            restored = resume_config_from_manifest(resume_cli_config)

            self.assertTrue(restored.enable_llm)
            self.assertTrue(restored.mock_provider)
            self.assertIn("llm_candidate_judge", graph_node_order(restored))

    def test_child_process_timeout_is_retryable_and_logged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="child_timeout")
            with patched_attr(producer_graph, "ARS_CHILD_TIMEOUT_SECONDS", 1):
                ok, detail, code, retryable = run_child(
                    config=config,
                    node="sleepy_child",
                    argv=[sys.executable, "-c", "import time; time.sleep(2)"],
                    artifact_refs=[],
                )

            self.assertFalse(ok)
            self.assertIn("timed out", detail)
            self.assertEqual(code, "child_timeout")
            self.assertTrue(retryable)
            log_text = command_log_path(config).read_text(encoding="utf-8")
            self.assertIn('"status": "timeout"', log_text)

    def test_retryable_provider_error_retries_and_records_trace(self) -> None:
        class FlakyProvider:
            name = "fake"
            model = "fake-model"
            mock_provider = False

            def __init__(self) -> None:
                self.calls = 0

            def complete_json(self, prompt: dict[str, object], schema: dict[str, object]) -> dict[str, object]:
                self.calls += 1
                if self.calls == 1:
                    raise LlmProviderError("ark request failed: ReadTimeout: timeout")
                return {
                    "schema_version": "deadman_llm_candidate_judgment.v0.1",
                    "task": "llm_candidate_judge",
                    "run_id": prompt["run_id"],
                    "drama_id": prompt["drama_id"],
                    "drama_title": prompt["drama_title"],
                    "provider": {
                        "name": self.name,
                        "model": self.model,
                        "mock_provider": False,
                        "latency_ms": 0,
                        "token_usage": {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0,
                        },
                    },
                    "source_candidate_ref": "fake",
                    "input_candidate_count": 0,
                    "shortlist_policy": {},
                    "judgment_count": 0,
                    "decisions_summary": {
                        "recommend": 0,
                        "keep_for_review": 0,
                        "reject": 0,
                    },
                    "judgments": [],
                }

        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="provider_retry", enable_llm=True)
            provider = FlakyProvider()
            with patched_attr(
                producer_graph,
                "make_llm_provider",
                lambda *args, **kwargs: provider,
            ), patched_env(
                {
                    "DEADMAN_LLM_CACHE_MODE": "off",
                    "LLM_PROVIDER_MAX_ATTEMPTS": "2",
                    "LLM_PROVIDER_RETRY_BASE_SECONDS": "0",
                },
            ):
                ok, message = run_llm_json_node(
                    config=config,
                    node="llm_candidate_judge",
                    output_key="llm_candidate_judgment",
                    schema_path=LLM_CANDIDATE_JUDGMENT_SCHEMA,
                    prompt={
                        "run_id": config.run_id,
                        "drama_id": config.drama_id,
                        "drama_title": config.drama_title,
                    },
                )

            self.assertTrue(ok, message)
            self.assertEqual(provider.calls, 2)
            trace = (config.run_dir / "provider_trace_redacted.jsonl").read_text(encoding="utf-8")
            self.assertIn("provider_retry", trace)
            self.assertIn('"status": "pass"', trace)

    def test_real_llm_candidate_judge_requires_env_without_secret_echo(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="llm_ark_missing_env", enable_llm=True, mock_provider=False)
            self._write_candidate_inputs(config)

            with patched_env({"ARK_API_KEY": "", "ARK_MODEL": "ep-test", "ARK_ENDPOINT_ID": ""}):
                ok, message = run_llm_candidate_judge(config)

            self.assertFalse(ok)
            self.assertIn("ARK_API_KEY", message)
            self.assertNotIn("Bearer", message)
            self.assertFalse((config.run_dir / "llm_candidate_judgment.json").exists())
            trace_path = config.run_dir / "provider_trace_redacted.jsonl"
            self.assertTrue(trace_path.exists())
            trace = trace_path.read_text(encoding="utf-8")
            self.assertIn("provider_unavailable", trace)
            self.assertNotIn("Bearer", trace)

    def test_ark_payload_omits_optional_unsupported_fields_by_default(self) -> None:
        provider = ArkCandidateJudgeProvider(api_key="test-key", model="ep-test")
        with patched_env({}, clear=True):
            payload = provider._chat_payload({"run_id": "r"}, {"title": "Schema"})
        self.assertNotIn("response_format", payload)
        self.assertNotIn("thinking", payload)

        with patched_env({"ARK_ENABLE_JSON_RESPONSE_FORMAT": "1", "ARK_DISABLE_THINKING": "1"}):
            opt_in_payload = provider._chat_payload({"run_id": "r"}, {"title": "Schema"})
        self.assertEqual(opt_in_payload["response_format"], {"type": "json_object"})
        self.assertEqual(opt_in_payload["thinking"], {"type": "disabled"})

    def test_context_draft_normalizes_provider_numeric_strings(self) -> None:
        normalized = normalize_context_draft(
            {
                "premise_draft": "premise",
                "genre_contract_draft": "genre",
                "protagonist_draft": "lead",
                "core_constraints_draft": [
                    {
                        "field": "truth",
                        "value": "source first",
                        "confidence": "0.9",
                        "inference_level": "source_supported",
                        "source_refs": {"a": "b"},
                    }
                ],
                "relationship_drafts": [
                    {
                        "field": "ally",
                        "value": "needs review",
                        "confidence": "0.25",
                        "inference_level": "bad_value",
                    }
                ],
                "guardrails": ["g", 1],
                "open_questions": ["q"],
            }
        )

        self.assertEqual(normalized["core_constraints_draft"][0]["confidence"], 0.9)
        self.assertEqual(normalized["relationship_drafts"][0]["confidence"], 0.25)
        self.assertEqual(normalized["relationship_drafts"][0]["inference_level"], "human_review_required")
        self.assertEqual(normalized["guardrails"], ["g", "1"])

    def test_spike_graph_interrupts_and_resumes_with_memory_saver(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self._config(Path(temp), run_id="memory_spike")
            self._write_candidate_inputs(config)
            graph = build_spike_graph(config).compile(checkpointer=MemorySaver())
            thread_config = {"configurable": {"thread_id": config.thread_id}}

            started = graph.invoke(
                {
                    "run_id": config.run_id,
                    "status": "running",
                    "node_statuses": {"spike_review_gate": "running"},
                    "artifact_paths": {},
                    "errors": [],
                    "review_decision": "pending",
                },
                config=thread_config,
            )
            self.assertIn("__interrupt__", started)
            self.assertTrue(is_interrupt_result(started))
            self.assertFalse(is_interrupt_result({"__interrupt__": []}))
            self.assertFalse(is_interrupt_result({"__interrupt__": "not-an-interrupt"}))

            resumed = graph.invoke(Command(resume={"decision": "approve"}), config=thread_config)
            self.assertEqual(resumed["status"], "pass")
            self.assertEqual(resumed["review_decision"], "approve")

    def _config(
        self,
        root: Path,
        *,
        run_id: str,
        enable_llm: bool = False,
        mock_provider: bool = False,
    ) -> ProducerConfig:
        return ProducerConfig(
            run_id=run_id,
            drama_id="testdrama",
            drama_title="Test Drama",
            analysis_dir=root / "analysis",
            video_dir=root / "video",
            drama_dir=root / "drama",
            run_dir=root / "runs" / run_id,
            thread_id=f"deadman-producer:{run_id}",
            reviewed_demo_nodes=root / "review" / "demo_nodes.json",
            reviewed_candidates=root / "review" / "candidates.json",
            enable_llm=enable_llm,
            mock_provider=mock_provider,
        )

    def _write_candidate_inputs(self, config: ProducerConfig) -> None:
        candidate_dir = config.analysis_dir / "candidates"
        write_json(
            candidate_dir / f"{config.drama_id}_windows.v0.1.json",
            {
                "version": "v0.1",
                "windows": [
                    {
                        "window_id": "w1",
                        "episode_id": "ep1",
                        "start_ms": 0,
                        "end_ms": 20000,
                        "transcript_text": "A tense source window where a viewer may want to intervene.",
                        "source_quality": "asr",
                    }
                ],
            },
        )
        write_json(
            candidate_dir / f"{config.drama_id}_candidates.v0.1.json",
            {
                "version": "v0.1",
                "candidates": [
                    self._candidate("c1", rank=1, score=91.0),
                    self._candidate("c2", rank=12, score=72.0),
                    self._candidate("c3", rank=80, score=10.0),
                ],
            },
        )
        write_json(
            candidate_dir / f"{config.drama_id}_mechanism_buckets.v0.1.json",
            {"version": "v0.1", "mechanism_buckets": {}},
        )
        (candidate_dir / f"{config.drama_id}_field_hypotheses.v0.1.md").parent.mkdir(parents=True, exist_ok=True)
        (candidate_dir / f"{config.drama_id}_field_hypotheses.v0.1.md").write_text(
            "# Field hypotheses\n",
            encoding="utf-8",
        )
        write_json(config.reviewed_demo_nodes, {"demo_nodes": []})
        write_json(
            config.reviewed_demo_nodes,
            {
                "demo_nodes": [
                    {
                        "moment_id": "m1",
                        "candidate_id": "c1",
                        "review_status": "demo_candidate",
                        "companion_hook": "Should we intervene here?",
                        "viewer_impulse": "If I were there, I would step in.",
                        "default_options": ["Help now", "Wait", "Hide the resource"],
                        "original_plot_note_reviewed": "The original plot keeps pressure visible.",
                    }
                ]
            },
        )
        write_json(
            config.reviewed_candidates,
            {
                "reviewed_candidates": [
                    {
                        "candidate_id": "c1",
                        "review_status": "keep",
                        "episode_id": "ep1",
                        "window_id": "w1",
                        "scene_specific_hook": "Should we intervene here?",
                        "revised_default_options": ["Help now", "Wait", "Hide the resource"],
                        "why_now_reviewed": "The scene has immediate pressure.",
                        "evidence_grade": "source_supported",
                    }
                ]
            },
        )

    def _candidate(self, candidate_id: str, *, rank: int, score: float) -> dict[str, object]:
        return {
            "candidate_id": candidate_id,
            "rank": rank,
            "rank_score": score,
            "trigger_type": "resource_crisis",
            "hook": "Should this be reviewed?",
            "evidence_excerpt": "source evidence",
            "source_refs": {"candidate": repo_relative(f"tmp/{candidate_id}.json")},
        }


if __name__ == "__main__":
    unittest.main()
