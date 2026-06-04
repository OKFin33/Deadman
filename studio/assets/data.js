(() => {
  const NODE_CATALOG = [
    {
      id: "prepare_assets",
      zh: "\u51C6\u5907\u7D20\u6750",
      phase: "\u91C7\u96C6 \xB7 Ingest",
      llm: false,
      purpose: "\u628A\u672C\u5730 MP4 \u8F6C\u6210\u5FFD\u7565\u7684\u5236\u4F5C\u8D44\u4EA7\uFF08\u97F3\u9891 / \u5173\u952E\u5E27 / contact sheet\uFF09\u3002",
      authority: "\u672C\u5730\u8D44\u4EA7\u51C6\u5907",
      cmd: "python3 tools/ars/deadman_prepare_drama_assets.py \\\n  --drama-id {drama_id} --drama-title {drama_title} \\\n  --video-dir {video_dir} --analysis-dir {analysis_dir}",
      outputs: ["{analysis_dir}/media_index.json", "\uFF08\u5FFD\u7565\u7684\u97F3\u9891/\u5173\u952E\u5E27/contact-sheet \u4EA7\u7269\uFF09"],
      fails: ["asset_video_dir_missing", "asset_media_index_missing", "asset_prepare_failed"]
    },
    {
      id: "register_media",
      zh: "\u6CE8\u518C\u5A92\u4F53",
      phase: "\u91C7\u96C6 \xB7 Ingest",
      llm: false,
      purpose: "\u751F\u6210 runtime \u5B89\u5168\u7684\u5A92\u4F53\u6CE8\u518C\u8868\uFF1B\u672C\u5730\u8DEF\u5F84\u53EA\u7559\u5728 producer_media \u5143\u6570\u636E\u91CC\u3002",
      authority: "\u5A92\u4F53\u6CE8\u518C\uFF08runtime \u5B89\u5168\uFF09",
      cmd: "python3 tools/ars/deadman_register_media.py \\\n  --media-index {analysis_dir}/media_index.json \\\n  --out {drama_dir}/media_registry.v0.1.json \\\n  --episode-ids {episode_ids}",
      outputs: ["{drama_dir}/media_registry.v0.1.json"],
      fails: ["media_index_invalid", "media_required_episode_missing", "media_register_failed"]
    },
    {
      id: "build_timeline_windows",
      zh: "\u6784\u5EFA\u65F6\u95F4\u7A97",
      phase: "\u91C7\u96C6 \xB7 Ingest",
      llm: false,
      purpose: "\u7528 ASR / \u5173\u952E\u5E27\u751F\u6210\u5E26\u65F6\u95F4\u6233\u7684\u6E90\u7A97\u53E3\uFF1B\u7F3A ASR \u4F1A\u964D\u4F4E source_quality \u5E76\u8BB0\u5F55\u3002",
      authority: "\u6E90\u7A97\u53E3\u6784\u5EFA",
      cmd: "python3 tools/ars/deadman_build_timeline_windows.py \\\n  --analysis-dir {analysis_dir} --drama-id {drama_id} --version v0.1",
      outputs: ["{analysis_dir}/candidates/{drama_id}_windows.v0.1.json"],
      fails: ["windows_media_index_missing", "windows_build_failed"]
    },
    {
      id: "mine_candidates",
      zh: "\u5019\u9009\u6316\u6398",
      phase: "\u6316\u6398 \xB7 Mining",
      llm: false,
      purpose: "\u786E\u5B9A\u6027\u5E7F\u53EC\u56DE\u4E0E\u53EF\u56DE\u653E\u8BC1\u636E\u6C60\u3002\u53EA\u63D0\u8BAE\u3001\u6392\u5E8F\u3001\u4FDD\u7559\u8BC1\u636E\u2014\u2014\u4ECE\u4E0D\u6279\u51C6\u3001\u4ECE\u4E0D\u5B9A\u7A3F\u3002",
      authority: "\u63D0\u8BAE / \u6392\u5E8F / \u53EF\u56DE\u653E\u57FA\u7EBF",
      cmd: "python3 tools/ars/deadman_mine_candidates.py \\\n  --candidate-dir {analysis_dir}/candidates \\\n  --max-candidates {recall_budget} --drama-id {drama_id}",
      outputs: ["{analysis_dir}/candidates/{drama_id}_candidates.v0.1.json", "\u2026_candidates.v0.1.md"],
      fails: ["candidate_windows_missing", "candidate_mine_failed"]
    },
    {
      id: "llm_semantic_miner",
      zh: "\u8BED\u4E49\u6316\u6398",
      phase: "\u6316\u6398 \xB7 Mining",
      llm: true,
      purpose: "\u627E\u5173\u952E\u8BCD\u53EC\u56DE\u6F0F\u6389\u6216\u89E3\u91CA\u4E0D\u8DB3\u7684\u8BED\u4E49\u5F3A\u4EA4\u4E92\u70B9\uFF1B\u533A\u5206 deterministic_enriched \u4E0E llm_discovered\u3002",
      authority: "\u8BED\u4E49\u7406\u89E3\u4E0E\u5019\u9009\u63D0\u8BAE\uFF08\u4E0D\u5199 runtime \u5305\uFF09",
      cmd: "\uFF08\u56FE\u5185 LLM \u8282\u70B9\uFF0C--enable-llm \u65F6\u542F\u7528\uFF09\n# \u8F93\u51FA: {run_dir}/llm_semantic_candidates.json",
      outputs: ["{run_dir}/llm_semantic_candidates.json"],
      fails: ["llm_schema_invalid", "provider_failed"]
    },
    {
      id: "cluster_candidates",
      zh: "\u673A\u5236\u805A\u7C7B",
      phase: "\u6316\u6398 \xB7 Mining",
      llm: false,
      purpose: "\u6309\u673A\u5236\u4E0E\u573A\u538B\uFF08field pressure\uFF09\u7ED9\u5019\u9009\u5206\u7EC4\uFF1B\u89E3\u91CA\u573A\u538B\uFF0C\u4F46\u4ECE\u4E0D\u81EA\u884C\u6269\u5C55 runtime schema\u3002",
      authority: "\u89E3\u91CA\u573A\u538B",
      cmd: "python3 tools/ars/deadman_cluster_candidates.py \\\n  --candidate-dir {analysis_dir}/candidates --drama-id {drama_id}",
      outputs: ["{drama_id}_mechanism_buckets.v0.1.json", "{drama_id}_field_hypotheses.v0.1.md"],
      fails: ["cluster_candidates_missing", "cluster_failed"]
    },
    {
      id: "llm_candidate_judge",
      zh: "\u5019\u9009\u521D\u7B5B",
      phase: "\u6316\u6398 \xB7 Mining",
      llm: true,
      purpose: "\u786E\u5B9A\u6027\u53EC\u56DE\u4E0E\u4EBA\u5DE5\u8BC4\u5BA1\u4E4B\u95F4\u7684\u8BED\u4E49\u521D\u7B5B\u95F8\uFF1B\u53EA\u9009\u89C2\u4F17\u4F1A\u60C5\u7EEA\u6CE2\u52A8\u3001\u60F3\u7ACB\u523B\u53D1\u58F0\u7684\u65F6\u523B\uFF0C\u4EA7\u51FA shortlist\u3002",
      authority: "\u4E8C\u6B21\u7B5B\u9009 + \u5931\u8D25\u6A21\u5F0F\u6807\u6CE8\uFF08\u4E0D\u664B\u5347 runtime\uFF09",
      cmd: "\uFF08\u56FE\u5185 LLM \u8282\u70B9\uFF0C--enable-llm \u65F6\u542F\u7528\uFF09\n# \u8F93\u51FA: {run_dir}/llm_candidate_judgment.json",
      outputs: ["{run_dir}/llm_candidate_judgment.json"],
      fails: ["llm_schema_invalid", "provider_failed"]
    },
    {
      id: "prepare_human_review",
      zh: "\u51C6\u5907\u8BC4\u5BA1",
      phase: "\u8BC4\u5BA1 \xB7 Review",
      llm: false,
      purpose: "\u5728 interrupt \u4E4B\u524D\u6301\u4E45\u5316\u8BC4\u5BA1\u8BF7\u6C42\uFF0C\u5E76\u628A run \u6807\u8BB0\u4E3A waiting_for_review\uFF08\u4E0E checkpoint \u4E00\u81F4\uFF09\u3002",
      authority: "\u8BC4\u5BA1\u8BF7\u6C42\u6301\u4E45\u5316",
      cmd: "\uFF08\u56FE\u5185\u8282\u70B9\uFF09\u5199 review_request.json\uFF0C\u8BA1\u7B97 request_hash",
      outputs: ["{run_dir}/review_request.json", "manifest.status = waiting_for_review"],
      fails: ["review_request_drift"]
    },
    {
      id: "human_review_gate",
      zh: "\u4EBA\u5DE5\u8BC4\u5BA1\u95F8\u95E8",
      phase: "\u8BC4\u5BA1 \xB7 Review",
      llm: false,
      gate: true,
      purpose: "\u7528 LangGraph interrupt() \u5728\u4EFB\u4F55\u53EF\u53D1\u5E03\u72B6\u6001\u53D8\u66F4\u524D\u6682\u505C\u3002\u6279\u51C6\u2192build_drama_context\uFF1B\u9A73\u56DE\u2192\u7EC8\u6001\u3002",
      authority: "\u552F\u4E00\u6279\u51C6\u6743",
      cmd: "# resume:\npython3 tools/ars/deadman_run_producer_graph.py resume \\\n  --run-id {run_id} --review-decision approve|reject",
      outputs: ["reviewed_demo_nodes.v0.1.json", "reviewed_candidates.reviewed.v0.1.json"],
      fails: ["review_request_drift", "review_resume_invalid", "review_artifact_missing"]
    },
    {
      id: "llm_drama_context_draft",
      zh: "\u4E0A\u4E0B\u6587\u8349\u7A3F",
      phase: "\u53D1\u5E03 \xB7 Publish",
      llm: true,
      purpose: "\u4E3A\u5236\u4F5C\u4EBA\u8BC4\u5BA1\u8D77\u8349\u5267\u76EE\u4E0A\u4E0B\u6587\uFF1Binferred \u5B57\u6BB5\u6807 draft\uFF0C\u7EDD\u4E0D\u76F4\u63A5\u8986\u76D6\u5DF2\u8FFD\u8E2A\u7684 context.v0.1.json\u3002",
      authority: "\u8349\u7A3F\uFF08\u8BC4\u5BA1\u901A\u8FC7\u540E\u624D\u8FD0\u884C\uFF09",
      cmd: "\uFF08\u56FE\u5185 LLM \u8282\u70B9\uFF0Capprove \u540E\u8FD0\u884C\uFF09\n# \u8F93\u51FA: {run_dir}/llm_drama_context_draft.json",
      outputs: ["{run_dir}/llm_drama_context_draft.json"],
      fails: ["llm_schema_invalid", "provider_failed"]
    },
    {
      id: "llm_moment_pack_draft",
      zh: "Moment \u8349\u7A3F",
      phase: "\u53D1\u5E03 \xB7 Publish",
      llm: true,
      purpose: "\u4E3A\u5DF2\u6279\u51C6\u5019\u9009\u8D77\u8349 Moment Pack \u5B57\u6BB5\uFF1B\u6BCF\u6761\u5F3A\u5236 requires_human_review=true\uFF0C\u7EDD\u4E0D\u76F4\u63A5\u53D1\u5E03\u3002",
      authority: "\u8349\u7A3F\uFF08\u4EC5\u7528\u5DF2\u6279\u51C6\u5019\u9009\uFF09",
      cmd: "\uFF08\u56FE\u5185 LLM \u8282\u70B9\uFF0Capprove \u540E\u8FD0\u884C\uFF09\n# \u8F93\u51FA: {run_dir}/llm_moment_pack_drafts.json",
      outputs: ["{run_dir}/llm_moment_pack_drafts.json"],
      fails: ["llm_schema_invalid", "provider_failed"]
    },
    {
      id: "build_drama_context",
      zh: "\u6784\u5EFA\u5267\u76EE\u4E0A\u4E0B\u6587",
      phase: "\u53D1\u5E03 \xB7 Publish",
      llm: false,
      purpose: "\u628A\u5DF2\u8BC4\u5BA1\u8BC1\u636E\u8F6C\u6210\u4E0A\u4E0B\u6587\u4E0E moment pack \u6E90\u6750\u6599\uFF0C\u5E76 promote \u5230 drama_dir\u3002\u4EC5\u4ECE\u5DF2\u8BC4\u5BA1\u8F93\u5165\u6784\u5EFA\u3002",
      authority: "\u4EC5\u4ECE\u5DF2\u8BC4\u5BA1\u8F93\u5165\u6784\u5EFA",
      cmd: "python3 tools/ars/deadman_build_drama_context.py \\\n  --drama-id {drama_id} --reviewed-demo-nodes \u2026 --promote --promote-dir {drama_dir}",
      outputs: ["{analysis_dir}/drama_context/*", "promoted \u2192 {drama_dir}/"],
      fails: ["context_review_not_approved", "context_build_failed"]
    },
    {
      id: "publish_p0_bridge",
      zh: "\u53D1\u5E03 P0 \u5305",
      phase: "\u53D1\u5E03 \xB7 Publish",
      llm: false,
      purpose: "\u628A\u5DF2\u8BC4\u5BA1\u8F93\u5165\u5199\u6210 runtime \u53EF\u8BFB\u7684 pack \u6587\u4EF6\uFF08manifest / context / moments / evidence\uFF09\u3002",
      authority: "\u53EA\u4ECE\u5DF2\u8BC4\u5BA1\u8F93\u5165\u5199 runtime \u5305",
      cmd: "python3 tools/ars/deadman_publish_p0_bridge.py \\\n  --drama-dir {drama_dir} --reviewed-demo-nodes \u2026 --media-registry \u2026",
      outputs: ["{drama_dir}/manifest.v0.1.json", "context.v0.1.json", "moments.v0.1.json", "evidence/"],
      fails: ["publish_input_not_reviewed", "publish_media_registry_missing", "publish_failed"]
    },
    {
      id: "validate_producer_bridge",
      zh: "\u53D1\u5E03\u6821\u9A8C",
      phase: "\u53D1\u5E03 \xB7 Publish",
      llm: false,
      purpose: "\u62E6\u622A\u4E0D\u5B89\u5168\u7684 runtime \u4EA7\u7269\uFF1A\u68C0\u67E5\u4E00\u81F4\u6027\u3001review \u72B6\u6001\u3001runtime \u5B89\u5168\u6E90\u5F15\u7528\u3001\u65E0 raw media / .env\u3002",
      authority: "\u53D1\u5E03\u540E\u552F\u4E00\u5B89\u5168\u6743",
      cmd: "python3 tools/ars/deadman_validate_producer_bridge.py \\\n  --drama-dir {drama_dir} --report {analysis_dir}/producer_bridge_validation_report.md",
      outputs: ["producer_bridge_validation_report.md", "manifest.validation_result"],
      fails: ["validation_failed", "validation_report_missing"]
    },
    {
      id: "final_report",
      zh: "\u6700\u7EC8\u62A5\u544A",
      phase: "\u53D1\u5E03 \xB7 Publish",
      llm: false,
      purpose: "\u7ED9\u64CD\u4F5C\u8005\u4E0E\u8BC4\u5BA1\u4EBA\u7684\u603B\u7ED3\uFF1A\u6700\u7EC8\u72B6\u6001\u3001\u8282\u70B9\u8868\u3001\u5B50\u547D\u4EE4\u3001\u8BC4\u5BA1\u51B3\u5B9A\u3001\u6821\u9A8C\u7ED3\u679C\u3001runtime \u5305\u8DEF\u5F84\u3002",
      authority: "\u53EA\u62A5\u544A\uFF0C\u4E0D\u6539\u5DF2\u53D1\u5E03\u6570\u636E",
      cmd: "\uFF08\u56FE\u5185\u8282\u70B9\uFF09\u5199 final_report.md",
      outputs: ["{run_dir}/final_report.md"],
      fails: ["final_report_failed"]
    }
  ];
  const PHASES = ["\u91C7\u96C6 \xB7 Ingest", "\u6316\u6398 \xB7 Mining", "\u8BC4\u5BA1 \xB7 Review", "\u53D1\u5E03 \xB7 Publish"];
  function nodeStatuses(passList, overrides, mode) {
    const out = {};
    for (const n of NODE_CATALOG) {
      if (n.llm && mode !== "llm") {
        out[n.id] = "skipped_by_config";
        continue;
      }
      out[n.id] = passList.includes(n.id) ? "pass" : "planned";
    }
    return Object.assign(out, overrides || {});
  }
  const RUNS = [
    {
      run_id: "deadman-producer:huangnian-20260603-01",
      thread_id: "deadman-producer:huangnian-20260603-01",
      drama_id: "huangnian",
      drama_title: "\u8352\u5E74\u5168\u6751\u5543\u6811\u76AE\uFF0C\u6211\u6709\u7CFB\u7EDF\u6EE1\u4ED3\u8089",
      graph_mode: "llm",
      status: "waiting_for_review",
      started_at: "2026-06-03 09:41",
      updated_at: "2026-06-03 09:58",
      current_node: "human_review_gate",
      recall_budget: 80,
      deterministic_candidate_count: 80,
      node_statuses: nodeStatuses(
        [
          "prepare_assets",
          "register_media",
          "build_timeline_windows",
          "mine_candidates",
          "llm_semantic_miner",
          "cluster_candidates",
          "llm_candidate_judge",
          "prepare_human_review"
        ],
        { human_review_gate: "waiting_for_review" },
        "llm"
      )
    },
    {
      run_id: "deadman-producer:huangnian-20260524-07",
      thread_id: "deadman-producer:huangnian-20260524-07",
      drama_id: "huangnian",
      drama_title: "\u8352\u5E74\u5168\u6751\u5543\u6811\u76AE\uFF0C\u6211\u6709\u7CFB\u7EDF\u6EE1\u4ED3\u8089",
      graph_mode: "base",
      status: "pass",
      started_at: "2026-05-24 14:02",
      updated_at: "2026-05-24 14:39",
      current_node: "final_report",
      recall_budget: 80,
      deterministic_candidate_count: 80,
      review_decision: "approve",
      validation_result: "pass",
      published_moments: 5,
      node_statuses: nodeStatuses(NODE_CATALOG.map((n) => n.id), {}, "base")
    },
    {
      run_id: "deadman-producer:yunmiao-20260603-02",
      thread_id: "deadman-producer:yunmiao-20260603-02",
      drama_id: "yunmiao",
      drama_title: "\u4E91\u6E3A",
      graph_mode: "llm",
      status: "running",
      started_at: "2026-06-03 10:12",
      updated_at: "2026-06-03 10:15",
      current_node: "llm_candidate_judge",
      recall_budget: 64,
      deterministic_candidate_count: 64,
      node_statuses: nodeStatuses(
        [
          "prepare_assets",
          "register_media",
          "build_timeline_windows",
          "mine_candidates",
          "llm_semantic_miner",
          "cluster_candidates"
        ],
        { llm_candidate_judge: "running" },
        "llm"
      )
    },
    {
      run_id: "deadman-producer:lihun-20260531-04",
      thread_id: "deadman-producer:lihun-20260531-04",
      drama_id: "lihun",
      drama_title: "\u5E78\u5F97\u76F8\u9047\u79BB\u5A5A\u65F6",
      graph_mode: "base",
      status: "validation_failed",
      started_at: "2026-05-31 16:20",
      updated_at: "2026-05-31 16:54",
      current_node: "validate_producer_bridge",
      recall_budget: 48,
      deterministic_candidate_count: 48,
      review_decision: "approve",
      validation_result: "failed",
      node_statuses: nodeStatuses(
        [
          "prepare_assets",
          "register_media",
          "build_timeline_windows",
          "mine_candidates",
          "cluster_candidates",
          "prepare_human_review",
          "human_review_gate",
          "build_drama_context",
          "publish_p0_bridge"
        ],
        { validate_producer_bridge: "failed", final_report: "blocked_by_prior_failure" },
        "base"
      ),
      errors: [
        {
          node: "validate_producer_bridge",
          code: "validation_failed",
          retryable: false,
          message: "moments.v0.1.json \u542B\u672A\u8131\u654F\u672C\u5730\u8DEF\u5F84 tmp/\u89C6\u9891\u7D20\u6750/...\uFF0Cruntime \u6E90\u5F15\u7528\u4E0D\u5B89\u5168\u3002",
          artifact_refs: ["data/dramas/lihun/moments.v0.1.json"]
        }
      ]
    }
  ];
  const SHORTLIST = {
    run_id: "deadman-producer:huangnian-20260603-01",
    drama_id: "huangnian",
    drama_title: "\u8352\u5E74\u5168\u6751\u5543\u6811\u76AE\uFF0C\u6211\u6709\u7CFB\u7EDF\u6EE1\u4ED3\u8089",
    review_policy_version: "deadman_studio_review_gate.v0.1",
    input_candidate_count: 80,
    shortlist_target: 6,
    expected_reviewed_paths: {
      reviewed_demo_nodes: "tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json",
      reviewed_candidates: "tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json"
    },
    human_instructions: [
      "\u786E\u8BA4 interaction_window \u65F6\u95F4\u6233\u8DB3\u4EE5\u89E6\u53D1\u64AD\u653E\u5668\u63D0\u793A\u3002",
      "\u786E\u8BA4 hook \u4E0E\u9009\u9879\u8D34\u5408\u6E90\u7A97\u53E3\u8BC1\u636E\uFF0C\u4E0D\u6697\u793A\u8FDE\u7EED\u6539\u5199\u540E\u7EED\u5267\u96C6\u3002",
      "\u52FE\u9009\u8981\u53D1\u5E03\u7684\u5019\u9009\uFF1B\u9A73\u56DE\u6574\u6B21 run \u9700\u65B0\u5EFA run_id \u91CD\u6765\u3002"
    ],
    candidates: [
      {
        id: "huangnian_ep03_c001",
        episode: "huangnian_ep03",
        window: [0, 20],
        action_type: "system_rule",
        source: "deterministic_enriched",
        llm_label: "recommend",
        grade: "high",
        keep: true,
        hook: "\u91CE\u8568\u83DC\u80FD\u5356\u94B1\uFF0C\u7CFB\u7EDF\u9762\u677F\u8981\u4E0D\u8981\u73B0\u5728\u8BD5\uFF1F",
        impulse: "\u8981\u662F\u6211\u6765\uFF0C\u60F3\u7528\u7CFB\u7EDF\u80FD\u529B\u5FEB\u901F\u6539\u5C40\u9762\u3002",
        options: ["\u7ACB\u523B\u552E\u5356\u91CE\u8568\u83DC\u9A8C\u8BC1\u7CFB\u7EDF", "\u53EA\u5356\u4E00\u5C0F\u90E8\u5206\uFF0C\u786E\u8BA4\u522B\u4EBA\u770B\u4E0D\u89C1\u9762\u677F", "\u5148\u4E0D\u5356\uFF0C\u79BB\u5F00\u7076\u53F0\u518D\u5355\u72EC\u6D4B\u8BD5"],
        excerpt: "\u5929\u7136\u65E0\u6C61\u67D3\u91CE\u8568\u83DC\u4E00\u65A4\u4EF7\u503C\u5341\u6587\u94B1\uFF0C\u662F\u5426\u552E\u5356\uFF1F\u5475\uFF0C\u8FD9\u662F\u7CFB\u7EDF\uFF1F\u2026\u2026\u8FD9\u4E2A\u9762\u677F\u53EA\u6709\u6211\u80FD\u770B\u89C1\uFF0C\u6211\u5F97\u627E\u4E2A\u5730\u65B9\u8BD5\u9A8C\u4E00\u4E0B\u7CFB\u7EDF\u7684\u529F\u80FD\u3002",
        scores: { emotion_heat: 78, choice_leverage: 84, world_constraint_value: 88, watch_flow_fit: 82 },
        note: "\u7CFB\u7EDF\u7B2C\u4E00\u6B21\u51FA\u73B0\uFF0CP0 \u6700\u5E72\u51C0\u7684 hidden-power \u89C4\u5219\u8FB9\u754C\u3002"
      },
      {
        id: "huangnian_ep04_c001",
        episode: "huangnian_ep04",
        window: [12, 32],
        action_type: "resource",
        source: "deterministic",
        llm_label: "recommend",
        grade: "high",
        keep: true,
        hook: "\u6362\u6765\u7684\u7CAE\u98DF\u53EA\u591F\u4E00\u987F\uFF0C\u5148\u7D27\u7740\u8C01\uFF1F",
        impulse: "\u8981\u662F\u6211\u6765\uFF0C\u5148\u628A\u6700\u997F\u7684\u4EBA\u5582\u9971\u3002",
        options: ["\u5168\u7ED9\u5B69\u5B50\uFF0C\u81EA\u5DF1\u625B\u997F", "\u5747\u5206\u4E00\u5C0F\u4EFD\uFF0C\u7559\u4E00\u70B9\u5E94\u6025", "\u6362\u6210\u8010\u653E\u7684\u6742\u7CAE\uFF0C\u62C9\u957F\u8FD9\u70B9\u5B58\u91CF"],
        excerpt: "\u5C31\u8FD9\u4E00\u70B9\u4E86\u2026\u2026\u7701\u7740\u70B9\u5403\uFF0C\u6491\u4E0D\u5230\u4E0B\u56DE\u8D76\u96C6\u3002",
        scores: { emotion_heat: 80, choice_leverage: 72, world_constraint_value: 79, watch_flow_fit: 81 },
        note: "\u8D44\u6E90\u5206\u914D\u538B\u529B\u6E05\u6670\uFF0C\u8BC1\u636E\u6765\u81EA\u8D76\u96C6/\u5206\u7CAE ASR\u3002"
      },
      {
        id: "huangnian_ep06_c001",
        episode: "huangnian_ep06",
        window: [40, 62],
        action_type: "relationship",
        source: "llm_discovered",
        llm_label: "keep_for_review",
        grade: "medium",
        keep: true,
        hook: "\u6751\u90BB\u4E0A\u95E8\u501F\u7CAE\uFF0C\u501F\u8FD8\u662F\u4E0D\u501F\uFF1F",
        impulse: "\u8981\u662F\u6211\u6765\uFF0C\u4E0D\u60F3\u6495\u7834\u8138\uFF0C\u4E5F\u4E0D\u60F3\u88AB\u638F\u7A7A\u3002",
        options: ["\u501F\u4E00\u70B9\uFF0C\u7ACB\u4E2A\u660E\u786E\u7684\u8FD8\u6CD5", "\u4E0D\u501F\uFF0C\u4F46\u5E2E\u7740\u51FA\u522B\u7684\u4E3B\u610F", "\u53EA\u501F\u7ED9\u771F\u6B63\u65AD\u987F\u7684\u90A3\u5BB6"],
        excerpt: "\u90FD\u662F\u4E00\u4E2A\u6751\u7684\uFF0C\u4F60\u5BB6\u6709\u4F59\u7CAE\uFF0C\u5300\u6211\u4EEC\u4E00\u53E3\u2026\u2026",
        scores: { emotion_heat: 74, choice_leverage: 70, world_constraint_value: 83, watch_flow_fit: 76 },
        note: "\u66B4\u9732\u4E0E\u4EBA\u60C5\u98CE\u9669\u5E76\u5B58\uFF1B\u8BED\u4E49\u6316\u6398\u8865\u5230\uFF0C\u9700\u4EBA\u5DE5\u786E\u8BA4\u7A97\u53E3\u3002"
      },
      {
        id: "huangnian_ep07_c001",
        episode: "huangnian_ep07",
        window: [20, 40],
        action_type: "humiliation",
        source: "deterministic_enriched",
        llm_label: "recommend",
        grade: "high",
        keep: true,
        hook: "\u513F\u5AB3\u88AB\u903C\u5403\u6700\u810F\u7684\u4E1C\u897F\uFF0C\u8981\u4E0D\u8981\u5F53\u573A\u6539\u684C\u89C4\uFF1F",
        impulse: "\u8981\u662F\u6211\u6765\uFF0C\u5148\u8BA9\u773C\u524D\u7684\u4EBA\u5403\u4E0A\u4E00\u53E3\u5E72\u51C0\u7684\u3002",
        options: ["\u5F53\u573A\u8BA9\u513F\u5AB3\u4E0A\u684C\uFF0C\u63A8\u7FFB\u65E7\u89C4\u77E9", "\u5148\u628A\u996D\u6362\u6389\uFF0C\u518D\u79C1\u4E0B\u5904\u7406\u5A46\u5AB3\u6743\u529B", "\u4E0D\u5F53\u4F17\u7FFB\u8138\uFF0C\u53EA\u8BA9\u5979\u5148\u5403\u4E00\u53E3\u5E72\u51C0\u7684"],
        excerpt: "\u4F60\u662F\u5730\u4F4D\u6700\u4F4E\uFF0C\u6839\u672C\u4E0D\u914D\u4E0A\u684C\u5403\u996D\uFF0C\u53EA\u80FD\u5403\u6700\u96BE\u5403\u6700\u810F\u7684\u4E1C\u897F\uFF0C\u4E0D\u7136\u5C31\u7ED9\u6211\u997F\u7740\u3002",
        scores: { emotion_heat: 85, choice_leverage: 74, world_constraint_value: 76, watch_flow_fit: 82 },
        note: "\u9996\u8F6E\u8BEF\u6807 resource_crisis\uFF0C\u5B9E\u4E3A\u5BB6\u5EAD\u7F9E\u8FB1+\u79E9\u5E8F\u4FEE\u590D\uFF1B\u60C5\u7EEA\u70ED\u5EA6\u6700\u9AD8\u3002"
      },
      {
        id: "huangnian_ep12_c001",
        episode: "huangnian_ep12",
        window: [0, 20],
        action_type: "resource",
        source: "deterministic",
        llm_label: "recommend",
        grade: "high",
        keep: true,
        hook: "\u56DB\u86CB\u6293\u5230\u5154\u5B50\uFF0C\u5154\u5B50\u8089\u4ECA\u665A\u8981\u4E0D\u8981\u771F\u7684\u4E0B\u9505\uFF1F",
        impulse: "\u8981\u662F\u6211\u6765\uFF0C\u5148\u8BA9\u773C\u524D\u7684\u4EBA\u5403\u4E0A\u4E1C\u897F\u3002",
        options: ["\u4ECA\u665A\u5206\u5154\u8089\uFF0C\u5148\u8BA9\u56DB\u86CB\u786E\u8BA4\u6709\u4EFD", "\u5148\u7559\u5154\u5B50\u548C\u76AE\u6BDB\uFF0C\u6539\u7528\u522B\u7684\u98DF\u7269\u8865\u8FD9\u987F", "\u5F53\u6210\u56DB\u86CB\u7684\u529F\u52B3\uFF0C\u5C11\u91CF\u5904\u7406\u7ED9\u5168\u5BB6\u5C1D\u5473"],
        excerpt: "\u56DB\u86CB\u6293\u4E86\u53EA\u5154\u5B50\uFF0C\u4ECA\u5929\u665A\u4E0A\u54B1\u5403\u5154\u8089\u2026\u2026\u54B1\u5BB6\u4E00\u5E74\u90FD\u6CA1\u5403\u8FC7\u8089\u4E86\uFF0C\u867D\u7136\u80AF\u5B9A\u6CA1\u6211\u7684\u4EFD\u3002",
        scores: { emotion_heat: 85, choice_leverage: 74, world_constraint_value: 88, watch_flow_fit: 82 },
        note: "\u8D44\u6E90\u5206\u914D + \u4EB2\u5B50\u4FE1\u4EFB\u540C\u65F6\u89E6\u53D1\uFF0C\u89C6\u89C9\u8BC1\u636E 00:00 \u660E\u786E\u53EF\u89C1\u5154\u5B50\u3002"
      },
      {
        id: "huangnian_ep05_c002",
        episode: "huangnian_ep05",
        window: [88, 104],
        action_type: "resource",
        source: "llm_discovered",
        llm_label: "keep_for_review",
        grade: "low",
        keep: false,
        hook: "\u7076\u4E0A\u591A\u51FA\u4E00\u888B\u7C73\uFF0C\u8981\u4E0D\u8981\u89E3\u91CA\u6765\u8DEF\uFF1F",
        impulse: "\u8981\u662F\u6211\u6765\uFF0C\u6015\u88AB\u8FFD\u95EE\uFF0C\u60F3\u542B\u7CCA\u8FC7\u53BB\u3002",
        options: ["\u4E3B\u52A8\u7ED9\u4E2A\u666E\u901A\u8BF4\u6CD5", "\u8F6C\u79FB\u8BDD\u9898\uFF0C\u5148\u85CF\u8D77\u6765", "\u53EA\u8DDF\u6700\u4EB2\u7684\u4EBA\u4EA4\u5E95"],
        excerpt: "\uFF08\u5173\u952E\u5E27\u4EC5\u89C1\u7076\u53F0\u4E0E\u53E3\u888B\uFF0CASR \u672A\u660E\u786E\u7C73\u7684\u6765\u8DEF\uFF09",
        scores: { emotion_heat: 58, choice_leverage: 55, world_constraint_value: 64, watch_flow_fit: 52 },
        failure_mode: "evidence_thin \xB7 \u6765\u8DEF\u7F3A ASR \u4F50\u8BC1\uFF0C\u6613\u8D8A\u754C\u66B4\u9732\u7CFB\u7EDF\u3002",
        note: "\u8BC1\u636E\u504F\u5F31\uFF0C\u7A97\u53E3\u6A21\u7CCA\uFF1B\u5EFA\u8BAE\u5148\u4E0D\u53D1\u5E03\u3002"
      },
      {
        id: "huangnian_ep09_c003",
        episode: "huangnian_ep09",
        window: [203, 219],
        action_type: "resource",
        source: "deterministic",
        llm_label: "keep_for_review",
        grade: "low",
        keep: false,
        hook: "\u96C6\u5E02\u4E0A\u6709\u4EBA\u538B\u4EF7\uFF0C\u5356\u4E0D\u5356\uFF1F",
        impulse: "\u8981\u662F\u6211\u6765\uFF0C\u60F3\u591A\u6362\u70B9\u94B1\u3002",
        options: ["\u7167\u4EF7\u5356\u6389", "\u50F5\u7740\u7B49\u66F4\u597D\u4EF7", "\u6362\u4E2A\u4E70\u5BB6"],
        excerpt: "\uFF08\u5173\u952E\u8BCD\u547D\u4E2D\u201C\u5356/\u4EF7\u201D\uFF0C\u4F46\u573A\u538B\u4F4E\uFF0C\u60C5\u7EEA\u5E73\u6DE1\uFF09",
        scores: { emotion_heat: 41, choice_leverage: 48, world_constraint_value: 50, watch_flow_fit: 44 },
        failure_mode: "low_pressure \xB7 \u5173\u952E\u8BCD\u53EC\u56DE\u566A\u58F0\uFF0C\u89C2\u4F17\u4E0D\u4F1A\u60F3\u7ACB\u523B\u53D1\u58F0\u3002",
        note: "\u786E\u5B9A\u6027\u53EC\u56DE\u566A\u58F0\uFF0C\u7559\u4F5C audit \u8BC1\u636E\u5373\u53EF\u3002"
      },
      {
        id: "huangnian_ep11_c004",
        episode: "huangnian_ep11",
        window: [150, 168],
        action_type: "humiliation",
        source: "llm_discovered",
        llm_label: "keep_for_review",
        grade: "medium",
        keep: false,
        hook: "\u5F53\u4F17\u88AB\u6CFC\u810F\u6C34\uFF0C\u8981\u4E0D\u8981\u7ACB\u523B\u81EA\u8BC1\uFF1F",
        impulse: "\u8981\u662F\u6211\u6765\uFF0C\u6C14\u4E0D\u8FC7\uFF0C\u60F3\u5F53\u573A\u8BF4\u6E05\u695A\u3002",
        options: ["\u5F53\u4F17\u5BF9\u8D28", "\u5148\u5FCD\uFF0C\u79C1\u4E0B\u53D6\u8BC1", "\u62C9\u4E00\u4E2A\u8BC1\u4EBA\u51FA\u6765"],
        excerpt: "\uFF08ASR \u6709\u53E3\u89D2\uFF0C\u4F46\u88AB\u6307\u63A7\u7684\u5177\u4F53\u4E8B\u5B9E\u5728\u7A97\u53E3\u5185\u4E0D\u5B8C\u6574\uFF09",
        scores: { emotion_heat: 69, choice_leverage: 60, world_constraint_value: 58, watch_flow_fit: 63 },
        failure_mode: "window_incomplete \xB7 \u6307\u63A7\u4E8B\u5B9E\u8DE8\u7A97\u53E3\uFF0C\u89E6\u53D1\u70B9\u4E0D\u7A33\u3002",
        note: "\u60C5\u7EEA\u6709\u5F20\u529B\uFF0C\u4F46\u7A97\u53E3\u8FB9\u754C\u9700\u91CD\u5207\u540E\u518D\u8BC4\u3002"
      }
    ]
  };
  const FINAL_REPORT = `# Deadman Studio Final Report

- run_id: deadman-producer:huangnian-20260524-07
- drama: huangnian \xB7 \u8352\u5E74\u5168\u6751\u5543\u6811\u76AE\uFF0C\u6211\u6709\u7CFB\u7EDF\u6EE1\u4ED3\u8089
- graph_mode: base
- final status: **pass**
- review decision: **approve**
- validation_result: **pass**
- LLM enrichment: skipped_by_config

## \u8282\u70B9\u8868
prepare_assets \u2713 \xB7 register_media \u2713 \xB7 build_timeline_windows \u2713 \xB7 mine_candidates \u2713 \xB7
cluster_candidates \u2713 \xB7 prepare_human_review \u2713 \xB7 human_review_gate \u2713(approve) \xB7
build_drama_context \u2713 \xB7 publish_p0_bridge \u2713 \xB7 validate_producer_bridge \u2713 \xB7 final_report \u2713

## Runtime \u5305\u8DEF\u5F84
- data/dramas/huangnian/manifest.v0.1.json
- data/dramas/huangnian/context.v0.1.json
- data/dramas/huangnian/moments.v0.1.json  (5 moments)
- data/dramas/huangnian/evidence/reviewed_demo_nodes.v0.1.json

## \u6709\u610F\u6392\u9664\u7684\u5236\u4F5C\u4EA7\u7269
raw MP4 / keyframes / contact sheets / score_axes \u8C03\u8BD5\u5B57\u6BB5 \u2014 \u4EC5\u4FDD\u7559\u5728 tmp/ \u5FFD\u7565\u76EE\u5F55\u3002`;
  window.DeadmanData = { NODE_CATALOG, PHASES, RUNS, SHORTLIST, FINAL_REPORT };
})();
