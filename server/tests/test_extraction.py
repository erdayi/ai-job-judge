from app.models import ElementCandidate, LinkCandidate, PageSnapshot, TextBlock
from app.services.job_extraction import extract_jobs
from app.services.matcher import match_jobs
from app.services.resume import DEFAULT_PROFILE


def test_beisen_mixed_list_and_detail_page_extracts_all_jobs() -> None:
    snapshot = PageSnapshot(
        url="https://campus.example.com/jobs",
        title="科大讯飞招聘",
        visible_text="""
全部职位（共 3 个）
飞凡计划-研发方向(J12884)
飞凡计划
全职
安徽省·合肥市
研发类
2026-06-30 发布
飞凡计划-营销方向(J12883)
飞凡计划
全职
安徽省·合肥市
营销类
2026-06-30 发布
飞凡计划-产品方向(J12874)
飞凡计划
全职
安徽省·合肥市
产品类
2026-06-30 发布
工作职责
飞凡计划的产品方向岗位是连接用户需求、市场趋势和技术创新的桥梁。
任职资格
良好的商业敏锐度，对不同类型互联网产品充满热爱。
立即投递
查看详情
没有更多了~
""",
        links=[],
        buttons=[],
        blocks=[],
    )

    response = extract_jobs(snapshot)
    titles = [job.title for job in response.jobs]

    assert titles == [
        "飞凡计划-研发方向(J12884)",
        "飞凡计划-营销方向(J12883)",
        "飞凡计划-产品方向(J12874)",
    ]
    assert "工作职责" in response.jobs[-1].description


def test_sparse_rd_direction_is_maybe_not_reject() -> None:
    jobs = extract_jobs(
        PageSnapshot(
            url="https://campus.example.com/jobs",
            title="校招",
            visible_text="飞凡计划-研发方向(J12884)\n飞凡计划\n全职\n安徽省·合肥市\n研发类\n2026-06-30 发布",
            links=[],
            buttons=[],
            blocks=[],
        )
    ).jobs

    matches = match_jobs(jobs, DEFAULT_PROFILE)

    assert matches[0].job.title == "飞凡计划-研发方向(J12884)"
    assert matches[0].decision == "maybe"


def test_focused_title_receives_same_page_detail_panel() -> None:
    snapshot = PageSnapshot(
        url="https://campus.example.com/jobs",
        title="科大讯飞招聘",
        visible_text="""
飞凡计划-研发方向(J12884)
飞凡计划-营销方向(J12883)
飞凡计划-产品方向(J12874)
工作职责
负责 AI 应用研发、RAG、Agent 和 Python 服务开发。
任职资格
熟悉 Python、C++、大模型应用工程化。
""",
        links=[],
        buttons=[],
        blocks=[],
        meta={"focused_title": "飞凡计划-研发方向(J12884)"},
    )

    jobs = extract_jobs(snapshot).jobs
    rd_job = next(job for job in jobs if job.title == "飞凡计划-研发方向(J12884)")
    product_job = next(job for job in jobs if job.title == "飞凡计划-产品方向(J12874)")

    assert "Python" in rd_job.description
    assert "Python" not in product_job.description


def test_expanded_multiple_jobs_keep_their_own_details() -> None:
    snapshot = PageSnapshot(
        url="https://campus.example.com/jobs",
        title="科大讯飞招聘",
        visible_text="""
飞凡计划-研发方向(J12884)
飞凡计划
全职
安徽省·合肥市
研发类
工作职责
飞凡计划的研发方向专注于软件开发领域。
任职资格
热爱编程，熟练掌握至少一种编程语言，包括但不限于Java、C/C++、Python等；
飞凡计划-营销方向(J12883)
飞凡计划
全职
安徽省·合肥市
营销类
工作职责
负责区域内行业客户拓展和解决方案提供。
任职资格
良好的沟通理解和人际交往能力。
飞凡计划-产品方向(J12874)
飞凡计划
全职
安徽省·合肥市
产品类
工作职责
产品方向岗位是连接用户需求、市场趋势和技术创新的桥梁。
任职资格
良好的商业敏锐度，对不同类型互联网产品充满热爱。
""",
        links=[],
        buttons=[],
        blocks=[],
    )

    jobs = extract_jobs(snapshot).jobs
    rd_job = next(job for job in jobs if job.title == "飞凡计划-研发方向(J12884)")
    marketing_job = next(job for job in jobs if job.title == "飞凡计划-营销方向(J12883)")
    product_job = next(job for job in jobs if job.title == "飞凡计划-产品方向(J12874)")

    assert "Python" in rd_job.description
    assert "客户拓展" not in rd_job.description
    assert "客户拓展" in marketing_job.description
    assert "Python" not in marketing_job.description
    assert "商业敏锐度" in product_job.description


def test_beisen_detail_url_is_preserved_on_detail_page() -> None:
    detail_url = "https://iflytek.zhiye.com/5/detail?jobAdId=71aea93a-7e2d-4471-8912-1056c6949383"
    snapshot = PageSnapshot(
        url=detail_url,
        title="科大讯飞招聘",
        visible_text="""
飞凡计划-研发方向(J12884)
飞凡计划
全职
安徽省·合肥市
研发类
工作职责
飞凡计划的研发方向专注于软件开发领域。
任职资格
熟练掌握至少一种编程语言，包括但不限于Java、C/C++、Python等；
""",
        links=[],
        buttons=[],
        blocks=[],
        meta={"focused_title": "飞凡计划-研发方向(J12884)"},
    )

    jobs = extract_jobs(snapshot).jobs

    assert jobs[0].detail_url == detail_url


