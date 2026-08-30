from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any

from app.settings import settings


class ClaudeCliClient:
    @property
    def enabled(self) -> bool:
        return bool(shutil.which(settings.claude_command))

    async def json_prompt(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Claude CLI is not available")

        args = [
            settings.claude_command,
            "-p",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(schema, ensure_ascii=False),
            "--max-budget-usd",
            str(settings.claude_max_budget_usd),
            "--no-session-persistence",
            "--permission-mode",
            "dontAsk",
        ]
        if settings.claude_model:
            args.extend(["--model", settings.claude_model])

        process = await _create_process(args)
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(prompt.encode("utf-8")),
                timeout=settings.claude_timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError("Claude CLI timed out")

        if process.returncode != 0:
            message = stderr.decode("utf-8", errors="ignore") or stdout.decode("utf-8", errors="ignore")
            raise RuntimeError(f"Claude CLI failed: {message[-1200:]}")

        text = stdout.decode("utf-8", errors="ignore").strip()
        payload = json.loads(text)
        if isinstance(payload, dict) and "result" in payload:
            result = payload["result"]
            if isinstance(result, str):
                return json.loads(result)
            if isinstance(result, dict):
                return result
        if isinstance(payload, dict):
            return payload
        raise RuntimeError("Claude CLI returned non-object JSON")


async def _create_process(args: list[str]) -> asyncio.subprocess.Process:
    if os.name == "nt":
        resolved_args = args.copy()
        resolved_args[0] = _resolve_windows_claude_exe(resolved_args[0])
        return await asyncio.create_subprocess_exec(
            *resolved_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    return await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


def _resolve_windows_claude_exe(command: str) -> str:
    path = shutil.which(command)
    if not path:
        return command
    candidate = Path(path)
    if candidate.suffix.lower() in {".cmd", ".ps1", ""}:
        exe = candidate.parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
        if exe.exists():
            return str(exe)
    return path


claude_cli_client = ClaudeCliClient()
