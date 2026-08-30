from __future__ import annotations

import re

from app.models import PageAnalyzeResponse, PageSnapshot, PaginationPlan, PaginationType
from app.services.site_patterns import classify_site


LOGIN_KEYWORDS = ["登录", "登陆", "sign in", "login", "验证码", "扫码登录", "账号密码"]
JOB_KEYWORDS = ["岗位", "职位", "招聘", "校招", "社招", "职责", "要求", "任职", "投递", "apply", "job", "career"]
NEXT_KEYWORDS = ["下一页", "下页", "next", ">", "›", "»"]
MORE_KEYWORDS = ["加载更多", "查看更多", "更多岗位", "more", "load more"]


def analyze_page(snapshot: PageSnapshot) -> PageAnalyzeResponse:
    text = f"{snapshot.title}\n{snapshot.visible_text}".lower()
    site = classify_site(snapshot.url)
    requires_login = _requires_login(snapshot, text)
    pagination = _detect_pagination(snapshot)
    is_job_page = any(keyword.lower() in text for keyword in JOB_KEYWORDS) or _has_job_like_links(snapshot)
    if requires_login:
        return PageAnalyzeResponse(
            is_job_page=False,
            requires_login=True,
            login_reason="页面看起来需要登录或验证码，完成登录后可继续扫描。",
            pagination=PaginationPlan(),
            extraction_hint="login_required",
            site_family=str(site["family"]),
            site_hints=list(site["hints"]),
        )
    return PageAnalyzeResponse(
        is_job_page=is_job_page,
        requires_login=False,
        pagination=pagination,
        extraction_hint="优先从职位卡片、表格行、详情链接附近文本抽取岗位。",
        site_family=str(site["family"]),
        site_hints=list(site["hints"]),
    )


def _requires_login(snapshot: PageSnapshot, text: str) -> bool:
    login_hits = sum(1 for keyword in LOGIN_KEYWORDS if keyword.lower() in text)
    has_little_content = len(snapshot.visible_text.strip()) < 500
    has_password = "password" in text or "密码" in text
    return (login_hits >= 2 and has_little_content) or (has_password and login_hits >= 1)


def _has_job_like_links(snapshot: PageSnapshot) -> bool:
    pattern = re.compile(r"岗位|职位|工程师|研发|开发|算法|实习|校招|社招|job|career|apply", re.I)
    return any(pattern.search(link.text) or pattern.search(link.href) for link in snapshot.links)


def _detect_pagination(snapshot: PageSnapshot) -> PaginationPlan:
    candidates = snapshot.buttons + [
        type("LinkLike", (), {"text": link.text, "selector": link.selector, "href": link.href}) for link in snapshot.links
    ]
    for item in candidates:
        label = (item.text or "").strip().lower()
        if not label:
            continue
        if any(keyword.lower() == label or keyword.lower() in label for keyword in MORE_KEYWORDS):
            return PaginationPlan(type=PaginationType.load_more, next_selector=item.selector, reason=f"发现加载更多入口：{item.text}")
        if any(keyword.lower() == label or keyword.lower() in label for keyword in NEXT_KEYWORDS):
            return PaginationPlan(type=PaginationType.next_button, next_selector=item.selector, reason=f"发现下一页入口：{item.text}")
    page_number_buttons = [button for button in snapshot.buttons if re.fullmatch(r"\d{1,3}", (button.text or "").strip())]
    if len(page_number_buttons) >= 2:
        next_page = page_number_buttons[1]
        return PaginationPlan(type=PaginationType.page_numbers, next_selector=next_page.selector, reason="发现页码按钮")
    if snapshot.meta.get("scrollHeight", 0) > snapshot.meta.get("innerHeight", 1) * 2:
        return PaginationPlan(type=PaginationType.infinite_scroll, reason="页面可滚动且未发现明确分页，尝试无限滚动")
    return PaginationPlan(type=PaginationType.none, reason="未发现分页入口")
