"""Agent loop: plan tool calls from a user request, execute the allowed ones,
and report denials instead of crashing.

Demo mode uses a deterministic rule-based planner (keyword routing), so it
runs with only the Python standard library and no API key:

- "profile" -> get_user_profile
- "ticket"  -> list_tickets
- "search" / "docs" -> search_docs
- "note"    -> create_note (approval-gated)
- "delete"  -> delete_user (always denied by the registry)

When OPENAI_API_KEY is set, ``plan_with_llm`` offers an optional LLM planner
instead. Its langchain imports are lazy: importing this module never requires
langchain, and calling the LLM planner without the key raises a clear error.
"""
from __future__ import annotations

import re

from src.registry import ToolRegistry


def plan_rule_based(request: str) -> tuple[str, dict] | None:
    """Return (tool_name, arguments) for a request, or None if nothing matches."""
    text = request.lower()
    user_match = re.search(r"\bu(\d{3})\b", text)
    user_id = f"u{user_match.group(1)}" if user_match else "u001"

    if "delete" in text:
        return ("delete_user", {"user_id": user_id})
    if "note" in text:
        note_text = request
        about = re.search(r"about\s+(.+)$", request, re.IGNORECASE)
        if about:
            note_text = about.group(1).strip()
        return ("create_note", {"text": note_text})
    if "profile" in text or "user" in text:
        return ("get_user_profile", {"user_id": user_id})
    if "ticket" in text:
        status = None
        for candidate in ("open", "in_progress", "resolved"):
            if candidate in text:
                status = candidate
        args: dict = {}
        if status:
            args["status"] = status
        return ("list_tickets", args)
    if "search" in text or "doc" in text:
        query = re.sub(r"(?i)\b(search|docs?|for|the|me|please|about)\b", " ", request).strip()
        return ("search_docs", {"query": query or request})
    return None


def plan_with_llm(request: str, api_key: str, model: str = "gpt-4o-mini") -> tuple[str, dict]:
    """Optional LLM planner. Requires OPENAI_API_KEY; lazy langchain import."""
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. The LLM planner needs a key; "
            "leave it unset to use the deterministic rule-based planner instead."
        )
    try:
        from langchain_openai import ChatOpenAI  # noqa: F401  (lazy, optional)
    except ImportError as exc:
        raise RuntimeError(
            "langchain-openai is not installed. Run `pip install -r requirements.txt` "
            "to enable the LLM planner, or leave OPENAI_API_KEY unset for demo mode."
        ) from exc
    raise RuntimeError(
        "LLM planning is a stub in this demo: the rule-based planner handles the "
        "supported requests. Wire ChatOpenAI tool-calling here to extend it."
    )


class Agent:
    def __init__(self, registry: ToolRegistry | None = None,
                 api_key: str = "", model: str = "gpt-4o-mini") -> None:
        self.registry = registry or ToolRegistry()
        self.api_key = api_key
        self.model = model

    def handle(self, request: str, approved: bool = False) -> dict:
        """Plan, execute, and report. Denials are reported, never raised."""
        print(f"Request: {request}")
        plan = None
        if self.api_key:
            try:
                plan = plan_with_llm(request, self.api_key, self.model)
            except RuntimeError as exc:
                print(f"LLM planner unavailable ({exc}); falling back to rule-based planning.")
        plan = plan or plan_rule_based(request)
        if plan is None:
            print("No tool matches this request. Try asking about a profile, "
                  "tickets, docs, a note, or (to see a denial) deleting a user.")
            return {"ok": False, "error": "No matching tool."}
        tool_name, arguments = plan
        print(f"Planned tool call: {tool_name}({arguments})")
        outcome = self.registry.call(tool_name, arguments, approved=approved)
        if outcome["ok"]:
            print(f"Allowed. Result: {outcome['result']}")
        else:
            print(f"Denied/blocked: {outcome['error']}")
        return outcome
