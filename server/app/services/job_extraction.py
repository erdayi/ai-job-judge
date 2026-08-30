from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin, urlparse

from app.models import JobItem, JobsExtractResponse, PageSnapshot
from app.services.llm import llm_client
from app.services.page_analysis import analyze_page


TITLE_HINT = re.compile(
    r"(?P<title>[\w\u4e00-\u9fa5/+\-#（）()·— ]{2,70}(工程师|研发|开发|算法|实习生|实习|研究员|架构师|后端|客户端|大模型|AI|机器学习|数据科学|数据分析|平台|管培生|岗位|方向|科学家)(?:[\w\u4e00-\u9fa5/+\-#（）()·— ]{0,24})?)",
    re.I,
)
LIST_JOB_TITLE = re.compile(
    r"^[\w\u4e00-\u9fa5/+\-#（）()·— ]{2,90}(?:\([A-Z]?\d{3,}\)|（[A-Z]?\d{3,}）|\(J\d+\)|（J\d+）|工程师|研发|开发|算法|实习生|实习|研究员|架构师|后端|客户端|大模型|AI|机器学习|数据科学|数据分析|平台|管培生|岗位|方向|科学家)[\w\u4e00-\u9fa5/+\-#（）()·— ]{0,24}$",
    re.I,
)
SKILL_PATTERN = re.compile(
    r"Python|C\+\+|Java\b|Golang|Go\b|JavaScript|TypeScript|React|Vue|LLM|RAG|Agent|PyTorch|TensorFlow|Docker|Kubernetes|MySQL|Redis|向量数据库|大模型|机器学习|深度学习|NLP",
    re.I,
)
LOCATION_PATTERN = re.compile(r"北京|上海|深圳|广州|杭州|南京|成都|武汉|西安|苏州|远程|Remote|北京|上海")
DEPARTMENT_PATTERN = re.compile(r"研发类|技术类|算法类|产品类|营销类|销售类|职能类|设计类|运营类|工程类|数据类")


def extract_jobs(snapshot: PageSnapshot) -> JobsExtractResponse:
    jobs: list[JobItem] = []
    seen: set[str] = set()
    for job in _jobs_from_visible_lines(snapshot):
        key = _job_key(job)
        if key in seen:
            continue
        seen.add(key)
        jobs.append(job)

    for block in snapshot.blocks:
        job = _job_from_text(block.text, snapshot.url, block.links)
        if not job:
            continue
        key = _job_key(job)
        if key in seen:
            continue
        seen.add(key)
        jobs.append(job)

    if not jobs:
        jobs.extend(_jobs_from_links(snapshot))

    return JobsExtractResponse(jobs=jobs[:120], pagination=analyze_page(snapshot).pagination, source="heuristic")


def _current_detail_url(snapshot: PageSnapshot) -> str | None:
    parsed = urlparse(snapshot.url)
    lowered = f"{parsed.path}?{parsed.query}".lower()
    if "/detail" in lowered and any(
        key in lowered for key in ["jobadid=", "jobid=", "job_id=", "positionid=", "position_id=", "recruitjobid="]
    ):
        return snapshot.url
    return None


async def extract_jobs_with_fallback(snapshot: PageSnapshot) -> JobsExtractResponse:
    heuristic = extract_jobs(snapshot)
    if heuristic.jobs or not llm_client.enabled:
        return heuristic
    try:
        payload = await llm_client.json_chat(
            system=(
                "你是网页岗位信息抽取器。请从页面文本和链接中抽取招聘岗位。"
                "只输出页面真实存在的信息，不要编造。"
            ),
            user=(
                f"URL: {snapshot.url}\n标题: {snapshot.title}\n"
                f"页面文本:\n{snapshot.visible_text[:18000]}\n\n"
                f"链接候选:\n{[link.model_dump() for link in snapshot.links[:80]]}"
            ),
            schema_name="job_extraction",
            schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "jobs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "title": {"type": "string"},
                                "company": {"type": ["string", "null"]},
                                "department": {"type": ["string", "null"]},
                                "location": {"type": ["string", "null"]},
                                "description": {"type": "string"},
                                "requirements": {"type": "string"},
                                "skills": {"type": "array", "items": {"type": "string"}},
                                "detail_url": {"type": ["string", "null"]},
                                "apply_url": {"type": ["string", "null"]},
                                "confidence": {"type": "number"},
                            },
                            "required": [
                                "title",
                                "company",
                                "department",
                                "location",
                                "description",
                                "requirements",
                                "skills",
                                "detail_url",
                                "apply_url",
                                "confidence",
                            ],
                        },
                    }
                },
                "required": ["jobs"],
            },
        )
        jobs = [
            JobItem(
                **item,
                source_url=snapshot.url,
                detail_url=urljoin(snapshot.url, item["detail_url"]) if item.get("detail_url") else None,
                apply_url=urljoin(snapshot.url, item["apply_url"]) if item.get("apply_url") else None,
            )
            for item in payload.get("jobs", [])
            if item.get("title")
        ]
        return JobsExtractResponse(jobs=jobs[:120], pagination=analyze_page(snapshot).pagination, source="llm")
    except Exception:
        return heuristic


