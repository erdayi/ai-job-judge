from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "data" / "site_inventory.json"
DEFAULT_OUT = ROOT / "data" / "site_validation_runs.json"
DEFAULT_REPORT = ROOT / "docs" / "SITE_VALIDATION.md"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Validate recruiting sites in inventory order.")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--start", type=int, default=1, help="1-based inventory offset.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--family", default="", help="Optional family filter.")
    parser.add_argument("--live", action="store_true", help="Fetch each URL and record lightweight page evidence.")
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    items = json.loads(args.inventory.read_text(encoding="utf-8"))
    indexed = [(index + 1, item) for index, item in enumerate(items)]
    if args.family:
        indexed = [(index, item) for index, item in indexed if item.get("family") == args.family]
    selected = indexed[max(args.start - 1, 0) : max(args.start - 1, 0) + args.limit]

    records = build_records(selected, args.live, args.timeout, args.workers)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict] = []
    if args.out.exists():
        existing = json.loads(args.out.read_text(encoding="utf-8"))
    merged = upsert_records(existing, records)
    args.out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    mode = "live" if args.live else "report-only" if not records else "queue"
    write_report(args.report, merged, mode)
    print(json.dumps({"count": len(records), "live": args.live, "report": str(args.report)}, ensure_ascii=False, indent=2))


def fetch_evidence(url: str, timeout: int) -> dict[str, object]:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    context = ssl.create_default_context()
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            raw = response.read(800_000)
            content_type = response.headers.get("content-type", "")
            text = decode_bytes(raw, content_type)
            return {
                "status": "fetched",
                "http_status": response.status,
                "final_url": response.geturl(),
                "content_type": content_type,
                "title": extract_title(text),
                "content_length": len(text),
                "signals": detect_signals(text, response.geturl()),
            }
    except HTTPError as exc:
        reason = str(exc)
        if exc.code in {301, 302, 303, 307, 308} and "infinite loop" in reason.lower():
            return {"status": "browser_required", "http_status": exc.code, "reason": reason}
        return {"status": "http_error", "http_status": exc.code, "reason": str(exc)}
    except URLError as exc:
        return {"status": "url_error", "reason": str(exc.reason)}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)[-300:]}


def decode_bytes(raw: bytes, content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    encodings = [match.group(1)] if match else []
    encodings.extend(["utf-8", "gb18030", "latin-1"])
    for encoding in encodings:
        try:
            return raw.decode(encoding, errors="replace")
        except LookupError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_title(text: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    if match:
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        if title:
            return title[:120]
    for pattern in [
        r"var\s+msg_title\s*=\s*'([^']+)'",
        r'var\s+msg_title\s*=\s*"([^"]+)"',
        r'"msg_title"\s*:\s*"([^"]+)"',
    ]:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()[:120]
    return ""


def detect_signals(text: str, url: str) -> list[str]:
    haystack = f"{url}\n{text[:120000]}".lower()
    checks = {
        "wechat_article": ["mp.weixin.qq.com", "js_name", "rich_media"],
        "moka": ["mokahr", "moka", "campus-recruitment"],
        "beisen_zhiye": ["zhiye.com", "jobadid", "beisen", "北森"],
        "feishu_jobs": ["jobs.feishu.cn", "position/list", "current=", "limit="],
        "hotjob_wecruit": ["wecruit.hotjob.cn", "hotjob", "school.html"],
        "pagination": ["下一页", "next", "page", "current", "load more", "加载更多"],
        "detail_link": ["detail", "jobadid", "positionid", "jobid", "职位详情", "查看详情"],
        "login_gate": ["登录", "login", "sign in", "验证码", "sessionid"],
        "job_text": ["岗位职责", "任职资格", "职位描述", "工作职责", "requirements"],
    }
    signals = []
    for name, needles in checks.items():
        if any(needle.lower() in haystack for needle in needles):
            signals.append(name)
    return signals


def write_report(path: Path, records: list[dict], mode: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 站点顺序验证记录",
        "",
        "本文件按 `data/site_inventory.json` 的顺序追加记录。状态含义：",
        "",
        "- `pending_manual_scan`：已进入验证队列，待插件真实扫描。",
        "- `fetched`：已完成轻量 HTTP 读取，仍需插件扫描验证岗位抽取和详情链接。",
        "- `browser_required`：轻量 HTTP 无法处理跳转/SPA/风控，需要用浏览器插件验证。",
        "- `http_error` / `url_error` / `error`：轻量读取失败，需要浏览器人工确认。",
        "",
        f"最近一次运行模式：{mode}",
        "",
        "## 摘要",
        "",
        f"- 覆盖链接：`{len(records)}`",
        f"- 清单顺序：`{records[0]['inventory_order'] if records else 0}` - `{records[-1]['inventory_order'] if records else 0}`",
        f"- 状态分布：{format_counter(Counter(record.get('status', 'unknown') for record in records))}",
        f"- 家族分布：{format_counter(Counter(record.get('family', 'unknown') for record in records))}",
        "",
        "## 明细",
        "",
        "| 顺序 | 公司 | 家族 | 状态 | 页面证据 | URL |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        evidence = record.get("evidence", {})
        signals = ", ".join(evidence.get("signals", [])) if isinstance(evidence, dict) else ""
        title = evidence.get("title", "") if isinstance(evidence, dict) else ""
        proof = title or signals or evidence.get("reason", "") if isinstance(evidence, dict) else ""
        lines.append(
            "| {order} | {company} | `{family}` | `{status}` | {proof} | {url} |".format(
                order=record["inventory_order"],
                company=escape_cell(record["company"]),
                family=record["family"],
                status=record["status"],
                proof=escape_cell(str(proof)[:80]),
                url=record["url"],
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def upsert_records(existing: list[dict], new_records: list[dict]) -> list[dict]:
    by_order = {record.get("inventory_order"): record for record in existing}
    for record in new_records:
        by_order[record.get("inventory_order")] = record
    return [by_order[key] for key in sorted(key for key in by_order if isinstance(key, int))]


def build_records(selected: list[tuple[int, dict]], live: bool, timeout: int, workers: int) -> list[dict]:
    if not live:
        return [build_record(order, item, {"mode": "queued"}, live) for order, item in selected]

    workers = max(1, min(workers, len(selected) or 1))
    evidence_by_order: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_evidence, item["url"], timeout): (order, item)
            for order, item in selected
        }
        for future in as_completed(futures):
            order, _item = futures[future]
            try:
                evidence_by_order[order] = future.result()
            except Exception as exc:
                evidence_by_order[order] = {"status": "error", "reason": str(exc)[-300:]}
    return [build_record(order, item, evidence_by_order.get(order, {"status": "error"}), live) for order, item in selected]


def build_record(order: int, item: dict, evidence: dict, live: bool) -> dict:
    return {
        "inventory_order": order,
        "company": item.get("company", ""),
        "family": item.get("family", ""),
        "host": item.get("host", ""),
        "url": item.get("url", ""),
        "status": "pending_manual_scan" if not live else evidence.get("status", "unknown"),
        "evidence": evidence,
        "validated_at": datetime.now().isoformat(timespec="seconds"),
    }


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def format_counter(counter: Counter) -> str:
    return ", ".join(f"`{key}` {value}" for key, value in sorted(counter.items()))


if __name__ == "__main__":
    main()
