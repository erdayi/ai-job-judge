from __future__ import annotations

import re
from io import BytesIO
from typing import Any

from docx import Document
from fastapi import UploadFile
from pypdf import PdfReader

from app.models import ResumeProfile
from app.services.claude_cli import claude_cli_client
from app.services.llm import llm_client


DEFAULT_PROFILE = ResumeProfile(
    target_roles=["AI应用研发工程师", "大模型应用开发工程师", "Agent开发工程师", "Java/Python后端研发工程师"],
    core_skills=["Python", "Java", "LLM", "RAG", "Agent", "模型部署", "推理服务", "后端服务"],
    secondary_skills=["FastAPI", "Spring Boot", "PyTorch", "向量数据库", "Docker", "数据处理"],
    project_keywords=["大模型", "知识库", "问答", "推荐", "检索", "后端服务", "工程化"],
    negative_directions=["销售", "营销", "市场", "运营", "纯测试", "硬件", "嵌入式", "C++主导", "外包", "驻场"],
    ranking_weights={
        "role_direction": 35,
        "core_skill_match": 30,
        "project_relevance": 20,
        "location_or_company": 10,
        "risk_penalty": 5,
    },
)


async def extract_resume_text(upload: UploadFile | None = None, text: str | None = None) -> str:
    if text and text.strip():
        return normalize_text(text)
    if not upload:
        return ""

    content = await upload.read()
    filename = (upload.filename or "").lower()
    if filename.endswith(".pdf"):
        return normalize_text(_read_pdf(content))
    if filename.endswith(".docx"):
        return normalize_text(_read_docx(content))
    return normalize_text(content.decode("utf-8", errors="ignore"))


def _read_pdf(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_docx(content: bytes) -> str:
    doc = Document(BytesIO(content))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def normalize_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text.replace("\r", "\n")).strip()


async def generate_resume_rules(resume_text: str) -> tuple[ResumeProfile, dict[str, Any], str]:
    if claude_cli_client.enabled:
        try:
            payload = await claude_cli_client.json_prompt(
                _resume_rules_prompt(resume_text),
                _resume_rules_schema(),
            )
            profile = _sanitize_profile(ResumeProfile.model_validate(payload))
            return profile, profile.model_dump(), "claude"
        except Exception:
            pass

    if llm_client.enabled:
        try:
            payload = await llm_client.json_chat(
                system=(
                    "你是求职岗位匹配规则生成器。根据简历生成可被程序执行的岗位匹配规则。"
                    "不要编造简历没有体现的核心能力。不要把 C++ 默认作为目标岗位，除非简历明确以 C++ 岗位为目标。输出必须是 JSON。"
                ),
                user=(
                    "请基于以下简历生成匹配规则。优先从简历标题、求职方向、最近实习和项目中提炼目标。"
                    "如果 C++ 只是岗位描述中的可选语言或非主线经历，不要放入 core_skills 或 target_roles；"
                    "可将 C++主导/嵌入式C++ 放入 negative_directions。\n\n"
                    f"{resume_text[:12000]}"
                ),
                schema_name="resume_profile_rules",
                schema=_resume_rules_schema(),
            )
            profile = _sanitize_profile(ResumeProfile.model_validate(payload))
            return profile, payload, "llm"
        except Exception:
            pass

    profile = _sanitize_profile(heuristic_resume_rules(resume_text))
    return profile, profile.model_dump(), "heuristic"


def heuristic_resume_rules(resume_text: str) -> ResumeProfile:
    text = resume_text.lower()
    profile = DEFAULT_PROFILE.model_copy(deep=True)
    core_candidates = [
        "Python",
        "Java",
        "RAG",
        "LLM",
        "Agent",
        "Spring Boot",
        "FastAPI",
        "Django",
        "Flask",
    ]
    secondary_candidates = [
        "C++",
        "PyTorch",
        "TensorFlow",
        "Docker",
        "Kubernetes",
        "MySQL",
        "Redis",
        "向量数据库",
        "Elasticsearch",
        "Kafka",
        "RocketMQ",
    ]
    detected_core = [skill for skill in core_candidates if skill.lower() in text or skill in resume_text]
    detected_secondary = [skill for skill in secondary_candidates if skill.lower() in text or skill in resume_text]
    if detected_core:
        profile.core_skills = list(dict.fromkeys(detected_core + profile.core_skills))[:12]
    if detected_secondary:
        profile.secondary_skills = list(dict.fromkeys(detected_secondary + profile.secondary_skills))[:12]
    return profile


def _resume_rules_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "target_roles": {"type": "array", "items": {"type": "string"}},
            "core_skills": {"type": "array", "items": {"type": "string"}},
            "secondary_skills": {"type": "array", "items": {"type": "string"}},
            "project_keywords": {"type": "array", "items": {"type": "string"}},
            "negative_directions": {"type": "array", "items": {"type": "string"}},
            "ranking_weights": {"type": "object", "additionalProperties": {"type": "integer"}},
        },
        "required": [
            "target_roles",
            "core_skills",
            "secondary_skills",
            "project_keywords",
            "negative_directions",
            "ranking_weights",
        ],
    }


def _resume_rules_prompt(resume_text: str) -> str:
    return (
        "你是求职岗位匹配规则生成器。请根据简历生成可被程序执行的个人岗位匹配规则。\n"
        "重要要求：\n"
        "1. 目标岗位必须来自简历里的求职方向、最近实习、项目主线，不要使用系统默认目标。\n"
        "2. 不要默认加入 C++。只有当简历明确表达要投 C++ 开发岗位时，才把 C++ 放入 target_roles/core_skills。\n"
        "3. 如果 C++ 只是可选语言、课程、算法/历史项目里的辅助能力，应放入 secondary_skills，"
        "并把 C++主导、嵌入式C++、底层驱动 等放入 negative_directions。\n"
        "4. 对这类简历通常应优先关注 AI应用研发、Agent/RAG、大模型应用工程化、Java/Python后端、工程化落地。\n"
        "5. 输出只能是符合 JSON Schema 的 JSON。\n\n"
        f"简历文本：\n{resume_text[:14000]}"
    )


def _sanitize_profile(profile: ResumeProfile) -> ResumeProfile:
    def remove_cpp_target(values: list[str]) -> list[str]:
        result = []
        for value in values:
            lowered = value.lower()
            if "c++" in lowered or "c/c++" in lowered:
                continue
            result.append(value)
        return result

    profile.target_roles = remove_cpp_target(profile.target_roles) or DEFAULT_PROFILE.target_roles
    profile.core_skills = remove_cpp_target(profile.core_skills)
    if not profile.core_skills:
        profile.core_skills = DEFAULT_PROFILE.core_skills
    profile.negative_directions = list(
        dict.fromkeys(profile.negative_directions + ["C++主导", "嵌入式C++", "底层驱动", "硬件"])
    )
    return profile
