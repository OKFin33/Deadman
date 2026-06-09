/* =============================================================================
   Deadman · Studio (Surface 2) — data
   -----------------------------------------------------------------------------
   Real content from data/datasets/studio_guidance/studio_cab_taste_overlay.v0.2
   and data/schemas/companion_exchange_pack.v0.1. The yunmiao_ep17 demo path
   uses the dataset's OWN flagged examples as the CAB draft, and its gold as the
   repaired/approved result — a true end-to-end audit story.
   ============================================================================ */

/* ---- dramas (real drama_id slugs) --------------------------------------- */
window.STUDIO_DRAMAS = [
  { drama_id: "yunmiao",  title: "云渺1：我修仙多年，强亿点怎么了", cover: "assets/covers/yunmiao.png",  authored: 2, queued: 0 },
  { drama_id: "lihun",    title: "幸得相遇离婚时",                 cover: "assets/covers/xingde.png",   authored: 2, queued: 0 },
  { drama_id: "huangnian", title: "荒年全村啃树皮，我有系统满仓肉", cover: "assets/covers/huangnian.png", authored: 0, queued: 5 },
];

/* ---- taste overlay: the spec the owner review applies ------------------- */
window.STUDIO_TASTE = {
  version: "studio_cab_taste_overlay.v0.2",
  status: "accumulating",
  rules: [
    { layer: "lead", title: "开场白 · 纯粹在场反应", items: [
      "纯粹的当下反应，不点题、不加前缀（「说到X」「聊到X」「X的这段」「看到X」）——你们在一起看，指代已在画面上，直接给反应。",
      "开场并邀请：托出此刻的情绪、让观众想接话，但不替观众说出结论/金句——那句留给观众自己说。",
    ]},
    { layer: "display", title: "观众选说 · 那一句", items: [
      "是观众针对画面选来说的一句，而非对开场白的回复。克制、可被广泛共享，不替观众断言反应或私人经历。",
      "保持简单、偏概括——一个很多观众都能认领的宽泛姿态，而非细到只贴合少数人的具体感受。简单 = 覆盖更广。",
      "短剧里观众通常已知道发生了什么，不要写揭秘/反转式反应（「真相大白」「原来如此」）——尊重观众的认知状态。",
    ]},
    { layer: "echo", title: "搭子接话 · 接住别复读", items: [
      "肯定式「接」（是啊 / 确实 / 也是 / 可不是 / 太对了）是接住感，但别三条都用——有∶无 ≈ 2∶1，且每条换着用。",
      "「接」要匹配观众的言语行为：「太对了/确实」批准的是主张；担忧（「太危险了」）要同担（「真替她捏把汗」），祈愿要同盼，别用「正确」去接情绪。",
      "语气要贴合此刻——别在严肃/担忧的节点甩网络梗或自信满满，且永远不预测下一秒剧情。",
      "接话必须补一个独立的角度或细节，绝不只是复述观众那句（复读机）。落地自然，别浮夸、别尬。",
    ]},
    { layer: "reply_set", title: "三条候选 · 覆盖", items: [
      "三条候选按覆盖来组：#1 #2 从两个不同方向打中要害；#3 是兜底。每条都简单、宽泛。",
    ]},
  ],
  /* the 10 named negatives — generalizable FAILURE PATTERNS, not verbatim strings */
  negatives: [
    { id: "overclaims_viewer_reaction", layer: "display", severity: "hard",
      pattern: "替观众把强烈的身体/情绪反应当事实断言——哭了、鼻酸、起鸡皮、「太好哭了」。把反应塞进观众嘴里，而非给一句他选来说的话。",
      example: "我直接看红了眼，这也太好哭了", why: "把观众未必有的反应安到他头上" },
    { id: "presumes_viewer_personal_experience", layer: "display", severity: "hard",
      pattern: "预设观众亲历了屏幕上的经历或有过平行经历（「难怪我也…」「难怪最近总…」「我家也…」）。即便没有「我」，暗示观众自己做梦/哭过/经历过也算。",
      example: "难怪我最近也总梦到家里老人，太懂这种感觉了", why: "强加一段观众未必拥有的私人经历" },
    { id: "too_specific_narrow_coverage", layer: "display", severity: "hard",
      pattern: "过于具体/细腻——塞进一个只有少数观众能认领的具体情境或微妙感受。应当简单、概括。",
      example: "最近接连发生这么多糟心事，总做这种梦也太熬人了", why: "过于具体 = 覆盖面窄" },
    { id: "reaction_assumes_withheld_info", layer: "display", severity: "hard",
      pattern: "揭秘/悬念兑现式反应（「这下终于找到真相了」「真相大白」「原来如此」），只有在剧情对观众隐瞒了信息时才成立。短剧观众通常早已看到铺垫。",
      example: "这下终于找到真相了", why: "把观众当成被隐瞒了谜底，可短剧观众其实早知道" },
    { id: "lead_prefaces_or_names_topic", layer: "lead", severity: "hard",
      pattern: "在反应前先指出/点名/引入屏幕上的话题——「说到X」「聊到X」「X的这段」「看到X」——而非纯粹的当下反应。指代已在画面共享，点题像个局外旁白。",
      example: "聊到过世长辈舍不得小辈这段，太戳人了", why: "点题把说话者摆成局外叙述者；同看的人只管反应" },
    { id: "lead_preempts_viewer", layer: "lead", severity: "hard",
      pattern: "抢戏——把观众想说的完整结论/金句（「原来不是X，全是Y啊」）替他说了，观众无话可加，观众那句便塌成对开场白的回复。开场白要开场、邀请，把结论留给观众。",
      example: "原来老人家不肯走根本不是有执念，全是放心不下小辈啊", why: "lead 与观众的台词重合；display 沦为对 lead 的回复" },
    { id: "catch_mismatches_speech_act", layer: "echo", severity: "hard",
      pattern: "肯定「接」不匹配观众的言语行为——用「太对了/确实」去批准一句担忧（「女主太危险了」）或祈愿（「千万别…」）而非主张。不能把情绪当命题去评对错；该同担/同盼。",
      example: "太对了 ← 接「女主现在处境也太危险了」", why: "把担忧/祈愿当成可评对错的命题，读着冷而别扭" },
    { id: "register_clash_or_predicts_plot", layer: "echo", severity: "hard",
      pattern: "接话的语气与此刻冲突（在严肃/担忧节点甩网络梗或自信满满，如「必须的!」），或接话预测下一秒剧情（「下一秒…就…」「后面肯定…」）。",
      example: "必须的！下一秒说不定就有人撞破他们换药的阴谋", why: "语气割裂 + 预测后续剧情（禁止）" },
    { id: "echo_restates_display", layer: "echo", severity: "hard",
      pattern: "复读机——接话只是把观众那句换句话说，而没有补上独立的角度/细节。",
      example: "确实，孙家人现在全僵在原地看懵了 ← 接「对面人都直接看傻了」", why: "没有新内容；主持人只是复述同样的话" },
    { id: "echo_overwrought_or_overspecific", layer: "echo", severity: "hard",
      pattern: "接话浮夸/戏剧化/尬（「冷得刺骨的眼神，哪是普通小辈能有的气场」），或过于具体（「追这么多集…今天」）。接话要落地、自然、简单。",
      example: "太对了，就刚才那冷得刺骨的眼神，哪是普通小辈能有的气场啊", why: "浮夸啰嗦的 echo 读着假，还盖过观众" },
  ],
};

