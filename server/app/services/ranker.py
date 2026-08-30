from __future__ import annotations

from app.models import FinalResult, JobMatch, RankResponse, ResumeProfile
from app.services.claude_cli import claude_cli_client
from app.services.llm import llm_client
from app.services.resume import DEFAULT_PROFILE, _sanitize_profile
from app.settings import settings


async def rank_jobs(
    matches: list[JobMatch],
    profile: ResumeProfile | None,
    top_n: int,
    resume_text: str | None = None,
) -> RankResponse:
    top_n = max(1, min(top_n, 50))
    profile = _sanitize_profile(profile or DEFAULT_PROFILE.model_copy(deep=True))
    candidates = _select_rank_candidates(matches, top_n)
    diagnostics: list[str] = []
    if settings.ranker_provider.lower() in {"claude", "auto"} and candidates and claude_cli_client.enabled:
        try:
            return await _claude_rank(candidates, profile, top_n, resume_text)
        except Exception as exc:
            diagnostics.append(f"Claude ranker failed: {str(exc)[-500:]}")
    if llm_client.enabled and candidates:
        try:
            return await _llm_rank(candidates, profile, top_n)
        except Exception as exc:
            diagnostics.append(f"LLM ranker failed: {str(exc)[-500:]}")
    response = _heuristic_rank(candidates, top_n)
    response.diagnostics = diagnostics
    return response


def _rank_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "rank": {"type": "integer"},
                        "score": {"type": "integer"},
                        "decision": {"type": "string", "enum": ["recommend", "maybe", "reject"]},
                        "title": {"type": "string"},
                        "company": {"type": ["string", "null"]},
                        "reasons": {"type": "array", "items": {"type": "string"}},
                        "risks": {"type": "array", "items": {"type": "string"}},
                        "missing_skills": {"type": "array", "items": {"type": "string"}},
                        "job_url": {"type": ["string", "null"]},
                    },
                    "required": [
                        "rank",
                        "score",
                        "decision",
                        "title",
                        "company",
                        "reasons",
                        "risks",
                        "missing_skills",
                        "job_url",
                    ],
                },
            }
        },
        "required": ["results"],
    }


def _select_rank_candidates(matches: list[JobMatch], top_n: int) -> list[JobMatch]:
    ordered = sorted(matches, key=lambda item: item.score, reverse=True)
    positives = [match for match in ordered if match.decision != "reject"]
    rejects = [match for match in ordered if match.decision == "reject"]
    candidate_limit = max(top_n, min(16, top_n * 3))
    selected = positives[:candidate_limit]
    if len(selected) < top_n:
        selected.extend(rejects[: top_n - len(selected)])
    elif top_n <= 10:
        selected.extend(rejects[: min(3, len(rejects))])
    return selected[: max(top_n, candidate_limit)]


async def _claude_rank(
    matches: list[JobMatch],
    profile: ResumeProfile | None,
    top_n: int,
    resume_text: str | None,
) -> RankResponse:
    candidate_jobs = [
        {
            "title": match.job.title,
            "company": match.job.company,
            "department": match.job.department,
            "location": match.job.location,
            "description": match.job.description,
            "requirements": match.job.requirements,
            "skills": match.job.skills,
            "detail_url": match.job.detail_url,
            "apply_url": match.job.apply_url,
            "source_url": match.job.source_url,
            "confidence": match.job.confidence,
        }
        for match in matches
    ]
    prompt = (
        "你是求职岗位精排器。请根据简历画像和候选岗位，输出最值得投递的 Top N。\n"
        "要求：\n"
        "1. 只依据候选岗位中每条岗位自己的 title/description/requirements/skills 判断，不要把不同岗位信息混用。\n"
        "2. 优先遵循简历画像里的 target_roles、core_skills、project_keywords 和 negative_directions。\n"
        "3. 不要把 C++ 当作默认目标；如果岗位是 C++ 主导、嵌入式、底层驱动，而简历画像没有明确要求 C++ 岗位，应明显降权或 reject。\n"
        "4. 如果 JD 只是写“包括但不限于 Java、C/C++、Python”等泛语言要求，C/C++ 只能视为可选语言，不能写成 Python/C++ 研发目标或核心推荐理由。\n"
        "5. 对营销、销售、产品经理、运营、纯测试、硬件、嵌入式、外包驻场明显降权或 reject。\n"
        "6. 如果岗位命中 negative_directions 且没有开发/工程/算法/AI 应用职责，必须 reject，分数不超过 30，不能给 maybe。\n"
        "7. 分数 0-100；recommend 通常 >=72，maybe 50-71，reject <50。\n"
        "8. 必须保留原岗位链接，不要虚构岗位。\n"
        "9. reasons 要写成具体的人类分析，不要照抄关键词命中模板，不要出现“Python/C++研发工程师”这类未在简历目标中明确出现的表述。\n"
        "10. 如果岗位 JD 信息很泛，要明确说明不确定点，而不是过度推荐。\n"
        "11. 只输出符合 JSON Schema 的 JSON，不要 Markdown。\n\n"
        f"Top N: {top_n}\n\n"
        f"简历画像 JSON:\n{(profile.model_dump() if profile else {})}\n\n"
        f"简历全文或抽取文本（可能截断）:\n{(resume_text or '')[:14000]}\n\n"
        f"候选岗位 JSON（不要混用不同岗位信息）:\n{candidate_jobs}"
    )
    payload = await claude_cli_client.json_prompt(prompt, _rank_schema())
    return _rank_response_from_payload(payload, matches, top_n, source="claude")


