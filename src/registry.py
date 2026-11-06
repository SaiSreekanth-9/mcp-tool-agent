"""Tool registry: loads the manifest, validates it, and dispatches calls.

Only tools declared in the manifest can run. Dispatch enforces the manifest
(unknown tool -> error, disabled tool -> denial) and the policy gate
(write tools need approval). Tool implementations read/write only the
synthetic sample data under ``data/``.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.audit import AuditLogger
from src.policy import ApprovalRequiredError, DeniedError, check_policy

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class UnknownToolError(Exception):
    """Raised when a call names a tool that is not in the manifest."""


class ToolRegistry:
    def __init__(
        self,
        manifest_path: str | Path | None = None,
        data_dir: str | Path | None = None,
        audit_log: str | Path | None = None,
    ) -> None:
        self.manifest_path = Path(manifest_path or PROJECT_ROOT / "tools" / "manifest.json")
        self.data_dir = Path(data_dir or PROJECT_ROOT / "data")
        self.audit = AuditLogger(audit_log or "audit.log")
        self.tools = self._load_manifest()

    # -- manifest ---------------------------------------------------------
    def _load_manifest(self) -> dict[str, dict]:
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        tools: dict[str, dict] = {}
        for tool in manifest.get("tools", []):
            for field in ("name", "description", "scope"):
                if field not in tool:
                    raise ValueError(f"Manifest tool missing required field '{field}': {tool}")
            if tool["scope"] not in {"read_only", "write"}:
                raise ValueError(f"Tool '{tool['name']}' has invalid scope: {tool['scope']}")
            if tool["name"] in tools:
                raise ValueError(f"Duplicate tool in manifest: {tool['name']}")
            tools[tool["name"]] = tool
        if not tools:
            raise ValueError("Manifest declares no tools.")
        return tools

    def list_tools(self) -> list[dict]:
        return list(self.tools.values())

    # -- dispatch ---------------------------------------------------------
    def call(self, name: str, arguments: dict | None = None, approved: bool = False,
             caller: str = "agent") -> dict:
        """Dispatch one tool call, enforcing manifest + policy, auditing the outcome.

        Returns ``{"ok": bool, "result": ...}``. Denials are returned, not raised,
        so the agent loop can report them instead of crashing.
        """
        arguments = arguments or {}
        tool = self.tools.get(name)
        if tool is None:
            self.audit.log(name, caller, arguments, allowed=False,
                           result=f"Unknown tool: {name} is not in the manifest.")
            return {"ok": False, "error": f"Unknown tool '{name}': not in the manifest."}
        try:
            check_policy(tool, approved=approved)
            self._validate_arguments(tool, arguments)
        except (DeniedError, ApprovalRequiredError, ValueError) as exc:
            self.audit.log(name, caller, arguments, allowed=False, result=str(exc))
            return {"ok": False, "error": str(exc)}
        try:
            result = self._execute(name, arguments)
        except Exception as exc:  # tool failure is audited, not fatal to the loop
            self.audit.log(name, caller, arguments, allowed=True, result=f"Error: {exc}")
            return {"ok": False, "error": str(exc)}
        summary = json.dumps(result, default=str)[:200]
        self.audit.log(name, caller, arguments, allowed=True, result=summary)
        return {"ok": True, "result": result}

    def _validate_arguments(self, tool: dict, arguments: dict) -> None:
        for param, spec in (tool.get("parameters") or {}).items():
            if spec.get("required") and param not in arguments:
                raise ValueError(f"Tool '{tool['name']}' missing required parameter '{param}'.")

    # -- tool implementations (synthetic data only) -----------------------
    def _execute(self, name: str, arguments: dict):
        if name == "get_user_profile":
            return self._get_user_profile(arguments["user_id"])
        if name == "search_docs":
            return self._search_docs(arguments["query"])
        if name == "list_tickets":
            return self._list_tickets(arguments.get("status"))
        if name == "create_note":
            return self._create_note(arguments["text"])
        if name == "delete_user":
            # Unreachable in practice: check_policy denies disabled tools first.
            raise DeniedError("Tool 'delete_user' is disabled and can never be executed.")
        raise UnknownToolError(f"No implementation for tool '{name}'.")

    def _load_json(self, filename: str):
        path = self.data_dir / filename
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _get_user_profile(self, user_id: str) -> dict:
        for user in self._load_json("sample_users.json"):
            if user.get("id") == user_id:
                return user
        raise ValueError(f"No user found with id '{user_id}'.")

    def _search_docs(self, query: str) -> list[dict]:
        keywords = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", query) if len(w) > 2]
        docs_dir = self.data_dir / "sample_docs"
        hits: list[dict] = []
        for doc_path in sorted(docs_dir.glob("*.md")):
            text = doc_path.read_text(encoding="utf-8")
            lowered = text.lower()
            score = sum(lowered.count(kw) for kw in keywords)
            if score == 0:
                continue
            snippet = next(
                (line.strip() for line in text.splitlines()
                 if any(kw in line.lower() for kw in keywords) and line.strip()),
                "",
            )
            hits.append({"file": doc_path.name, "score": score, "snippet": snippet})
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits

    def _list_tickets(self, status: str | None = None) -> list[dict]:
        tickets = self._load_json("sample_tickets.json")
        if status:
            tickets = [t for t in tickets if t.get("status") == status]
        return tickets

    def _create_note(self, text: str) -> dict:
        notes_path = self.data_dir / "notes.json"
        notes = self._load_json("notes.json")
        note = {
            "id": f"n{len(notes) + 1:03d}",
            "text": text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        notes.append(note)
        notes_path.write_text(json.dumps(notes, indent=2), encoding="utf-8")
        return note
