"""Append-only audit log (JSON lines).

Every planned tool call is recorded, whether it was allowed or denied:
timestamp, tool, caller, arguments, allowed/denied, and a short result
summary. Arguments are logged as given; never pass secrets as tool arguments.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    def __init__(self, log_path: str | Path = "audit.log") -> None:
        self.log_path = Path(log_path)

    def log(
        self,
        tool: str,
        caller: str = "agent",
        arguments: dict | None = None,
        allowed: bool = True,
        result: str = "",
    ) -> dict:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "caller": caller,
            "arguments": arguments or {},
            "allowed": allowed,
            "result": result,
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def read_all(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        entries = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                entries.append(json.loads(line))
        return entries
