# 站点顺序验证记录

本文件按 `data/site_inventory.json` 的顺序追加记录。状态含义：

- `pending_manual_scan`：已进入验证队列，待插件真实扫描。
- `fetched`：已完成轻量 HTTP 读取，仍需插件扫描验证岗位抽取和详情链接。
- `browser_required`：轻量 HTTP 无法处理跳转/SPA/风控，需要用浏览器插件验证。
- `http_error` / `url_error` / `error`：轻量读取失败，需要浏览器人工确认。

最近一次运行模式：report-only

## 摘要

- 覆盖链接：`104`
- 清单顺序：`1` - `104`
- 状态分布：`browser_required` 13, `fetched` 91
- 家族分布：`ats_custom` 21, `beisen_zhiye` 14, `external_form` 2, `feishu_jobs` 6, `hotjob_wecruit` 4, `moka` 11, `wechat_article` 46

## 明细

| 顺序 | 公司 | 家族 | 状态 | 页面证据 | URL |
| ---: | --- | --- | --- | --- | --- |
| 1 | 中国航天科工 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/yTLw8hN6GF26vSZy8zekEw |
| 2 | 诺亚控股 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/KLmrx-mrAFuyEq8oRNfy1g?scene=1&click_id=1504 |
| 3 | 中科光电 | `moka` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://app.mokahr.com/campus-recruitment/hdzn/151324?locale=zh-CN#/jobs?zhineng%5B0%5D=209066 |
| 4 | 京东方 | `ats_custom` | `fetched` | 京东方科技集团股份有限公司 | https://campus.boe.com/custom/campus |
| 5 | 内蒙古农商银行 | `ats_custom` | `fetched` | 内蒙古农村商业银行股份有限公司2026年度校园招聘 | https://nmnshxy2026.hersingdat.com/ |
| 6 | 科大讯飞 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/OEW0DyGsAZUxlUtEWfUwvQ |
| 7 | 开立医疗 | `moka` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://app.mokahr.com/campus-recruitment/sonoscape/94392/#/ |
| 8 | 镭目科技 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/zLiUEigJl1iApPnE6EpBDw?scene=1&click_id=1344 |
| 9 | 穹彻智能（人才计划） | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/LR6BvAhbjuMPc4GtYQGkug?scene=1 |
| 10 | 中兴通讯 | `moka` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://app.mokahr.com/campus-recruitment/zte/46903#/jobs?project=100120257 |
| 11 | 乐元素 | `moka` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://app.mokahr.com/campus-recruitment/leyuansu/166186#/jobs?340045%5B0%5D=%E5%BA%94%E5%B1%8A%E7%94%9F&page=1&anchorName=jobsList |
| 12 | 长飞光纤 | `beisen_zhiye` | `fetched` | 长飞光纤光缆股份有限公司 27届校招 | https://yofc2.zhiye.com/campus/jobs |
| 13 | 杭州新中大 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/OD0N30qrrUgW-9UspxjnsA?scene=1&click_id=1278 |
| 14 | 必易微 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/KM8M5MLyPnkMNWhc3MuQ3g?scene=1&click_id=1277 |
| 15 | 掌趣科技 | `moka` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://app.mokahr.com/campus-recruitment/ourpalm/43628#/job/0289ff68-d764-4c22-bfe7-f368cbbb2263 |
| 16 | 科华集团 | `moka` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://app.mokahr.com/campus-recruitment/kehua/92510#/page/%E6%A0%A1%E6%8B%9B%E8%81%8C%E4%BD%8D |
| 17 | 中国电信天翼云 | `hotjob_wecruit` | `fetched` | hotjob_wecruit, pagination | https://wecruit.hotjob.cn/SU62b2ae672f9d24458d72f9cc/pb/school.html |
| 18 | 小马智行（人才计划） | `feishu_jobs` | `fetched` | 小马智行校园招聘 | https://ponyai.jobs.feishu.cn/ponycampus |
| 19 | 航天科技集团 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/z3LM4t-hkE0QJj_YXBilUw?scene=1&click_id=1225 |
| 20 | 联合飞机 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/7L_3_kHppSb4si2x1aYP0Q?scene=1&click_id=1199 |
| 21 | 能良电商 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/LYM7hdZ9iW3tMA9uZffCEw |
| 22 | 中核—中国中原对外工程有限公司 | `beisen_zhiye` | `fetched` | 中核集团招聘 | https://cnnc.m.zhiye.com/joblist.html?jc=2&ky=&pi=1&ps=10&c1=&c2=1_162&c= |
| 23 | 中建八局集团 | `ats_custom` | `fetched` | 中国建筑第八工程局有限公司 | https://job.cscec8b.com.cn/campus |
| 24 | 联发科技 | `beisen_zhiye` | `fetched` | 联发科技招聘 | https://mediatek.zhiye.com/campus |
| 25 | 大疆 | `ats_custom` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://apply.careers.dji.com/campus-recruitment/dji/143359?locale=zh-CN#/?page=1&pageSize=30 |
| 26 | 欧普照明 | `hotjob_wecruit` | `fetched` | hotjob_wecruit | https://wecruit.hotjob.cn/SU646ed9920dcad45af14821b4/mc/position/campus |
| 27 | 新凯来 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/LCZtpuXbu6uumZmNFg7AZA?scene=1 |
| 28 | 固胜科技 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/zuap56bn_5aTm3FuZ1Rg5w |
| 29 | 华夏航空 | `beisen_zhiye` | `fetched` | 华夏航空股份有限公司 | https://hxhk.zhiye.com/campus/jobs |
| 30 | 自变量机器人 | `feishu_jobs` | `fetched` | 加入自变量机器人 \| 校园招聘 | https://x2-robot.jobs.feishu.cn/912130/position/list?keywords=&category=&location=&project=7650350869535869227&type=&job_hot_flag=&current=1&limit=10&functionCategory=&tag= |
| 31 | 智元机器人（人才计划） | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/YtVOtxKeyXX7IH6bL_4Y5A |
| 32 | 它石智航（人才计划） | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/Fa164U5Atgslp3861-TGnQ?scene=1&click_id=484 |
| 33 | 上海中建东孚公司 | `ats_custom` | `fetched` | 东孚公司2027届校园招聘 - 中国建筑第八工程局有限公司 | https://job.cscec8b.com.cn/recruitment/job/detail/id/2776 |
| 34 | 中车株洲电机 | `beisen_zhiye` | `fetched` | 中车株洲电力机车研究所有限公司 | https://crrczzs.zhiye.com/campus |
| 35 | 普渡机器人 | `beisen_zhiye` | `fetched` | 普渡机器人招聘 | https://pudutech.zhiye.com/campus |
| 36 | BCG（中国） | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/pG8ZfkWVigYQDxOcnTHsUg?scene=1&click_id=469 |
| 37 | 阿里巴巴（人才计划） | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/5phiRqiTz7RqzGy8SDf3gg?scene=1&click_id=457 |
| 38 | 拓竹科技 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/NRXtFGt3MXRKgs-zzZjFqg?scene=1&click_id=455 |
| 39 | 卓驭（人才计划） | `ats_custom` | `fetched` | 深圳市卓驭科技有限公司 | https://we.zyt.com/5/jobs?sessionid= |
| 40 | 哔哩哔哩 | `ats_custom` | `fetched` | 哔哩哔哩-招聘 | https://jobs.bilibili.com/campus/positions?channel=bilibiliaccounts |
| 41 | 四维图新 | `beisen_zhiye` | `fetched` | 四维总门户 | https://navinfo102.zhiye.com/campus/jobs |
| 42 | 惠普 | `ats_custom` | `fetched` | 【27卒対象】サプライチェーン担当/Business Operations Analyst \| HP | https://apply.hp.com/careers?start=0&pid=41922401&sort_by=timestamp&filter_seniority=graduate |
| 43 | 艾为电子 | `beisen_zhiye` | `fetched` | 艾为电子\|中国数模龙头\|艾为招聘 | https://awinic.zhiye.com/?sessionid= |
| 44 | 库玛科技 | `feishu_jobs` | `fetched` | 加入深圳库犸科技有限公司 | https://mammotion.jobs.feishu.cn/campus_recruitment/position/list?project=7611843487977654537 |
| 45 | 博世 | `moka` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://app.mokahr.com/campus-recruitment/bosch/73873#/jobs?keyword=2027%E6%A0%A1%E6%8B%9B |
| 46 | 软通动力 | `ats_custom` | `fetched` | isoftstone软通动力-人才招聘 | https://career.isoftstone.com/talent/htmls/xiaoyuanzhaopin/index.html |
| 47 | 中国电科第十四研究所 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/lqZMq0oPNHeqasWwZY5Lgw?scene=1&click_id=423 |
| 48 | 中国电科第十研究所 | `ats_custom` | `fetched` | 招聘官网 | https://cetc.iguopin.com/job-campus |
| 49 | 云象机器人 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/Y2WjDpk52xezGcrmgteqiQ?scene=1&click_id=400 |
| 50 | 代塔供应链 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/oiuQlCDxIGovilgzjDlIqQ?scene=1&click_id=390 |
| 51 | vivo（人才计划） | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/0KlCGXBMwxbU2NquqE6eQw?scene=1 |
| 52 | 牧原 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/BKMC3SHRH65x48d6_CumaA?scene=1&click_id=366 |
| 53 | 龙蟠科技 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/wdA3reFkAkCV3uuXWy0H1Q?scene=1 |
| 54 | 北京国望光学科技 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/P7v0alwzLWnwD041R-Ipow?scene=1 |
| 55 | 上海电气 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/wKttLoGxZOWIA5Cr5vYfaA |
| 56 | 是为科技 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/OB_FDFcVt2LteSslt8w53g?scene=1&click_id=343 |
| 57 | 游族网络 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/frovjpGTxw00M5mpeAN4VQ |
| 58 | 禾赛科技 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/iiP1Ap4JW3i48TM9-se6Iw |
| 59 | 中电锦江 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/Vf_rAneDi62eISDVjnijkw?scene=1 |
| 60 | 米哈游（llm方向） | `ats_custom` | `fetched` | miHoYo招聘官网 | https://jobs.mihoyo.com/#/campus/position/8785 |
| 61 | 上海宇量昇 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/DnsN8K3oI2Xl5p_Lhj590A?scene=1&click_id=284 |
| 62 | 中铁设计集团 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/AYkr0nHEyVkcatHBrLl8Ng?scene=1&click_id=252 |
| 63 | 科大讯飞（人才计划） | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/vmh4sa_HA_0jJCq0nngJRA?scene=1&click_id=205 |
| 64 | 安必平 | `feishu_jobs` | `fetched` | 加入安必平集团 | https://anbiping.jobs.feishu.cn/index/?keywords=&category=&location=&project=7639283695312554259&type=&job_hot_flag=&current=1&limit=10&functionCategory=&tag= |
| 65 | 中国科学院光电技术研究所 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/ZlSb1jOeyY6ld1NbQwbiZg |
| 66 | 中国天楹 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/so7zsBb_A0Zy_Qo0VluIIQ |
| 67 | 杰瑞集团 | `ats_custom` | `fetched` | 社会招聘_校园招聘 —杰瑞集团招聘官网 | https://future.jereh.com/campus/jobs?memory=%7B%7D&silence=1 |
| 68 | 航空工业通飞 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/xEJCfP5Bl_kC-cQo84Gb_A |
| 69 | 中国汽车技术研究中心 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/6gFAYRnHtyiGKJqZkMSTqA |
| 70 | 中国平安 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/OGTRehNcDZgKaNosQ-aIvw |
| 71 | 精进电动 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/ixbn4WXqkjKj75m98ukvHA?scene=1&click_id=166 |
| 72 | 长江存储 | `beisen_zhiye` | `fetched` | 长江存储—校招 | https://ymtc-campus.zhiye.com/campus/jobs |
| 73 | 海克斯康 | `hotjob_wecruit` | `fetched` | 招聘官网 | https://hexagonhms.hotjob.cn/ |
| 74 | 中铁二院 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/dnmyS1l2IMaTqunbsISI2w?scene=1&click_id=73 |
| 75 | 中铁第四勘察设计院 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/Sbd3pxyYVugQkfsIZvnOCw |
| 76 | 工大卫星 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/KWBu6Bo_l1bAHRpwEfc_Nw?scene=1&click_id=56 |
| 77 | 新意科技 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/-QRqs07m4wEziNzdduNmNQ?scene=1&click_id=89 |
| 78 | 星图测控 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/BIN95z6M_WQzbgy_esb05A?scene=1&click_id=57 |
| 79 | 群核科技（公众战略人才计划） | `moka` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://app.mokahr.com/campus_apply/qunhemail/2832#/job/c204257b-1827-4874-8ba3-436334e4d21d |
| 80 | sharpa | `feishu_jobs` | `fetched` | 加入Sharpa Robotics | https://fcn5hvc5qbfs.jobs.feishu.cn/668262/?spread=A2B3G4G |
| 81 | 东芯半导体 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/3Jh5YexL980PlyjgZWy6mg?scene=1&click_id=90 |
| 82 | 小米（人才计划） | `ats_custom` | `fetched` | 小米招聘 | https://hr.xiaomi.com/toptalent?sessionid= |
| 83 | 万得wind | `ats_custom` | `fetched` | detail_link | https://wcms.wind.com.cn:9006/wcmsweb/recruitH5/#/position/detail?id=37&projectID=4170&type=9002 |
| 84 | 美团（人才计划） | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/g-8j7uMH3FSWdrVLiJ5fXQ |
| 85 | 金凤科技 | `beisen_zhiye` | `fetched` | 金风科技 | https://goldwind2.zhiye.com/campus/jobs |
| 86 | Meshy | `moka` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://app.mokahr.com/social-recruitment/taichi/148086?locale=en-US#/ |
| 87 | 长鑫存储 | `beisen_zhiye` | `fetched` | 长鑫存储技术有限公司 | https://cxmt.zhiye.com/campus/jobs |
| 88 | TP-LINK | `ats_custom` | `fetched` | TP-LINK 招聘 | https://hr.tp-link.com.cn/?sessionid= |
| 89 | 知乎 | `moka` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://app.mokahr.com/campus_apply/zhihu/68321#/jobs?zhineng%5B0%5D=131503&page=1&_k=1ggyui |
| 90 | 歌尔股份 | `hotjob_wecruit` | `fetched` | hotjob_wecruit | https://wecruit.hotjob.cn/SU63c50f8b0dcad47488052192/mc/position/campus?projectCode=106001&showProjectBanner=true |
| 91 | 海信集团 | `ats_custom` | `fetched` | 海信招聘—海信集团招聘官网 | https://jobs.hisense.com/7/jobs |
| 92 | 云深处科技 | `ats_custom` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://app135149.dingtalkoxm.com/campus-recruitment/yunshenchu/100000136?locale=zh-CN#/ |
| 93 | 懂车帝 | `feishu_jobs` | `fetched` | 懂车帝招聘 | https://dcar.jobs.feishu.cn/campus/?sessionid= |
| 94 | 韶音科技 | `moka` | `browser_required` | HTTP Error 302: The HTTP server returned a redirect error that would lead to an  | https://app.mokahr.com/campus-recruitment/aftershokzhr/36940?sessionid=#/page/%E6%A0%A1%E5%9B%AD%E6%8B%9B%E8%81%98 |
| 95 | 百度 | `ats_custom` | `fetched` | 百度校园招聘 | https://talent.baidu.com/jobs/list |
| 96 | 蚂蚁集团 | `ats_custom` | `fetched` | 职位列表 | https://hrrecommend.antgroup.com/job-list.html?code=RI2D8Qo_53mjwttzQKtL6z1ZIgy8ysp5ZdhFF3N6Hoo%3D |
| 97 | 三未信安 | `beisen_zhiye` | `fetched` | 三未信安 | https://sansec.zhiye.com/campus |
| 98 | 卫宁健康 | `wechat_article` | `fetched` | wechat_article, pagination | https://mp.weixin.qq.com/s/ulfbeXte8r2KHogOpBTN7g?scene=1&click_id=47 |
| 99 | 凯捷中国 | `external_form` | `fetched` | 凯捷中国27届校招宣讲简历投递 | https://v.wjx.cn/vm/ryU3Kv3.aspx |
| 100 | 航天一院 | `external_form` | `fetched` | Security Verification | https://m.zhaopin.com/xiaoyuan/company/detail?number=KA0133192447P90000003000&srccode=644201 |
| 101 | 宇树科技 | `beisen_zhiye` | `fetched` | 宇树科技 | https://unitree.zhiye.com/ |
| 102 | 三一集团 | `beisen_zhiye` | `fetched` | 三一集团有限公司 | https://sany.zhiye.com/campus/jobs?LocId=%5B%7B%22id%22%3A%221100%22%2C%22label%22%3A%22%E5%8C%97%E4%BA%AC%E5%B8%82%22%7D%5D |
| 103 | 海尔智家 | `ats_custom` | `fetched` | 海尔招聘-海尔官方招聘网站 | https://maker.haier.net/client/campusmobile/customizedjobs/type/top.html?sessionid= |
| 104 | 三环集团 | `ats_custom` | `fetched` | 三环集团招聘 | https://hr.cctc.cc |
