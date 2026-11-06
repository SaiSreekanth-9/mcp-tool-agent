"""mcp-tool-agent command line.

Usage:
    python main.py run "<request>" [--approve]
    python main.py demo
    python main.py list-tools
"""
import argparse
import sys

from src.agent import Agent
from src.config import settings
from src.registry import ToolRegistry


def _build_agent() -> Agent:
    return Agent(registry=ToolRegistry(audit_log=settings.audit_log),
                 api_key=settings.openai_api_key, model=settings.chat_model)


def cmd_list_tools() -> None:
    registry = ToolRegistry(audit_log=settings.audit_log)
    print(f"{'Tool':<18} {'Scope':<10} {'Approval':<10} Description")
    print("-" * 90)
    for tool in registry.list_tools():
        approval = "yes" if tool.get("approval_required") else "no"
        status = "" if tool.get("enabled", True) else " [DISABLED]"
        print(f"{tool['name']:<18} {tool['scope']:<10} {approval:<10} {tool['description']}{status}")


def cmd_run(request: str, approve: bool) -> int:
    agent = _build_agent()
    # Write tools need explicit approval. When stdin is a terminal, offer an
    # interactive y/n prompt; otherwise (scripts, pipes) block and say how
    # to approve. Never auto-approve.
    if not approve and ("note" in request.lower()):
        if sys.stdin.isatty():
            answer = input("This request calls a write tool (create_note). Approve? [y/N] ").strip().lower()
            approve = answer in {"y", "yes"}
        if not approve:
            # Route the blocked call through the agent/registry
            # (approved=False) so the denial is recorded in audit.log,
            # like every other denial. The registry refuses the write;
            # nothing is executed and no note is written.
            agent.handle(request, approved=False)
            print("Blocked: create_note is a write tool and requires explicit approval.")
            print("Re-run with --approve to allow it, e.g.:")
            print(f'  python main.py run "{request}" --approve')
            return 1
    outcome = agent.handle(request, approved=approve)
    return 0 if outcome.get("ok") else 1


def cmd_demo() -> None:
    agent = _build_agent()
    steps = [
        ("1. Profile lookup (read_only, no approval needed)",
         "Show me the profile for user u001", False),
        ("2. Ticket list (read_only, no approval needed)",
         "List the open tickets", False),
        ("3. Doc search (read_only, no approval needed)",
         "Search the docs for password reset", False),
        ("4. Create a note (write tool, approved for this demo step)",
         "Create a note about the outage", True),
        ("5. Delete attempt (disallowed tool — expect a denial)",
         "Delete user u001", False),
    ]
    for title, request, approve in steps:
        print(f"\n=== {title} ===")
        agent.handle(request, approved=approve)
    print(f"\nDemo done. Audit log: {settings.audit_log} "
          f"({len(agent.registry.audit.read_all())} entries total)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mcp-tool-agent",
        description="MCP-style tool registry + agent loop with permissions, "
                    "audit logging, and guardrails (demo mode needs no API key).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Handle a single request through the agent loop.")
    run_p.add_argument("request", help="User request, e.g. 'Show me the profile for user u001'")
    run_p.add_argument("--approve", action="store_true",
                       help="Approve write tools for this run (required for create_note).")

    sub.add_parser("demo", help="Run the canned demo: profile, tickets, docs, note, denied delete.")
    sub.add_parser("list-tools", help="Print the tool manifest table.")

    args = parser.parse_args()
    if args.command == "run":
        sys.exit(cmd_run(args.request, args.approve))
    if args.command == "demo":
        cmd_demo()
    elif args.command == "list-tools":
        cmd_list_tools()


if __name__ == "__main__":
    main()
