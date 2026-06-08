"""Deterministic-first judgment service for Deadman companion runtime."""

from __future__ import annotations

from typing import Any

from .adapter_mapping import AdapterMappingError, build_adapter_input
from .models import (
    AggregateStats,
    CanonAnchor,
    ChoiceShare,
    Consequence,
    EngineMetadata,
    JudgmentBasis,
    JudgmentMedia,
    JudgmentRequest,
    JudgmentResponse,
    ResultCard,
    Verdict,
)
from .pack_store import DeadmanPackStore, PackStoreError
from .runtime_client import CabRuntimeWorkerClient, RuntimeClientError


OVERPOWERED_KEYWORDS = ("无限", "全村", "直接公开系统", "杀光", "改写后续", "后面全部", "一键", "开挂", "暴富")

USER_FACING_TERM_MAP = {
    "first visible use of system sale/exchange logic": "第一次试用系统售卖/兑换能力",
    "system can convert ordinary goods into survival resources": "系统把普通物品换成活命资源这件事",
    "keep hidden from public witnesses": "不让公开围观者知道",
    "white rice/resource visibility": "白米已经被看见",
    "family-level witnesses in reviewed demo node": "家人这些当前在场者",
    "白米/food resource": "白米",
    "daughter-in-law": "儿媳",
    "mother-in-law / daughter-in-law protection": "婆媳桌规",
    "daughter-in-law is being humiliated by household rules": "儿媳被桌规羞辱",
}