/* gold exemplars (owner-approved) — used for side-by-side in review --------- */
window.STUDIO_GOLD = [
  { drama_id: "yunmiao", moment_id: "yunmiao_ep18_m001", episode_id: "yunmiao_ep18",
    companion_lead: "这眼神谁看了不发怵啊",
    replies: [
      { display_text: "孙家这下要踢到铁板了", echo: "可不是，刚还放话的孙家这下要栽了", coverage: "core_direction_a" },
      { display_text: "她藏的实力果然深不可测", echo: "那身气场，哪是普通小辈能压得住的", coverage: "core_direction_b" },
      { display_text: "这气场也太唬人了", echo: "确实，站她跟前的人连大气都不敢喘", coverage: "fallback" },
    ],
    taste_note: "owner-approved + 微调 (round-6)：2 方向 + 兜底，catch≈2:1，言语行为匹配。" },
  { drama_id: "lihun", moment_id: "lihun_ep06_m001", episode_id: "lihun_ep06",
    companion_lead: "他们居然敢打这种恶毒主意",
    replies: [
      { display_text: "这也太歹毒了吧", echo: "可不是，连孕妇肚里的小生命都下得去手", coverage: "core_direction_a" },
      { display_text: "绝对不能让他们得逞啊", echo: "我也攥着心呢，盼着她能早点识破", coverage: "core_direction_b" },
      { display_text: "看得人心里直发毛", echo: "确实，这种害人的手段太阴损了", coverage: "fallback" },
    ],
    taste_note: "owner-approved + 微调 (round-6)：注意 #2 是祈愿 → echo 同盼而非「太对了」。" },
];

