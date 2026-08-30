from __future__ import annotations

import re

from app.models import JobItem, JobMatch, ResumeProfile
from app.services.resume import DEFAULT_PROFILE, _sanitize_profile

TECH_DIRECTION_HINTS = ["研发", "开发", "算法", "工程师", "大模型", "后端"]
BUILTIN_NEGATIVE_HINTS = [
    "销售",
    "营销",
    "市场推广",
    "运营",
    "产品方向",
    "产品类",
    "商业敏锐",
    "客户拓展",
    "测试",
    "硬件",
    "嵌入式",
    "c++主导",
    "底层驱动",
    "外包",
    "驻场",
]


def match_jobs(jobs: list[JobItem], profile: ResumeProfile | None = None, max_candidates: int = 30) -> list[JobMatch]:
    profile = _sanitize_profile(profile or DEFAULT_PROFILE.model_copy(deep=True))
    matches = [_match_one(job, profile) for job in jobs]
    matches.sort(key=lambda item: item.score, reverse=True)
    non_rejects = [item for item in matches if item.decision != "reject"]
    rejects = [item for item in matches if item.decision == "reject"]
    return (non_rejects + rejects)[:max_candidates]


def _match_one(job: JobItem, profile: ResumeProfile) -> JobMatch:
    title_text = _normalize(job.title)
    haystack = _normalize(" ".join([job.title, job.description, job.requirements, " ".join(job.skills)]))
    score = 35
    reasons: list[str] = []
    risks: list[str] = []
    missing: list[str] = []
    has_sparse_detail = len(job.description) < 140 and len(job.requirements) < 80

    for role in profile.target_roles:
        if _contains_any(haystack, _tokenize(role)):
            score += 10
            reasons.append(f"岗位方向接近：{role}")
            break

    direction_source = title_text
    if job.department:
        direction_source += " " + _normalize(job.department)
    if "研发类" in haystack:
        direction_source += " 研发类"
    direction_hits = [hint for hint in TECH_DIRECTION_HINTS if hint in direction_source]
    if direction_hits:
        score += 12
        reasons.append("岗位标题/类别偏技术研发：" + "、".join(direction_hits[:3]))

    core_hits = [skill for skill in profile.core_skills if _contains_skill(haystack, skill)]
    secondary_hits = [skill for skill in profile.secondary_skills if _contains_skill(haystack, skill)]
    project_hits = [word for word in profile.project_keywords if word and word.lower() in haystack]
    negative_pool = list(dict.fromkeys(profile.negative_directions + BUILTIN_NEGATIVE_HINTS))
    negative_hits = [word for word in negative_pool if word and word.lower() in haystack]
    if _is_cpp_dominant(haystack, profile):
        negative_hits.append("C++主导")

    score += min(len(core_hits) * 8, 32)
    score += min(len(secondary_hits) * 4, 16)
    score += min(len(project_hits) * 5, 15)
    score -= min(len(negative_hits) * 18, 45)

    if core_hits:
        reasons.append("核心技能命中：" + "、".join(core_hits[:6]))
    else:
        if has_sparse_detail and direction_hits:
            risks.append("列表信息较少，尚未看到具体技术栈，需要进入详情确认")
            score -= 4
        else:
            risks.append("未明显命中简历核心技能")
            score -= 12
    if secondary_hits:
        reasons.append("辅助技能命中：" + "、".join(secondary_hits[:5]))
    if project_hits:
        reasons.append("项目关键词相关：" + "、".join(project_hits[:5]))
    if negative_hits:
        risks.append("触发降权方向：" + "、".join(negative_hits[:5]))

    missing = [skill for skill in profile.core_skills[:8] if skill not in core_hits][:4]
    if has_sparse_detail:
        risks.append("岗位描述较短，匹配置信度较低")
        score -= 3 if direction_hits else 8

    if has_sparse_detail and direction_hits and not negative_hits:
        score = max(score, 52)

    score = max(0, min(100, score))
    decision = "recommend" if score >= 72 else "maybe" if score >= 50 else "reject"
    return JobMatch(job=job, score=score, decision=decision, reasons=reasons, risks=risks, missing_skills=missing)


def _contains_skill(text: str, skill: str) -> bool:
    needle = skill.lower()
    if needle in {"c++", "c#"}:
        return needle in text
    if re.fullmatch(r"[a-z0-9+#. -]+", needle):
        return re.search(rf"(?<![a-z0-9+#]){re.escape(needle)}(?![a-z0-9+#])", text) is not None
    return needle in text


def _contains_any(text: str, tokens: list[str]) -> bool:
    return any(token.lower() in text for token in tokens if len(token.strip()) >= 2)


def _tokenize(value: str) -> list[str]:
    return re.split(r"[/,，、\s]+", value)


def _normalize(value: str) -> str:
    return value.lower()


def _is_cpp_dominant(text: str, profile: ResumeProfile) -> bool:
    has_cpp = "c++" in text or "c/c++" in text
    if not has_cpp:
        return False
    user_targets_cpp = any("c++" in item.lower() or "c/c++" in item.lower() for item in profile.target_roles + profile.core_skills)
    if user_targets_cpp:
        return False
    cpp_context = any(word in text for word in ["嵌入式", "底层", "驱动", "音视频", "图形", "客户端", "高性能c++", "c++开发"])
    python_java_context = any(word in text for word in ["python", "java", "agent", "rag", "llm", "大模型", "后端"])
    return cpp_context or not python_java_context
