# AI Job Judge

通用网页岗位分析原型：Chrome Manifest V3 插件 + 本地 Python FastAPI 服务。

目标流程：

1. 上传简历，生成由大模型产出的个人匹配规则。
2. 打开任意招聘/校招/企业官网页面。
3. 插件扫描当前页面、分页、加载更多、无限滚动和详情链接。
4. 服务端抽取岗位详情，用 AI 规则做低成本粗筛。
5. 只把候选岗位交给大模型精排，返回 Top N 推荐。

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r server\requirements.txt
uvicorn app.main:app --reload --port 8765 --app-dir server
```

Chrome 打开 `chrome://extensions`，开启开发者模式，加载 `extension/` 目录。

可选模型配置（OpenAI-compatible API）：

```powershell
$env:AI_JOB_JUDGE_LLM_BASE_URL="https://api.openai.com/v1"
$env:AI_JOB_JUDGE_LLM_API_KEY="sk-..."
$env:AI_JOB_JUDGE_LLM_MODEL="gpt-4.1-mini"
```

默认优先使用本机 Claude Code CLI 做最终精排。如果要指定 Claude 模型或关闭 Claude：

```powershell
$env:AI_JOB_JUDGE_RANKER_PROVIDER="claude"   # claude | llm | auto | heuristic
$env:AI_JOB_JUDGE_CLAUDE_MODEL=""            # 留空交给 Claude 当前配置
$env:AI_JOB_JUDGE_CLAUDE_MAX_BUDGET_USD="0.5"
```

如果 Claude CLI 和 API Key 都不可用，服务会用本地启发式逻辑兜底，方便先验证扫描闭环。