/* ---- hero moments (the authoring queue) --------------------------------- */
window.STUDIO_MOMENTS = [
  { moment_id: "yunmiao_ep17_m001", drama_id: "yunmiao", episode_id: "yunmiao_ep17",
    scene_signal: "亡故长辈托梦，不舍小辈", notice_marker: "?", status: "needs_review",
    window: { notice_at: 41, start: 34, end: 56 },
    window_rationale: "长辈托梦交代牵挂的情绪高点；观众最想就「惦记」接一句。",
    isDemo: true },
  { moment_id: "yunmiao_ep18_m001", drama_id: "yunmiao", episode_id: "yunmiao_ep18",
    scene_signal: "扮猪吃虎，气场镇住孙家", notice_marker: "!", status: "reviewed",
    window: { notice_at: 58, start: 50, end: 71 },
    window_rationale: "主角亮气场的爽点，观众想嗑碾压人设。" },
  { moment_id: "lihun_ep06_m001", drama_id: "lihun", episode_id: "lihun_ep06",
    scene_signal: "反派对孕妇起恶毒之心", notice_marker: "!", status: "reviewed",
    window: { notice_at: 49, start: 42, end: 63 },
    window_rationale: "反派起意的愤怒高点，观众想骂也想护。" },
  { moment_id: "lihun_ep12_m001", drama_id: "lihun", episode_id: "lihun_ep12",
    scene_signal: "暗害坐实，疑点全对上", notice_marker: "?", status: "reviewed",
    window: { notice_at: 77, start: 70, end: 92 },
    window_rationale: "真相坐实的节点，观众想骂也想心疼女主。" },
];

/* ---- the demo: yunmiao_ep17 draft (with real flagged lines) → gold ------- */
window.STUDIO_DEMO = {
  moment_id: "yunmiao_ep17_m001",
  drama_id: "yunmiao",
  goldRef: "yunmiao_ep18_m001",        // sibling gold shown side-by-side
  evidence_refs: ["yunmiao/ep17#34-56", "reviewed_demo_nodes.v0.1#yunmiao_ep17"],
  constraint_refs: ["context.v0.1#tone", "taste_overlay.v0.2#lead", "taste_overlay.v0.2#display"],
  /* CAB stage-A/B draft. flag = named-negative id it trips (null = clean). */
  draft: {
    companion_lead: { text: "聊到过世长辈舍不得小辈这段，太戳人了", flag: "lead_prefaces_or_names_topic" },
    replies: [
      { display_text: "难怪我最近也总梦到家里老人，太懂这种感觉了", motivation: "想抒发对长辈牵挂的触动", coverage: "core_direction_a",
        echo: "太对了，哪有什么执念，全是长辈放心不下小辈的软牵挂。", display_flag: "presumes_viewer_personal_experience", echo_flag: null },
      { display_text: "最近接连发生这么多糟心事，总做这种梦也太熬人了", motivation: "吐槽连续变故的疲惫", coverage: "core_direction_b",
        echo: "可不是，攒了一堆糟心事连觉都睡不踏实啊", display_flag: "too_specific_narrow_coverage", echo_flag: null },
      { display_text: "这种感觉真的太复杂了", motivation: "笼统表达当下的复杂感受", coverage: "fallback",
        echo: "确实，暖得发烫又酸得发堵，全是长辈藏在心底的软牵挂", display_flag: null, echo_flag: null },
    ],
    echo_catch_ratio: { withCatch: 3, total: 3, note: "三条 echo 都带「接」——round-6 偏好有∶无≈2∶1，建议留一条更软。" },
  },
  /* owner-repaired = the approved gold for this moment */
  gold: {
    companion_lead: "听完心里怪不是滋味的",
    replies: [
      { display_text: "长辈的惦记永远是最戳人的", motivation: "想抒发对长辈纯粹牵挂的触动", coverage: "core_direction_a",
        echo: "太对了，哪有什么执念，全是长辈放心不下小辈的软牵挂。" },
      { display_text: "接连遇上糟心事真的太耗人了", motivation: "吐槽连续遭遇变故的疲惫", coverage: "core_direction_b",
        echo: "可不是，攒了一堆糟心事连觉都睡不踏实啊" },
      { display_text: "这种感觉真的太复杂了", motivation: "笼统表达当下的复杂感受", coverage: "fallback",
        echo: "确实，暖得发烫又酸得发堵，全是长辈藏在心底的软牵挂" },
    ],
  },
};

