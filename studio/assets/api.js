(() => {
  const { RUNS, SHORTLIST, FINAL_REPORT, NODE_CATALOG } = window.DeadmanData;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const clone = (x) => JSON.parse(JSON.stringify(x));
  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
  const nowStr = () => "2026-06-03 10:31";
  const store = {
    runs: clone(RUNS),
    shortlists: { [SHORTLIST.run_id]: clone(SHORTLIST) }
  };
  function freshStatuses(mode) {
    const out = {};
    for (const n of NODE_CATALOG) {
      out[n.id] = n.llm && mode !== "llm" ? "skipped_by_config" : "planned";
    }
    return out;
  }
  function buildShortlistForRun(payload, recall) {
    const tpl = clone(SHORTLIST.candidates);
    const eps = payload.episodes.map((e) => e.epId);
    const n = clamp(eps.length * 2, 4, tpl.length);
    const candidates = [];
    for (let i = 0; i < n; i++) {
      const t = tpl[i % tpl.length];
      const ep = eps[i % eps.length];
      candidates.push({ ...t, id: `${payload.dramaId}_${ep}_c${String(i + 1).padStart(2, "0")}`, episode: ep });
    }
    return {
      run_id: payload.runId,
      drama_id: payload.dramaId,
      drama_title: payload.dramaTitle,
      review_policy_version: SHORTLIST.review_policy_version,
      input_candidate_count: recall,
      shortlist_target: Math.max(3, Math.round(n * 0.6)),
      expected_reviewed_paths: {
        reviewed_demo_nodes: `tmp/ars_${payload.dramaId}_analysis/review/${payload.dramaId}_demo_nodes.v0.1.json`,
        reviewed_candidates: `tmp/ars_${payload.dramaId}_analysis/review/${payload.dramaId}_candidates.reviewed.v0.1.json`
      },
      human_instructions: SHORTLIST.human_instructions,
      candidates
    };
  }
  function ingestOrder(mode) {
    const base = ["prepare_assets", "register_media", "build_timeline_windows", "mine_candidates"];
    if (mode === "llm") base.push("llm_semantic_miner");
    base.push("cluster_candidates");
    if (mode === "llm") base.push("llm_candidate_judge");
    base.push("prepare_human_review");
    return base;
  }
  const StudioAPI = {
    async listRuns() {
      await wait(80);
      return clone(store.runs);
    },
    async getRun(runId) {
      await wait(70);
      return clone(store.runs.find((r) => r.run_id === runId)) || null;
    },
    async getReport(runId) {
      await wait(90);
      const run = store.runs.find((r) => r.run_id === runId);
      if (run && run.status === "pass") return FINAL_REPORT;
      return null;
    },
    async getReview(runId) {
      await wait(110);
      return store.shortlists[runId] ? clone(store.shortlists[runId]) : null;
    },
    // --- create + start a run (the GUI ingest entry) ------------------------
    async startRun(payload) {
      await wait(160);
      const recall = clamp(Math.round(payload.episodes.length * 4), 20, 400);
      const runId = `deadman-producer:${payload.dramaId}-20260603-09`;
      const run = {
        run_id: runId,
        thread_id: runId,
        drama_id: payload.dramaId,
        drama_title: payload.dramaTitle,
        graph_mode: payload.mode,
        status: "running",
        started_at: nowStr(),
        updated_at: nowStr(),
        current_node: "prepare_assets",
        recall_budget: recall,
        deterministic_candidate_count: recall,
        episodes: payload.episodes,
        node_statuses: freshStatuses(payload.mode)
      };
      run.node_statuses.prepare_assets = "running";
      store.runs = store.runs.filter((r) => r.run_id !== runId);
      store.runs.unshift(run);
      store.shortlists[runId] = buildShortlistForRun({ ...payload, runId }, recall);
      return clone(run);
    },
    ingestOrder(runId) {
      const run = store.runs.find((r) => r.run_id === runId);
      return ingestOrder(run ? run.graph_mode : "base");
    },
    async setNode(runId, nodeId, status) {
      await wait(20);
      const run = store.runs.find((r) => r.run_id === runId);
      if (!run) return null;
      run.node_statuses[nodeId] = status;
      if (status === "running" || status === "pass") run.current_node = nodeId;
      run.updated_at = nowStr();
      return clone(run);
    },
    async gateWaiting(runId) {
      await wait(20);
      const run = store.runs.find((r) => r.run_id === runId);
      if (!run) return null;
      run.node_statuses.human_review_gate = "waiting_for_review";
      run.status = "waiting_for_review";
      run.current_node = "human_review_gate";
      run.updated_at = nowStr();
      return clone(run);
    },
    // --- resume the human_review_gate ---------------------------------------
    async resume(runId, decision, keptIds, note) {
      await wait(180);
      const run = store.runs.find((r) => r.run_id === runId);
      if (!run) throw new Error("run_not_found");
      run.reviewer_note = note || "";
      run.updated_at = nowStr();
      run.node_statuses.human_review_gate = "pass";
      if (decision === "reject") {
        run.status = "rejected_by_human_review";
        run.review_decision = "reject";
        run.current_node = "human_review_gate";
        return clone(run);
      }
      run.review_decision = "approve";
      run.kept_candidate_ids = keptIds;
      run.published_moments = keptIds.length;
      run.status = "publishing";
      run.current_node = "build_drama_context";
      return clone(run);
    },
    publishSequence(runId) {
      const run = store.runs.find((r) => r.run_id === runId);
      const mode = run ? run.graph_mode : "base";
      const seq = [
        "llm_drama_context_draft",
        "llm_moment_pack_draft",
        "build_drama_context",
        "publish_p0_bridge",
        "validate_producer_bridge",
        "final_report"
      ];
      return seq.filter((id) => mode === "llm" || !id.startsWith("llm_"));
    },
    async advancePublish(runId, nodeId, isLast) {
      await wait(50);
      const run = store.runs.find((r) => r.run_id === runId);
      if (!run) return null;
      run.node_statuses[nodeId] = "pass";
      run.current_node = nodeId;
      if (nodeId === "validate_producer_bridge") run.validation_result = "pass";
      if (isLast) run.status = "pass";
      return clone(run);
    }
  };
  window.StudioAPI = StudioAPI;
})();