def merge_job_details(base_jobs: list[JobItem], detail_jobs: list[JobItem]) -> list[JobItem]:
    by_url = {job.detail_url or job.source_url or job.title: job for job in base_jobs}
    for detail in detail_jobs:
        key = detail.source_url or detail.detail_url or detail.title
        if key in by_url:
            original = by_url[key]
            original.description = _longer(original.description, detail.description)
            original.requirements = _longer(original.requirements, detail.requirements)
            original.skills = list(dict.fromkeys(original.skills + detail.skills))
            original.confidence = max(original.confidence, detail.confidence)
        else:
            by_url[key] = detail
    return list(by_url.values())


def _job_from_text(text: str, source_url: str, links) -> JobItem | None:
    clean = _compact(text)
    if len(clean) < 12:
        return None
    title = _detect_title(clean)
    if not title:
        return None
    skills = list(dict.fromkeys(match.group(0) for match in SKILL_PATTERN.finditer(clean)))
    location = _first_match(LOCATION_PATTERN, clean)
    detail_url = _best_detail_url(links, source_url)
    requirements = _section(clean, ["任职要求", "岗位要求", "要求", "Qualifications", "Requirements"])
    description = clean[:3000]
    confidence = 0.85 if skills and detail_url else 0.65 if skills else 0.5
    return JobItem(
        id=_hash(f"{title}|{detail_url or source_url}|{clean[:80]}"),
        title=title,
        location=location,
        description=description,
        requirements=requirements,
        skills=skills,
        detail_url=detail_url,
        apply_url=_best_apply_url(links, source_url),
        source_url=source_url,
        confidence=confidence,
    )


def _jobs_from_visible_lines(snapshot: PageSnapshot) -> list[JobItem]:
    lines = [line.strip() for line in snapshot.visible_text.splitlines() if line.strip()]
    title_indexes = [index for index, line in enumerate(lines) if _looks_like_job_title_line(line)]
    if not title_indexes:
        return []

    jobs: list[JobItem] = []
    focused_title = (snapshot.meta or {}).get("focused_title")
    global_detail_index = _find_first_index(lines, ["工作职责", "岗位职责", "职位描述", "任职资格", "任职要求"])
    for ordinal, index in enumerate(title_indexes):
        next_index = title_indexes[ordinal + 1] if ordinal + 1 < len(title_indexes) else len(lines)
        has_separate_detail_panel = global_detail_index is not None and global_detail_index > title_indexes[-1]
        window_end = next_index
        if has_separate_detail_panel and index < global_detail_index < window_end:
            window_end = global_detail_index
        window = lines[index:window_end]
        title = _clean_title(lines[index])
        has_own_detail = _find_first_index(window, ["工作职责", "岗位职责", "职位描述", "任职资格", "任职要求"]) is not None
        should_attach_global_detail = (
            not has_own_detail
            and has_separate_detail_panel
            and global_detail_index is not None
            and (_same_title(focused_title, title) or (not focused_title and ordinal == len(title_indexes) - 1))
        )
        if should_attach_global_detail:
            window = lines[index:next_index] + lines[global_detail_index : global_detail_index + 80]

        text = "\n".join(window[:90])
        skills = list(dict.fromkeys(match.group(0) for match in SKILL_PATTERN.finditer(text)))
        detail_url = _current_detail_url(snapshot) or _find_link_for_title(snapshot, title) or _find_block_detail_link(snapshot, title)
        detail_selector = _find_selector_for_title(snapshot, title)
        jobs.append(
            JobItem(
                id=_hash(f"{title}|{detail_url or snapshot.url}|{text[:80]}"),
                title=title,
                department=_first_match(DEPARTMENT_PATTERN, text),
                location=_first_match(LOCATION_PATTERN, text),
                description=text[:3000],
                requirements=_section(text, ["任职资格", "任职要求", "岗位要求", "要求", "Qualifications", "Requirements"]),
                skills=skills,
                detail_url=detail_url,
                detail_selector=detail_selector,
                apply_url=_find_apply_link(snapshot),
                source_url=snapshot.url,
                confidence=0.78 if detail_url or detail_selector else 0.62,
            )
        )
    return jobs


