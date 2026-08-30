from app.models import JobItem
from app.services.matcher import match_jobs
from app.services.resume import DEFAULT_PROFILE


def test_ai_application_role_ranks_high() -> None:
    jobs = [
        JobItem(
            title="大模型应用研发工程师",
            description="负责 RAG、Agent、Python 服务开发，C++ 推理优化优先。",
            requirements="Python C++ LLM RAG",
        ),
        JobItem(
            title="销售运营专员",
            description="负责客户销售、运营活动和线下推广。",
            requirements="沟通能力",
        ),
    ]
    matches = match_jobs(jobs, DEFAULT_PROFILE, max_candidates=10)
    assert matches[0].job.title == "大模型应用研发工程师"
    assert matches[0].decision == "recommend"
    assert matches[-1].decision == "reject"


def test_top_candidates_are_limited() -> None:
    jobs = [JobItem(title=f"Python AI应用研发工程师 {i}", description="Python RAG Agent 大模型") for i in range(20)]
    matches = match_jobs(jobs, DEFAULT_PROFILE, max_candidates=5)
    assert len(matches) == 5

