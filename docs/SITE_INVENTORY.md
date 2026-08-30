# 招聘站点样本池

用户已提供 `104` 个有效招聘入口链接，来源文件：

`C:\Users\17514\.codex\attachments\88c0c432-d939-4825-9d41-1cef58d55500\pasted-text.txt`

生成后的结构化清单：

`data/site_inventory.json`

## 站点家族分布

| 家族 | 数量 | 说明 |
| --- | ---: | --- |
| `wechat_article` | 46 | 微信公众号文章，重点是发现外部投递入口，或抽取文章中的岗位表格 |
| `ats_custom` | 21 | 企业自研招聘站，DOM 结构差异最大，需要通用块抽取和详情链接识别 |
| `beisen_zhiye` | 14 | 北森 zhiye，常见同页详情、`/detail?jobAdId=`、岗位编号 `Jxxxxx` |
| `moka` | 11 | Moka/MokaHR，常见 hash 路由、列表页、详情页 |
| `feishu_jobs` | 6 | 飞书招聘，常见 SPA 列表、`current/limit` 分页 |
| `hotjob_wecruit` | 4 | Hotjob/Wecruit，常见校园招聘项目页和职位列表 |
| `external_form` | 2 | 问卷星、智联等外部表单或第三方入口，通常不适合按 ATS 列表抽取 |

## 第一批重点回归样本

优先用这些样本验证“列表抽取、分页、详情链接、同页详情、Claude 精排”五条链路：

| 家族 | 样本 |
| --- | --- |
| `beisen_zhiye` | 科大讯飞、长飞光纤、华夏航空、长江存储、金风科技、三一集团 |
| `moka` | 中科光电、中兴通讯、乐元素、掌趣科技、博世、知乎、韶音科技 |
| `feishu_jobs` | 小马智行、自变量机器人、库玛科技、安必平、懂车帝 |
| `hotjob_wecruit` | 中国电信天翼云、欧普照明、歌尔股份 |
| `ats_custom` | 京东方、中建八局、大疆、B 站、惠普、软通动力、米哈游、百度、蚂蚁集团 |
| `wechat_article` | 公众号文章先验证外链发现；如果没有外链，再验证文章内岗位文本抽取 |

## 使用方式

重新生成清单：

```powershell
.\.venv\Scripts\python.exe tools\prepare_site_inventory.py C:\Users\17514\.codex\attachments\88c0c432-d939-4825-9d41-1cef58d55500\pasted-text.txt data\site_inventory.json
```

按原始清单顺序验证站点：

```powershell
.\.venv\Scripts\python.exe tools\validate_site_sequence.py --start 1 --limit 104 --live --workers 12 --timeout 10
```

验证记录会写入：

- `data/site_validation_runs.json`
- `docs/SITE_VALIDATION.md`

后续每次优化一个站点，必须记录：

- 站点家族
- 原始 URL
- 是否需要登录
- 是否有分页
- 详情页模式：独立 URL / 同页展开 / 弹窗 / 跳外链
- 抽取到的岗位数
- Top N 精排是否合理
- 失败原因和修复策略
