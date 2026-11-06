"""Permission scopes and the approval gate.

Rules:
- read_only tools run freely.
- write tools require explicit approval. In the CLI that approval is the
  ``--approve`` flag (see main.py); approval is never granted implicitly.
- A tool that is disabled in the manifest (``enabled: false``) is denied
  outright, approval or not.
"""
from __future__ import annotations


class DeniedError(Exception):
    """Raised when a tool call is refused by policy."""


class ApprovalRequiredError(Exception):
    """Raised when a write tool is called without explicit approval."""


def requires_approval(tool: dict) -> bool:
    return bool(tool.get("approval_required", False)) or tool.get("scope") == "write"


def check_policy(tool: dict, approved: bool = False) -> None:
    """Enforce the policy for one manifest entry. Raises on denial."""
    if not tool.get("enabled", True):
        raise DeniedError(
            f"Tool '{tool['name']}' is disabled in the manifest and can never be executed."
        )
    if requires_approval(tool) and not approved:
        raise ApprovalRequiredError(
            f"Tool '{tool['name']}' is a write tool and requires explicit approval "
            f"(re-run with --approve)."
        )
