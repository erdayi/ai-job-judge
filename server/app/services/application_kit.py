from __future__ import annotations

from app.models import ApplicationKitRequest, ApplicationKitResponse, ResumeProfile
from app.services.claude_cli import claude_cli_client
from app.services.llm import llm_client
from app.services.resume import DEFAULT_PROFILE, _sanitize_profile
from app.settings import settings


async def generate_application_kit(
    request: ApplicationKitRequest,
    profile: ResumeProfile | None,
    resume_text: str | None,
) -> ApplicationKitResponse:
    profile = _sanitize_profile(profile or request.profile or DEFAULT_PROFILE.model_copy(deep=True))
    diagnostics: list[str] = []
    if settings.ranker_provider.lower() in {"claude", "auto"} and claude_cli_client.enabled:
        try:
            payload = await claude_cli_client.json_prompt(
                _application_kit_prompt(request, profile, resume_text),
                _application_kit_schema(),
            )
            return _response_from_payload(payload, source="claude")
        except Exception as exc:
            diagnostics.append(f"Claude application kit failed: {str(exc)[-500:]}")

    if llm_client.enabled:
        try:
            payload = await llm_client.json_chat(
                system=(
                    "你是求职投递材料助手。根据简历、岗位详情和已有匹配分析，生成可执行的投递准备材料。"
                    "不要编造简历没有体现的经历、指标或技能。输出必须是 JSON。"
                ),
                user=_application_kit_prompt(request, profile, resume_text),
                schema_name="application_kit",
                schema=_application_kit_schema(),
            )
            return _response_from_payload(payload, source="llm")
        except Exception as exc:
            diagnostics.append(f"LLM application kit failed: {str(exc)[-500:]}")

    response = heuristic_application_kit(request, profile)
    response.diagnostics = diagnostics
    return response


def heuristic_application_kit(request: ApplicationKitRequest, profile: ResumeProfile | None = None) -> ApplicationKitResponse:
    job = request.job
    profile = _sanitize_profile(profile or request.profile or DEFAULT_PROFILE.model_copy(deep=True))
    text = f"{job.title}\n{job.description}\n{job.requirements}\n{' '.join(job.skills)}".lower()
    matched_skills = [skill for skill in profile.core_skills + profile.secondary_skills if skill.lower() in text or skill in text]
    project_hits = [word for word in profile.project_keywords if word.lower() in text or word in text]
    risk_points = list(dict.fromkeys(request.risks + [item for item in profile.negative_directions if item.lower() in text or item in text]))
    focus = []
    if matched_skills:
        focus.append(f"突出与岗位直接相关的技术栈：{', '.join(matched_skills[:8])}")
    if project_hits:
        focus.append(f"把项目描述靠近岗位关键词：{', '.join(project_hits[:6])}")
    focus.append("优先呈现最近 AI 应用研发、Agent/RAG、后端工程化和业务落地经历。")
    missing = request.missing_skills or [skill for skill in profile.core_skills[:6] if skill not in matched_skills][:3]
    title = job.title or "该岗位"
    company = f"{job.company} " if job.company else ""
    decision_text = _decision_text(request.decision)
    return ApplicationKitResponse(
        source="heuristic",
        fit_summary=f"{company}{title}当前判断为{decision_text}，匹配分 {request.score if request.score is not None else 0}。重点依据是：{_join_or_default(request.reasons, '岗位方向与简历画像存在一定相关性')}。",
        resume_focus=focus,
        cover_note=(
            f"您好，我关注到{company}{title}。我的经历主要集中在 AI 应用研发、Agent/RAG 工程化、"
            "后端服务与异步任务治理方向，曾参与大模型应用、检索增强、智能工作流和高并发链路建设。"
            "我希望结合过往项目中的工程落地经验，支持该岗位相关系统的稳定交付与持续优化。"
        ),
        interview_prep=[
            "准备 1-2 个最贴近 JD 的项目，按背景、技术方案、工程难点、结果指标讲清楚。",
            "复盘岗位要求中涉及的核心技术，并补充自己在项目中真实使用过的细节。",
            "准备为什么选择该公司/岗位，以及自己能在入职后优先贡献什么。",
        ],
        keywords_to_add=list(dict.fromkeys(matched_skills + project_hits))[:10],
        risk_mitigation=[
            f"风险：{risk}" for risk in risk_points[:5]
        ] + ([f"缺口：{', '.join(missing[:5])}。建议用学习计划或相近项目经验解释，不要硬写成已掌握。"] if missing else []),
        questions_to_prepare=[
            "这个岗位最核心的业务场景和当前技术挑战是什么？",
            "团队的大模型/Agent/RAG 能力是自研、平台化还是业务侧集成？",
            "新人会更偏工程交付、算法落地、平台建设，还是业务工具链？",
        ],
    )


