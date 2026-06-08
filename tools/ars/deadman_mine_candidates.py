#!/usr/bin/env python3
"""Mine first-pass Deadman companion-exchange candidate nodes from timeline windows."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

try:
    from deadman_paths import find_deadman_root
except ModuleNotFoundError:
    from .deadman_paths import find_deadman_root
from typing import Any


REPO_ROOT = find_deadman_root(__file__)
DEFAULT_CANDIDATE_DIR = REPO_ROOT / "tmp/ars_huangnian_analysis/candidates"
WEIGHTS = {
    "emotion_heat": 0.25,
    "choice_leverage": 0.22,
    "world_constraint_value": 0.18,
    "causal_clarity": 0.15,
    "watch_flow_fit": 0.12,
    "visual_result_fit": 0.08,
}


RESOURCE_CO_OCCURRENCE_GROUPS: dict[str, list[str]] = {
    "hunger": ["饿", "饿死", "吃不上", "没吃", "吃不饱", "一年都没有", "好想吃", "不配上桌"],
    "scarcity": ["荒年", "灾荒", "余粮", "最后一点", "口粮", "发霉", "粟米", "粮袋"],
    "food_object": ["白米", "大米", "粟米", "野菜", "兔肉", "兔子", "鸡蛋", "萝卜", "小鹅菜", "肉", "饭", "糊糊"],
    "distribution": ["分", "拿出来", "给", "借粮", "送", "要吃的", "上桌", "没有我的份"],
    "exposure_or_pressure": ["哪来", "偷偷", "全村", "村", "阿奶", "婆婆", "娘家", "露富", "看见", "起疑"],
}


MECHANISMS: dict[str, dict[str, Any]] = {
    "resource_crisis": {
        "keywords": ["粮", "白米", "大米", "粟米", "野菜", "兔肉", "鸡蛋", "萝卜", "吃", "饿", "口粮", "肉"],
        "hook": "这口吃的压到眼前了。",
        "impulse": "我想说一句，先让眼前的人吃上东西。",
        "marker": "!",
    },
    "exposure_risk": {
        "keywords": ["哪来", "瞒", "怀璧其罪", "露富", "来源", "白米哪来的", "偷偷", "看见", "起疑"],
        "hook": "这份资源一露出来，风险也跟着来了。",
        "impulse": "我想说一句，别让底牌一下子摊光。",
        "marker": "!",
    },
    "family_pressure": {
        "keywords": ["娘", "儿子", "儿媳", "孩子", "大山", "二狗", "三牛", "四蛋", "慧娘", "阿奶", "婆婆", "怀孕"],
        "hook": "家里弱势的人先被压住了。",
        "impulse": "我想说一句，先把家里弱势的人护下来。",
        "marker": "?",
    },
    "village_pressure": {
        "keywords": ["村", "大家快来看", "邻居", "大嫂子", "借粮", "程家村", "全村", "乡亲"],
        "hook": "村里人围上来，这口气很难咽。",
        "impulse": "我想说一句，当场把话说清楚。",
        "marker": "!",
    },
    "humiliation_reversal": {
        "keywords": ["跪", "打", "欺负", "抢", "不配", "饿着", "报仇", "住手", "打死", "撒尿"],
        "hook": "这口气已经压到脸上了。",
        "impulse": "我想说一句，不能让对方继续欺负人。",
        "marker": "!",
    },
    "evidence_or_trap": {
        "keywords": ["偷", "算账", "赔", "抓", "绑", "证据", "账", "鸡", "兔子", "脚下穿过去"],
        "hook": "这笔账终于有机会摊开了。",
        "impulse": "我想说一句，抓住证据一次讲清楚。",
        "marker": "?",
    },
    "system_rule": {
        "keywords": ["系统", "商城", "是否售卖", "价值", "购买", "面板", "铜钱", "售卖"],
        "hook": "系统能力一出现，眼前的局面变了。",
        "impulse": "我想说一句，这张底牌不能乱用。",
        "marker": "?",
    },
    "survival_tradeoff": {
        "keywords": ["荒年", "饿死", "借粮", "发霉", "粟米", "粮袋", "分家", "灾荒", "余粮"],
        "hook": "活下去和不暴露压在同一刻。",
        "impulse": "我想说一句，先保命，再补解释。",
        "marker": "!",
    },
    "nonsense_or_overpowered_break": {
        "keywords": ["一百斤", "白米饭", "天天吃", "商城", "系统", "全拿", "太奢侈"],
        "hook": "这一步开太大，爽感和风险都冲上来了。",
        "impulse": "我想说一句，别一步把局面掀翻。",
        "marker": "?",
    },
    "hidden_power_rule": {
        "keywords": ["修为", "灵力", "仙", "神", "魔", "法术", "宗门", "师父", "灵根", "渡劫", "封印", "血脉", "天命", "妖", "魂", "禁制", "阵法"],
        "hook": "隐藏能力一亮，场面就收不回去了。",
        "impulse": "我想说一句，别把真实实力一下亮完。",
        "marker": "!",
    },
    "identity_reveal": {
        "keywords": ["身份", "认出", "真相", "隐瞒", "假扮", "原来", "亲生", "少主", "公主", "夫人", "少爷", "不是", "知道"],
        "hook": "真实身份压在嘴边，场面快变了。",
        "impulse": "我想说一句，身份这张牌不能乱摊。",
        "marker": "?",
    },
    "relationship_betrayal": {
        "keywords": ["离婚", "丈夫", "前夫", "小三", "出轨", "背叛", "怀孕", "第三者", "欺负", "净身出户", "抛弃", "羞辱", "滚出去"],
        "hook": "背叛和羞辱已经摆到眼前。",
        "impulse": "我想说一句，不能让背叛和羞辱轻轻过去。",
        "marker": "!",
    },
    "status_reversal": {
        "keywords": ["总裁", "江辞云", "夫人", "董事长", "合同", "协议", "结婚", "offer", "公司", "证据", "律师", "股份", "项目", "机会"],
        "hook": "这张底牌一出，身份和局面都会变。",
        "impulse": "我想说一句，这张牌不能随便打出去。",
        "marker": "!",
    },
    "medical_or_pregnancy_risk": {
        "keywords": ["怀孕", "孩子", "胎", "医院", "医生", "流产", "生病", "受伤", "救", "疼", "血", "药"],
        "hook": "人已经受伤，责任可以后算。",
        "impulse": "我想说一句，先保住人，再处理责任。",
        "marker": "!",
    },
}


OPTIONS: dict[str, list[str]] = {
    "resource_crisis": ["直接拿出来，让眼前的人先吃上", "少量拿出来，编一个能糊弄过去的来源", "先藏住，换成更不显眼的办法"],
    "exposure_risk": ["直接亮出来解决危机", "只露出一小部分，保住来源秘密", "先不亮底牌，换一个低风险解释"],
    "family_pressure": ["先护住家里人，再处理外部压力", "让家里人自己说清楚，主角托底", "暂时忍下，回家后再补偿"],
    "village_pressure": ["当场硬刚，让围观者站队", "拿事实说话，避免泼妇式互骂", "先退一步，保住后续谈判空间"],
    "humiliation_reversal": ["当场反击，把人打回去", "先救人，再用更稳的方式讨回公道", "忍一口气，等证据和见证人齐了再反打"],
    "evidence_or_trap": ["马上算账，逼对方承认", "先留证据，再把账摊开", "先救人/拿回东西，不扩大冲突"],
    "system_rule": ["马上使用系统换资源", "小规模试用，验证规则和风险", "暂时不用，先用常规办法遮掩"],
    "survival_tradeoff": ["先保命，风险后面再补", "只解决最低生存线，避免暴露", "继续忍一段，等更安全的机会"],
    "nonsense_or_overpowered_break": ["一步到位开大", "控制输出规模，不让世界观崩", "不用超规格能力，保留戏剧张力"],
    "hidden_power_rule": ["直接亮出真实实力压住局面", "只用一小部分能力，保住底牌", "暂时不用能力，先观察规则和代价"],
    "identity_reveal": ["当场摊牌身份", "只放出一点线索，让对方先露破绽", "继续隐瞒身份，换低风险处理方式"],
    "relationship_betrayal": ["当场撕破脸，不再给对方台阶", "先拿证据和安全，再反击", "暂时离场，保住自己和孩子的主动权"],
    "status_reversal": ["立刻打出身份/资源底牌", "只动用一部分资源，留后手", "先不亮底牌，让对方继续暴露"],
    "medical_or_pregnancy_risk": ["先救人，账之后再算", "一边救人一边固定证据", "先反击对方，再处理伤情"],
}


BASELINES: dict[str, dict[str, str]] = {
    "resource_crisis": {
        "original_action": "原剧情没有无条件把全部资源摊开。",
        "original_rationale": "荒年里资源来源解释不清，会带来亲戚、村民和外部窥探风险。",
        "audience_tension": "观众会想立刻让孩子和家人吃饱。",
        "note": "原剧情压住资源，是为了保住后续生存空间和来源秘密。",
    },
    "exposure_risk": {
        "original_action": "原剧情倾向于遮掩资源来源。",
        "original_rationale": "系统/白米/钱的来源一旦暴露，短期爽感会换成长线麻烦。",
        "audience_tension": "观众会想用主角优势直接解决局面。",
        "note": "不亮底牌不是拖，是在避免荒年露富。",
    },
    "family_pressure": {
        "original_action": "原剧情让主角逐步修复家人信任。",
        "original_rationale": "家人长期被原身伤害，突然转好需要可信过程。",
        "audience_tension": "观众会想马上把家人保护起来。",
        "note": "原剧情慢慢修复，是为了让家人相信变化是真的。",
    },
    "village_pressure": {
        "original_action": "原剧情没有把每次围观压力都升级成彻底决裂。",
        "original_rationale": "村庄关系会持续影响生存、名声和资源交换。",
        "audience_tension": "观众会想当场怼回去。",
        "note": "原剧情留余地，是为了避免村庄关系完全失控。",
    },
    "humiliation_reversal": {
        "original_action": "原剧情通常先把人救下或稳住局面，再反击。",
        "original_rationale": "纯爽感反击可能制造新的伤害或证据风险。",
        "audience_tension": "观众会想立刻出口恶气。",
        "note": "原剧情不一定软弱，而是在选择更稳的反打时机。",
    },
    "evidence_or_trap": {
        "original_action": "原剧情会让冲突进入算账或见证阶段。",
        "original_rationale": "有证据和围观者时，反击更不容易被倒打一耙。",
        "audience_tension": "观众会想马上抓住对方漏洞。",
        "note": "原剧情先攒证据，是为了让反击站得住。",
    },
    "system_rule": {
        "original_action": "原剧情先试探系统规则，再逐步使用。",
        "original_rationale": "系统收益高，但解释成本和暴露风险也高。",
        "audience_tension": "观众会想马上用系统开挂。",
        "note": "原剧情控制系统使用，是为了不让世界约束失效。",
    },
    "survival_tradeoff": {
        "original_action": "原剧情在保命和保密之间做折中。",
        "original_rationale": "灾荒环境里一次错误分配会影响全家后续生存。",
        "audience_tension": "观众会想先救眼前，再管以后。",
        "note": "原剧情折中，是因为荒年的每口粮都影响后续风险。",
    },
    "nonsense_or_overpowered_break": {
        "original_action": "原剧情没有让主角无限制开大。",
        "original_rationale": "过强能力会让原剧冲突和继续观看理由失效。",
        "audience_tension": "观众会想一把梭解决所有问题。",
        "note": "原剧情限制开大，是为了保住短剧冲突和观看流。",
    },
    "hidden_power_rule": {
        "original_action": "原剧情通常不会一次性暴露全部隐藏实力。",
        "original_rationale": "过早亮出能力会让敌我关系、世界规则和后续冲突失去张力。",
        "audience_tension": "观众会想让主角直接开大打脸。",
        "note": "原剧情压住能力，是为了保住隐藏身份、规则代价和后续反转。",
    },
    "identity_reveal": {
        "original_action": "原剧情通常让身份真相分阶段揭开。",
        "original_rationale": "一次性摊牌会减少误会、试探和反转空间。",
        "audience_tension": "观众会想马上让对方知道主角是谁。",
        "note": "原剧情不马上摊牌，是为了让对方继续暴露态度和把柄。",
    },
    "relationship_betrayal": {
        "original_action": "原剧情通常让主角先承受背叛或羞辱，再逐步反击。",
        "original_rationale": "证据、安全和新关系资源还未齐备时，硬撕可能让主角处境更差。",
        "audience_tension": "观众会想当场离开、反击或让渣方付出代价。",
        "note": "原剧情延迟反击，是为了让证据和情绪账一起滚大。",
    },
    "status_reversal": {
        "original_action": "原剧情不会每次都立刻打出新身份或资源底牌。",
        "original_rationale": "底牌过早打出会让后续打脸和关系推进变薄。",
        "audience_tension": "观众会想马上用新身份压回去。",
        "note": "原剧情保留底牌，是为了把羞辱、误判和反转攒到更有效的位置。",
    },
    "medical_or_pregnancy_risk": {
        "original_action": "原剧情通常会把救人、受伤和追责分开推进。",
        "original_rationale": "急救优先级、证据固定和情绪反击之间存在现实冲突。",
        "audience_tension": "观众会想立刻救人或立刻追责。",
        "note": "原剧情先后排序，是为了让人身风险和责任追究都站得住。",
    },
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def repo_relative(path: Path) -> str:
    resolved = resolve_path(path).resolve(strict=False)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def score_keywords(text: str, mechanism: str) -> int:
    if mechanism == "resource_crisis":
        return score_resource_crisis(text)
    keywords = MECHANISMS[mechanism]["keywords"]
    return sum(text.count(keyword) for keyword in keywords)


def score_resource_crisis(text: str) -> int:
    """Avoid treating a bare "吃" mention as resource scarcity."""
    group_hits = {
        group: sum(text.count(keyword) for keyword in keywords)
        for group, keywords in RESOURCE_CO_OCCURRENCE_GROUPS.items()
    }
    active_groups = [group for group, count in group_hits.items() if count > 0]
    if "food_object" not in active_groups and "hunger" not in active_groups and "scarcity" not in active_groups:
        return 0
    if len(active_groups) < 2:
        return 0
    return sum(group_hits.values())


def clamp(value: float) -> int:
    return int(max(0, min(100, round(value))))


def infer_scores(text: str, mechanism: str, window: dict[str, Any], hit_count: int) -> dict[str, int]:
    text_len = len(text)
    has_asr = bool(window.get("transcript_refs"))
    has_visual = bool(window.get("keyframe_refs"))
    base = 48 + min(22, hit_count * 5)
    emotion_bonus = 10 if any(token in text for token in ["啊", "打", "抢", "饿", "娘", "孩子", "跪", "偷"]) else 0
    leverage_bonus = 10 if mechanism in {"resource_crisis", "exposure_risk", "system_rule", "evidence_or_trap"} else 4
    constraint_bonus = 12 if mechanism in {"resource_crisis", "system_rule", "survival_tradeoff", "exposure_risk"} else 6
    return {
        "emotion_heat": clamp(base + emotion_bonus),
        "choice_leverage": clamp(base + leverage_bonus),
        "causal_clarity": clamp(44 + min(28, text_len / 12) + (8 if has_asr else 0)),
        "world_constraint_value": clamp(base + constraint_bonus),
        "watch_flow_fit": clamp(64 + (8 if mechanism != "nonsense_or_overpowered_break" else -8)),
        "visual_result_fit": clamp(52 + min(18, len(window.get("keyframe_refs") or []) * 3) + (6 if has_visual else 0)),
    }


def rank_score(scores: dict[str, int]) -> float:
    return round(sum(scores[key] * weight for key, weight in WEIGHTS.items()), 2)


def compact_text(text: str, max_chars: int = 96) -> str:
    clean = re.sub(r"\s+", "", text)
    return clean if len(clean) <= max_chars else clean[: max_chars - 1] + "…"


def first_match(text: str, keywords: list[str]) -> str:
    best_keyword = ""
    best_index: int | None = None
    for keyword in keywords:
        index = text.find(keyword)
        if index >= 0 and (best_index is None or index < best_index):
            best_keyword = keyword
            best_index = index
    return best_keyword


def scene_specific_hook(mechanism: str, text: str) -> str:
    food = first_match(text, RESOURCE_CO_OCCURRENCE_GROUPS["food_object"])
    relation = first_match(text, ["娘", "儿子", "儿媳", "孩子", "四蛋", "大山", "二狗", "三牛", "慧娘", "阿奶", "婆婆"])
    public = first_match(text, ["村", "大家快来看", "邻居", "大嫂子", "全村", "乡亲"])
    system_object = first_match(text, ["系统", "商城", "面板", "铜钱", "价值", "售卖"])
    account_object = first_match(text, ["稻子", "小鹅菜", "兔子", "鸡", "账", "绑", "证据", "赔"])
    power_object = first_match(text, ["修为", "灵力", "身份", "血脉", "法术", "宗门", "封印", "阵法", "能力"])
    betrayal_actor = first_match(text, ["丈夫", "前夫", "小三", "第三者", "婆婆", "公司", "江辞云"])
    care_object = first_match(text, ["孩子", "胎", "怀孕", "受伤", "医院", "医生"])

    if mechanism == "resource_crisis":
        if food and relation:
            return f"{food}要不要现在分给{relation}？"
        if food:
            return f"{food}要不要现在拿出来？"
        return "这点口粮要不要现在分出去？"
    if mechanism == "exposure_risk":
        object_name = food or system_object or "这份资源"
        return f"{object_name}来源要不要现在解释？"
    if mechanism == "family_pressure":
        return f"{relation or '家里人'}这边要不要先护住？"
    if mechanism == "village_pressure":
        return f"当着{public or '村里人'}要不要把话说死？"
    if mechanism == "humiliation_reversal":
        return f"{relation or '眼前人'}被欺负时要不要当场还回去？"
    if mechanism == "evidence_or_trap":
        return f"{account_object or '这笔账'}要不要现在摊开算？"
    if mechanism == "system_rule":
        return f"{system_object or '系统能力'}要不要马上用？"
    if mechanism == "survival_tradeoff":
        return f"{food or '保命资源'}和不暴露要先保哪边？"
    if mechanism == "nonsense_or_overpowered_break":
        return "这一步开太大会不会把戏演塌？"
    if mechanism == "hidden_power_rule":
        return f"{power_object or '隐藏实力'}要不要现在亮出来？"
    if mechanism == "identity_reveal":
        return f"{power_object or '真实身份'}要不要现在摊牌？"
    if mechanism == "relationship_betrayal":
        return f"面对{betrayal_actor or '这次背叛'}要不要当场撕破脸？"
    if mechanism == "status_reversal":
        return f"{betrayal_actor or '这张底牌'}要不要现在打出去？"
    if mechanism == "medical_or_pregnancy_risk":
        return f"{care_object or '眼前风险'}要不要先救再算账？"
    return MECHANISMS[mechanism]["hook"]


def scene_specific_options(mechanism: str, text: str) -> list[str]:
    defaults = OPTIONS[mechanism]
    food = first_match(text, RESOURCE_CO_OCCURRENCE_GROUPS["food_object"]) or "资源"
    relation = first_match(text, ["四蛋", "孩子", "儿媳", "家里人", "阿奶", "婆婆"]) or "眼前人"
    if mechanism == "resource_crisis":
        return [
            f"把{food}拿出来，先解决{relation}眼前这一口",
            f"只拿出一小部分{food}，把来源说圆",
            f"先不用{food}，换一个更不显眼的撑法",
        ]
    if mechanism == "exposure_risk":
        return [
            f"直接承认{food}在手里，先压住局面",
            f"只露出一小部分{food}，保住真正来源",
            "换成低风险解释，不让围观者继续追问",
        ]
    if mechanism == "family_pressure":
        return [
            f"先站到{relation}这边，把伤害挡下来",
            "让家里人自己说，主角只在关键处托底",
            "先不正面翻旧账，回家后再补偿和解释",
        ]
    return defaults


def why_now(mechanism: str, text: str) -> str:
    snippets = {
        "resource_crisis": "资源已经进入眼前场景，人物有饥饿或分配压力，观众会自然想替主角重新分配。",
        "exposure_risk": "资源/系统优势可能被家人或外人察觉，当前选择会影响后续是否露富。",
        "family_pressure": "家人信任和照护关系正在变化，主角的一步选择会决定家里人是否继续相信她。",
        "village_pressure": "冲突暴露在村庄关系里，处理方式会影响名声、借粮和后续生存空间。",
        "humiliation_reversal": "对方正在压迫或羞辱弱势人物，观众有立即反击的冲动。",
        "evidence_or_trap": "场景里有可抓住的账、物或见证点，适合测试反打是否成立。",
        "system_rule": "系统规则和现实解释成本同时出现，适合测试能力使用边界。",
        "survival_tradeoff": "眼前生存和长期风险发生冲突，适合让观众做一次局部取舍。",
        "nonsense_or_overpowered_break": "主角能力有开大诱惑，但过强操作可能破坏继续观看的可信度。",
        "hidden_power_rule": "隐藏能力和现实代价同时出现，观众会想测试直接开大是否可信。",
        "identity_reveal": "身份信息会改变他人态度，但过早摊牌也可能损失试探和反转空间。",
        "relationship_betrayal": "背叛或羞辱正在发生，观众会自然想替主角切断关系或当场反击。",
        "status_reversal": "主角可能握有身份、资源或证据底牌，适合判断何时打出去最爽且最稳。",
        "medical_or_pregnancy_risk": "人身或孕育风险会改变行动优先级，适合测试救人和追责的顺序。",
    }
    return snippets.get(mechanism, "当前局面存在可选择的局部因果岔口。") + f" 证据片段：{compact_text(text, 72)}"


def make_candidate(window: dict[str, Any], mechanism: str, local_index: int, hit_count: int) -> dict[str, Any]:
    text = window.get("transcript_text") or ""
    scores = infer_scores(text, mechanism, window, hit_count)
    baseline = BASELINES[mechanism]
    episode_id = window["episode_id"]
    return {
        "candidate_id": f"{episode_id}_c{local_index:03d}",
        "episode_id": episode_id,
        "window_id": window["window_id"],
        "start_ms": window["start_ms"],
        "end_ms": window["end_ms"],
        "trigger_type": mechanism,
        "notice_marker": MECHANISMS[mechanism]["marker"],
        "hook": scene_specific_hook(mechanism, text),
        "why_now": why_now(mechanism, text),
        "viewer_impulse": MECHANISMS[mechanism]["impulse"],
        "canon_baseline": {
            "original_action": baseline["original_action"],
            "original_rationale": baseline["original_rationale"],
            "audience_tension": baseline["audience_tension"],
        },
        "scores": scores,
        "rank_score": rank_score(scores),
        "default_options": scene_specific_options(mechanism, text),
        "canon_context_note_need": mechanism in {"exposure_risk", "system_rule", "nonsense_or_overpowered_break", "survival_tradeoff"},
        "original_plot_note": baseline["note"],
        "evidence_excerpt": compact_text(text, 140),
        "source_refs": {
            "transcript_refs": window.get("transcript_refs") or [],
            "keyframe_refs": window.get("keyframe_refs") or [],
            "contact_sheet_ref": window.get("contact_sheet_ref") or "",
        },
        "reliability": {
            "asr_quality": "high" if len(window.get("transcript_refs") or []) >= 3 else "medium" if text else "unknown",
            "keyframe_ref_quality": "medium" if len(window.get("keyframe_refs") or []) >= 2 else "low" if window.get("keyframe_refs") else "none",
            "visual_evidence": "medium" if window.get("keyframe_refs") else "low",
            "visual_evidence_basis": "keyframe refs only; not machine-interpreted visual claims",
            "needs_human_review": True,
        },
    }


def mine_candidates(windows: list[dict[str, Any]], max_candidates: int) -> list[dict[str, Any]]:
    scored_windows: list[tuple[float, dict[str, Any], list[tuple[str, int]]]] = []
    for window in windows:
        text = window.get("transcript_text") or ""
        mechanism_hits = sorted(
            ((mechanism, score_keywords(text, mechanism)) for mechanism in MECHANISMS),
            key=lambda item: item[1],
            reverse=True,
        )
        best_score = mechanism_hits[0][1] if mechanism_hits else 0
        if best_score <= 0:
            continue
        density = best_score + min(8, len(text) / 80)
        scored_windows.append((density, window, mechanism_hits))

    candidates: list[dict[str, Any]] = []
    per_episode_counts: dict[str, int] = defaultdict(int)
    candidate_seen: set[tuple[str, str]] = set()

    for _, window, mechanism_hits in sorted(scored_windows, key=lambda item: item[0], reverse=True):
        episode_id = window["episode_id"]
        selected = [item for item in mechanism_hits if item[1] > 0][:2]
        for mechanism, hit_count in selected:
            if len(candidates) >= max_candidates:
                break
            key = (window["window_id"], mechanism)
            if key in candidate_seen:
                continue
            per_episode_counts[episode_id] += 1
            candidate_seen.add(key)
            candidates.append(make_candidate(window, mechanism, per_episode_counts[episode_id], hit_count))

    covered = {candidate["episode_id"] for candidate in candidates}
    for _, window, mechanism_hits in sorted(scored_windows, key=lambda item: item[1]["episode_id"]):
        if len(candidates) >= max_candidates:
            break
        episode_id = window["episode_id"]
        if episode_id in covered:
            continue
        mechanism, hit_count = mechanism_hits[0]
        per_episode_counts[episode_id] += 1
        candidates.append(make_candidate(window, mechanism, per_episode_counts[episode_id], hit_count))
        covered.add(episode_id)

    candidates.sort(key=lambda candidate: candidate["rank_score"], reverse=True)
    for rank, candidate in enumerate(candidates, start=1):
        candidate["rank"] = rank
    return candidates


def format_ms(ms: int) -> str:
    seconds = ms // 1000
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def write_markdown(path: Path, candidates: list[dict[str, Any]]) -> None:
    rows = [
        "# Deadman Candidate Nodes v0.2",
        "",
        "> Semi-automatic ARS bridge evidence. Hooks/options are scene-conditioned, visual evidence is capped at keyframe-reference quality, and every row requires human review before Moment Causality Pack promotion.",
        "",
        "| Rank | ID | Time | Mechanism | Score | Hook | Evidence | Review |",
        "|---:|---|---|---|---:|---|---|---|",
    ]
    for candidate in candidates:
        time = f"{candidate['episode_id']} {format_ms(candidate['start_ms'])}-{format_ms(candidate['end_ms'])}"
        evidence = candidate.get("evidence_excerpt", "").replace("|", " ")
        rows.append(
            "| {rank} | `{cid}` | {time} | `{mechanism}` | {score:.2f} | {hook} | {evidence} | {review} |".format(
                rank=candidate["rank"],
                cid=candidate["candidate_id"],
                time=time,
                mechanism=candidate["trigger_type"],
                score=candidate["rank_score"],
                hook=candidate["hook"].replace("|", " "),
                evidence=evidence,
                review="required" if candidate["reliability"]["needs_human_review"] else "optional",
            )
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--candidate-dir", default=str(DEFAULT_CANDIDATE_DIR))
    parser.add_argument("--windows", help="Input windows JSON path. Defaults to candidate-dir output.")
    parser.add_argument("--out-json", help="Exact candidate JSON output path.")
    parser.add_argument("--out-md", help="Exact ranked-table Markdown output path.")
    parser.add_argument("--max-candidates", type=int, default=60)
    parser.add_argument("--drama-id", default="huangnian")
    parser.add_argument("--drama-title", default="荒年全村啃树皮，我有系统满仓肉")
    parser.add_argument("--version", default="v0.2")
    args = parser.parse_args()

    candidate_dir = resolve_path(args.candidate_dir)
    windows_path = resolve_path(args.windows) if args.windows else candidate_dir / f"{args.drama_id}_windows.{args.version}.json"
    out_json = resolve_path(args.out_json) if args.out_json else candidate_dir / f"{args.drama_id}_candidates.{args.version}.json"
    out_md = resolve_path(args.out_md) if args.out_md else candidate_dir / f"{args.drama_id}_candidates.{args.version}.md"
    windows_data = read_json(windows_path)
    candidates = mine_candidates(windows_data["windows"], args.max_candidates)
    output = {
        "version": args.version,
        "drama_id": args.drama_id,
        "source_drama": args.drama_title,
        "ranking_formula": WEIGHTS,
        "limit_policy": {
            "max_candidates": args.max_candidates,
            "behavior": "hard_cap",
            "episode_coverage_backfill": "only while under max_candidates",
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    write_json(out_json, output)
    write_markdown(out_md, candidates)
    print(
        json.dumps(
            {
                "candidate_count": len(candidates),
                "out_json": repo_relative(out_json),
                "out_md": repo_relative(out_md),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
