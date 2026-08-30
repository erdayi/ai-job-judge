from app.models import JobItem, JobMatch
from app.services.ranker import _rank_response_from_payload


def test_ranker_prefers_real_detail_url_over_model_list_url() -> None:
    detail_url = "https://iflytek.zhiye.com/5/detail?jobAdId=71aea93a-7e2d-4471-8912-1056c6949383"
    list_url = "https://iflytek.zhiye.com/5/jobs"
    match = JobMatch(
        job=JobItem(
            title="飞凡计划-研发方向(J12884)",
            description="负责 AI 应用研发、Python 和 Java 服务开发。",
            requirements="熟悉 Java、C/C++、Python 等语言。",
            detail_url=detail_url,
            source_url=list_url,
        ),
        score=85,
        decision="recommend",
        reasons=["岗位方向匹配研发"],
    )
    payload = {
        "results": [
            {
                "rank": 1,
                "score": 85,
                "decision": "recommend",
                "title": "飞凡计划-研发方向(J12884)",
                "company": None,
                "reasons": ["岗位方向匹配研发"],
                "risks": [],
                "missing_skills": [],
                "job_url": list_url,
            }
        ]
    }

    response = _rank_response_from_payload(payload, [match], top_n=1, source="claude")

    assert response.results[0].job_url == detail_url


def test_ranker_fills_missing_model_results_with_local_matches() -> None:
    matches = [
        JobMatch(
            job=JobItem(title="飞凡计划-研发方向(J12884)", description="AI 应用研发 Python Java", detail_url="https://iflytek.zhiye.com/5/detail?jobAdId=rd"),
            score=85,
            decision="recommend",
            reasons=["研发方向匹配"],
        ),
        JobMatch(
            job=JobItem(title="飞凡计划-产品方向(J12874)", description="产品规划", detail_url="https://iflytek.zhiye.com/5/detail?jobAdId=pm"),
            score=23,
            decision="reject",
            risks=["产品方向"],
        ),
        JobMatch(
            job=JobItem(title="飞凡计划-营销方向(J12883)", description="客户拓展", detail_url="https://iflytek.zhiye.com/5/detail?jobAdId=sales"),
            score=0,
            decision="reject",
            risks=["营销"],
        ),
    ]
    payload = {
        "results": [
            {
                "rank": 1,
                "score": 85,
                "decision": "recommend",
                "title": "飞凡计划-研发方向(J12884)",
                "company": None,
                "reasons": ["研发方向匹配"],
                "risks": [],
                "missing_skills": [],
                "job_url": "https://iflytek.zhiye.com/5/detail?jobAdId=rd",
            }
        ]
    }

    response = _rank_response_from_payload(payload, matches, top_n=3, source="claude")

    assert [item.title for item in response.results] == [
        "飞凡计划-研发方向(J12884)",
        "飞凡计划-产品方向(J12874)",
        "飞凡计划-营销方向(J12883)",
    ]
