"""Deadman-owned friend voice composer for runtime judgment material."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .models import JudgmentResponse, UserAction
from .runtime_models import ResultSurface, RuntimeMicroCue


FORBIDDEN_PUBLIC_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"原剧情",
        r"剧情结论",
        r"不改写[^。！？.!?]*",
        r"不改变[^。！？.!?]*",
        r"没有任何影响",
        r"不会影响[^。！？.!?]*",
        r"不影响[^。！？.!?]*",
        r"后续主线",
        r"主线",
        r"分支剧情",
        r"后面剧集",
        r"未来分支",
        r"当前场景",
        r"局部后果",
        r"later episode",
        r"future branch",
    )
]


@dataclass(frozen=True)
class FriendVoiceResult:
    result_surface: ResultSurface
    summary_for_next_moment: str
    safe_to_reference: bool


class FriendVoiceComposer:
    """Converts structured judgment material into one companion utterance."""

    def compose(
        self,
        judgment: JudgmentResponse,
        *,
        moment: dict[str, Any],
        previous_summary: str = "",
        host_should_persist: bool = True,
    ) -> FriendVoiceResult:
        text = self._compose_text(judgment, moment, previous_summary)
        micro_cue = self._select_micro_cue(judgment, moment)
        summary = self._summary_for_next_moment(judgment.action, judgment.verdict.stance)
        should_persist_summary = bool(host_should_persist and summary and not _contains_forbidden_public_copy(summary))
        return FriendVoiceResult(
            result_surface=ResultSurface(
                text=text,
                micro_cue=micro_cue,
                continue_label="继续看",
            ),
            summary_for_next_moment=summary if should_persist_summary else "",
            safe_to_reference=should_persist_summary,
        )

    def _compose_text(self, judgment: JudgmentResponse, moment: dict[str, Any], previous_summary: str) -> str:
        if judgment.engine.mode == "cab_runtime":
            text = self._compose_cab_runtime_text(judgment)
            if text:
                return text
        action_text = _compact_action(judgment.action.text)
        consequence = _strip_leading_action(sanitize_viewer_copy(judgment.consequence.text), judgment.action.text)
        verdict = sanitize_viewer_copy(judgment.verdict.summary)
        lead = self._compose_lead(judgment, moment, _quote_action(action_text), previous_summary)
        body = consequence or verdict
        text = _compact_result_text(sanitize_viewer_copy(f"{lead}{body}"), lead)
        return text or "我先接住这个思路，别把话说满，先看眼前的人怎么接。"

    def _compose_cab_runtime_text(self, judgment: JudgmentResponse) -> str:
        for candidate in (judgment.verdict.summary, judgment.consequence.text):
            clean_text = sanitize_viewer_copy(candidate)
            if clean_text:
                return _compact_result_text(clean_text, "")
        return ""

    def _compose_lead(
        self,
        judgment: JudgmentResponse,
        moment: dict[str, Any],
        action_text: str,
        previous_summary: str,
    ) -> str:
        action_type = self._action_type(moment)
        bank = _LEAD_BANK.get(action_type, _LEAD_BANK["other"])
        candidates = bank.get(judgment.verdict.stance, bank["caution"])
        seed = "|".join(
            [
                str(moment.get("moment_id") or moment.get("pack_id") or ""),
                action_type,
                judgment.verdict.stance,
                judgment.action.source,
                judgment.action.text,
            ]
        )
        lead = _stable_pick(candidates, seed).format(action=action_text)
        if previous_summary:
            return f"接着你上一手看，{lead}"
        return lead

    def _select_micro_cue(self, judgment: JudgmentResponse, moment: dict[str, Any]) -> RuntimeMicroCue | None:
        if judgment.action.source == "custom":
            if judgment.verdict.stance == "reject_softly":
                return RuntimeMicroCue(kind="cost_hint", text="这手爽是爽，搭子建议收一点。")
            return None
        if self._has_high_stakes(moment) and judgment.verdict.stance != "support":
            return RuntimeMicroCue(kind="cost_hint", text="这一步有代价，别把牌一次打完。")
        selected = None
        if judgment.aggregate_stats is not None:
            selected = next((choice for choice in judgment.aggregate_stats.choices if choice.selected), None)
        if selected is not None:
            return RuntimeMicroCue(kind="aggregate_hint", text=f"有{selected.percent}%其他观众也这么想。")
        return None

    def _summary_for_next_moment(self, action: UserAction, stance: str) -> str:
        action_text = _compact_action(action.text)
        if stance == "reject_softly":
            return f"你上一手是想猛推一把，但搭子把尺度收住了。"
        return f"你上一手是{action_text}。"

    def _has_high_stakes(self, moment: dict[str, Any]) -> bool:
        typed = moment.get("typed_fields")
        if isinstance(typed, dict) and typed.get("critical_stakes_state"):
            return True
        local_constraints = moment.get("local_constraints")
        if isinstance(local_constraints, dict):
            risk_notes = local_constraints.get("risk_notes", [])
            return bool(risk_notes)
        return False

    def _action_type(self, moment: dict[str, Any]) -> str:
        action_space = moment.get("action_space")
        if isinstance(action_space, dict):
            raw = action_space.get("action_type")
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        typed = moment.get("typed_fields")
        if isinstance(typed, dict):
            raw = typed.get("action_type") or typed.get("moment_type")
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        return "other"


_LEAD_BANK: dict[str, dict[str, list[str]]] = {
    "resource": {
        "support": [
            "这顿饭先别只看肉，{action}是在给家里立个能服众的分法。",
            "这里最要紧的是让孩子知道自己没被落下，{action}能先稳住这口气。",
            "荒年里吃什么不难，难的是怎么分，{action}这一步抓得住重点。",
        ],
        "caution": [
            "这口肉能救急，但动静不能太大，{action}最好再压一层解释。",
            "这步有爽点，也有被追问的风险，{action}得留住余地。",
            "先照顾眼前人没错，但荒年资源太扎眼，{action}不能摊得太满。",
        ],
        "reject_softly": [
            "这个方向太容易把家底亮出来，{action}得换成更小的动作。",
            "爽是爽，但这口肉一旦摊大，后面全是追问，{action}先收一下。",
            "这里不能只图痛快，{action}会让资源来源变成新的麻烦。",
        ],
    },
    "humiliation": {
        "support": [
            "这桌上的问题不是饭，是谁被当人看，{action}能先把人护住。",
            "这种羞辱不能干看着，{action}先把底线摆出来。",
            "先让被欺负的人喘口气，{action}比直接吵赢更稳。",
        ],
        "caution": [
            "这场面得拦，但桌上人都在看，{action}最好别把火一下烧满。",
            "护人是对的，问题是怎么落地，{action}还需要留个台阶。",
            "这口气能出，但家里关系会跟着炸，{action}得压住尺度。",
        ],
        "reject_softly": [
            "当场硬掀桌会很爽，但也容易让被护的人更难站住，{action}先换个更稳的说法。",
            "这个反击太满了，{action}会把一顿饭变成全家对撞。",
            "这不是不能怼，是现在这么怼会失控，{action}先降一档。",
        ],
    },
    "system_rule": {
        "support": [
            "系统刚露头，第一步要验规则，{action}这个节奏能让人安心一点。",
            "这里不是开挂越大越好，{action}先确认规则才有后劲。",
            "面板能救命，但得先知道它怎么收尾，{action}方向是对的。",
        ],
        "caution": [
            "系统能力太扎眼，{action}可以试，但别在别人眼皮底下试太满。",
            "这步有用，也有暴露成本，{action}最好再藏一点。",
            "先试系统没问题，问题是见证人和解释，{action}得收着来。",
        ],
        "reject_softly": [
            "直接把系统摊出来会把世界规则撞碎，{action}这版不能这么打。",
            "这不是不能用系统，是不能让所有人都跟着知道，{action}得改成暗线。",
            "开太大反而不爽，{action}会让后续每个问题都变成解释系统。",
        ],
    },
    "evidence": {
        "support": [
            "被人当众扣帽子，先抓证据，{action}能把话柄抢回来。",
            "这里吵赢不如让旁人看懂，{action}抓的是证据位。",
            "围观者都在，{action}能把局面从骂战拉回事实。",
        ],
        "caution": [
            "反打可以，但证据要先站稳，{action}别急着把话说死。",
            "这场有围观者，{action}要小心别被对方带成新的骂战。",
            "证据牌能打，但顺序很关键，{action}最好先问住对方。",
        ],
        "reject_softly": [
            "这一下太像硬冲了，{action}容易给对方倒打一耙的口子。",
            "没有先把证据放稳，{action}会从反击变成互骂。",
            "这口气能理解，但{action}太快了，旁人未必跟得上。",
        ],
    },
    "exposure": {
        "support": [
            "白米已经露了，重点是压住来源，{action}能先稳住家里这轮追问。",
            "这里最怕越解释越显眼，{action}把动静控制住了。",
            "资源已经被看见，{action}先护住信任，比摊牌更重要。",
        ],
        "caution": [
            "白米这东西太扎眼，{action}能走，但解释必须轻一点。",
            "这步能安人心，也会招追问，{action}别把来源说满。",
            "现在不是不能承认有东西，是不能让来源变成焦点，{action}要压住。",
        ],
        "reject_softly": [
            "这时候全说破会把白米变成麻烦中心，{action}先别这么亮。",
            "直接摊牌太危险，{action}会让所有人都盯上来源。",
            "这口气想护人没错，但{action}会把资源暴露放大。",
        ],
    },
    "other": {
        "support": [
            "这一刻先抓住眼前压力，{action}能让局面往可控处走。",
            "这个处理有戏，{action}不是硬莽，是先把关键人稳住。",
            "你这个点选得准，{action}先把最要紧的矛盾按住。",
        ],
        "caution": [
            "方向能聊，但这一步要留余地，{action}别一下说满。",
            "这个选择有用，也有代价，{action}得看旁边人怎么接。",
            "眼前这么做能推一下局面，但{action}最好别冲过头。",
        ],
        "reject_softly": [
            "这个动作太满了，{action}得先拆成更可信的一小步。",
            "爽点有，但落地会飘，{action}先降一档。",
            "这一下容易把戏推穿，{action}换成更近的动作更稳。",
        ],
    },
}

_LEAD_BANK["relationship"] = _LEAD_BANK["humiliation"]
_LEAD_BANK["survival"] = _LEAD_BANK["resource"]


def _stable_pick(options: list[str], seed: str) -> str:
    if not options:
        return "{action}这一步要先看眼前怎么落地。"
    digest = sha256(seed.encode("utf-8")).hexdigest()
    return options[int(digest[:8], 16) % len(options)]


def sanitize_viewer_copy(value: str) -> str:
    sentences = [
        item.strip()
        for item in re.sub(r"([。！？.!?])", r"\1\n", value).splitlines()
        if item.strip()
    ]
    kept = [sentence for sentence in sentences if not _contains_forbidden_public_copy(sentence)]
    return "".join(kept).strip()


def _contains_forbidden_public_copy(value: str) -> bool:
    return any(pattern.search(value) for pattern in FORBIDDEN_PUBLIC_PATTERNS)


def _compact_action(value: str) -> str:
    text = re.sub(r"\s+", "", value.strip())
    if len(text) <= 18:
        return text
    return f"{text[:18]}..."


def _quote_action(value: str) -> str:
    return f"「{value}」"


def _compact_result_text(text: str, lead: str) -> str:
    clean_text = text.strip()
    if len(clean_text) <= 64:
        return clean_text
    clean_lead = sanitize_viewer_copy(lead)
    if clean_lead and len(clean_lead) <= 64:
        return clean_lead
    sentences = [
        sentence.strip()
        for sentence in re.sub(r"([。！？.!?])", r"\1\n", clean_text).splitlines()
        if sentence.strip()
    ]
    if sentences and len(sentences[0]) <= 64:
        return sentences[0]
    return f"{clean_text[:60]}..."


def _strip_leading_action(text: str, action: str) -> str:
    compact_text = re.sub(r"\s+", "", text)
    compact_action = re.sub(r"\s+", "", action.strip())
    if compact_action and compact_text.startswith(compact_action):
        return compact_text[len(compact_action) :].lstrip("，。；：:;,. ")
    return text