def _application_kit_schema() -> dict:
    array = {"type": "array", "items": {"type": "string"}}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "fit_summary": {"type": "string"},
            "resume_focus": array,
            "cover_note": {"type": "string"},
            "interview_prep": array,
            "keywords_to_add": array,
            "risk_mitigation": array,
            "questions_to_prepare": array,
            "no_fabrication_warning": {"type": "string"},
        },
        "required": [
            "fit_summary",
            "resume_focus",
            "cover_note",
            "interview_prep",
            "keywords_to_add",
            "risk_mitigation",
            "questions_to_prepare",
            "no_fabrication_warning",
        ],
    }


def _application_kit_prompt(request: ApplicationKitRequest, profile: ResumeProfile, resume_text: str | None) -> str:
    return (
        "你是一个严谨的求职投递材料助手。请基于简历、岗位详情和已有匹配分析，生成一份投递材料包。\n"
        "要求：\n"
        "1. 只根据输入内容分析，不要编造候选人没有的经历、指标、奖项、技能或公司背景。\n"
        "2. cover_note 是一段可直接放进投递备注/求职信的中文短文，控制在 120-220 字。\n"
        "3. resume_focus 是简历微调方向，不要让用户虚构，只建议突出已有经历。\n"
        "4. risk_mitigation 要把岗位风险和缺口转换成真实可解释的补强方式。\n"
        "5. questions_to_prepare 要适合投递前或面试前准备。\n"
        "6. 输出只能是符合 JSON Schema 的 JSON，不要 Markdown。\n\n"
        f"简历画像 JSON:\n{profile.model_dump()}\n\n"
        f"简历全文或抽取文本（可能截断）:\n{(resume_text or '')[:14000]}\n\n"
        f"岗位 JSON:\n{request.job.model_dump()}\n\n"
        f"已有匹配分析:\nscore={request.score}, decision={request.decision}, "
        f"reasons={request.reasons}, risks={request.risks}, missing_skills={request.missing_skills}\n\n"
        f"用户备注:\n{request.notes or ''}"
    )


def _response_from_payload(payload: dict, source: str) -> ApplicationKitResponse:
    return ApplicationKitResponse(
        source=source,
        fit_summary=payload.get("fit_summary", ""),
        resume_focus=payload.get("resume_focus", []),
        cover_note=payload.get("cover_note", ""),
        interview_prep=payload.get("interview_prep", []),
        keywords_to_add=payload.get("keywords_to_add", []),
        risk_mitigation=payload.get("risk_mitigation", []),
        questions_to_prepare=payload.get("questions_to_prepare", []),
        no_fabrication_warning=payload.get("no_fabrication_warning", "不要编造简历中没有体现的经历、指标或技能。"),
    )


def _decision_text(value: str | None) -> str:
    if value == "recommend":
        return "推荐投递"
    if value == "reject":
        return "暂不建议投递"
    return "可以进一步确认"


def _join_or_default(items: list[str], fallback: str) -> str:
    return "；".join(items[:4]) if items else fallback