def _looks_like_job_title_line(line: str) -> bool:
    line = _compact(line)
    if len(line) < 4 or len(line) > 90:
        return False
    blocked = ["全部职位", "搜索职位", "工作地点", "岗位类别", "发布时间", "工作职责", "任职资格", "立即投递", "查看详情"]
    if any(word in line for word in blocked):
        return False
    if re.search(r"[（(]J\d+[）)]", line, re.I):
        return True
    if LIST_JOB_TITLE.match(line) and any(
        word in line for word in ["工程师", "研发", "开发", "算法", "方向", "实习", "研究员", "管培生", "科学家", "平台"]
    ):
        return True
    return False


def _clean_title(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _find_first_index(lines: list[str], needles: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if any(needle.lower() in line.lower() for needle in needles):
            return index
    return None


def _find_link_for_title(snapshot: PageSnapshot, title: str) -> str | None:
    normalized_title = re.sub(r"\s+", "", title).lower()
    job_code = re.search(r"J\d+", title, re.I)
    candidates = []
    for item in [*snapshot.links, *snapshot.buttons]:
        href = getattr(item, "href", None) or ""
        detail_url = _candidate_detail_url(item, snapshot.url)
        if not detail_url:
            continue
        normalized_text = re.sub(r"\s+", "", getattr(item, "text", "") or "").lower()
        if normalized_text and (normalized_text in normalized_title or normalized_title in normalized_text):
            candidates.append((0, detail_url))
        if job_code and job_code.group(0).lower() in f"{normalized_text} {href}".lower():
            candidates.append((1, detail_url))
    if candidates:
        return sorted(candidates, key=lambda item: item[0])[0][1]
    return _find_nearby_detail_url(snapshot, title)


def _find_block_detail_link(snapshot: PageSnapshot, title: str) -> str | None:
    normalized_title = re.sub(r"\s+", "", title).lower()
    for block in snapshot.blocks:
        normalized_text = re.sub(r"\s+", "", block.text or "").lower()
        if normalized_title not in normalized_text[:500]:
            continue
        for link in block.links:
            label = f"{link.text} {link.href}".lower()
            detail_url = _candidate_detail_url(link, snapshot.url)
            if detail_url and any(key in label for key in ["详情", "detail", "position", "job", "apply", "投递", "申请", "jobadid"]):
                return detail_url
        first_detail = next((url for link in block.links if (url := _candidate_detail_url(link, snapshot.url))), None)
        if first_detail:
            return first_detail
    return None


def _find_selector_for_title(snapshot: PageSnapshot, title: str) -> str | None:
    normalized_title = re.sub(r"\s+", "", title).lower()
    for button in snapshot.buttons:
        normalized_text = re.sub(r"\s+", "", button.text or "").lower()
        if button.selector and normalized_text and (normalized_text in normalized_title or normalized_title in normalized_text):
            return button.selector
    for block in snapshot.blocks:
        normalized_text = re.sub(r"\s+", "", block.text or "").lower()
        if block.selector and normalized_title in normalized_text[:200]:
            return block.selector
    return None


def _same_title(left: str | None, right: str) -> bool:
    if not left:
        return False
    normalize = lambda value: re.sub(r"\s+", "", value).lower()
    left_key = normalize(left)
    right_key = normalize(right)
    return left_key in right_key or right_key in left_key


def _find_apply_link(snapshot: PageSnapshot) -> str | None:
    for link in snapshot.links:
        label = f"{link.text} {link.href}".lower()
        if any(key in label for key in ["投递", "申请", "apply"]):
            return urljoin(snapshot.url, link.href)
    return None


def _jobs_from_links(snapshot: PageSnapshot) -> list[JobItem]:
    jobs: list[JobItem] = []
    for link in snapshot.links:
        text = _compact(link.text)
        title = _detect_title(text)
        if not title:
            continue
        url = urljoin(snapshot.url, link.href)
        jobs.append(
            JobItem(
                id=_hash(f"{title}|{url}"),
                title=title,
                description=text,
                detail_url=url if _is_real_detail_url(url) else None,
                source_url=snapshot.url,
                confidence=0.45,
            )
        )
    return jobs


def _detect_title(text: str) -> str | None:
    first_line = next((line.strip() for line in text.split("\n") if line.strip()), "")
    if TITLE_HINT.search(first_line) and len(first_line) <= 60:
        return first_line[:60]
    match = TITLE_HINT.search(text[:300])
    return match.group("title").strip() if match else None


def _best_detail_url(links, source_url: str) -> str | None:
    for link in links:
        label = f"{link.text} {link.href}".lower()
        detail_url = _candidate_detail_url(link, source_url)
        if detail_url and any(key in label for key in ["详情", "detail", "job", "position", "apply", "投递", "jobadid"]):
            return detail_url
    for link in links:
        detail_url = _candidate_detail_url(link, source_url)
        if detail_url:
            return detail_url
    return None


def _best_apply_url(links, source_url: str) -> str | None:
    for link in links:
        label = f"{link.text} {link.href}".lower()
        if any(key in label for key in ["投递", "申请", "apply"]):
            return urljoin(source_url, link.href)
    return None


def _section(text: str, names: list[str]) -> str:
    for name in names:
        index = text.lower().find(name.lower())
        if index >= 0:
            return text[index : index + 1200]
    return ""


def _compact(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0) if match else None


def _longer(a: str, b: str) -> str:
    return b if len(b or "") > len(a or "") else a


def _hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _job_key(job: JobItem) -> str:
    return f"{job.title}|{job.detail_url or job.source_url or ''}"


def _find_nearby_detail_url(snapshot: PageSnapshot, title: str) -> str | None:
    normalized_title = re.sub(r"\s+", "", title).lower()
    job_code = re.search(r"J\d+", title, re.I)
    best: tuple[int, str] | None = None
    for block in snapshot.blocks:
        block_key = re.sub(r"\s+", "", block.text or "").lower()
        if normalized_title not in block_key[:800] and not (job_code and job_code.group(0).lower() in block_key[:800]):
            continue
        for link in block.links:
            detail_url = _candidate_detail_url(link, snapshot.url)
            if not detail_url:
                continue
            label = f"{link.text} {link.href}".lower()
            score = 0
            if "jobadid=" in detail_url.lower():
                score -= 10
            if any(word in label for word in ["详情", "detail", "职位", "岗位"]):
                score -= 5
            candidate = (score, detail_url)
            if best is None or candidate < best:
                best = candidate
    return best[1] if best else None


def _candidate_detail_url(candidate, source_url: str) -> str | None:
    href = getattr(candidate, "href", None) or ""
    absolute = urljoin(source_url, href) if href else None
    if _is_real_detail_url(absolute):
        return absolute
    attrs = getattr(candidate, "attrs", {}) or {}
    return _detail_url_from_attrs(attrs, source_url)


def _detail_url_from_attrs(attrs: dict[str, str], source_url: str) -> str | None:
    for name, value in attrs.items():
        lowered_name = name.lower()
        raw = str(value or "")
        if not raw:
            continue
        extracted = _extract_detail_url_from_text(raw, source_url)
        if extracted:
            return extracted
        is_moka_generic_id = "mokahr.com" in urlparse(source_url).netloc and lowered_name in {"data-id", "id"}
        if re.search(r"jobadid|job-ad-id|job_id|jobid|positionid|position-id|recruitjobid|recruit-job-id", lowered_name) or is_moka_generic_id:
            synthesized = _synthesize_detail_url(source_url, lowered_name, raw)
            if synthesized:
                return synthesized
    return None


def _extract_detail_url_from_text(text: str, source_url: str) -> str | None:
    full = re.search(r"https?://[^'\"\)\s<>]+", text, re.I)
    if full and _is_real_detail_url(full.group(0)):
        return full.group(0)
    path = re.search(r"/[^'\"\)\s<>]*(?:detail|jobAdId|jobId|job_id|positionId|position_id|recruitJobId)[^'\"\)\s<>]*", text, re.I)
    if path:
        absolute = urljoin(source_url, path.group(0))
        if _is_real_detail_url(absolute):
            return absolute
    query = re.search(r"(jobAdId|jobId|job_id|positionId|position_id|recruitJobId)=([A-Za-z0-9_-]{8,})", text, re.I)
    if query:
        return _synthesize_detail_url(source_url, query.group(1), query.group(2))
    return None


def _synthesize_detail_url(source_url: str, name: str, value: str) -> str | None:
    job_id = str(value or "").strip()
    if len(job_id) < 6:
        return None
    parsed = urlparse(source_url)
    lowered_name = name.lower()
    if "zhiye.com" in parsed.netloc:
        tenant = next((part for part in parsed.path.split("/") if part), "5")
        param = "positionId" if "position" in lowered_name else "recruitJobId" if "recruit" in lowered_name else "jobAdId"
        return f"{parsed.scheme}://{parsed.netloc}/{tenant}/detail?{param}={job_id}"
    if "mokahr.com" in parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}#/job/{job_id}"
    if "position" in lowered_name:
        return urljoin(source_url, f"/position/{job_id}")
    if "job" in lowered_name:
        return urljoin(source_url, f"/job/{job_id}")
    return None


def _is_real_detail_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(str(url))
    lowered = f"{parsed.path}?{parsed.query}#{parsed.fragment}".lower().replace("#", "/")
    if "/detail" in lowered:
        return True
    if any(key in lowered for key in ["jobadid=", "jobid=", "job_id=", "positionid=", "position_id=", "postid=", "post_id=", "recruitjobid="]):
        return True
    return bool(re.search(r"/(?:job|jobs|position|positions)/[^/?#]{6,}(?:[/?#]|$)", lowered))
