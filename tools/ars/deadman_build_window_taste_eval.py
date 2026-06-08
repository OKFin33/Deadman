#!/usr/bin/env python3
"""Build the first Deadman v0.41 window-taste eval fixture and review tray."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_WINDOWS_PATH = REPO_ROOT / "tmp/ars_huangnian_analysis/candidates/huangnian_windows.v0.2.json"
DEFAULT_CANDIDATES_PATH = REPO_ROOT / "tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.2.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data/evals/window_taste_eval.v0.1.json"
DEFAULT_REVIEW_TRAY_PATH = REPO_ROOT / "local_artifacts/window_taste_review/index.html"
DEFAULT_WINDOW_REVIEW_TRAY_PATH = REPO_ROOT / "local_artifacts/window_taste_review/window_review.html"

GLOBAL_STORY_CONTEXT = (
    "现代企业家程弯弯穿到荒年恶婆婆身上。原主长期偏向娘家、亏待儿子儿媳，"
    "所以家人和村里人会把她的新行为先按旧人设理解。"
)

DEFAULT_LEAD_STYLE_POLICY = (
    "Lead must stay open enough to invite the viewer's own line, but it must be tied to the exact source-window situation. "
    "It should read like one well-timed friend comment, not a direct question, UI instruction, or plot analysis."
)
DEFAULT_REPLY_SET_POLICY = (
    "The first two preset replies should cover two plausible viewer-person types for this exact situation. "
    "The third reply is a softer fallback or tone-check option that lets a less-convinced viewer still answer without forcing a heavy stance."
)
DEFAULT_VIEWER_STANCE_POLICY = (
    "Author as two viewing companions reacting to the scene. Presets must be viewer utterances, not character instructions, "
    "delivery labels, RPG actions, or producer meta-analysis."
)
DEFAULT_PRESET_ECHO_POLICY = (
    "Preset selected_echo is reviewed pack copy. It may be polished by Studio authoring before human review, "
    "but user-side preset selection should return the reviewed echo rather than generating a new live answer."
)
DEFAULT_WINDOW_REVIEW_PROMPT = (
    "只判断这个 10 秒点位：它是不是本集最该让搭子冒出来的一刻？可选：best / usable backup / not a window / card insufficient。"
)

GOLD_TARGETS = {
    "huangnian_ep03": "taste_gold_owner_huangnian_ep03_0033",
    "huangnian_ep07": "taste_gold_owner_huangnian_ep07_0021",
    "huangnian_ep04": "taste_gold_owner_huangnian_ep04_0149",
    "huangnian_ep06": "taste_gold_owner_huangnian_ep06_0103",
    "huangnian_ep02": "taste_gold_proposed_huangnian_ep02_0125",
    "huangnian_ep08": "taste_gold_proposed_huangnian_ep08_0148",
    "huangnian_ep09": "taste_gold_proposed_huangnian_ep09_0044",
    "huangnian_ep10": "taste_gold_proposed_huangnian_ep10_0027",
    "huangnian_ep14": "taste_gold_proposed_huangnian_ep14_0048",
    "huangnian_ep17": "taste_gold_proposed_huangnian_ep17_0048",
}


OWNER_GOLD_SEEDS: list[dict[str, Any]] = [
    {
        "item_id": "taste_gold_owner_huangnian_ep03_0033",
        "episode_id": "huangnian_ep03",
        "anchor_ms": 33000,
        "source_start_ms": 20000,
        "source_end_ms": 40000,
        "viewer_line_pressure": "原主的人设有点离谱，别又把最后一口送走了。",
        "why_now": "孩子已经把“又要去大舅家”和“家里最后一点吃的”说出口，观众会先吐槽原主人设，再轻轻心疼孩子。",
        "expected_tone": ["轻吐槽主导", "早期心疼下调", "朋友式接话"],
        "expected_reply_axes": ["吐槽原主人设", "轻轻心疼孩子", "别再向大舅家让渡"],
        "owner_notes": "EP03 anchor fixed at 00:33; default visible window is 10 seconds. Early empathy must be capped because viewer attachment is still shallow.",
    },
    {
        "item_id": "taste_gold_owner_huangnian_ep07_0021",
        "episode_id": "huangnian_ep07",
        "anchor_ms": 21000,
        "source_start_ms": 20000,
        "source_end_ms": 40000,
        "viewer_line_pressure": "这恶婆婆有点可恶了。",
        "why_now": "穿越前原主对怀孕儿媳恶语相向并扔饭，承接 EP03 起持续强化的恶婆婆形象，观众的吐槽开始带怒气。",
        "expected_tone": ["吐槽上调", "怒气开始上来", "心疼儿媳但不写成苦情"],
        "expected_reply_axes": ["骂恶婆婆人设", "心疼儿媳被羞辱", "别让这口饭变成羞辱"],
        "owner_notes": "This is a cumulative persona beat from EP03 to EP07, not an isolated table-choice node.",
    },
    {
        "item_id": "taste_gold_owner_huangnian_ep04_0149",
        "episode_id": "huangnian_ep04",
        "anchor_ms": 109000,
        "source_start_ms": 100000,
        "source_end_ms": 117252,
        "viewer_line_pressure": "这主角不愧是做老板的，嘴倒是挺会说。",
        "why_now": "主角在稻田试系统后被误会偷稻谷，临场把小鹅菜和借粮话术抛出来化解危机，观众会接能力感和嘴会说。",
        "expected_tone": ["能力感", "轻爽", "佩服嘴皮子"],
        "expected_reply_axes": ["夸她会说", "看懂她借势化解", "吐槽原主口碑带来的麻烦"],
        "owner_notes": "This replaces the old EP04 runtime gold around 01:00 for taste calibration; the target beat is the 01:49 verbal reversal.",
    },
    {
        "item_id": "taste_gold_owner_huangnian_ep06_0103",
        "episode_id": "huangnian_ep06",
        "anchor_ms": 63000,
        "source_start_ms": 60000,
        "source_end_ms": 80000,
        "viewer_line_pressure": "人设依旧稳固。",
        "why_now": "儿子们从“从前娘被大舅打也拦着讨公道”推回原主旧人设，白米和死心借口反而强化了家人疑惑。",
        "expected_tone": ["轻吐槽", "原主人设余波", "不急着解释系统"],
        "expected_reply_axes": ["吐槽原主人设稳固", "理解儿子疑惑", "提醒别把系统底牌露光"],
        "owner_notes": "The point is not merely white-rice exposure; it is the family reading today's change through the old persona.",
    },
]

PROPOSED_GOLD_SEEDS: list[dict[str, Any]] = [
    {
        "item_id": "taste_gold_proposed_huangnian_ep02_0125",
        "episode_id": "huangnian_ep02",
        "anchor_ms": 125000,
        "source_start_ms": 120000,
        "source_end_ms": 140000,
        "viewer_line_pressure": "他们被她亏待成这样，居然还先把吃的端给娘。",
        "why_now": "野菜糊糊端上来时，重点不是单纯“饿”，而是“饿 + 原主以前亏待他们”的双重前提下，家里人仍先孝顺她。",
        "expected_tone": ["轻心疼", "轻吐槽", "第三条回收话锋"],
        "expected_reply_axes": ["孝顺得让人愣住", "吐槽原主不值得", "承认短剧夸张并收住"],
        "owner_notes": "Owner reviewed: understandable but previous version over-weighted hunger; revise toward hunger + prior harm + still filial.",
    },
    {
        "item_id": "taste_gold_proposed_huangnian_ep08_0148",
        "episode_id": "huangnian_ep08",
        "anchor_ms": 148000,
        "source_start_ms": 140000,
        "source_end_ms": 160000,
        "viewer_line_pressure": "孩子被夸一下就开心成这样。",
        "why_now": "第一次被夸的反应把旧家庭关系露出来，但情绪轻，适合测试温柔点不能过度苦情。",
        "expected_tone": ["轻暖", "一点心疼", "不沉重", "观众看剧反应"],
        "expected_reply_axes": ["孩子太容易满足", "孩子以前太缺夸", "看得心软"],
        "owner_notes": "Owner reviewed: window understandable, but first pass presets were wrong-taste. The missing subject of praise is the child, not the original persona.",
    },
    {
        "item_id": "taste_gold_proposed_huangnian_ep09_0044",
        "episode_id": "huangnian_ep09",
        "anchor_ms": 44000,
        "source_start_ms": 40000,
        "source_end_ms": 60000,
        "viewer_line_pressure": "茅坑里捡来的这种话也太损了。",
        "why_now": "外人用原主偏心来羞辱孩子，观众会想吐槽这句话太狠，也能看见旧人设的外部后果。",
        "expected_tone": ["不爽", "吐槽外人嘴毒", "观众看剧反应"],
        "expected_reply_axes": ["吐槽小孩嘴毒", "吐槽原主自己孩子都不宠", "替孩子难受"],
        "owner_notes": "Owner reviewed: window understandable, but first pass presets used action/meta posture. Rewrite as viewer-and-companion reactions while watching.",
    },
    {
        "item_id": "taste_gold_proposed_huangnian_ep10_0027",
        "episode_id": "huangnian_ep10",
        "anchor_ms": 27000,
        "source_start_ms": 20000,
        "source_end_ms": 40000,
        "viewer_line_pressure": "这小孩说话不算数也太欠了。",
        "why_now": "程家小孩赖账和威胁叠在一起，观众会有即时吐槽，不需要等后续打脸。",
        "expected_tone": ["吐槽", "一点火气", "短剧爽点前奏"],
        "expected_reply_axes": ["骂赖账太欠", "护四蛋别被拿捏", "等主角反手收拾"],
        "owner_notes": "Agent-proposed; needs owner review.",
    },
    {
        "item_id": "taste_gold_proposed_huangnian_ep14_0048",
        "episode_id": "huangnian_ep14",
        "anchor_ms": 48000,
        "source_start_ms": 40000,
        "source_end_ms": 60000,
        "viewer_line_pressure": "连婆婆都怕她把东西补贴娘家。",
        "why_now": "婆婆送粮还专门警告别补贴娘家，原主人设从家里扩展到婆家关系，是清晰的吐槽点。",
        "expected_tone": ["轻吐槽", "人设余波", "带一点好笑"],
        "expected_reply_axes": ["吐槽口碑太稳", "理解婆婆防备", "提醒这次别再补贴娘家"],
        "owner_notes": "Agent-proposed; needs owner review.",
    },
    {
        "item_id": "taste_gold_proposed_huangnian_ep17_0048",
        "episode_id": "huangnian_ep17",
        "anchor_ms": 48000,
        "source_start_ms": 40000,
        "source_end_ms": 60000,
        "viewer_line_pressure": "以前家里鸡蛋都被原主吃了？这也太离谱。",
        "why_now": "孩子想吃一小口鸡蛋，把原主吃独食的人设落到具体物件上，观众容易接一句吐槽。",
        "expected_tone": ["吐槽", "轻心疼", "具体物件"],
        "expected_reply_axes": ["吐槽原主吃独食", "让孩子吃一口", "别让孕妇小孩再被排除"],
        "owner_notes": "Agent-proposed; needs owner review.",
    },
]

OWNER_EPISODE_WINDOW_REVIEWS: list[dict[str, Any]] = [
    {
        "episode_id": "huangnian_ep02",
        "selected_item_id": "taste_gold_proposed_huangnian_ep02_0125",
        "selected_at": "2026-06-06T18:37:02.879Z",
        "rejected_item_ids": [
            "taste_negative_legacy_huangnian_ep02_c001",
            "taste_negative_legacy_huangnian_ep02_c003",
            "taste_negative_legacy_huangnian_ep02_c007",
            "taste_negative_legacy_huangnian_ep02_c009",
        ],
    },
    {
        "episode_id": "huangnian_ep08",
        "selected_item_id": "taste_gold_proposed_huangnian_ep08_0148",
        "selected_at": "2026-06-06T19:26:09.848Z",
        "rejected_item_ids": [
            "taste_negative_legacy_huangnian_ep08_c002",
            "taste_negative_legacy_huangnian_ep08_c003",
            "taste_negative_legacy_huangnian_ep08_c001",
            "taste_negative_legacy_huangnian_ep08_c005",
        ],
    },
    {
        "episode_id": "huangnian_ep09",
        "selected_item_id": "taste_gold_proposed_huangnian_ep09_0044",
        "selected_at": "2026-06-06T19:26:17.316Z",
        "rejected_item_ids": [
            "taste_negative_legacy_huangnian_ep09_c003",
            "taste_negative_legacy_huangnian_ep09_c001",
        ],
    },
    {
        "episode_id": "huangnian_ep10",
        "selected_item_id": "taste_gold_proposed_huangnian_ep10_0027",
        "selected_at": "2026-06-06T19:26:30.798Z",
        "rejected_item_ids": [],
    },
    {
        "episode_id": "huangnian_ep14",
        "selected_item_id": "taste_gold_proposed_huangnian_ep14_0048",
        "selected_at": "2026-06-06T19:26:37.482Z",
        "rejected_item_ids": [
            "taste_negative_legacy_huangnian_ep14_c001",
            "taste_negative_legacy_huangnian_ep14_c002",
            "taste_negative_legacy_huangnian_ep14_c003",
        ],
    },
    {
        "episode_id": "huangnian_ep17",
        "selected_item_id": "taste_gold_proposed_huangnian_ep17_0048",
        "selected_at": "2026-06-06T19:26:47.199Z",
        "rejected_item_ids": [
            "taste_negative_legacy_huangnian_ep17_c001",
            "taste_negative_legacy_huangnian_ep17_c003",
            "taste_negative_legacy_huangnian_ep17_c005",
        ],
    },
]

OWNER_PHASE15_SELECTED_BY_ITEM = {
    str(review["selected_item_id"]): review
    for review in OWNER_EPISODE_WINDOW_REVIEWS
    if review.get("selected_item_id")
}
OWNER_PHASE15_REJECTED_BY_ITEM = {
    str(item_id): review
    for review in OWNER_EPISODE_WINDOW_REVIEWS
    for item_id in review.get("rejected_item_ids", [])
}

CONTEXT_CARD_OVERRIDES: dict[str, dict[str, str]] = {
    "taste_gold_owner_huangnian_ep03_0033": {
        "episode_context": "程弯弯刚穿进原主身份，家里仍按旧恶婆婆人设理解她。她想把野菜拿出去处理时，孩子立刻联想到她又要把家里吃的送去大舅家。",
        "scene_function": "早期原主人设强化：用“最后一点吃的”把旧人设的离谱感落到具体物件上。",
        "character_relationship_state": "孩子们还没有建立对新程弯弯的信任；他们不是撒娇，是怕最后一口吃的再次被送走。",
        "dependency_note": "episode-local enough；只需知道原主过去常补贴娘家即可理解。",
    },
    "taste_gold_owner_huangnian_ep07_0021": {
        "episode_context": "EP03 到 EP07 一直在强化穿越前原主的恶婆婆形象。这里回到过去/原主行为：她对怀孕儿媳恶语相向，还把饭变成羞辱。",
        "scene_function": "恶婆婆人设加码：从亏待孩子推进到羞辱怀孕儿媳，让观众吐槽开始带怒气。",
        "character_relationship_state": "儿媳处在低位和恐惧里；观众对原主还没有深情感连接，主要是骂人设、顺带心疼儿媳。",
        "dependency_note": "needs light cross-episode persona bridge；卡片必须交代这是持续强化原主人设，不是孤立餐桌选择。",
    },
    "taste_gold_owner_huangnian_ep04_0149": {
        "episode_context": "主角在稻田试系统和挖野菜时，被稻田主人按原主坏口碑误认为偷稻谷，围观者也顺着旧名声攻击她。",
        "scene_function": "能力感/嘴会说的反转：主角不靠开挂解释，而是把小鹅菜和借粮话术抛出来化解危机。",
        "character_relationship_state": "村里默认原主会偷、会补贴娘家；主角需要在公开场合用话术保护自己和家里。",
        "dependency_note": "episode-local with adjacent ASR；必须看到前一段被扣偷稻谷帽子，01:49 的嘴会说才成立。",
    },
    "taste_gold_owner_huangnian_ep06_0103": {
        "episode_context": "主角拿出系统兑换的大米，但不能透露系统，只能用对娘家死心等借口遮住来源。",
        "scene_function": "原主人设余波：家人把今天的转变和过去一心向娘家的母亲对比，疑惑比白米本身更有味。",
        "character_relationship_state": "儿子们对母亲仍不确定：他们记得她过去被大舅打也拦着儿子讨公道，所以“死心了”不容易被立刻相信。",
        "dependency_note": "episode-local plus prior persona bridge；Agent 不能只按白米曝光风险判断。",
    },
    "taste_gold_proposed_huangnian_ep02_0125": {
        "episode_context": "EP02 在交代原主有多恶：打骂家人、拿抚恤银补贴娘家、讨粮被娘家赶走。随后家里人明明也饿，却仍把野菜糊糊先端给她。",
        "scene_function": "家庭基线建立：不是单纯卖惨，而是用“被亏待过的人仍先孝顺她”立住原主人设和家人惯性。",
        "character_relationship_state": "孩子和儿媳长期被亏待，但还把母亲放在优先位置；观众的反应应是轻心疼加吐槽，不是沉重苦情。",
        "dependency_note": "episode-local enough；前 2 分钟 ASR 已交代原主伤害和家里饥饿。",
    },
    "taste_gold_proposed_huangnian_ep08_0148": {
        "episode_context": "主角开始带家里人分工上山，用系统识别野菜蘑菇。孩子们还在适应这个突然变好的娘。",
        "scene_function": "关系修复轻节点：一句夸奖让孩子明显开心，显示他们过去太少被正向对待。",
        "character_relationship_state": "孩子对母亲的温柔和夸奖非常不习惯；这是轻暖而不是大哭点。",
        "dependency_note": "needs prior persona bridge；卡片要说明“第一次夸”来自长期缺失，不然只看一句会偏淡。",
    },
    "taste_gold_proposed_huangnian_ep09_0044": {
        "episode_context": "四蛋的兔子被程家孩子抢，外人拿原主偏心程家、亏待四个儿子的旧名声来羞辱孩子。",
        "scene_function": "外部后果显影：原主过去偏心娘家，变成别人羞辱孩子的武器。",
        "character_relationship_state": "孩子正在被抢东西又被戳母亲偏心的旧伤；观众会先骂这话太损，再想护孩子。",
        "dependency_note": "episode-local plus persona bridge；ASR 自带“最疼的不是四个儿子”说明。",
    },
    "taste_gold_proposed_huangnian_ep10_0027": {
        "episode_context": "承接 EP09 抢兔子，程家孩子先逼四蛋受辱，又赖掉刚才的承诺，还拿阿奶和爹威胁主角。",
        "scene_function": "爽点反打前奏：先把对方欠揍和不讲理摆满，等待主角收拾。",
        "character_relationship_state": "程家孩子习惯借大人和旧偏心压人；四蛋还在被拿捏，主角刚开始介入。",
        "dependency_note": "needs immediate previous beat；没有 EP09/EP10 前一段，单看这句仍能懂欠揍，但兔子冲突会弱。",
    },
    "taste_gold_proposed_huangnian_ep14_0048": {
        "episode_context": "婆家知道原主曾把丈夫抚恤银和粮食补贴娘家，也知道她分家后和婆家关系差。",
        "scene_function": "外部长辈验证人设：连婆婆给粮都要防她补贴娘家，把原主口碑从家里扩展到婆家。",
        "character_relationship_state": "说话人 cue：婆婆把粮交给怀孕儿媳/大山媳妇，防的是原主再拿去补贴娘家；主角/旁白随后吐槽“这口碑也是没谁了”。婆婆嘴硬但仍顾着四个孙子和怀孕儿媳，不是纯反派。",
        "dependency_note": "episode-local enough, but ASR has no speaker diarization；卡片需要人工 speaker cue，否则会看懂大意但卡在细节。",
    },
    "taste_gold_proposed_huangnian_ep17_0048": {
        "episode_context": "家里开始有一点改善，但孩子仍记得过去好东西都归原主。四蛋拿到鸡蛋后，只敢问能不能吃一小口。",
        "scene_function": "具体物件上的人设修复：鸡蛋把原主吃独食的离谱感落到孩子小愿望上。",
        "character_relationship_state": "四蛋不是贪吃，他是在试探现在的娘会不会还像从前那样把好东西全占走。",
        "dependency_note": "episode-local enough；ASR 直接说从前家里的鸡蛋都是娘吃的。",
    },
}

OWNER_REVIEW_OVERRIDES: dict[str, dict[str, Any]] = {
    "taste_gold_proposed_huangnian_ep02_0125": {
        "owner_review_outcome": "understood_gold_with_revision",
        "authoring_seed": {
            "companion_lead_seed": "他们居然还先把吃的端给娘。",
            "lead_style_policy": DEFAULT_LEAD_STYLE_POLICY,
            "reply_set_policy": DEFAULT_REPLY_SET_POLICY,
            "reply_candidate_seeds": [
                {
                    "display_text": "是呀，也太孝顺了",
                    "emotion_role": "轻心疼",
                    "semantic_role": "filial_even_after_harm",
                    "intent_note": "接住“被亏待过但仍先照顾娘”的惊讶和心疼。",
                },
                {
                    "display_text": "这么坏，是我早不理她了",
                    "emotion_role": "轻吐槽",
                    "semantic_role": "call_out_original_persona_not_deserving",
                    "intent_note": "把原主过去对他们不好说出来，但不升级成沉重控诉。",
                },
                {
                    "display_text": "有点夸张",
                    "emotion_role": "回收话锋",
                    "semantic_role": "tone_check_short_drama_exaggeration",
                    "intent_note": "兜底给不完全买账的用户，承认短剧夸张，同时保留桥段功能。",
                },
            ],
            "response_tone_policy": "轻接住，不煽情。先承认孝顺/夸张感，再点到原主以前确实亏待他们。不要把这段写成深度亲情审判。",
            "preset_echo_policy": DEFAULT_PRESET_ECHO_POLICY,
            "custom_reply_policy_hint": "用户若心疼、骂原主、或觉得夸张，都在当前窗口内接住；回复必须回到“饿 + 过去被亏待 + 仍先孝顺”这个复合点。",
            "rejected_lead_examples": [
                {
                    "display_text": "他们都饿成这样了，还先把吃的端给娘",
                    "negative_type": "single_axis_hunger_framing",
                    "reject_reason": "懂但略偏，过于强调孩子们饿，漏掉“原主以前对他们不好 + 他们仍然先孝顺”的复合前提。",
                    "correction_hint": "改成“他们居然还先把吃的端给娘。”这类更聚焦反差的搭子引子。",
                },
                {
                    "display_text": "刚才那一下，你是不是想说：",
                    "negative_type": "questionnaire_template",
                    "reject_reason": "这是让用户答题的问卷式模板，不像一起追剧的朋友自然接话。",
                    "correction_hint": "改成和当前情景强绑定的一句话，例如“他们居然还先把吃的端给娘。”",
                },
                {
                    "display_text": "三句我想说的话",
                    "negative_type": "ui_label_as_lead",
                    "reject_reason": "这是功能标签，不是搭子对剧情开口的引子。",
                    "correction_hint": "UI 可以有隐藏结构，但 visible lead 必须是 scene-specific friend speech。",
                },
            ],
            "blocked_claims_hint": [
                "不能宣称家人已经原谅原主",
                "不能宣称现实中应该无条件孝顺亏待自己的人",
                "不能预测后续亲情已经修复",
            ],
        },
    },
    "taste_gold_proposed_huangnian_ep08_0148": {
        "owner_review_outcome": "understood_wrong_taste",
        "authoring_seed": {
            "companion_lead_seed": "孩子被夸一下就开心成这样。",
            "lead_style_policy": DEFAULT_LEAD_STYLE_POLICY,
            "reply_set_policy": DEFAULT_REPLY_SET_POLICY,
            "viewer_stance_policy": DEFAULT_VIEWER_STANCE_POLICY,
            "reply_candidate_seeds": [
                {
                    "display_text": "这孩子也太容易满足了",
                    "emotion_role": "轻暖心疼",
                    "semantic_role": "child_too_easy_to_make_happy",
                    "intent_note": "方向保留“孩子太容易满足”，但写成观众脱口而出的反应，不写成分析标签。",
                },
                {
                    "display_text": "以前是多缺夸啊",
                    "emotion_role": "轻心疼",
                    "semantic_role": "child_lacked_praise_before",
                    "intent_note": "把缺夸的主体改成孩子，避免误写成原主缺夸。",
                },
                {
                    "display_text": "这一下看得我心软",
                    "emotion_role": "回收话锋",
                    "semantic_role": "viewer_heart_softens",
                    "intent_note": "兜底给不想重说旧账的用户，落在观众看到孩子开心反应时的心软。",
                },
            ],
            "response_tone_policy": "轻暖，一点心疼，但不能苦情化。回复像搭子看见孩子第一次被夸后的反应，不要评价剧情煽不煽，也不要替角色下任务。",
            "preset_echo_policy": DEFAULT_PRESET_ECHO_POLICY,
            "custom_reply_policy_hint": "用户若说孩子太容易满足、以前没被夸过、或觉得这段有点甜，都只围绕孩子这次被夸的反应接住。",
            "rejected_lead_examples": [
                {
                    "display_text": "有点暖，但别太煽",
                    "negative_type": "third_layer_meta_lead",
                    "reject_reason": "这是对剧情写法/煽情程度的评价，已经跳到第三层，不是搭子在场内接住观众的一句话。",
                    "correction_hint": "改成观众和搭子看见孩子反应时的现场话，例如“夸一句就这么开心啊。”",
                }
            ],
            "rejected_reply_examples": [
                {
                    "display_text": "有点暖，但别太煽",
                    "negative_type": "third_layer_meta",
                    "reject_reason": "这是对剧情写法/煽情程度的评价，不是观众看剧时想对搭子说的话。",
                    "correction_hint": "改成观众当下的轻心疼或心软反应。",
                },
                {
                    "display_text": "他这反应有点戳人",
                    "negative_type": "awkward_viewer_abstraction",
                    "reject_reason": "方向接近，但“戳人”仍然像抽象评价，口语搭子感弱。",
                    "correction_hint": "改成更自然的观众反应，例如“这一下看得我心软”。",
                },
                {
                    "display_text": "孩子太容易满足",
                    "negative_type": "right_direction_flat_wording",
                    "reject_reason": "方向勉强成立，但写法像归纳标签，不像观众当下会点的一句话。",
                    "correction_hint": "改成更具体的看剧反应，例如“夸一句就这么开心啊”。",
                },
                {
                    "display_text": "原主以前太缺夸",
                    "negative_type": "wrong_subject",
                    "reject_reason": "缺夸的主体是孩子，不是原主。",
                    "correction_hint": "明确孩子以前缺夸。",
                },
                {
                    "display_text": "现在这一下要接住",
                    "negative_type": "producer_delivery_label",
                    "reject_reason": "这是生产者对话术功能的描述，不是用户会点的预设回复。",
                    "correction_hint": "改成观众直接说出的心软、心疼或轻暖反应。",
                },
            ],
            "blocked_claims_hint": [
                "不能把缺夸主体写成原主",
                "不能宣称孩子已经完全原谅原主",
                "不能写成教育孩子或护住孩子面子的行动建议",
            ],
        },
    },
    "taste_gold_proposed_huangnian_ep09_0044": {
        "owner_review_outcome": "understood_wrong_taste",
        "authoring_seed": {
            "companion_lead_seed": "茅坑里捡来的这种话也太损了。",
            "lead_style_policy": DEFAULT_LEAD_STYLE_POLICY,
            "reply_set_policy": DEFAULT_REPLY_SET_POLICY,
            "viewer_stance_policy": DEFAULT_VIEWER_STANCE_POLICY,
            "reply_candidate_seeds": [
                {
                    "display_text": "就是，这小孩嘴好毒",
                    "emotion_role": "吐槽嘴毒",
                    "semantic_role": "kid_talks_too_poisonous",
                    "intent_note": "接住用户对辱骂话术本身的第一反应。",
                },
                {
                    "display_text": "原主自己孩子都不宠，有点离谱",
                    "emotion_role": "吐槽原主",
                    "semantic_role": "original_persona_did_not_favor_own_children",
                    "intent_note": "换到观众吐槽原主偏心造成孩子被戳痛点，不写成生产者 meta。",
                },
                {
                    "display_text": "听着都替他难受",
                    "emotion_role": "回收话锋",
                    "semantic_role": "feel_bad_for_child",
                    "intent_note": "兜底给不想继续骂嘴毒的用户，转成观众替孩子难受的反应。",
                },
            ],
            "response_tone_policy": "观众搭子口吻，先吐槽嘴毒和偏心旧账带来的难堪。不要写成“护住孩子面子”的行动指令，也不要上升成剧情分析报告。",
            "preset_echo_policy": DEFAULT_PRESET_ECHO_POLICY,
            "custom_reply_policy_hint": "用户若骂小孩嘴毒、骂原主偏心、或觉得这话过分，都只在这场抢兔子和羞辱孩子的语境里接住。",
            "rejected_reply_examples": [
                {
                    "display_text": "护住孩子面子",
                    "negative_type": "character_action_task",
                    "reject_reason": "这是替角色规划动作/交付，不是观众看剧时的反应。",
                    "correction_hint": "改成观众吐槽嘴毒或替孩子难受。",
                },
                {
                    "display_text": "点出原主偏心后果",
                    "negative_type": "producer_meta_analysis",
                    "reject_reason": "这是生产者对桥段功能的说明，不是用户会说的话。",
                    "correction_hint": "改成“原主自己孩子都不宠，有点离谱”这类观众吐槽。",
                },
                {
                    "display_text": "原主自己孩子都不宠",
                    "negative_type": "underfinished_viewer_line",
                    "reject_reason": "方向对，但半句停在概念上，还没有落成观众会顺手发出的吐槽。",
                    "correction_hint": "补一个口语落点，例如“原主自己孩子都不宠，有点离谱”。",
                },
                {
                    "display_text": "这话有点损过头了",
                    "negative_type": "duplicate_axis",
                    "reject_reason": "和“就是，这小孩嘴好毒”同轴重复，第三条没有提供新的观众姿态。",
                    "correction_hint": "改成替孩子难受的方向，例如“听着都替他难受”。",
                },
                {
                    "display_text": "这话也太损了",
                    "negative_type": "lead_candidate_duplicate",
                    "reject_reason": "可以当 lead 的即时引子，但作为 preset 会和 lead/第一条回复重复。",
                    "correction_hint": "preset 应该转到嘴毒、原主偏心、替孩子难受三种不同观众姿态。",
                },
            ],
            "blocked_claims_hint": [
                "不能写成护住孩子面子的行动交付",
                "不能只说点出原主偏心后果这种 producer meta",
                "不能把用户带回 RPG/改剧情选择",
            ],
        },
    },
    "taste_gold_proposed_huangnian_ep10_0027": {
        "owner_review_outcome": "understood_gold_with_revision",
        "authoring_seed": {
            "companion_lead_seed": "坐等看戏。",
            "lead_style_policy": DEFAULT_LEAD_STYLE_POLICY,
            "reply_set_policy": DEFAULT_REPLY_SET_POLICY,
            "viewer_stance_policy": DEFAULT_VIEWER_STANCE_POLICY,
            "reply_candidate_seeds": [
                {
                    "display_text": "还真是，现在不是原主了",
                    "emotion_role": "看戏期待",
                    "semantic_role": "new_protagonist_not_original_persona",
                    "intent_note": "接住短剧反打前奏：现在不是会偏心程家的原主，观众等着看局面翻转。",
                },
                {
                    "display_text": "确实，主角肯定会护着四蛋",
                    "emotion_role": "护短期待",
                    "semantic_role": "expect_protagonist_to_protect_sidan",
                    "intent_note": "把观众对主角介入的爽点期待说出来，作为短剧节奏判断，不写成正式剧情预测。",
                },
                {
                    "display_text": "经典打脸剧情",
                    "emotion_role": "类型爽点",
                    "semantic_role": "classic_face_slapping_setup",
                    "intent_note": "给熟悉短剧套路的用户一个轻松回收选项。",
                },
            ],
            "response_tone_policy": "短剧看戏口吻，轻、快、带一点等打脸的爽点期待。不要把这段写成严肃控诉，也不要做道德审判。",
            "preset_echo_policy": DEFAULT_PRESET_ECHO_POLICY,
            "custom_reply_policy_hint": "预设是短剧节奏下的快捷弹幕，不替代自定义输入。用户若想自己骂赖账、护四蛋、或等打脸，都围绕抢兔子/赖账/主角介入这个当前窗口接住。",
            "rejected_lead_examples": [
                {
                    "display_text": "这小孩说话不算数也太欠了。",
                    "negative_type": "normal_summary_human_machine",
                    "reject_reason": "懂但不对味，太像正常概括反派行为，缺少短剧等反打的看戏节奏。",
                    "correction_hint": "改成“坐等看戏。”这类更贴近短剧爽点前奏的一句话。",
                }
            ],
            "rejected_reply_examples": [
                {
                    "display_text": "骂赖账太欠",
                    "negative_type": "axis_label_no_viewer_voice",
                    "reject_reason": "这是情绪轴标签，不是观众会点的短句。",
                    "correction_hint": "改成具体观众话，例如“还真是，现在不是原主了”。",
                },
                {
                    "display_text": "护四蛋别被拿捏",
                    "negative_type": "character_action_task",
                    "reject_reason": "这是替角色规划动作，回到了 RPG/行动菜单。",
                    "correction_hint": "改成观众对主角护四蛋的期待。",
                },
                {
                    "display_text": "等主角反手收拾",
                    "negative_type": "plot_action_axis",
                    "reject_reason": "方向接近但仍像剧情动作标签，不够像观众弹幕。",
                    "correction_hint": "改成“经典打脸剧情”这类短剧类型反应。",
                },
            ],
            "blocked_claims_hint": [
                "不能宣称后续具体打脸方式已经发生",
                "不能把预设写成让角色采取行动",
                "不能把看戏期待写成正式剧情预测报告",
            ],
        },
    },
    "taste_gold_proposed_huangnian_ep14_0048": {
        "owner_review_outcome": "understood_gold_with_revision",
        "authoring_seed": {
            "companion_lead_seed": "连婆婆都怕她把东西补贴娘家。",
            "lead_style_policy": DEFAULT_LEAD_STYLE_POLICY,
            "reply_set_policy": DEFAULT_REPLY_SET_POLICY,
            "viewer_stance_policy": DEFAULT_VIEWER_STANCE_POLICY,
            "reply_candidate_seeds": [
                {
                    "display_text": "这口碑也是没谁了",
                    "emotion_role": "吐槽口碑",
                    "semantic_role": "reputation_is_absurdly_bad",
                    "intent_note": "直接接 ASR/旁白里的吐槽，带出原主人设余波。",
                },
                {
                    "display_text": "原主那个人设，也难怪婆婆防备",
                    "emotion_role": "理解防备",
                    "semantic_role": "mother_in_law_defense_makes_sense",
                    "intent_note": "保留用户给出的修正：理解婆婆防备，但说成观众吐槽，不写成分析标签。",
                },
                {
                    "display_text": "婆婆嘴硬归嘴硬，粮是真给了",
                    "emotion_role": "关系补充",
                    "semantic_role": "strict_but_helpful_mother_in_law",
                    "intent_note": "补足婆婆不是纯反派的情绪面，避免只剩元分析。",
                },
            ],
            "response_tone_policy": "轻吐槽，带一点人设余波的好笑。需要说清婆婆防备谁，但不要变成关系分析报告。",
            "preset_echo_policy": DEFAULT_PRESET_ECHO_POLICY,
            "custom_reply_policy_hint": "用户若吐槽口碑、理解婆婆防备、或注意到婆婆嘴硬心软，都只围绕给粮/防补贴娘家这段接住。",
            "rejected_reply_examples": [
                {
                    "display_text": "吐槽口碑太稳",
                    "negative_type": "axis_label_no_emotion",
                    "reject_reason": "方向勉强可用，但没有情绪，只像标签。",
                    "correction_hint": "改成“这口碑也是没谁了”这类观众吐槽。",
                },
                {
                    "display_text": "理解婆婆防备",
                    "negative_type": "meta_no_emotion",
                    "reject_reason": "有点 meta，也没有情绪，不像观众会点的句子。",
                    "correction_hint": "改成“原主那个人设，也难怪婆婆防备”。",
                },
                {
                    "display_text": "提醒这次别再补贴娘家",
                    "negative_type": "character_action_task",
                    "reject_reason": "这是跑偏到角色行动/RPG 任务，不是看剧搭子的预设回复。",
                    "correction_hint": "改成婆婆防备、原主口碑、嘴硬给粮这些观众反应。",
                },
            ],
            "blocked_claims_hint": [
                "不能把婆婆写成纯反派",
                "不能把回复写成让主角承诺不补贴娘家",
                "不能忽略 ASR 无说话人区分导致的细节歧义",
            ],
        },
    },
    "taste_gold_proposed_huangnian_ep17_0048": {
        "owner_review_outcome": "understood_wrong_taste",
        "authoring_seed": {
            "companion_lead_seed": "以前家里鸡蛋都被原主吃了？",
            "lead_style_policy": DEFAULT_LEAD_STYLE_POLICY,
            "reply_set_policy": DEFAULT_REPLY_SET_POLICY,
            "viewer_stance_policy": DEFAULT_VIEWER_STANCE_POLICY,
            "reply_candidate_seeds": [
                {
                    "display_text": "这原主，自私到骨子里了",
                    "emotion_role": "吐槽原主",
                    "semantic_role": "original_persona_kept_eggs_for_herself",
                    "intent_note": "把“吐槽原主吃独食”的轴落成更自然、更狠一点的观众吐槽。",
                },
                {
                    "display_text": "他连一小口都不敢直接要",
                    "emotion_role": "心疼孩子",
                    "semantic_role": "child_afraid_to_ask_for_one_bite",
                    "intent_note": "接住孩子只敢试探一小口的心酸。",
                },
                {
                    "display_text": "原主人设又稳得离谱",
                    "emotion_role": "人设余波吐槽",
                    "semantic_role": "original_persona_still_absurd",
                    "intent_note": "回到系列里反复出现的原主人设梗，作为轻一点的兜底。",
                },
            ],
            "response_tone_policy": "具体物件吐槽，不苦情化。先让鸡蛋这个物件立住，再轻轻带出孩子试探和原主人设余波。",
            "preset_echo_policy": DEFAULT_PRESET_ECHO_POLICY,
            "custom_reply_policy_hint": "用户若吐槽鸡蛋、心疼孩子只敢要一小口、或说原主人设稳，都围绕鸡蛋这个当前窗口具体物件接住。",
            "rejected_lead_examples": [
                {
                    "display_text": "以前家里鸡蛋都被原主吃了？这也太离谱。",
                    "negative_type": "overclosed_lead_tail",
                    "reject_reason": "前半句能打开情景，后半句直接替用户完成评价，让 lead 变得不够自然。",
                    "correction_hint": "去掉尾巴，保留“以前家里鸡蛋都被原主吃了？”作为更开放的搭子引子。",
                }
            ],
            "rejected_reply_examples": [
                {
                    "display_text": "鸡蛋都自己吃，也太离谱了",
                    "negative_type": "unnatural_viewer_wording",
                    "reject_reason": "方向对但不自然，像把 lead 改写了一遍，不像用户会顺手点的吐槽。",
                    "correction_hint": "改成“这原主，自私到骨子里了”。",
                },
                {
                    "display_text": "吐槽原主吃独食",
                    "negative_type": "axis_label_no_viewer_voice",
                    "reject_reason": "不应该把语义轴直接给用户看；这不是一句观众吐槽。",
                    "correction_hint": "改成“这原主，自私到骨子里了”。",
                },
                {
                    "display_text": "让孩子吃一口",
                    "negative_type": "character_action_task",
                    "reject_reason": "这是角色行动/RPG 指令，不是看剧时嘴边那句话。",
                    "correction_hint": "改成孩子小心试探带来的观众反应。",
                },
                {
                    "display_text": "别让孕妇小孩再被排除",
                    "negative_type": "policy_like_action_task",
                    "reject_reason": "这像议题/任务表述，完全脱离当前鸡蛋物件和短剧口吻。",
                    "correction_hint": "回到“鸡蛋”“一小口”“原主人设”这些场内触发点。",
                },
            ],
            "blocked_claims_hint": [
                "不能把回复写成角色行动菜单",
                "不能把鸡蛋桥段上升成泛泛议题",
                "不能预测后续家庭关系已经修复",
            ],
        },
    },
}

SCENE_FUNCTION_BY_LABEL = {
    "gold": "Candidate is being tested as an episode-best mouthpiece moment.",
    "hard_negative": "Candidate is useful as a taste boundary or context-insufficient negative.",
}

MANUAL_HARD_NEGATIVE_SEEDS: list[dict[str, Any]] = [
    {
        "item_id": "taste_negative_huangnian_ep12_skip_context",
        "episode_id": "huangnian_ep12",
        "anchor_ms": 0,
        "source_start_ms": 0,
        "source_end_ms": 20000,
        "evaluation_focus": "window_selection",
        "nomination_role": "skip_candidate",
        "viewer_line_pressure": "单看这一集还没形成清晰嘴边一句。",
        "why_now": "兔子和吃肉都有情绪材料，但单集上下文不自足，owner 明确不确定怎么切。",
        "reject_dimensions": ["context_insufficient", "episode_transition", "weak_standalone_pressure"],
        "reject_reason": "不为每集覆盖率硬发搭子点；EP12 先作为 skip/negative 校准。",
        "evidence_excerpt": "四蛋抓了只兔子，今天晚上咱吃兔肉。咱们家一年都没有吃过肉了，虽然肯定没有我的份。",
        "evidence_refs": ["huangnian_ep12_w001"],
    },
    {
        "item_id": "taste_negative_huangnian_ep03_nearmiss_0040",
        "episode_id": "huangnian_ep03",
        "anchor_ms": 40000,
        "source_start_ms": 40000,
        "source_end_ms": 60000,
        "evaluation_focus": "window_selection",
        "nomination_role": "near_miss",
        "viewer_line_pressure": "这更像解释补充，不是最适合冒出的第一秒。",
        "why_now": "孩子继续解释大舅和每次都送走，但 00:33 已经完成嘴边一句的触发。",
        "reject_dimensions": ["late_after_gold", "lower_first-hit_pressure"],
        "reject_reason": "同集已有更强 best window，后续解释不应再抢一个搭子点。",
        "evidence_excerpt": "娘，你每次都这么说，可你每次都送给他们。娘，求你了，你还不明白吗？",
        "evidence_refs": ["huangnian_ep03_w003"],
    },
    {
        "item_id": "taste_negative_huangnian_ep07_nearmiss_0040",
        "episode_id": "huangnian_ep07",
        "anchor_ms": 40000,
        "source_start_ms": 40000,
        "source_end_ms": 60000,
        "evaluation_focus": "window_selection",
        "nomination_role": "near_miss",
        "viewer_line_pressure": "这个更像角色反应收尾。",
        "why_now": "儿媳和家人已经开始意识到变化，情绪压力不如 00:21 的恶婆婆羞辱直接。",
        "reject_dimensions": ["late_after_gold", "weaker_mouthpiece_pressure"],
        "reject_reason": "同集最多一个 best window，不能把后续反应也切成搭子点。",
        "evidence_excerpt": "我咋突然变得这么陌生呢？看来不是在做梦，是真的！快点吃！",
        "evidence_refs": ["huangnian_ep07_w003"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows", default=str(DEFAULT_WINDOWS_PATH))
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES_PATH))
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--review-tray", default=str(DEFAULT_REVIEW_TRAY_PATH))
    args = parser.parse_args()

    windows = load_windows(resolve_path(args.windows))
    candidates = load_candidates(resolve_path(args.candidates))
    dataset = build_dataset(windows=windows, candidates=candidates)
    out_path = resolve_path(args.out)
    write_json(out_path, dataset)
    tray_path = resolve_path(args.review_tray)
    write_review_tray(tray_path, dataset)
    window_tray_path = tray_path.parent / DEFAULT_WINDOW_REVIEW_TRAY_PATH.name
    write_window_review_tray(window_tray_path, dataset)
    print(f"wrote {repo_relative(out_path)}")
    print(f"wrote {repo_relative(tray_path)}")
    print(f"wrote {repo_relative(window_tray_path)}")
    return 0


def build_dataset(*, windows: dict[str, dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for seed in OWNER_GOLD_SEEDS:
        items.append(gold_item(seed, windows, review_status="owner_confirmed", source_origin="owner_seed"))
    for seed in PROPOSED_GOLD_SEEDS:
        items.append(gold_item(seed, windows, review_status="proposed_for_owner_review", source_origin="agent_proposed"))
    for seed in MANUAL_HARD_NEGATIVE_SEEDS:
        items.append(manual_negative_item(seed))
    items.extend(legacy_negative_items(candidates, existing_ids={item["item_id"] for item in items}, target_count=50))
    apply_owner_episode_window_reviews(items)
    add_window_reviews(items)
    add_context_cards(items, windows)

    return {
        "schema_version": "window_taste_eval.v0.1",
        "product": "看剧搭子",
        "created_at": "2026-06-06",
        "status": "draft_owner_calibration",
        "policy": {
            "episode_window_policy": "at_most_one_best_window_per_episode_publish_zero_allowed",
            "interaction_window_duration_ms": 10000,
            "source_window_policy": "Interaction window is anchor to anchor+10s; source window may be wider for ASR/keyframe context.",
            "publish_policy": "Studio may nominate at most one best window per episode; runtime publishes zero when taste score or review fails.",
        },
        "targets": {
            "owner_confirmed_gold_min": 10,
            "gold_candidate_min": 10,
            "hard_negative_min": 50,
            "hard_negative_acceptance_target": 0.8,
        },
        "rubric": {
            "positive_axes": [
                {
                    "axis_id": "mouthpiece_pressure",
                    "description": "Viewer has a concrete line stuck in the mouth now, not after an explanation.",
                    "weight": 0.28,
                },
                {
                    "axis_id": "scene_specificity",
                    "description": "The line depends on this scene's people, object, or exact beat.",
                    "weight": 0.20,
                },
                {
                    "axis_id": "evidence_grounding",
                    "description": "ASR/keyframe refs support the beat without future-plot invention.",
                    "weight": 0.16,
                },
                {
                    "axis_id": "reply_axis_capacity",
                    "description": "The beat can naturally produce two to three distinct emotional replies.",
                    "weight": 0.16,
                },
                {
                    "axis_id": "friend_lead_potential",
                    "description": "A companion can open with one friend-like line, not a questionnaire.",
                    "weight": 0.12,
                },
                {
                    "axis_id": "watch_flow_fit",
                    "description": "The interruption feels like a natural watch-along aside.",
                    "weight": 0.08,
                },
            ],
            "penalty_axes": [
                {
                    "axis_id": "action_menu_pull",
                    "description": "The surface becomes 'should she do X' instead of 'I want to say this'.",
                    "weight": 0.34,
                },
                {
                    "axis_id": "generic_theme",
                    "description": "The candidate only names family/resource/system themes without a specific viewer line.",
                    "weight": 0.24,
                },
                {
                    "axis_id": "future_branch_dependency",
                    "description": "The value depends on changing or predicting later plot.",
                    "weight": 0.18,
                },
                {
                    "axis_id": "exposition_required",
                    "description": "The viewer needs a producer explanation before the line lands.",
                    "weight": 0.14,
                },
                {
                    "axis_id": "coverage_pressure",
                    "description": "The episode is being forced to have a point just for coverage.",
                    "weight": 0.10,
                },
            ],
        },
        "items": items,
    }


def gold_item(seed: dict[str, Any], windows: dict[str, dict[str, Any]], *, review_status: str, source_origin: str) -> dict[str, Any]:
    episode_id = str(seed["episode_id"])
    excerpt = lookup_excerpt(windows, episode_id, int(seed["source_start_ms"]), int(seed["source_end_ms"]))
    return {
        "item_id": seed["item_id"],
        "label": "gold",
        "review_status": review_status,
        "evaluation_focus": "window_selection",
        "episode_id": episode_id,
        "anchor_ms": int(seed["anchor_ms"]),
        "interaction_window": interaction_window(int(seed["anchor_ms"])),
        "source_window": {
            "start_ms": int(seed["source_start_ms"]),
            "end_ms": int(seed["source_end_ms"]),
            "evidence_excerpt": excerpt,
        },
        "nomination_role": "episode_best_candidate",
        "source_origin": source_origin,
        "viewer_line_pressure": seed["viewer_line_pressure"],
        "why_now": seed["why_now"],
        "expected_tone": list(seed["expected_tone"]),
        "expected_reply_axes": list(seed["expected_reply_axes"]),
        "reject_dimensions": [],
        "reject_reason": "",
        "evidence_refs": [source_ref_for_window(episode_id, int(seed["source_start_ms"]))],
        "owner_notes": seed["owner_notes"],
        "agent_notes": [],
    }


def apply_owner_episode_window_reviews(items: list[dict[str, Any]]) -> None:
    for item in items:
        item_id = str(item["item_id"])
        if item_id in OWNER_PHASE15_SELECTED_BY_ITEM:
            item["review_status"] = "owner_confirmed"
            item["owner_notes"] = append_note(
                str(item.get("owner_notes") or ""),
                "Owner phase 1.5 selected this candidate as the episode gold window.",
            )
        elif item_id in OWNER_PHASE15_REJECTED_BY_ITEM:
            item["owner_notes"] = append_note(
                str(item.get("owner_notes") or ""),
                "Owner phase 1.5 rejected this displayed same-episode competitor.",
            )
            item["reject_dimensions"] = unique([*item.get("reject_dimensions", []), "owner_phase15_rejected"])


def manual_negative_item(seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": seed["item_id"],
        "label": "hard_negative",
        "review_status": "agent_labeled",
        "evaluation_focus": seed["evaluation_focus"],
        "episode_id": seed["episode_id"],
        "anchor_ms": int(seed["anchor_ms"]),
        "interaction_window": interaction_window(int(seed["anchor_ms"])),
        "source_window": {
            "start_ms": int(seed["source_start_ms"]),
            "end_ms": int(seed["source_end_ms"]),
            "evidence_excerpt": seed["evidence_excerpt"],
        },
        "nomination_role": seed["nomination_role"],
        "source_origin": "near_miss",
        "viewer_line_pressure": seed["viewer_line_pressure"],
        "why_now": seed["why_now"],
        "expected_tone": [],
        "expected_reply_axes": [],
        "reject_dimensions": list(seed["reject_dimensions"]),
        "reject_reason": seed["reject_reason"],
        "evidence_refs": list(seed["evidence_refs"]),
        "owner_notes": "",
        "agent_notes": [],
    }


def legacy_negative_items(
    candidates: list[dict[str, Any]], *, existing_ids: set[str], target_count: int
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    sorted_candidates = sorted(candidates, key=lambda item: float(item.get("rank_score") or 0), reverse=True)
    for candidate in sorted_candidates:
        if len(items) >= target_count - 3:
            break
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id:
            continue
        item_id = f"taste_negative_legacy_{candidate_id}"
        if item_id in existing_ids:
            continue
        episode_id = str(candidate.get("episode_id") or "")
        start_ms = int(candidate.get("start_ms") or 0)
        end_ms = int(candidate.get("end_ms") or start_ms + 10000)
        same_episode_gold = episode_id in GOLD_TARGETS
        focus = "framing_quality" if same_episode_gold else "window_selection"
        reject_dimensions = infer_reject_dimensions(candidate, focus=focus, same_episode_gold=same_episode_gold)
        if not reject_dimensions:
            reject_dimensions = ["generic_theme"]
        items.append(
            {
                "item_id": item_id,
                "label": "hard_negative",
                "review_status": "agent_labeled",
                "evaluation_focus": focus,
                "episode_id": episode_id,
                "anchor_ms": start_ms,
                "interaction_window": interaction_window(start_ms),
                "source_window": {
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "evidence_excerpt": compact_text(str(candidate.get("evidence_excerpt") or "")),
                },
                "nomination_role": "legacy_false_positive",
                "source_origin": "legacy_miner",
                "viewer_line_pressure": str(candidate.get("viewer_impulse") or "旧系统没有给出自然的嘴边一句。"),
                "why_now": str(candidate.get("why_now") or "旧系统按机制命中，但还未证明值得搭子打断。")[:300],
                "expected_tone": [],
                "expected_reply_axes": [],
                "reject_dimensions": reject_dimensions,
                "reject_reason": reject_reason_for(candidate, focus=focus, same_episode_gold=same_episode_gold),
                "evidence_refs": [candidate_id, str(candidate.get("window_id") or "")],
                "owner_notes": "",
                "agent_notes": [
                    "Generated from legacy deterministic miner as a hard-negative candidate for taste calibration."
                ],
            }
        )
    return items


def infer_reject_dimensions(candidate: dict[str, Any], *, focus: str, same_episode_gold: bool) -> list[str]:
    dimensions: list[str] = []
    hook = str(candidate.get("hook") or "")
    if any(token in hook for token in ("要不要", "该不该", "会不会", "能不能")):
        dimensions.append("action_menu_pull")
    trigger = str(candidate.get("trigger_type") or "")
    if trigger in {"system_rule", "resource_crisis", "family_pressure", "survival_tradeoff"}:
        dimensions.append("generic_theme")
    if trigger in {"system_rule", "nonsense_or_overpowered_break"}:
        dimensions.append("system_mechanism_pull")
    if same_episode_gold:
        dimensions.append("not_episode_best")
        if focus == "framing_quality":
            dimensions.append("legacy_framing_rejected")
    if len(str(candidate.get("evidence_excerpt") or "")) < 40:
        dimensions.append("weak_evidence_excerpt")
    return unique(dimensions)


def reject_reason_for(candidate: dict[str, Any], *, focus: str, same_episode_gold: bool) -> str:
    hook = str(candidate.get("hook") or "")
    trigger = str(candidate.get("trigger_type") or "")
    if focus == "framing_quality":
        return (
            f"Legacy miner phrased this as `{hook}` under {trigger}; the source beat may be useful, "
            "but this framing teaches the rejected action-menu/RPG surface."
        )
    if same_episode_gold:
        return "Same episode already has a stronger owner/proposed best window; this should not be promoted just for coverage."
    return f"High legacy score came from {trigger}, but the candidate still needs a concrete viewer line rather than mechanism coverage."


def add_window_reviews(items: list[dict[str, Any]]) -> None:
    by_episode: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_episode.setdefault(str(item["episode_id"]), []).append(item)
    for item in items:
        item["window_review"] = build_window_review(item, by_episode.get(str(item["episode_id"]), []))


def build_window_review(item: dict[str, Any], same_episode_items: list[dict[str, Any]]) -> dict[str, Any]:
    item_id = str(item["item_id"])
    decision = "unreviewed"
    decision_source = "unreviewed"
    episode_rank = "unranked"
    reason = "Explicit window-level owner review is still pending; prior feedback may only cover context comprehension or copy taste."
    needs_video_review = True

    if item["label"] == "gold" and item["source_origin"] == "owner_seed":
        decision = "accepted_best"
        decision_source = "owner_seed"
        episode_rank = "best"
        reason = "Owner supplied this as the episode-level gold window for taste calibration."
        needs_video_review = False
    elif item_id in OWNER_PHASE15_SELECTED_BY_ITEM:
        decision = "accepted_best"
        decision_source = "owner_episode_review"
        episode_rank = "best"
        reason = "Owner selected this candidate as the episode gold window in phase 1.5; displayed competitors did not beat it."
        needs_video_review = False
    elif item_id in OWNER_PHASE15_REJECTED_BY_ITEM:
        review = OWNER_PHASE15_REJECTED_BY_ITEM[item_id]
        selected_id = str(review["selected_item_id"])
        decision = "rejected_framing" if item["evaluation_focus"] == "framing_quality" else "rejected_window"
        decision_source = "owner_episode_review"
        episode_rank = "not_best"
        prior_reason = str(item.get("reject_reason") or "No prior reject reason.")
        reason = (
            f"Owner selected {selected_id} as the episode gold window in phase 1.5; "
            f"this displayed competitor was rejected. Prior reason: {prior_reason}"
        )
        needs_video_review = False
    elif item_id == "taste_negative_huangnian_ep12_skip_context":
        decision = "context_insufficient"
        decision_source = "owner_context_review"
        episode_rank = "not_best"
        reason = "Owner could not confidently cut EP12 from available context; keep it as a skip/context-insufficient boundary until better context exists."
        needs_video_review = True
    elif item["label"] == "hard_negative":
        decision = "rejected_framing" if item["evaluation_focus"] == "framing_quality" else "rejected_window"
        decision_source = "agent_labeled"
        episode_rank = "not_best"
        reason = str(item.get("reject_reason") or "Agent-labeled hard negative for window taste calibration.")
        needs_video_review = item.get("nomination_role") in {"near_miss", "skip_candidate"}

    competitors = [
        str(candidate["item_id"])
        for candidate in same_episode_items
        if candidate["item_id"] != item_id and candidate["label"] == "hard_negative"
    ][:6]
    if item["label"] == "hard_negative":
        competitors = [
            str(candidate["item_id"])
            for candidate in same_episode_items
            if candidate["item_id"] != item_id and candidate["label"] == "gold"
        ][:6]

    return {
        "review_version": "window_review.v0.1",
        "decision": decision,
        "decision_source": decision_source,
        "episode_rank": episode_rank,
        "reason": reason,
        "needs_video_review": bool(needs_video_review),
        "competing_candidate_ids": competitors,
        "owner_review_prompt": DEFAULT_WINDOW_REVIEW_PROMPT,
    }


def append_note(current: str, note: str) -> str:
    if not current:
        return note
    if note in current:
        return current
    return f"{current} {note}"


def interaction_window(anchor_ms: int) -> dict[str, int]:
    return {"start_ms": anchor_ms, "end_ms": anchor_ms + 10000, "duration_ms": 10000}


def lookup_excerpt(windows: dict[str, dict[str, Any]], episode_id: str, start_ms: int, end_ms: int) -> str:
    for window in windows.values():
        if window.get("episode_id") == episode_id and int(window.get("start_ms") or -1) == start_ms:
            return compact_text(str(window.get("transcript_text") or "source transcript unavailable"))
    for window in windows.values():
        if window.get("episode_id") != episode_id:
            continue
        window_start = int(window.get("start_ms") or 0)
        window_end = int(window.get("end_ms") or 0)
        if window_start <= start_ms < window_end or start_ms <= window_start < end_ms:
            return compact_text(str(window.get("transcript_text") or "source transcript unavailable"))
    return "source transcript unavailable in local first-pass windows"


def source_ref_for_window(episode_id: str, start_ms: int) -> str:
    return f"{episode_id}_w{start_ms // 20000 + 1:03d}"


def load_windows(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = read_json(path)
    return {
        str(item.get("window_id")): item
        for item in data.get("windows", [])
        if isinstance(item, dict) and item.get("window_id")
    }


def load_candidates(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = read_json(path)
    return [item for item in data.get("candidates", []) if isinstance(item, dict)]


def write_review_tray(path: Path, dataset: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    items = dataset["items"]
    gold_review = [item for item in items if item["label"] == "gold"]
    priority_negatives = [
        item
        for item in items
        if item["label"] == "hard_negative"
        and (
            item["nomination_role"] in {"skip_candidate", "near_miss"}
            or "action_menu_pull" in item["reject_dimensions"]
        )
    ][:25]
    cards = gold_review + priority_negatives
    body = "\n".join(
        render_context_card(item, index=index, total=len(cards))
        for index, item in enumerate(cards, start=1)
    )
    path.write_text(
        f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Deadman Context Card Review v0.2</title>
  <style>
    :root {{ color-scheme: light; --ink:#241f1a; --muted:#6f655b; --paper:#fffdf8; --line:#ddd0c1; --gold:#fff0b8; --bad:#f3d1ca; --green:#dbeedb; --blue:#dce9f7; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; background: #f5f1ea; color: var(--ink); }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 28px 18px 52px; }}
    h1 {{ font-size: 26px; margin: 0 0 8px; letter-spacing: 0; }}
    h2 {{ font-size: 20px; margin: 14px 0 6px; letter-spacing: 0; }}
    h3 {{ font-size: 14px; margin: 0 0 7px; color: #5d5148; letter-spacing: 0; }}
    p {{ line-height: 1.56; margin: 8px 0; }}
    .meta {{ color: var(--muted); margin-bottom: 18px; line-height: 1.5; }}
    .toolbar {{ background:#ebe2d6; border:1px solid var(--line); border-radius:8px; padding:10px 12px; margin-bottom:20px; }}
    .card {{ background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 16px; margin: 16px 0; box-shadow: 0 1px 2px rgba(54, 39, 22, 0.05); }}
    .card-head {{ display:flex; justify-content:space-between; gap:12px; align-items:flex-start; margin-bottom:10px; }}
    .card-title {{ font-size:18px; font-weight:800; line-height:1.25; }}
    .card-id {{ color:var(--muted); font-size:12px; text-align:right; word-break:break-all; max-width:420px; }}
    .row {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
    .pill {{ font-size: 12px; padding: 3px 8px; border-radius: 999px; background: #eee4d7; color: #574c42; white-space: nowrap; }}
    .gold {{ background: var(--gold); }}
    .neg {{ background: var(--bad); }}
    .review {{ background: var(--green); }}
    .ready {{ background: var(--blue); }}
    .grid {{ display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }}
    .panel {{ border:1px solid #e4d8ca; border-radius:8px; padding:11px; background:#fffbf3; }}
    .panel.full {{ grid-column: 1 / -1; }}
    .asr {{ display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:10px; margin-top:12px; }}
    .asr .panel {{ background:#f3eee7; }}
    .line {{ font-size: 17px; font-weight: 700; }}
    .small {{ color: var(--muted); font-size: 13px; }}
    details {{ border:1px dashed #d5c5b5; border-radius:8px; padding:8px 10px; margin-top:10px; background:#fff8ed; }}
    summary {{ cursor:pointer; font-size:13px; color:#5d5148; font-weight:700; }}
    .review-actions {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:13px; }}
    .action {{ border:1px solid #d2c3b5; border-radius:8px; padding:8px 10px; background:#fff; font-size:13px; }}
    @media (max-width: 760px) {{ .grid, .asr {{ grid-template-columns: 1fr; }} main {{ padding:20px 12px 36px; }} }}
  </style>
</head>
<body>
<main>
  <h1>Context Card Review v0.2</h1>
  <div class=\"meta\">目标不是让你回视频补脑，而是验证卡片本身是否足够让人理解情景。若卡片看不懂，标记为 context_insufficient，不能进 Agent authoring。</div>
  <div class=\"toolbar\">前 10 张是 gold / proposed gold；当前优先审未定的 EP10、EP14、EP17。每张卡顶部都有编号、EP、时间和 item id。</div>
  {body}
</main>
</body>
</html>
""",
        encoding="utf-8",
    )


