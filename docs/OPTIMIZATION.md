# 优化路线

## 站点家族

当前按招聘系统家族迭代，而不是按单个公司硬编码：

- `moka`：Moka/MokaHR，常见 hash 路由和列表/详情页。
- `beisen_zhiye`：北森 zhiye，常见同页详情和 `Jxxxxx` 岗位编号。
- `feishu_jobs`：飞书招聘，常见 `current/limit` 分页和 SPA 列表。
- `hotjob_wecruit`：Hotjob/Wecruit，常见企业 ATS。
- `wechat_article`：微信公众号文章，通常不是岗位列表，需要发现外部投递入口或提取文章里的岗位表。
- `ats_custom`：企业自研站点，走通用 DOM/文本/链接抽取。

## 扫描策略

- 先做快速可见页抽取，得到岗位列表和详情链接。
- 岗位详情足够完整时不补抓。
- 详情不足时才补抓；真实详情 URL 走隐藏标签页并发打开，同页详情只处理没有真实详情 URL 的岗位。
- `补详情数` 是一次扫描的总预算，避免深分页页面每页重复消耗导致过慢。
- 排序结果、复制摘要、岗位库保存和打开详情都必须优先使用真实详情 URL；模型返回列表页时不能覆盖本地捕获到的详情页。
- 抽取阶段不再把 `/jobs` 这类列表页写成 `detail_url`；只有 `/detail`、`jobAdId`、`jobId`、`positionId` 等真实岗位详情模式才进入详情链接。
- Moka/MokaHR 使用 hash 路由：`#/jobs` 只视为列表页，`#/job/{id}`、`#/jobs/{id}` 或由 `data-id` 合成出的 `#/job/{id}` 才视为真实详情页。
- 对 `<div>查看详情</div>`、`<span>详情</span>` 这类无 `href` 的动作节点，content script 会从父级 `data-*`、`onclick`、路由字段中推断详情 URL；北森 `data-job-ad-id` 会合成为 `/detail?jobAdId=...`。
- 点击无 `href` 详情动作后，会轮询等待 URL 变成详情页或同页详情面板出现，避免 SPA 延迟渲染导致误判。
- 扫描诊断会展示真实详情、列表回退、缺失详情数量，用于定位站点适配问题。
- 去重合并必须校验岗位标题，不能因为多个岗位误拿到同一个详情 URL 就折叠成一个岗位。
- Claude 精排如果只返回少量岗位，后端会用本地规则结果补齐到 Top N，避免 UI 只显示一个岗位。
- Claude 只看压缩后的候选岗位，避免多页大站点过慢。
- 明显硬负向岗位由本地规则保护，避免模型误抬。

## 投递准备闭环

- 推荐结果和岗位库都支持生成投递材料包。
- 材料包只针对单个岗位调用 Claude/API，避免扫描阶段成本膨胀。
- 输入包括简历画像、简历文本、岗位详情、匹配理由、风险点和缺失技能。
- 输出包括匹配判断、简历突出点、投递备注、面试准备、关键词和风险补强。
- Claude 不可用时复制兜底 Prompt，保证工作流不中断。

## 回归样本

用 `tools/prepare_site_inventory.py` 把用户提供的表格转成站点家族清单：

```powershell
python tools\prepare_site_inventory.py C:\path\pasted-text.txt data\site_inventory.json
```

后续每修一个页面，把它归档到对应家族并补充回归测试。

当前用户已提供 `104` 个有效招聘入口，详见 `docs/SITE_INVENTORY.md` 和 `data/site_inventory.json`。后续迭代不再按“单个临时样例”处理，而是从这批样本池里按站点家族抽样回归。
