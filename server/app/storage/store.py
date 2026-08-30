from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.models import ResumeProfile
from app.settings import settings


class JsonStore:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or settings.data_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.resumes_file = self.base_dir / "resumes.json"
        self.rules_file = self.base_dir / "rules.json"
        self.results_file = self.base_dir / "results.json"

    def _read(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_resume(self, text: str) -> str:
        resume_id = str(uuid.uuid4())
        data = self._read(self.resumes_file)
        data[resume_id] = {"text": text}
        self._write(self.resumes_file, data)
        return resume_id

    def get_resume(self, resume_id: str) -> str | None:
        return self._read(self.resumes_file).get(resume_id, {}).get("text")

    def save_rules(self, resume_id: str, profile: ResumeProfile, raw_rules: dict[str, Any], source: str) -> None:
        data = self._read(self.rules_file)
        data[resume_id] = {
            "profile": profile.model_dump(),
            "raw_rules": raw_rules,
            "source": source,
        }
        self._write(self.rules_file, data)

    def get_profile(self, resume_id: str) -> ResumeProfile | None:
        item = self._read(self.rules_file).get(resume_id)
        if not item:
            return None
        return ResumeProfile.model_validate(item["profile"])

    def latest_profile(self) -> ResumeProfile | None:
        data = self._read(self.rules_file)
        if not data:
            return None
        latest_key = list(data.keys())[-1]
        return ResumeProfile.model_validate(data[latest_key]["profile"])

    def save_results(self, key: str, payload: dict[str, Any]) -> None:
        data = self._read(self.results_file)
        data[key] = payload
        self._write(self.results_file, data)

    def export_results(self) -> dict[str, Any]:
        return self._read(self.results_file)

