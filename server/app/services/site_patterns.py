from __future__ import annotations

from urllib.parse import urlparse


SITE_FAMILIES = [
    {
        "family": "moka",
        "hosts": ["app.mokahr.com"],
        "hints": ["hash router", "campus-recruitment", "jobs list", "detail route"],
    },
    {
        "family": "beisen_zhiye",
        "hosts": ["zhiye.com"],
        "hints": ["campus/jobs", "same-page detail", "job code like J12884"],
    },
    {
        "family": "feishu_jobs",
        "hosts": ["jobs.feishu.cn"],
        "hints": ["position/list", "current/limit pagination", "SPA list/detail"],
    },
    {
        "family": "hotjob_wecruit",
        "hosts": ["wecruit.hotjob.cn", "hotjob.cn"],
        "hints": ["position/campus", "school.html", "enterprise ATS"],
    },
    {
        "family": "external_form",
        "hosts": ["wjx.cn", "zhaopin.com"],
        "hints": ["form or third-party job board", "usually not a direct ATS list"],
    },
    {
        "family": "wechat_article",
        "hosts": ["mp.weixin.qq.com"],
        "hints": ["article text", "external application link discovery", "not a direct ATS list"],
    },
    {
        "family": "ats_custom",
        "hosts": ["jobs", "career", "careers", "campus", "talent", "hr", "hersingdat.com", "dingtalkoxm.com"],
        "hints": ["custom careers site", "DOM-driven generic extraction"],
    },
]


def classify_site(url: str) -> dict[str, object]:
    host = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    for item in SITE_FAMILIES:
        if any(pattern in host for pattern in item["hosts"]):
            return {
                "family": item["family"],
                "host": host,
                "hints": item["hints"],
            }
    if any(token in host or token in path for token in ["job", "career", "campus", "talent", "hr", "recruit"]):
        item = SITE_FAMILIES[-1]
        return {"family": item["family"], "host": host, "hints": item["hints"]}
    return {"family": "unknown", "host": host, "hints": []}