def test_beisen_block_detail_url_is_preferred_over_jobs_list_url() -> None:
    detail_url = "https://iflytek.zhiye.com/5/detail?jobAdId=71aea93a-7e2d-4471-8912-1056c6949383"
    snapshot = PageSnapshot(
        url="https://iflytek.zhiye.com/5/jobs",
        title="科大讯飞招聘",
        visible_text="""
飞凡计划-研发方向(J12884)
飞凡计划
全职
安徽省·合肥市
研发类
2026-06-30 发布
""",
        links=[LinkCandidate(text="飞凡计划-研发方向(J12884)", href="https://iflytek.zhiye.com/5/jobs")],
        blocks=[
            TextBlock(
                text="飞凡计划-研发方向(J12884) 飞凡计划 全职 安徽省·合肥市 研发类 查看详情",
                selector=".job-card",
                links=[
                    LinkCandidate(text="飞凡计划-研发方向(J12884)", href="https://iflytek.zhiye.com/5/jobs"),
                    LinkCandidate(text="查看详情", href=detail_url),
                ],
            )
        ],
    )

    jobs = extract_jobs(snapshot).jobs

    assert jobs[0].detail_url == detail_url


def test_jobs_list_url_is_not_marked_as_real_detail_url() -> None:
    snapshot = PageSnapshot(
        url="https://iflytek.zhiye.com/5/jobs",
        title="科大讯飞招聘",
        visible_text="飞凡计划-研发方向(J12884)\n飞凡计划\n全职\n安徽省·合肥市\n研发类",
        links=[LinkCandidate(text="飞凡计划-研发方向(J12884)", href="https://iflytek.zhiye.com/5/jobs")],
        blocks=[],
    )

    jobs = extract_jobs(snapshot).jobs

    assert jobs[0].detail_url is None


def test_beisen_div_detail_action_with_data_job_ad_id_becomes_detail_url() -> None:
    job_ad_id = "71aea93a-7e2d-4471-8912-1056c6949383"
    snapshot = PageSnapshot(
        url="https://iflytek.zhiye.com/5/jobs",
        title="科大讯飞招聘",
        visible_text="""
飞凡计划-研发方向(J12884)
飞凡计划
全职
安徽省·合肥市
研发类
查看详情
""",
        links=[],
        buttons=[
            ElementCandidate(
                text="查看详情",
                selector=".job-card .detail",
                tag="div",
                href=None,
                attrs={"data-job-ad-id": job_ad_id},
            )
        ],
        blocks=[
            TextBlock(
                text="飞凡计划-研发方向(J12884) 飞凡计划 全职 安徽省·合肥市 研发类 查看详情",
                selector=".job-card",
                links=[
                    LinkCandidate(
                        text="查看详情",
                        href="https://iflytek.zhiye.com/5/jobs",
                        selector=".detail",
                        attrs={"data-job-ad-id": job_ad_id},
                    )
                ],
            )
        ],
    )

    jobs = extract_jobs(snapshot).jobs

    assert jobs[0].detail_url == f"https://iflytek.zhiye.com/5/detail?jobAdId={job_ad_id}"


def test_moka_hash_jobs_page_synthesizes_detail_from_data_id() -> None:
    job_id = "186487320001"
    snapshot = PageSnapshot(
        url="https://app.mokahr.com/campus-recruitment/leyuansu/166186#/jobs",
        title="乐元素校园招聘",
        visible_text="""
大模型应用研发工程师
校招
北京
研发类
查看详情
算法工程师
校招
上海
技术类
查看详情
""",
        links=[],
        buttons=[
            ElementCandidate(
                text="查看详情",
                selector=".job-card .detail",
                tag="div",
                href=None,
                attrs={"data-id": job_id},
            )
        ],
        blocks=[
            TextBlock(
                text="大模型应用研发工程师 校招 北京 研发类 查看详情",
                selector=".job-card",
                links=[
                    LinkCandidate(
                        text="查看详情",
                        href="https://app.mokahr.com/campus-recruitment/leyuansu/166186#/jobs",
                        selector=".detail",
                        attrs={"data-id": job_id},
                    )
                ],
            )
        ],
    )

    jobs = extract_jobs(snapshot).jobs

    assert jobs[0].detail_url == f"https://app.mokahr.com/campus-recruitment/leyuansu/166186#/job/{job_id}"


def test_moka_jobs_hash_list_url_is_not_detail_url() -> None:
    snapshot = PageSnapshot(
        url="https://app.mokahr.com/campus-recruitment/leyuansu/166186#/jobs",
        title="乐元素校园招聘",
        visible_text="大模型应用研发工程师\n校招\n北京\n研发类",
        links=[
            LinkCandidate(
                text="大模型应用研发工程师",
                href="https://app.mokahr.com/campus-recruitment/leyuansu/166186#/jobs",
            )
        ],
        blocks=[],
    )

    jobs = extract_jobs(snapshot).jobs

    assert jobs[0].detail_url is None