class DeterministicJudgmentService:
    def __init__(self, store: DeadmanPackStore) -> None:
        self.store = store

    def judge(self, request: JudgmentRequest) -> JudgmentResponse:
        pack = self.store.get_drama(request.drama_id)
        moment = self.store.get_moment(request.drama_id, request.moment_id)
        self._validate_action(request, moment)
        try:
            build_adapter_input(
                request_id=f"{request.drama_id}:{request.moment_id}:{request.action.source}:{request.action.option_index}",
                drama_pack=pack,
                moment=moment,
                request=request,
            )
        except AdapterMappingError as exc:
            raise PackStoreError(exc.code, exc.message, status_code=500) from exc

        is_overpowered = self._is_overpowered(request.action.text)
        stance = self._stance(request, moment, is_overpowered)
        optional_modules = moment.get("optional_modules", {}) if isinstance(moment.get("optional_modules"), dict) else {}
        original_plot_note = self._original_plot_note(moment)
        watch_flow_fit = self._watch_flow_fit(moment, stance)
        applied_constraints = self._applied_constraints(pack.context, moment)
        evidence_refs = self._evidence_refs(moment, pack.context)
        warnings = self._warnings(request, moment, is_overpowered)

        return JudgmentResponse(
            drama_id=request.drama_id,
            moment_id=request.moment_id,
            action=request.action,
            verdict=Verdict(
                label=self._label(stance),
                stance=stance,
                summary=self._summary(request, moment, stance, is_overpowered),
            ),
            consequence=Consequence(
                text=self._consequence_text(request, moment, optional_modules, stance, is_overpowered),
                time_horizon="current_scene_or_immediate_aftermath",
                watch_flow_fit=watch_flow_fit,
            ),
            canon_anchor=CanonAnchor(
                original_plot_note=original_plot_note,
                safe_to_continue=True,
            ),
            scores=self._scores(moment, optional_modules, stance, is_overpowered),
            result_card=ResultCard(
                mode="fallback_card",
                title=self._card_title(moment, stance),
                prompt=self._card_prompt(request, moment, optional_modules, stance, is_overpowered),
            ),
            media=self._media_result(request, moment),
            aggregate_stats=self._aggregate_stats(request, moment),
            judgment_basis=JudgmentBasis(
                evidence_refs=evidence_refs,
                applied_constraints=applied_constraints,
                inference_notes=self._inference_notes(moment, stance, is_overpowered),
                warnings=warnings,
            ),
            engine=EngineMetadata(),
        )

    def judge_for_runtime(
        self,
        request: JudgmentRequest,
        *,
        viewer_session_id: str,
        event_id: str,
        host_state: dict[str, Any] | None = None,
    ) -> tuple[JudgmentResponse, bool]:
        return self.judge(request), True

    def _validate_action(self, request: JudgmentRequest, moment: dict[str, Any]) -> None:
        options = self._default_options(moment)
        if request.action.source == "preset_candidate":
            candidate = self._candidate_for_action(request, moment)
            if request.action.text.strip() != str(candidate.get("display_text") or "").strip():
                raise PackStoreError(
                    "preset_candidate_text_mismatch",
                    "Preset candidate action.text must match the selected display_text.",
                    status_code=422,
                )
            submitted_payload = request.action.action_payload or {}
            expected_payload = candidate.get("action_payload") if isinstance(candidate.get("action_payload"), dict) else {}
            if submitted_payload != expected_payload:
                raise PackStoreError(
                    "preset_candidate_payload_mismatch",
                    "Preset candidate action_payload must match the reviewed moment pack payload.",
                    status_code=422,
                )
            return
        if request.action.source == "preset":
            if request.action.option_index is None:
                raise PackStoreError(
                    "preset_option_required",
                    "Preset actions must include action.option_index.",
                    status_code=422,
                )
            if request.action.option_index < 0 or request.action.option_index >= len(options):
                raise PackStoreError(
                    "preset_option_invalid",
                    f"Preset option_index {request.action.option_index} is outside the moment's default options.",
                    status_code=422,
                )
            expected_text = options[request.action.option_index].strip()
            if request.action.text.strip() != expected_text:
                raise PackStoreError(
                    "preset_option_text_mismatch",
                    "Preset action.text must match the selected default option.",
                    status_code=422,
                )

    def _candidate_for_action(self, request: JudgmentRequest, moment: dict[str, Any]) -> dict[str, Any]:
        candidate_id = (request.action.candidate_id or "").strip()
        if not candidate_id:
            raise PackStoreError(
                "preset_candidate_required",
                "Preset candidate actions must include action.candidate_id.",
                status_code=422,
            )
        for candidate in _reply_candidates(moment):
            if isinstance(candidate, dict) and str(candidate.get("candidate_id") or "") == candidate_id:
                return candidate
        raise PackStoreError(
            "preset_candidate_invalid",
            f"Preset candidate_id {candidate_id!r} is not available for this moment.",
            status_code=422,
        )

    def _stance(self, request: JudgmentRequest, moment: dict[str, Any], is_overpowered: bool) -> str:
        if is_overpowered:
            return "reject_softly"
        if request.action.source == "custom":
            return "caution"
        if self._selected_option_index(request, moment) == 0 and self._has_module(moment, "resource_scarcity", "relationship_pressure"):
            return "support"
        return "caution"

    def _summary(
        self,
        request: JudgmentRequest,
        moment: dict[str, Any],
        stance: str,
        is_overpowered: bool,
    ) -> str:
        actor = moment.get("actor_context", {}).get("pov_actor", "主角")
        pressure = moment.get("actor_context", {}).get("local_emotional_pressure")
        if is_overpowered:
            return f"这个冲动能理解，但它把 {actor} 推出了当前场景证据和短剧约束之外，只能收成局部动作。"
        if stance == "support" and self._has_module(moment, "humiliation_reversal"):
            return f"这一步站得住：先把被羞辱的人护住，比单纯吵赢更像 {actor} 会做的选择。"
        if stance == "support":
            return f"这一步站得住：先处理眼前人和眼前物，比直接炫能力更像 {actor} 会做的选择。"
        if pressure:
            return f"方向可以，但要压住尺度；这场的张力是“{pressure}”，不是一口气改完整条线。"
        return "方向可以，但结果只能落在当前场景或紧接着的一小段后果里。"

    def _consequence_text(
        self,
        request: JudgmentRequest,
        moment: dict[str, Any],
        optional_modules: dict[str, Any],
        stance: str,
        is_overpowered: bool,
    ) -> str:
        actors = "、".join(moment.get("actor_context", {}).get("directly_affected_actors", [])[:2]) or "身边人"
        object_name = self._object_name(optional_modules)
        witness = self._witness_scope(optional_modules)
        protected_actor = self._protected_actor(optional_modules, actors)
        if is_overpowered:
            return (
                f"可以保留“想马上翻盘”的爽感，但不能按“{request.action.text}”全量执行。"
                f"更稳的落点是只在{witness}面前处理{object_name}，让{actors}看到一个可信的局部变化，"
                "不把系统、后续剧集或全村秩序一次性掀开。"
            )
        if self._has_module_dict(optional_modules, "humiliation_reversal"):
            if stance == "support":
                return (
                    f"{request.action.text}会先把羞辱从桌上挡住：{protected_actor}能被当人照顾，"
                    f"{witness}也看见这条底线。"
                )
            return (
                f"{request.action.text}可以成立，但要小步执行：先护住{protected_actor}，"
                f"再给{witness}留一个不继续施压的台阶。"
            )
        if stance == "support":
            return (
                f"{request.action.text}会把{object_name}从单纯资源变成关系修复信号：{actors}先确认自己被照顾，"
                f"{witness}的解释压力也还压得住。"
            )
        return (
            f"{request.action.text}可以成立，但要小步执行：先解决{object_name}的眼前分配或证据问题，"
            f"别把{witness}扩大成公开承诺。这样会产生局部信任/名声变化，但不会替后面剧集改命。"
        )

    def _scores(
        self,
        moment: dict[str, Any],
        optional_modules: dict[str, Any],
        stance: str,
        is_overpowered: bool,
    ) -> dict[str, int]:
        axes = moment.get("score_axes", {}) if isinstance(moment.get("score_axes"), dict) else {}
        emotion = int(axes.get("emotion_heat", 65))
        credibility = int(axes.get("causal_clarity", 65))
        flow = int(axes.get("watch_flow_fit", 65))
        exposure_base = 72 if self._has_module_dict(optional_modules, "exposure_and_secrecy", "system_or_hidden_power_rule") else 45
        relationship = 76 if self._has_module_dict(optional_modules, "relationship_pressure", "humiliation_reversal") else 55
        if is_overpowered:
            return {
                "爽度": min(100, emotion + 6),
                "可信度": max(20, credibility - 34),
                "风险": 94,
                "暴露度": max(84, exposure_base),
                "关系冲击": min(100, relationship + 8),
                "回看顺滑度": max(25, flow - 38),
            }
        if stance == "support":
            return {
                "爽度": emotion,
                "可信度": min(100, credibility + 8),
                "风险": 38,
                "暴露度": exposure_base,
                "关系冲击": relationship,
                "回看顺滑度": min(100, flow + 8),
            }
        return {
            "爽度": emotion,
            "可信度": credibility,
            "风险": 62,
            "暴露度": exposure_base,
            "关系冲击": relationship,
            "回看顺滑度": flow,
        }

    def _card_title(self, moment: dict[str, Any], stance: str) -> str:
        hook = moment.get("companion_surface", {}).get("hook")
        if stance == "reject_softly":
            return "爽点收束一下"
        return str(hook or "看剧搭子")

    def _card_prompt(
        self,
        request: JudgmentRequest,
        moment: dict[str, Any],
        optional_modules: dict[str, Any],
        stance: str,
        is_overpowered: bool,
    ) -> str:
        object_name = self._object_name(optional_modules)
        if is_overpowered:
            return f"镜头给到{object_name}和当事人的反应：想法很猛，但结果只落回这一场能解释的范围。"
        if stance == "support":
            return f"镜头停在{object_name}被重新分配/解释的一刻，旁边人的表情从不信慢慢松动。"
        return f"镜头保留犹豫：{request.action.text}可以做，但代价和解释压力要同时出现在画面里。"

    def _inference_notes(self, moment: dict[str, Any], stance: str, is_overpowered: bool) -> list[str]:
        notes = [
            "This demo deterministic judgment separates promoted evidence from local product inference.",
            "The result is constrained to the current scene or immediate aftermath.",
        ]
        ev = moment.get("review_state", {}).get("evidence_vs_inference")
        if ev:
            notes.append(str(ev))
        if is_overpowered:
            notes.append("Overpowered custom action was accepted as viewer impulse, then softened to local credible consequence.")
        elif stance == "caution":
            notes.append("Caution stance chosen because the action needs scale control or is not the safest preset.")
        return notes

    def _warnings(self, request: JudgmentRequest, moment: dict[str, Any], is_overpowered: bool) -> list[str]:
        warnings = list(moment.get("local_constraints", {}).get("risk_notes", []))
        if is_overpowered:
            warnings.append("Custom action exceeds local evidence, hidden-system limits, or watch-flow constraints.")
        if request.action.source == "custom":
            warnings.append("Custom action is judged locally only; no later-episode branch is claimed.")
        return [str(item) for item in warnings]

    def _applied_constraints(self, context: dict[str, Any], moment: dict[str, Any]) -> list[str]:
        constraint_ids = [
            str(item.get("id", item.get("constraint", "")))
            for item in context.get("core_constraints", [])
            if isinstance(item, dict)
        ]
        hard_constraints = [str(item) for item in moment.get("local_constraints", {}).get("hard_constraints", [])]
        return [item for item in constraint_ids + hard_constraints if item][:10]

    def _evidence_refs(self, moment: dict[str, Any], context: dict[str, Any]) -> list[str]:
        refs: list[str] = []
        reviewed = moment.get("source_refs", {}).get("reviewed_demo_node")
        if reviewed:
            refs.append(str(reviewed))
        for snippet in moment.get("source_refs", {}).get("transcript_snippets", []):
            if isinstance(snippet, dict) and snippet.get("id"):
                refs.append(str(snippet["id"]))
        for keyframe in moment.get("source_refs", {}).get("keyframe_refs", []):
            if isinstance(keyframe, dict) and keyframe.get("id"):
                refs.append(str(keyframe["id"]))
        for field_ref in moment.get("producer_review_fields", {}).get("field_evidence_refs", []):
            refs.append(str(field_ref))
        for evidence in context.get("evidence_map", [])[:2]:
            if isinstance(evidence, dict) and evidence.get("id"):
                refs.append(str(evidence["id"]))
        return refs[:8]

    def _media_result(self, request: JudgmentRequest, moment: dict[str, Any]) -> JudgmentMedia:
        result_media = moment.get("result_media", {})
        if not isinstance(result_media, dict):
            result_media = {}
        selected_index = self._selected_option_index(request, moment)
        if request.action.source in {"preset", "preset_candidate"} and selected_index is not None:
            for slot in result_media.get("preset_options", []):
                if isinstance(slot, dict) and slot.get("option_index") == selected_index:
                    return JudgmentMedia(
                        status=str(slot.get("status") or "placeholder"),  # type: ignore[arg-type]
                        image_url=str(slot.get("image_url") or ""),
                        prompt=str(slot.get("prompt") or ""),
                        source=str(slot.get("source") or ""),
                        fallback_text=slot.get("fallback_text"),
                    )
        custom = result_media.get("custom_action", {})
        prompt = self._card_prompt(request, moment, moment.get("optional_modules", {}) or {}, "caution", False)
        if isinstance(custom, dict) and request.action.source == "custom":
            return JudgmentMedia(
                status="not_available",
                image_url="",
                prompt=prompt,
                source=str(custom.get("mode") or "realtime_generate_or_text_only_fallback"),
                fallback_text="实时图像生成未配置，本次先返回文字后果。",
            )
        return JudgmentMedia(
            status="not_available",
            image_url="",
            prompt=prompt,
            source="not_generated",
            fallback_text="当前没有可展示的结果图。",
        )

    def _aggregate_stats(self, request: JudgmentRequest, moment: dict[str, Any]) -> AggregateStats:
        options = self._default_options(moment)
        option_count = max(1, len(options))
        if option_count == 1:
            base = [100]
        elif option_count == 2:
            base = [58, 42]
        else:
            base = [46, 33, 21] + [0] * (option_count - 3)

        selected_index = self._selected_option_index(request, moment) if request.action.source in {"preset", "preset_candidate"} else None
        if selected_index is not None and 0 <= selected_index < option_count:
            boosted = base[:option_count]
            boosted[selected_index] += 6
            subtractable = [index for index in range(option_count) if index != selected_index and boosted[index] > 0]
            for index in subtractable[:6]:
                boosted[index] -= 1
            base = self._normalize_percentages(boosted)
        else:
            base = self._normalize_percentages(base[:option_count])

        total_count = 128 + (sum(ord(char) for char in str(moment.get("moment_id", ""))) % 280)
        return AggregateStats(
            total_count=total_count,
            choices=[
                ChoiceShare(label=self._option_label(index), percent=percent, selected=index == selected_index)
                for index, percent in enumerate(base)
            ],
            note="P0 演示静态分布；正式上线需要接入持久化统计。",
        )

    def _normalize_percentages(self, values: list[int]) -> list[int]:
        total = sum(max(0, value) for value in values)
        if total <= 0:
            return [100] + [0] * (len(values) - 1)
        normalized = [round(max(0, value) / total * 100) for value in values]
        delta = 100 - sum(normalized)
        if normalized:
            normalized[0] += delta
        return normalized

    def _option_label(self, index: int) -> str:
        if index == 1:
            return "B"
        if index == 2:
            return "C"
        return "A" if index == 0 else f"选项{index + 1}"

    def _watch_flow_fit(self, moment: dict[str, Any], stance: str) -> str:
        if stance == "reject_softly":
            return "low"
        score = int(moment.get("score_axes", {}).get("watch_flow_fit", 65))
        if score >= 78 and stance == "support":
            return "high"
        return "medium"

    def _label(self, stance: str) -> str:
        if stance == "support":
            return "稳，但别摊太大"
        if stance == "reject_softly":
            return "爽是爽，先别开挂"
        return "能做，但要收着"

    def _original_plot_note(self, moment: dict[str, Any]) -> str:
        return str(
            moment.get("original_plot_note")
            or moment.get("canon_baseline", {}).get("original_plot_note")
            or "这个落点按当前场面的可解释后果处理。"
        )

    def _default_options(self, moment: dict[str, Any]) -> list[str]:
        return [str(option) for option in moment.get("action_space", {}).get("default_options", [])]

    def _selected_option_index(self, request: JudgmentRequest, moment: dict[str, Any]) -> int | None:
        if request.action.source == "preset":
            return request.action.option_index
        if request.action.source != "preset_candidate":
            return None
        candidate_id = (request.action.candidate_id or "").strip()
        for index, candidate in enumerate(_reply_candidates(moment)):
            if isinstance(candidate, dict) and str(candidate.get("candidate_id") or "") == candidate_id:
                return index
        return None

    def _is_overpowered(self, text: str) -> bool:
        return any(keyword in text for keyword in OVERPOWERED_KEYWORDS)

    def _has_module(self, moment: dict[str, Any], *names: str) -> bool:
        optional_modules = moment.get("optional_modules", {})
        return self._has_module_dict(optional_modules if isinstance(optional_modules, dict) else {}, *names)

    def _has_module_dict(self, optional_modules: dict[str, Any], *names: str) -> bool:
        return any(name in optional_modules for name in names)

    def _object_name(self, optional_modules: dict[str, Any]) -> str:
        resource = optional_modules.get("resource_scarcity", {})
        if isinstance(resource, dict) and resource.get("resource_type"):
            return self._display_term(resource["resource_type"], "眼前这份资源")
        exposure = optional_modules.get("exposure_and_secrecy", {})
        if isinstance(exposure, dict) and exposure.get("visible_advantage"):
            return self._display_term(exposure["visible_advantage"], "眼前这件优势")
        power = optional_modules.get("system_or_hidden_power_rule", {})
        if isinstance(power, dict) and power.get("power_or_system_action"):
            return self._display_term(power["power_or_system_action"], "系统能力")
        evidence = optional_modules.get("evidence_or_trap_logic", {})
        if isinstance(evidence, dict) and evidence.get("claim_account"):
            return self._display_term(evidence["claim_account"], "眼前这件事")
        humiliation = optional_modules.get("humiliation_reversal", {})
        if isinstance(humiliation, dict) and humiliation.get("harm_state"):
            return self._display_term(humiliation["harm_state"], "眼前这场羞辱")
        return "眼前这件事"

    def _witness_scope(self, optional_modules: dict[str, Any]) -> str:
        public = optional_modules.get("village_or_public_reputation", {})
        if isinstance(public, dict) and public.get("witnesses"):
            return self._display_term(public["witnesses"], "当前在场者")
        exposure = optional_modules.get("exposure_and_secrecy", {})
        if isinstance(exposure, dict) and exposure.get("witness_scope"):
            return self._display_term(exposure["witness_scope"], "当前在场者")
        return "家人或当前在场者"

    def _protected_actor(self, optional_modules: dict[str, Any], fallback: str) -> str:
        humiliation = optional_modules.get("humiliation_reversal", {})
        if isinstance(humiliation, dict) and humiliation.get("protected_actor"):
            return self._display_term(humiliation["protected_actor"], fallback)
        relationship = optional_modules.get("relationship_pressure", {})
        if isinstance(relationship, dict) and relationship.get("care_priority"):
            return self._display_term(relationship["care_priority"], fallback)
        return fallback

    def _display_term(self, value: object, fallback: str) -> str:
        text = str(value).strip()
        if not text:
            return fallback
        mapped = USER_FACING_TERM_MAP.get(text)
        if mapped is not None:
            return mapped
        if "/" in text:
            visible_parts = [part.strip() for part in text.split("/") if part.strip() and not self._has_latin(part)]
            if visible_parts:
                return "/".join(visible_parts)
        if self._has_latin(text):
            return fallback
        return text

    def _has_latin(self, text: str) -> bool:
        return any("a" <= char.lower() <= "z" for char in text)


