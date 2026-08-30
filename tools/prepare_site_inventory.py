from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.services.site_patterns import classify_site  # noqa: E402


URL_RE = re.compile(r"https?://\S+")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python tools/prepare_site_inventory.py <pasted-text.txt> <out.json>")
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    rows = list(csv.DictReader(input_path.read_text(encoding="utf-8").splitlines(), delimiter="\t"))
    items = []
    for row in rows:
        link = row.get("投递链接", "").strip()
        match = URL_RE.search(link)
        if not match:
            continue
        url = match.group(0)
        site = classify_site(url)
        items.append(
            {
                "company": row.get("公司名称", "").strip(),
                "industry": row.get("行业", "").strip(),
                "status": row.get("状态", "").strip(),
                "url": url,
                "family": site["family"],
                "host": site["host"],
                "hints": site["hints"],
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    families: dict[str, int] = {}
    for item in items:
        families[item["family"]] = families.get(item["family"], 0) + 1
    print(json.dumps({"total": len(items), "families": families}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
