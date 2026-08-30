from app.models import ApplicationKitRequest, JobItem
from app.services.application_kit import heuristic_application_kit
from app.services.resume import DEFAULT_PROFILE


def test_heuristic_application_kit_contains_actionable_sections() -> None:
    request = ApplicationKitRequest(
        job=JobItem(
            title="大模型应用研发工程师",
            company="示例科技",
            description="负责 Agent、RAG、Python 后端服务和大模型应用工程化。",
            requirements="熟悉 Python、Java、LLM、RAG，有工程落地经验。",
            detail_url="https://example.com/job/ai-app",
        ),
        score=86,
        decision="recommend",
        reasons=["岗位方向匹配 AI 应用研发", "核心技能命中 Python、RAG、Agent"],
        risks=["JD 未说明团队模型平台成熟度"],
        missing_skills=["云原生部署"],
    )

    response = heuristic_application_kit(request, DEFAULT_PROFILE)

    assert response.source == "heuristic"
    assert "大模型应用研发工程师" in response.fit_summary
    assert response.resume_focus
    assert response.cover_note
    assert response.interview_prep
    assert "Python" in response.keywords_to_add
    assert response.risk_mitigation
