/* =============================================================================
   Deadman · Studio — live lint
   A lightweight heuristic matcher: given a layer ('lead' | 'display' | 'echo')
   and a line, return the named-negative id it trips (or null = clean).
   Mirrors the dataset's failure patterns closely enough to feel real while the
   owner edits a line. NOT the production judge — the real CAB runtime is formal.
   ============================================================================ */
(function () {
  const has = (s, arr) => arr.some((k) => s.includes(k));

  function lintLead(t) {
    if (/^(说到|聊到|看到|讲到|提到)/.test(t) || has(t, ["这段", "这一段", "的剧情"])) return "lead_prefaces_or_names_topic";
    if ((t.includes("原来") && (t.includes("全是") || t.includes("根本不是"))) || t.includes("不是…全是")) return "lead_preempts_viewer";
    return null;
  }

  function lintDisplay(t) {
    if (has(t, ["难怪我", "我也", "我家", "我最近", "我自己", "想起我", "让我想到"])) return "presumes_viewer_personal_experience";
    if (has(t, ["看红了眼", "好哭", "鼻酸", "泪目", "哭了", "起鸡皮", "破防"])) return "overclaims_viewer_reaction";
    if (has(t, ["真相", "原来如此", "终于找到", "真相大白", "水落石出"])) return "reaction_assumes_withheld_info";
    // over-specific: long AND packing a particular scenario (multiple specific markers).
    // NB: the gold "接连遇上糟心事真的太耗人了" (13 chars) must PASS, so "接连" alone is not a trigger;
    // the draft "最近接连发生这么多糟心事，总做这种梦也太熬人了" (~21 chars) carries 最近/这么多/总做/这种梦.
    if (t.length >= 16 && has(t, ["最近", "这么多", "总做", "这种梦", "今天", "追这么多", "频繁"])) return "too_specific_narrow_coverage";
    return null;
  }

  function lintEcho(t) {
    if ((t.includes("太对了") || t.includes("确实") || t.includes("必须的")) &&
        has(t, ["危险", "千万别", "别让", "盼", "希望", "捏把汗"])) return "catch_mismatches_speech_act";
    if (has(t, ["必须的", "绝绝子", "yyds", "下一秒", "后面肯定", "接下来肯定", "说不定就"])) return "register_clash_or_predicts_plot";
    // overwrought / over-specific — keyed to the failure pattern's markers, NOT raw length
    // (gold echoes can be long-but-clean, e.g. the 26-char "…全是长辈放心不下小辈的软牵挂。").
    if (has(t, ["刺骨", "哪是普通", "追这么多集", "埋的伏笔"])) return "echo_overwrought_or_overspecific";
    return null;
  }

  window.studioLint = function studioLint(layer, text) {
    const t = (text || "").trim();
    if (!t) return null;
    if (layer === "lead") return lintLead(t);
    if (layer === "display") return lintDisplay(t);
    if (layer === "echo") return lintEcho(t);
    return null;
  };

  // resolve a negative id -> its full record from the taste overlay
  window.studioNegative = function studioNegative(id) {
    if (!id) return null;
    return (window.STUDIO_TASTE.negatives || []).find((n) => n.id === id) || null;
  };
})();