async def _llm_rank(matches: list[JobMatch], profile: ResumeProfile | None, top_n: int) -> RankResponse:
    payload = await llm_client.json_chat(
        system=(
            "你是求职岗位精排器。根据简历画像和候选岗位，输出最值得投递的 Top N。"
            "必须保留岗位原链接，不要虚构岗位信息。"
        ),
        user=f"简历画像：{(profile.model_dump() if profile else {})}\n\n候选岗位：{[m.model_dump() for m in matches]}\n\nTop N={top_n}",
        schema_name="ranked_jobs",
        schema=_rank_schema(),
    )
    return _rank_response_from_payload(payload, matches, top_n, source="llm")


def _rank_response_from_payload(payload: dict, matches: list[JobMatch], top_n: int, source: str) -> RankResponse:
    fallback = _heuristic_rank(matches, top_n)
    results: list[FinalResult] = []
    for item in payload.get("results", [])[:top_n]:
        match = _find_match_for_rank_item(item, matches)
        if not match:
            continue
        score, decision, risks = _guard_rank_item(item, match)
        results.append(
            FinalResult(
                rank=item["rank"],
                score=score,
                decision=decision,
                title=item["title"],
                company=item.get("company"),
                reasons=item.get("reasons", []),
                risks=risks,
                missing_skills=item.get("missing_skills", []),
                job_url=_preferred_job_url(match, item.get("job_url")),
                job=match.job,
            )
        )
    if not results:
        return fallback
    if len(results) < min(top_n, len(matches)):
        _append_missing_fallback_results(results, matches, top_n)
    return RankResponse(results=results, source=source)


def _append_missing_fallback_results(results: list[FinalResult], matches: list[JobMatch], top_n: int) -> None:
    seen_titles = {_norm(item.title) for item in results}
    seen_urls = {item.job_url for item in results if item.job_url}
    for match in sorted(matches, key=lambda item: item.score, reverse=True):
        url = _preferred_job_url(match)
        if _norm(match.job.title) in seen_titles or (url and url in seen_urls):
            continue
        results.append(
            FinalResult(
                rank=len(results) + 1,
                score=match.score,
                decision=match.decision,
                title=match.job.title,
                company=match.job.company,
                reasons=match.reasons,
                risks=match.risks + ["Claude 返回结果少于候选数量，已用本地规则补齐该岗位"],
                missing_skills=match.missing_skills,
                job_url=url,
                job=match.job,
            )
        )
        seen_titles.add(_norm(match.job.title))
        if url:
            seen_urls.add(url)
        if len(results) >= top_n:
            break


def _find_match_for_rank_item(item: dict, matches: list[JobMatch]) -> JobMatch | None:
    title = item.get("title")
    if title:
        title_key = _norm(title)
        exact = next((match for match in matches if _norm(match.job.title) == title_key), None)
        if exact:
            return exact
        fuzzy = next((match for match in matches if title_key in _norm(match.job.title) or _norm(match.job.title) in title_key), None)
        if fuzzy:
            return fuzzy

    url = item.get("job_url")
    if url:
        url_matches = [
            match
            for match in matches
            if url in {match.job.detail_url, match.job.apply_url}
        ]
        if len(url_matches) == 1:
            return url_matches[0]
    return None


def _guard_rank_item(item: dict, match: JobMatch) -> tuple[int, str, list[str]]:
    score = int(item.get("score", match.score))
    decision = item.get("decision", match.decision)
    risks = list(item.get("risks", []))
    hard_negative = match.decision == "reject" and match.score < 40
    if hard_negative:
        score = min(score, 30)
        decision = "reject"
        if match.risks:
            risks.extend([risk for risk in match.risks if risk not in risks])
        risks.append("命中本地硬过滤，Claude 不能将明显不匹配岗位提升为可考虑")
    return score, decision, risks


def _preferred_job_url(match: JobMatch, model_url: str | None = None) -> str | None:
    for url in [match.job.detail_url, model_url, match.job.apply_url, match.job.source_url]:
        if _is_detail_url(url):
            return url
    return match.job.detail_url or model_url or match.job.apply_url or match.job.source_url


def _is_detail_url(url: str | None) -> bool:
    if not url:
        return False
    lowered = str(url).lower().replace("#", "/")
    if "/detail" in lowered:
        return True
    return any(key in lowered for key in ["jobadid=", "jobid=", "job_id=", "positionid=", "position_id=", "recruitjobid="])


def _norm(value: str | None) -> str:
    return "".join(str(value or "").split()).lower()


def _heuristic_rank(matches: list[JobMatch], top_n: int) -> RankResponse:
    results: list[FinalResult] = []
    for index, match in enumerate(sorted(matches, key=lambda item: item.score, reverse=True)[:top_n], start=1):
        results.append(
            FinalResult(
                rank=index,
                score=match.score,
                decision=match.decision,
                title=match.job.title,
                company=match.job.company,
                reasons=match.reasons,
                risks=match.risks,
                missing_skills=match.missing_skills,
                job_url=match.job.detail_url or match.job.apply_url or match.job.source_url,
                job=match.job,
            )
        )
    return RankResponse(results=results, source="heuristic")