window.STUDIO_COVERAGE_LABEL = {
  core_direction_a: "要害 · 方向 A",
  core_direction_b: "要害 · 方向 B",
  fallback: "兜底",
};

/* ---- humanizing maps + helpers (keep raw schema out of the UI) ---------- */
window.STUDIO_LAYER_LABEL = { lead: "开场", display: "选说", echo: "接话", reply_set: "三条" };

window.STUDIO_NEG_TITLE = {
  overclaims_viewer_reaction: "替观众断言反应",
  presumes_viewer_personal_experience: "预设观众的私人经历",
  too_specific_narrow_coverage: "太具体，覆盖面窄",
  reaction_assumes_withheld_info: "把观众当成被隐瞒",
  lead_prefaces_or_names_topic: "开场点题 / 加前缀",
  lead_preempts_viewer: "开场抢了观众的话",
  catch_mismatches_speech_act: "接得不对路（情绪当命题）",
  register_clash_or_predicts_plot: "语气出戏 / 预测剧情",
  echo_restates_display: "复读机，没补新意",
  echo_overwrought_or_overspecific: "接话浮夸 / 太具体",
};

window.epLabel = function epLabel(episodeId) {
  const m = /_ep0*(\d+)/.exec(episodeId || "");
  return m ? `第 ${m[1]} 集` : (episodeId || "");
};

window.dramaShort = function dramaShort(dramaId) {
  const d = (window.STUDIO_DRAMAS || []).find((x) => x.drama_id === dramaId);
  if (!d) return dramaId;
  let t = d.title.split("：")[0];
  if (t.length > 8) t = t.split("，")[0];
  return t.length > 9 ? t.slice(0, 9) + "…" : t;
};

/* ---- full authored exchanges per moment (reviewed ones render read-only) -- */
window.STUDIO_EXCHANGES = {
  yunmiao_ep18_m001: {
    companion_lead: "这眼神谁看了不发怵啊",
    replies: [
      { display_text: "孙家这下要踢到铁板了", echo: "可不是，刚还放话的孙家这下要栽了", coverage: "core_direction_a", motivation: "期待嚣张的孙家当场吃瘪" },
      { display_text: "她藏的实力果然深不可测", echo: "那身气场，哪是普通小辈能压得住的", coverage: "core_direction_b", motivation: "嗑主角扮猪吃虎的碾压人设" },
      { display_text: "这气场也太唬人了", echo: "确实，站她跟前的人连大气都不敢喘", coverage: "fallback", motivation: "单纯被主角气场震到" },
    ],
  },
  lihun_ep06_m001: {
    companion_lead: "他们居然敢打这种恶毒主意",
    replies: [
      { display_text: "这也太歹毒了吧", echo: "可不是，连孕妇肚里的小生命都下得去手", coverage: "core_direction_a", motivation: "对反派恶毒计划表达愤怒" },
      { display_text: "绝对不能让他们得逞啊", echo: "我也攥着心呢，盼着她能早点识破", coverage: "core_direction_b", motivation: "代入女主盼她躲过这一劫" },
      { display_text: "看得人心里直发毛", echo: "确实，这种害人的手段太阴损了", coverage: "fallback", motivation: "抒发当下看得心里发毛" },
    ],
  },
  lihun_ep12_m001: {
    companion_lead: "这摆明了是故意害她",
    replies: [
      { display_text: "这人也太恶毒了", echo: "可不是，连没出世的孩子都下毒手", coverage: "core_direction_a", motivation: "发泄对施害者的强烈不满" },
      { display_text: "之前肚子疼果然不是巧合", echo: "太对了，那些小疑点这下全对上了", coverage: "core_direction_b", motivation: "说出之前就觉得不对劲" },
      { display_text: "女主实在太委屈了", echo: "受了这么多罪，竟全是被人算计的", coverage: "fallback", motivation: "对女主处境的共情" },
    ],
  },
};