class CabRuntimeJudgmentService(DeterministicJudgmentService):
    """Formal judgment path backed by a CABRuntime project.

    The public API shape stays Deadman-owned. CAB returns the adapter output;
    this service maps it into the existing viewer response and fails closed on
    runtime errors.
    """

    def __init__(self, store: DeadmanPackStore, runtime_client: Any | None = None) -> None:
        super().__init__(store)
        self.runtime_client = runtime_client or CabRuntimeWorkerClient()

    def judge(self, request: JudgmentRequest) -> JudgmentResponse:
        pack = self.store.get_drama(request.drama_id)
        moment = self.store.get_moment(request.drama_id, request.moment_id)
        self._validate_action(request, moment)
        try:
            adapter_input = build_adapter_input(
                request_id=f"{request.drama_id}:{request.moment_id}:{request.action.source}:{request.action.option_index}",
                drama_pack=pack,
                moment=moment,
                request=request,
            )
            runtime_result = self.runtime_client.judge(adapter_input)
        except AdapterMappingError as exc:
            raise PackStoreError(exc.code, exc.message, status_code=500) from exc
        except RuntimeClientError as exc:
            raise PackStoreError(
                exc.code,
                exc.message,
                status_code=502,
                retryable=exc.retryable,
            ) from exc
        return self._response_from_adapter_output(request, moment, pack.context, runtime_result.adapter_output)

    def judge_for_runtime(
        self,
        request: JudgmentRequest,
        *,
        viewer_session_id: str,
        event_id: str,
        host_state: dict[str, Any] | None = None,
    ) -> tuple[JudgmentResponse, bool]:
        pack = self.store.get_drama(request.drama_id)
        moment = self.store.get_moment(request.drama_id, request.moment_id)
        self._validate_action(request, moment)
        try:
            adapter_input = build_adapter_input(
                request_id=f"{request.drama_id}:{request.moment_id}:{request.action.source}:{request.action.option_index}",
                drama_pack=pack,
                moment=moment,
                request=request,
            )
            runtime_result = self.runtime_client.judge(
                adapter_input,
                viewer_session_id=viewer_session_id,
                event_id=event_id,
                host_state=host_state,
            )
        except AdapterMappingError as exc:
            raise PackStoreError(exc.code, exc.message, status_code=500) from exc
        except RuntimeClientError as exc:
            raise PackStoreError(
                exc.code,
                exc.message,
                status_code=502,
                retryable=exc.retryable,
            ) from exc
        return (
            self._response_from_adapter_output(request, moment, pack.context, runtime_result.adapter_output),
            runtime_result.host_should_persist,
        )

    def _response_from_adapter_output(
        self,
        request: JudgmentRequest,
        moment: dict[str, Any],
        context: dict[str, Any],
        adapter_output: dict[str, Any],
    ) -> JudgmentResponse:
        verdict = str(adapter_output.get("verdict") or "mixed")
        stance = self._stance_from_adapter_verdict(verdict)
        consequence_text = str(adapter_output.get("result_text") or "这一步只能按眼前这场来接。")
        companion_reaction = str(adapter_output.get("companion_reaction") or self._label(stance))
        why_this_happens = [str(item) for item in adapter_output.get("why_this_happens", []) if item]
        watch_flow_rationale = str(adapter_output.get("watch_flow_rationale") or self._original_plot_note(moment))
        visual_plan = adapter_output.get("visual_result_plan") if isinstance(adapter_output.get("visual_result_plan"), dict) else {}

        return JudgmentResponse(
            drama_id=request.drama_id,
            moment_id=request.moment_id,
            action=request.action,
            verdict=Verdict(
                label=self._label(stance),
                stance=stance,  # type: ignore[arg-type]
                summary=companion_reaction,
            ),
            consequence=Consequence(
                text=consequence_text,
                time_horizon="current_scene_or_immediate_aftermath",
                watch_flow_fit=self._watch_flow_fit_from_adapter_verdict(verdict),  # type: ignore[arg-type]
            ),
            canon_anchor=CanonAnchor(
                original_plot_note=watch_flow_rationale,
                safe_to_continue=True,
            ),
            scores=self._viewer_scores_from_adapter_verdict(verdict),
            result_card=ResultCard(
                mode="fallback_card",
                title=companion_reaction[:24] or self._label(stance),
                prompt=self._visual_prompt_from_plan(visual_plan, consequence_text),
            ),
            media=self._media_from_visual_plan(visual_plan),
            aggregate_stats=None,
            judgment_basis=JudgmentBasis(
                evidence_refs=self._evidence_refs(moment, context),
                applied_constraints=self._applied_constraints(context, moment),
                inference_notes=why_this_happens
                + [
                    "Judgment produced through CABRuntime adapter output.",
                    "The response is constrained to the current scene or immediate aftermath.",
                ],
                warnings=[str(item) for item in adapter_output.get("blocked_claims", [])],
            ),
            engine=EngineMetadata(
                mode="cab_runtime",
                schema_version="deadman_judgment_adapter_output.v0.1",
            ),
        )

    def _stance_from_adapter_verdict(self, verdict: str) -> str:
        if verdict == "invalid_or_overpowered":
            return "reject_softly"
        if verdict in {"credible_win", "credible_costly_win"}:
            return "support"
        return "caution"

    def _watch_flow_fit_from_adapter_verdict(self, verdict: str) -> str:
        if verdict == "invalid_or_overpowered":
            return "low"
        if verdict in {"credible_win", "credible_costly_win"}:
            return "high"
        return "medium"

    def _viewer_scores_from_adapter_verdict(self, verdict: str) -> dict[str, int]:
        if verdict == "invalid_or_overpowered":
            return {"爽度": 72, "可信度": 34, "风险": 92, "暴露度": 88, "关系冲击": 76, "回看顺滑度": 38}
        if verdict == "credible_costly_win":
            return {"爽度": 82, "可信度": 82, "风险": 46, "暴露度": 52, "关系冲击": 78, "回看顺滑度": 86}
        if verdict == "credible_win":
            return {"爽度": 78, "可信度": 86, "风险": 34, "暴露度": 42, "关系冲击": 72, "回看顺滑度": 88}
        return {"爽度": 66, "可信度": 64, "风险": 62, "暴露度": 58, "关系冲击": 60, "回看顺滑度": 68}

    def _media_from_visual_plan(self, visual_plan: dict[str, Any]) -> JudgmentMedia:
        prompt = self._visual_prompt_from_plan(visual_plan, "")
        mode = str(visual_plan.get("mode") or "plan_only")
        if mode == "preset_slot":
            return JudgmentMedia(
                status="placeholder",
                image_url="",
                prompt=prompt,
                source=str(visual_plan.get("provider_policy") or "not_connected"),
                fallback_text="CABRuntime 返回预置视觉槽计划；当前未接入真实图片生成。",
            )
        return JudgmentMedia(
            status="not_available",
            image_url="",
            prompt=prompt,
            source=str(visual_plan.get("provider_policy") or "not_connected"),
            fallback_text="CABRuntime 返回文字判断；视觉结果本轮不生成。",
        )

    def _visual_prompt_from_plan(self, visual_plan: dict[str, Any], fallback: str) -> str:
        prompt_plan = visual_plan.get("visual_prompt_plan")
        if isinstance(prompt_plan, dict) and prompt_plan.get("prompt_text"):
            return str(prompt_plan["prompt_text"])
        return fallback or "结果图只可作为演示插图，不能当作剧情证据。"


def _reply_candidates(moment: dict[str, Any]) -> list[dict[str, Any]]:
    exchange = moment.get("companion_exchange")
    if isinstance(exchange, dict) and isinstance(exchange.get("reply_candidates"), list):
        return [item for item in exchange["reply_candidates"] if isinstance(item, dict)]
    action_space = moment.get("action_space")
    candidates = action_space.get("mouthpiece_candidates", []) if isinstance(action_space, dict) else []
    if not isinstance(candidates, list):
        return []
    return [item for item in candidates if isinstance(item, dict)]