def write_window_review_tray(path: Path, dataset: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    items = dataset["items"]
    groups = window_review_groups(items)
    nav = render_window_review_nav(groups)
    body = "\n".join(
        render_window_review_group(group, is_active=index == 0)
        for index, group in enumerate(groups)
    )
    pending = len(
        [
            item
            for item in items
            if item["label"] == "gold" and item["window_review"]["decision"] == "unreviewed"
        ]
    )
    owner_best = len(
        [
            item
            for item in items
            if item["window_review"]["decision"] == "accepted_best"
            and item["window_review"]["decision_source"] == "owner_seed"
        ]
    )
    owner_context_negatives = len(
        [
            item
            for item in items
            if item["window_review"]["decision_source"] == "owner_context_review"
            and item["label"] == "hard_negative"
        ]
    )
    visible_card_count = sum(len(group["candidates"]) for group in groups)
    path.write_text(
        f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Deadman Window Review Phase 1.5</title>
  <style>
    :root {{ color-scheme: light; --ink:#231f1a; --muted:#6d635a; --paper:#fffdf8; --line:#dccfbe; --accent:#e8f2ff; --ok:#ddf0d7; --warn:#fff0b8; --bad:#f4d5cf; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; background:#f4efe7; color:var(--ink); }}
    main {{ max-width: 1120px; margin:0 auto; padding:28px 18px 52px; }}
    h1 {{ font-size:26px; margin:0 0 8px; letter-spacing:0; }}
    h2 {{ font-size:20px; margin:12px 0 8px; letter-spacing:0; }}
    h3 {{ font-size:14px; margin:0 0 6px; color:#574d43; letter-spacing:0; }}
    p {{ line-height:1.55; margin:7px 0; }}
    .meta, .small {{ color:var(--muted); font-size:13px; line-height:1.5; }}
    .toolbar {{ border:1px solid var(--line); background:#ebe2d6; border-radius:8px; padding:12px; margin:18px 0; }}
    .tabs {{ position:sticky; top:0; z-index:5; display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:8px; padding:10px 0; background:#f4efe7; border-bottom:1px solid var(--line); }}
    .tab {{ border:1px solid #d1c2b2; border-radius:8px; background:#fffaf1; color:var(--ink); padding:10px 9px; text-align:left; cursor:pointer; font:inherit; min-height:66px; }}
    .tab strong {{ display:block; font-size:14px; margin-bottom:3px; }}
    .tab span {{ display:block; color:var(--muted); font-size:12px; line-height:1.35; }}
    .tab.is-active {{ background:#231f1a; color:#fffdf8; border-color:#231f1a; }}
    .tab.is-active span {{ color:#e9ddcf; }}
    .review-page {{ display:none; }}
    .review-page.is-active {{ display:block; }}
    .page-head {{ border:1px solid var(--line); background:#fffdf8; border-radius:8px; padding:12px; margin:16px 0 10px; }}
    .page-head h2 {{ margin:0 0 4px; }}
    .episode-grid {{ display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px; margin-top:12px; }}
    .candidate-list {{ display:grid; gap:12px; margin-top:14px; }}
    .candidate-card {{ background:var(--paper); border:1px solid var(--line); border-radius:8px; padding:14px; box-shadow:0 1px 2px rgba(54,39,22,.05); }}
    .candidate-card.is-selected {{ border-color:#231f1a; box-shadow:0 0 0 2px #231f1a inset; }}
    .candidate-head {{ display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }}
    .candidate-title {{ font-size:17px; font-weight:800; line-height:1.25; }}
    .candidate-id {{ color:var(--muted); font-size:12px; text-align:right; max-width:420px; word-break:break-all; }}
    .row {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-top:10px; }}
    .pill {{ font-size:12px; padding:3px 8px; border-radius:999px; background:#eee4d7; color:#53483f; white-space:nowrap; }}
    .pill.ok {{ background:var(--ok); }}
    .pill.warn {{ background:var(--warn); }}
    .pill.bad {{ background:var(--bad); }}
    .pill.accent {{ background:var(--accent); }}
    .grid {{ display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px; margin-top:12px; }}
    .panel {{ border:1px solid #e3d7c8; border-radius:8px; background:#fffaf1; padding:11px; }}
    .panel.full {{ grid-column:1 / -1; }}
    .lead-hypothesis {{ border:1px solid #d2c3b5; border-radius:8px; background:#fff8df; padding:11px; margin-top:12px; }}
    .lead-hypothesis strong {{ display:block; font-size:13px; color:#574d43; margin-bottom:5px; }}
    .lead-hypothesis p {{ margin:0; font-size:16px; line-height:1.45; font-weight:700; }}
    .lead-hypothesis .small {{ margin-top:6px; }}
    .review-output {{ border:1px solid var(--line); background:#fffdf8; border-radius:8px; padding:12px; margin:14px 0; }}
    .review-output textarea {{ width:100%; min-height:120px; resize:vertical; border:1px solid #d4c6b7; border-radius:8px; padding:9px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:12px; background:#fffaf1; color:var(--ink); }}
    .output-actions {{ display:flex; flex-wrap:wrap; gap:8px; margin:8px 0; }}
    .output-actions button {{ border:1px solid #d1c2b2; border-radius:8px; background:#fff; padding:8px 10px; cursor:pointer; }}
    .episode-actions {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }}
    .select-window, .select-none {{ border:1px solid #d4c6b7; border-radius:8px; background:#fff; color:var(--ink); padding:9px 10px; font:inherit; text-align:left; cursor:pointer; font-size:13px; }}
    .select-window.is-selected, .select-none.is-selected {{ border-color:#231f1a; background:#231f1a; color:#fffdf8; }}
    .selection-state {{ margin-top:8px; color:var(--muted); font-size:13px; }}
    ul {{ padding-left:18px; margin:7px 0; }}
    li {{ margin:4px 0; line-height:1.45; }}
    @media (max-width: 760px) {{ main {{ padding:20px 12px 36px; }} .tabs, .episode-grid, .grid {{ grid-template-columns:1fr; }} .tabs {{ position:static; }} }}
  </style>
</head>
<body>
<main>
  <h1>Window Review Phase 1.5</h1>
  <div class=\"meta\">按集审：先看这一集的剧情/关系上下文，再在候选 window 里选一个作为 gold；也可以选“本集不选”。本页同时看开窗假设是否自然，但不审三条回复或后续回声。</div>
  <div class=\"toolbar\">
    当前 owner-seed best：{owner_best}；待显式 window review 的 proposed gold：{pending}；owner context-insufficient negative：{owner_context_negatives}。<br />
    默认按 EP 分页。每集候选里选一个，则该候选成为本集 gold、其他候选成为 reject；选“本集不选”则本页候选都 reject。当前可见候选 {visible_card_count} 个。
    <div class=\"small\">原 Context Card 页：<a href=\"index.html\">index.html</a></div>
  </div>
  {nav}
  <div class=\"review-output\">
    <strong>Review JSON</strong>
    <div class=\"small\">每集选择一个 window 或选择本集不选后，这里会自动更新。静态 file 页面不能直接写回 repo；把这段 JSON 发给我，我再写进 dataset。</div>
    <div class=\"output-actions\">
      <button type=\"button\" id=\"copy-review-json\">复制 JSON</button>
      <button type=\"button\" id=\"download-review-json\">下载 JSON</button>
      <button type=\"button\" id=\"clear-review-json\">清空选择</button>
      <span class=\"small\" id=\"review-json-status\">0 selections</span>
    </div>
    <textarea id=\"review-json-output\" readonly></textarea>
  </div>
  {body}
</main>
<script>
(() => {{
  const tabs = Array.from(document.querySelectorAll('[data-page-target]'));
  const pages = Array.from(document.querySelectorAll('[data-page]'));
  const candidateCards = Array.from(document.querySelectorAll('[data-candidate-id]'));
  const output = document.getElementById('review-json-output');
  const status = document.getElementById('review-json-status');
  const storageKey = 'deadman.episode_window_review.owner_choices.v0.2';
  let choices = loadChoices();

  function show(pageId, updateHash = true) {{
    for (const page of pages) page.classList.toggle('is-active', page.dataset.page === pageId);
    for (const tab of tabs) tab.classList.toggle('is-active', tab.dataset.pageTarget === pageId);
    if (updateHash) history.replaceState(null, '', '#' + pageId);
  }}
  function loadChoices() {{
    try {{
      const parsed = JSON.parse(localStorage.getItem(storageKey) || '{{}}');
      return parsed && typeof parsed === 'object' ? parsed : {{}};
    }} catch (_error) {{
      return {{}};
    }}
  }}
  function saveChoices() {{
    localStorage.setItem(storageKey, JSON.stringify(choices));
  }}
  function reviewPayload() {{
    const entries = Object.entries(choices)
      .map(([episodeId, value]) => {{
        const page = document.querySelector(`[data-episode-id="${{CSS.escape(episodeId)}}"]`);
        const candidateIds = (page?.dataset.candidateIds || '').split(',').filter(Boolean);
        const selectedItemId = value.selected_item_id || null;
        return {{
        episode_id: episodeId,
        selected_item_id: selectedItemId,
        decision: selectedItemId ? 'selected_gold' : 'select_none',
        rejected_item_ids: candidateIds.filter((itemId) => itemId !== selectedItemId),
        selected_at: value.selected_at,
        source: 'owner_episode_local_html',
        }};
      }})
      .sort((left, right) => left.episode_id.localeCompare(right.episode_id));
    return {{
      schema_version: 'episode_window_review_owner_choices.v0.1',
      product: '看剧搭子',
      generated_from: 'local_artifacts/window_taste_review/window_review.html',
      exported_at: new Date().toISOString(),
      episode_reviews: entries,
    }};
  }}
  function refreshPage(page) {{
    const episodeId = page.dataset.episodeId;
    const selectedItemId = choices[episodeId]?.selected_item_id || null;
    const hasChoice = Object.prototype.hasOwnProperty.call(choices, episodeId);
    for (const card of page.querySelectorAll('[data-candidate-id]')) {{
      const isSelected = selectedItemId && card.dataset.candidateId === selectedItemId;
      card.classList.toggle('is-selected', Boolean(isSelected));
      const button = card.querySelector('[data-select-window]');
      if (button) button.classList.toggle('is-selected', Boolean(isSelected));
    }}
    const noneButton = page.querySelector('[data-select-none]');
    if (noneButton) noneButton.classList.toggle('is-selected', hasChoice && selectedItemId === null);
    const state = page.querySelector('[data-selection-state]');
    if (state) {{
      if (!hasChoice) {{
        state.textContent = '本集未选择';
      }} else if (selectedItemId) {{
        state.textContent = `本集已选：${{selectedItemId}}`;
      }} else {{
        state.textContent = '本集不选：本页候选都进入 reject';
      }}
    }}
  }}
  function refreshOutput() {{
    const payload = reviewPayload();
    output.value = JSON.stringify(payload, null, 2);
    status.textContent = `${{payload.episode_reviews.length}} / ${{pages.length}} episodes`;
    for (const page of pages) refreshPage(page);
  }}
  async function copyOutput() {{
    try {{
      await navigator.clipboard.writeText(output.value);
      status.textContent = `${{reviewPayload().episode_reviews.length}} / ${{pages.length}} episodes · copied`;
    }} catch (_error) {{
      output.focus();
      output.select();
      status.textContent = '复制失败，手动选中文本复制';
    }}
  }}
  function downloadOutput() {{
    const blob = new Blob([output.value + '\\n'], {{ type: 'application/json' }});
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'episode_window_review_owner_choices.v0.1.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
  }}
  const hash = location.hash ? location.hash.slice(1) : '';
  const initial = pages.some((page) => page.dataset.page === hash) ? hash : pages[0]?.dataset.page || '';
  for (const tab of tabs) {{
    tab.addEventListener('click', () => show(tab.dataset.pageTarget || initial));
  }}
  for (const card of candidateCards) {{
    const button = card.querySelector('[data-select-window]');
    if (button) {{
      button.addEventListener('click', () => {{
        const page = card.closest('[data-episode-id]');
        choices[page.dataset.episodeId] = {{
          selected_item_id: card.dataset.candidateId,
          selected_at: new Date().toISOString(),
        }};
        saveChoices();
        refreshOutput();
      }});
    }}
  }}
  for (const button of document.querySelectorAll('[data-select-none]')) {{
    button.addEventListener('click', () => {{
      const page = button.closest('[data-episode-id]');
      choices[page.dataset.episodeId] = {{
        selected_item_id: null,
        selected_at: new Date().toISOString(),
      }};
      saveChoices();
      refreshOutput();
    }});
  }}
  document.getElementById('copy-review-json')?.addEventListener('click', copyOutput);
  document.getElementById('download-review-json')?.addEventListener('click', downloadOutput);
  document.getElementById('clear-review-json')?.addEventListener('click', () => {{
    choices = {{}};
    saveChoices();
    refreshOutput();
  }});
  show(initial, false);
  refreshOutput();
}})();
</script>
</body>
</html>
""",
        encoding="utf-8",
    )


def window_review_groups(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(item["item_id"]): item for item in items}
    proposed_or_reviewed = [
        item
        for item in items
        if item["label"] == "gold"
        and item["source_origin"] == "agent_proposed"
        and item["window_review"]["decision_source"] in {"unreviewed", "owner_episode_review"}
    ]
    groups: list[dict[str, Any]] = []
    for item in sorted(proposed_or_reviewed, key=lambda value: (str(value["episode_id"]), int(value["anchor_ms"]))):
        candidates = [item]
        for candidate_id in item["window_review"].get("competing_candidate_ids", []):
            candidate = by_id.get(str(candidate_id))
            if candidate:
                candidates.append(candidate)
        candidates = unique_items(candidates)
        card = item["context_card"]
        episode_label = episode_label_for(item)
        groups.append(
            {
                "page_id": str(item["episode_id"]).replace("huangnian_", ""),
                "episode_id": str(item["episode_id"]),
                "title": f"{episode_label} · 本集候选",
                "short_title": episode_label,
                "description": "先判断这一集要不要搭子冒出来；如果要，只选一个最好的 window。",
                "episode_context": card["episode_context"],
                "scene_function": card["scene_function"],
                "relationship_state": card["character_relationship_state"],
                "dependency_note": card["dependency_note"],
                "primary_item_id": item["item_id"],
                "candidates": candidates,
            }
        )
    return groups


def render_window_review_nav(groups: list[dict[str, Any]]) -> str:
    buttons = []
    for index, group in enumerate(groups):
        active = " is-active" if index == 0 else ""
        buttons.append(
            f"<button class=\"tab{active}\" type=\"button\" data-page-target=\"{html.escape(str(group['page_id']))}\">"
            f"<strong>{html.escape(str(group['short_title']))}</strong>"
            f"<span>{len(group['candidates'])} candidates</span>"
            f"</button>"
        )
    return f"<nav class=\"tabs\" aria-label=\"Window review pages\">{''.join(buttons)}</nav>"


def render_window_review_group(group: dict[str, Any], *, is_active: bool = False) -> str:
    page_id = str(group["page_id"])
    candidates = list(group["candidates"])
    candidate_ids = ",".join(str(item["item_id"]) for item in candidates)
    card_html = "\n".join(
        render_window_review_candidate(item, index=index, total=len(candidates))
        for index, item in enumerate(candidates, start=1)
    )
    if not card_html:
        card_html = "<p class=\"small\">这一集当前没有候选。</p>"
    active = " is-active" if is_active else ""
    return f"""
<section class=\"review-page{active}\" data-page=\"{html.escape(page_id)}\" id=\"{html.escape(page_id)}\" data-episode-id=\"{html.escape(str(group["episode_id"]))}\" data-candidate-ids=\"{html.escape(candidate_ids)}\">
  <div class=\"page-head\">
    <h2>{html.escape(str(group["title"]))}</h2>
    <p class=\"small\">{html.escape(str(group["description"]))}</p>
    <div class=\"episode-grid\">
      {render_panel("本集剧情/上下文", str(group["episode_context"]))}
      {render_panel("角色/关系状态", str(group["relationship_state"]))}
      {render_panel("当前剧本功能", str(group["scene_function"]))}
      {render_panel("依赖判断", str(group["dependency_note"]))}
    </div>
    <div class=\"episode-actions\">
      <button class=\"select-none\" type=\"button\" data-select-none>本集不选 window</button>
      <span class=\"selection-state\" data-selection-state>本集未选择</span>
    </div>
  </div>
  <div class=\"candidate-list\">
  {card_html}
  </div>
</section>
"""


def window_review_queue(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for group in window_review_groups(items):
        result.extend(group["candidates"])
    return result


def render_window_review_candidate(item: dict[str, Any], *, index: int, total: int) -> str:
    review = item["window_review"]
    card = item["context_card"]
    opening_hypothesis = opening_hypothesis_for_window_review(item)
    episode_label = episode_label_for(item)
    time_label = f"{format_time(item['interaction_window']['start_ms'])}-{format_time(item['interaction_window']['end_ms'])}"
    decision_class = "ok" if review["decision"] == "accepted_best" else "bad" if review["decision"].startswith("rejected") else "warn"
    video_class = "warn" if review["needs_video_review"] else "ok"
    reject = render_optional_panel("Reject reason", item["reject_reason"]) if item["reject_reason"] else ""
    return f"""
<article class=\"candidate-card\" id=\"{html.escape(anchor_id(str(item['item_id'])))}\" data-candidate-id=\"{html.escape(str(item['item_id']))}\">
  <div class=\"candidate-head\">
    <div>
      <div class=\"candidate-title\">候选 #{index:02d}/{total:02d} · {html.escape(episode_label)} · {html.escape(time_label)}</div>
      <div class=\"small\">{html.escape(item['label'])} / {html.escape(item['source_origin'])} / {html.escape(item['nomination_role'])}</div>
    </div>
    <div class=\"candidate-id\">{html.escape(item['item_id'])}</div>
  </div>
  <div class=\"row\">
    <span class=\"pill {decision_class}\">{html.escape(review['decision'])}</span>
    <span class=\"pill accent\">source: {html.escape(review['decision_source'])}</span>
    <span class=\"pill\">rank: {html.escape(review['episode_rank'])}</span>
    <span class=\"pill {video_class}\">video review: {html.escape(str(review['needs_video_review']).lower())}</span>
    <span class=\"pill\">{html.escape(episode_label)}</span>
  </div>
  <div class=\"lead-hypothesis\">
    <strong>开窗假设：搭子此刻可能先接一句</strong>
    <p>{html.escape(opening_hypothesis)}</p>
    <div class=\"small\">用来判断这个 window 有没有“嘴边一句压力”；不是最终发布 lead。</div>
  </div>
  <div class=\"grid\">
    {render_panel("窗内发生（ASR）", card["adjacent_asr"]["current"])}
    {render_panel("为什么可能开窗", item["why_now"])}
    {render_panel("窗口剧本功能", card["scene_function"])}
    {render_panel("当前判定/风险", review["reason"])}
    {reject}
  </div>
  <button class=\"select-window\" type=\"button\" data-select-window>选这个 window</button>
</article>
"""


def opening_hypothesis_for_window_review(item: dict[str, Any]) -> str:
    card = item["context_card"]
    seed = card.get("authoring_seed") if isinstance(card, dict) else None
    if isinstance(seed, dict):
        lead_seed = str(seed.get("companion_lead_seed") or "").strip()
        if lead_seed:
            return lead_seed
    return str(card.get("mouthpiece_pressure") or item.get("viewer_line_pressure") or "").strip()


def unique_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        item_id = str(item["item_id"])
        if item_id in seen:
            continue
        seen.add(item_id)
        result.append(item)
    return result


def episode_label_for(item: dict[str, Any]) -> str:
    return str(item["episode_id"]).replace("huangnian_ep", "EP")


def anchor_id(value: str) -> str:
    return "item-" + re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")


def add_context_cards(items: list[dict[str, Any]], windows: dict[str, dict[str, Any]]) -> None:
    by_episode = windows_by_episode(windows)
    for item in items:
        item["context_card"] = build_context_card(item, by_episode)


def build_context_card(item: dict[str, Any], by_episode: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    item_id = str(item["item_id"])
    override = CONTEXT_CARD_OVERRIDES.get(item_id, {})
    owner_review = OWNER_REVIEW_OVERRIDES.get(item_id, {})
    adjacent = adjacent_asr_for_item(item, by_episode)
    is_gold = item["label"] == "gold"
    readiness = "negative_training_only"
    if item["review_status"] == "owner_confirmed":
        readiness = "owner_confirmed"
    elif item["review_status"] == "proposed_for_owner_review":
        readiness = "needs_owner_review"
    elif "context_insufficient" in item.get("reject_dimensions", []):
        readiness = "context_insufficient"
    episode_context = override.get("episode_context") or infer_episode_context(item, adjacent)
    scene_function = override.get("scene_function") or infer_scene_function(item)
    relationship_state = override.get("character_relationship_state") or infer_relationship_state(item)
    dependency_note = override.get("dependency_note") or infer_dependency_note(item)
    review_prompt = (
        "只看这张卡：你能不能 get 到这段？能且对味=understood_gold；能但不对味=understood_wrong_taste；看不懂=context_insufficient。"
        if is_gold
        else "只看这张卡：这个负例边界是否清楚？如果不清楚，补 context 或改 reject reason。"
    )
    owner_review_outcome = str(owner_review.get("owner_review_outcome") or "")
    if not owner_review_outcome and item["review_status"] == "owner_confirmed":
        owner_review_outcome = "understood_gold"
    if not owner_review_outcome:
        owner_review_outcome = "unreviewed"
    if "context_insufficient" in item.get("reject_dimensions", []):
        owner_review_outcome = "context_insufficient"
    authoring_seed = build_authoring_seed(item, override=owner_review.get("authoring_seed"))
    return {
        "card_version": "context_card.v0.2",
        "episode_context": episode_context,
        "scene_function": scene_function,
        "adjacent_asr": adjacent,
        "character_relationship_state": relationship_state,
        "mouthpiece_pressure": str(item["viewer_line_pressure"]),
        "dependency_note": dependency_note,
        "owner_review_prompt": review_prompt,
        "owner_review_outcome": owner_review_outcome,
        "agent_input_readiness": readiness,
        "authoring_seed": authoring_seed,
    }


def build_authoring_seed(item: dict[str, Any], *, override: Any = None) -> dict[str, Any]:
    if isinstance(override, dict):
        return {
            "seed_version": "authoring_seed.v0.1",
            "applicability": "authoring_reference",
            "companion_lead_seed": str(override.get("companion_lead_seed") or ""),
            "lead_style_policy": str(override.get("lead_style_policy") or DEFAULT_LEAD_STYLE_POLICY),
            "reply_set_policy": str(override.get("reply_set_policy") or DEFAULT_REPLY_SET_POLICY),
            "viewer_stance_policy": str(override.get("viewer_stance_policy") or DEFAULT_VIEWER_STANCE_POLICY),
            "reply_candidate_seeds": normalize_reply_seed_list(override.get("reply_candidate_seeds")),
            "response_tone_policy": str(override.get("response_tone_policy") or ""),
            "preset_echo_policy": str(override.get("preset_echo_policy") or DEFAULT_PRESET_ECHO_POLICY),
            "custom_reply_policy_hint": str(override.get("custom_reply_policy_hint") or ""),
            "rejected_lead_examples": normalize_rejected_examples(override.get("rejected_lead_examples")),
            "rejected_reply_examples": normalize_rejected_reply_examples(override.get("rejected_reply_examples")),
            "blocked_claims_hint": [
                str(value)
                for value in override.get("blocked_claims_hint", [])
                if isinstance(value, str)
            ],
        }
    if item["label"] == "gold":
        axes = [str(value) for value in item.get("expected_reply_axes", []) if isinstance(value, str)]
        return {
            "seed_version": "authoring_seed.v0.1",
            "applicability": "authoring_reference",
            "companion_lead_seed": str(item.get("viewer_line_pressure") or ""),
            "lead_style_policy": DEFAULT_LEAD_STYLE_POLICY,
            "reply_set_policy": DEFAULT_REPLY_SET_POLICY,
            "viewer_stance_policy": DEFAULT_VIEWER_STANCE_POLICY,
            "reply_candidate_seeds": [
                {
                    "display_text": axis,
                    "emotion_role": axis,
                    "semantic_role": slugify(axis),
                    "intent_note": f"Draft reply axis from taste eval: {axis}",
                }
                for axis in axes[:3]
            ],
            "response_tone_policy": "Follow the context card; keep the companion voice short, friend-like, scene-specific, and non-explanatory.",
            "preset_echo_policy": DEFAULT_PRESET_ECHO_POLICY,
            "custom_reply_policy_hint": "Reflect user custom input only within this source window and the context-card dependency note.",
            "rejected_lead_examples": [],
            "rejected_reply_examples": [],
            "blocked_claims_hint": ["no future-episode claims", "no full branch rewrite", "no unsupported character motivation"],
        }
    return {
        "seed_version": "authoring_seed.v0.1",
        "applicability": "negative_boundary",
        "companion_lead_seed": "",
        "lead_style_policy": "Do not author a lead from this hard-negative item.",
        "reply_set_policy": "Do not author preset replies from this hard-negative item.",
        "viewer_stance_policy": "Use this item only to learn what does not belong in the viewer companion surface.",
        "reply_candidate_seeds": [],
        "response_tone_policy": "Do not author visible runtime copy from this hard-negative item.",
        "preset_echo_policy": "No preset echo should be published from this hard-negative item.",
        "custom_reply_policy_hint": "Use only as a rejection/boundary example.",
        "rejected_lead_examples": [],
        "rejected_reply_examples": [],
        "blocked_claims_hint": ["not a publishable companion exchange seed"],
    }


def normalize_reply_seed_list(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "display_text": str(item.get("display_text") or ""),
                "emotion_role": str(item.get("emotion_role") or ""),
                "semantic_role": str(item.get("semantic_role") or ""),
                "intent_note": str(item.get("intent_note") or ""),
            }
        )
    return normalized


def normalize_rejected_reply_examples(value: Any) -> list[dict[str, str]]:
    return normalize_rejected_examples(value)


def normalize_rejected_examples(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "display_text": str(item.get("display_text") or ""),
                "negative_type": str(item.get("negative_type") or ""),
                "reject_reason": str(item.get("reject_reason") or ""),
                "correction_hint": str(item.get("correction_hint") or ""),
            }
        )
    return normalized


def slugify(text: str) -> str:
    ascii_text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return ascii_text or f"axis_{digest}"


def adjacent_asr_for_item(item: dict[str, Any], by_episode: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    episode_windows = by_episode.get(str(item["episode_id"]), [])
    source = item["source_window"]
    source_start = int(source["start_ms"])
    current_index = 0
    for index, window in enumerate(episode_windows):
        start = int(window.get("start_ms") or 0)
        end = int(window.get("end_ms") or 0)
        if start <= source_start < end or start == source_start:
            current_index = index
            break
    before = episode_windows[current_index - 1] if current_index > 0 else None
    current = episode_windows[current_index] if episode_windows else None
    after = episode_windows[current_index + 1] if current_index + 1 < len(episode_windows) else None
    return {
        "before": compact_text(str((before or {}).get("transcript_text") or ""), max_length=420),
        "current": compact_text(str((current or {}).get("transcript_text") or source["evidence_excerpt"]), max_length=520),
        "after": compact_text(str((after or {}).get("transcript_text") or ""), max_length=420),
    }


def infer_episode_context(item: dict[str, Any], adjacent: dict[str, str]) -> str:
    before = adjacent.get("before") or "前一段 ASR 不足。"
    if item["label"] == "hard_negative":
        return f"{GLOBAL_STORY_CONTEXT} 这个候选来自旧 miner 或 near-miss，需要用上下文判断它是否只是机制命中。前一段：{before}"
    return f"{GLOBAL_STORY_CONTEXT} 当前候选需要从本集相邻 ASR 理解。前一段：{before}"


def infer_scene_function(item: dict[str, Any]) -> str:
    if item["label"] == "hard_negative":
        return SCENE_FUNCTION_BY_LABEL["hard_negative"]
    return SCENE_FUNCTION_BY_LABEL["gold"]


def infer_relationship_state(item: dict[str, Any]) -> str:
    text = " ".join(
        [
            str(item.get("why_now") or ""),
            str(item.get("viewer_line_pressure") or ""),
            str(item.get("source_window", {}).get("evidence_excerpt") or ""),
        ]
    )
    if any(token in text for token in ("四蛋", "孩子", "儿子", "儿媳", "怀孕")):
        return "家庭信任仍在修复中；孩子/儿媳会把程弯弯的新行为先和原主旧伤害对照。"
    if any(token in text for token in ("村", "围观", "婆婆", "阿奶", "娘家", "程家")):
        return "外部亲邻/村庄关系会放大原主旧口碑；公开场合的误会和羞辱会变成 reputation pressure。"
    if "系统" in text or "白米" in text or "商城" in text:
        return "主角有隐藏系统或资源优势，但家人和外人不能自然知道来源，解释成本本身就是压力。"
    return "关系状态需要人工补充；当前卡片只能提供局部 ASR。"


def infer_dependency_note(item: dict[str, Any]) -> str:
    if "context_insufficient" in item.get("reject_dimensions", []):
        return "context_insufficient；只看当前卡片不足以证明这是可发布搭子点。"
    if item["review_status"] == "proposed_for_owner_review":
        return "needs owner check；如果只看卡片仍不懂，就降级为 context_insufficient。"
    if item["evaluation_focus"] == "framing_quality":
        return "window may contain useful evidence, but legacy framing is rejected as action-menu/RPG wording."
    return "scene-local enough for draft calibration unless owner review says otherwise."


def windows_by_episode(windows: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for window in windows.values():
        grouped.setdefault(str(window.get("episode_id") or ""), []).append(window)
    for episode_windows in grouped.values():
        episode_windows.sort(key=lambda item: int(item.get("start_ms") or 0))
    return grouped


def render_context_card(item: dict[str, Any], *, index: int, total: int) -> str:
    label_class = "gold" if item["label"] == "gold" else "neg"
    review_class = "review" if item["review_status"] == "proposed_for_owner_review" else ""
    ready_class = "ready" if item["context_card"]["agent_input_readiness"] in {"owner_confirmed", "needs_owner_review"} else ""
    reject = render_optional_panel("Reject reason", item["reject_reason"]) if item["reject_reason"] else ""
    axes = ", ".join(item["expected_reply_axes"] or item["reject_dimensions"])
    card = item["context_card"]
    adjacent = card["adjacent_asr"]
    authoring = card["authoring_seed"]
    authoring_panel = render_authoring_seed(authoring) if authoring["applicability"] == "authoring_reference" else ""
    episode_label = str(item["episode_id"]).replace("huangnian_ep", "EP")
    time_label = f"{format_time(item['interaction_window']['start_ms'])}-{format_time(item['interaction_window']['end_ms'])}"
    return f"""
<section class=\"card\">
  <div class=\"card-head\">
    <div>
      <div class=\"card-title\">#{index:02d}/{total:02d} · {html.escape(episode_label)} · {html.escape(time_label)}</div>
      <div class=\"small\">{html.escape(item['label'])} / {html.escape(item['review_status'])} / {html.escape(card['owner_review_outcome'])}</div>
    </div>
    <div class=\"card-id\">{html.escape(item['item_id'])}</div>
  </div>
  <div class=\"row\">
    <span class=\"pill {label_class}\">{html.escape(item['label'])}</span>
    <span class=\"pill {review_class}\">{html.escape(item['review_status'])}</span>
    <span class=\"pill {ready_class}\">{html.escape(card['agent_input_readiness'])}</span>
    <span class=\"pill\">{html.escape(card['owner_review_outcome'])}</span>
    <span class=\"pill\">{html.escape(item['evaluation_focus'])}</span>
    <span class=\"pill\">{html.escape(episode_label)}</span>
    <span class=\"pill\">{html.escape(time_label)}</span>
  </div>
  <h2>{html.escape(card['mouthpiece_pressure'])}</h2>
  <p class=\"small\">{html.escape(card['owner_review_prompt'])}</p>
  <div class=\"grid\">
    {render_panel("本集上下文", card["episode_context"])}
    {render_panel("剧本功能", card["scene_function"])}
    {render_panel("角色/关系状态", card["character_relationship_state"])}
    {render_panel("为什么现在", item["why_now"])}
    {render_panel("依赖判断", card["dependency_note"], full=True)}
  </div>
  <div class=\"asr\">
    {render_panel("前一段 ASR", adjacent["before"] or "无")}
    {render_panel("当前证据", adjacent["current"])}
    {render_panel("后一段 ASR", adjacent["after"] or "无")}
  </div>
  <p class=\"small\"><strong>Axes:</strong> {html.escape(axes)}</p>
  {authoring_panel}
  {reject}
  <div class=\"review-actions\">
    <span class=\"action\">懂且对味：understood_gold</span>
    <span class=\"action\">懂但不对味：understood_wrong_taste</span>
    <span class=\"action\">看不懂：context_insufficient</span>
  </div>
</section>
"""


def render_authoring_seed(authoring: dict[str, Any]) -> str:
    replies = "".join(
        f"<li><strong>{html.escape(item['display_text'])}</strong><br><span class=\"small\">{html.escape(item['intent_note'])}</span></li>"
        for item in authoring.get("reply_candidate_seeds", [])
    )
    rejected_leads = "".join(
        f"<li><strong>{html.escape(item['display_text'])}</strong><br><span class=\"small\">{html.escape(item['reject_reason'])} {html.escape(item['correction_hint'])}</span></li>"
        for item in authoring.get("rejected_lead_examples", [])
    )
    rejected = "".join(
        f"<li><strong>{html.escape(item['display_text'])}</strong><br><span class=\"small\">{html.escape(item['reject_reason'])} {html.escape(item['correction_hint'])}</span></li>"
        for item in authoring.get("rejected_reply_examples", [])
    )
    rejected_lead_panel = f"<h4>Rejected lead examples</h4><ul>{rejected_leads}</ul>" if rejected_leads else ""
    rejected_panel = f"<h4>Rejected reply examples</h4><ul>{rejected}</ul>" if rejected else ""
    return f"""
  <div class=\"panel full\">
    <h3>Authoring seed（给 Studio/CAB 的生产参考）</h3>
    <p><strong>Lead:</strong> {html.escape(authoring.get('companion_lead_seed') or '')}</p>
    <ol>{replies}</ol>
    {rejected_lead_panel}
    {rejected_panel}
    <details>
      <summary>内部生产规则：Lead policy / Reply set / Viewer stance / Tone / Preset echo</summary>
      <p class=\"small\"><strong>Lead policy:</strong> {html.escape(authoring.get('lead_style_policy') or '')}</p>
      <p class=\"small\"><strong>Reply set:</strong> {html.escape(authoring.get('reply_set_policy') or '')}</p>
      <p class=\"small\"><strong>Viewer stance:</strong> {html.escape(authoring.get('viewer_stance_policy') or '')}</p>
      <p class=\"small\"><strong>Tone:</strong> {html.escape(authoring.get('response_tone_policy') or '')}</p>
      <p class=\"small\"><strong>Preset echo:</strong> {html.escape(authoring.get('preset_echo_policy') or '')}</p>
    </details>
  </div>
"""


def format_time(ms: int) -> str:
    total_seconds = max(0, int(ms) // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def render_panel(title: str, value: str, *, full: bool = False) -> str:
    class_name = "panel full" if full else "panel"
    return f"<div class=\"{class_name}\"><h3>{html.escape(title)}</h3><p>{html.escape(value)}</p></div>"


def render_optional_panel(title: str, value: str) -> str:
    return f"<div class=\"panel full\"><h3>{html.escape(title)}</h3><p>{html.escape(value)}</p></div>"


def compact_text(text: str, *, max_length: int = 320) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if len(cleaned) <= max_length else cleaned[: max_length - 1] + "…"


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


if __name__ == "__main__":
    raise SystemExit(main())
