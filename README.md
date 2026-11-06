# MCP Tool Agent — a permission-scoped tool registry + agent loop

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![LangChain](https://img.shields.io/badge/langchain-optional-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

A small **MCP-style tool registry and agent loop** that shows how an LLM agent
can safely call tools: every tool is declared in a manifest with a permission
scope, write tools need explicit approval, a disallowed tool is always refused,
and every planned call — allowed or denied — is written to an append-only
audit log.

Give it a request like *"Show me the profile for user u001"* and the agent
plans a tool call, checks the policy, executes it, and reports the result.
Ask it to *"Delete user u001"* and it plans the call, the registry refuses it,
and the agent reports the denial instead of crashing.

## Origin & honesty note

This project is **inspired by** resume experience building MCP servers and
clients that connect LLM agents to internal systems through secure,
permission-scoped tool calls. It is a **standalone portfolio project built
from scratch with synthetic sample data only**. It was **not** deployed at any
employer, uses **no real company data**, and makes **no claims about employment
metrics or dates**. All users, tickets, documents, and notes in `data/` are
fictional.

## MCP-style, not the official MCP SDK

This project demonstrates the **concepts** behind the Model Context Protocol —
a tool manifest, permission scopes, an approval gate, and an audit log — with
a small local registry of its own. It is **not** the official MCP Python SDK,
does not implement the MCP wire protocol, and makes **no claim of protocol
compliance**. If you need real MCP servers/clients, use the official SDK; this
project is a readable, dependency-light illustration of the ideas.

## Problem statement

Agents that can call tools are powerful and dangerous: one bad plan can write,
delete, or leak data. The usual fixes — prompt the model nicely, hope for the
best — are not controls. This project puts the controls in code, outside the
model: a manifest decides which tools exist, a policy module decides which
calls are allowed, and an audit log records what was attempted. The agent
plans; the registry enforces.

## Features

- 📋 **Tool manifest** (`tools/manifest.json`): name, description, scope
  (`read_only` / `write`), parameters, and approval requirement per tool
- 🔐 **Permission scopes + approval gate**: write tools require explicit
  approval via `--approve` (or an interactive y/n prompt); never auto-approved
- 🛡️ **Guardrail demo**: `delete_user` is declared in the manifest as
  disabled — the registry always refuses it, and the agent reports the denial
- 📜 **Append-only audit log** (`audit.log`, JSON lines): timestamp, tool,
  caller, arguments, allowed/denied, result summary
- 🤖 **Deterministic rule-based planner** in demo mode — keyword routing, no
  API key, standard library only
- 🧠 **Optional LLM planner** when `OPENAI_API_KEY` is set (lazy langchain
  import; demo mode never needs it)

## Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ User request │─────▶│    Agent     │─────▶│   Registry   │
│  "Show me    │      │  plan (rule- │      │  manifest +  │
│   the profile│      │  based, or   │      │  dispatch    │
│   for u001"  │      │  optional    │      │  (only listed│
└──────────────┘      │  LLM plan)   │      │   tools run) │
                      └──────┬───────┘      └──────┬───────┘
                             │                     │
                      ┌──────▼───────┐      ┌──────▼───────┐
                      │    Policy    │◀─────│    Tools     │
                      │  scopes +    │      │  profile /   │
                      │  approval    │      │  docs /      │
                      │  gate        │      │  tickets /   │
                      └──────┬───────┘      │  notes       │
                             │              └──────┬───────┘
                      ┌──────▼───────┐             │
                      │  Audit log   │◀────────────┘
                      │  (JSON lines,│   every call,
                      │  allowed and │   allowed or denied
                      │  denied)     │
                      └──────────────┘
```

**Flow:** the agent plans one tool call from the request. The registry looks
the tool up in the manifest (unknown → refused), the policy module checks
scope and approval (disabled → denied, write without approval → blocked),
the tool runs against the synthetic data, and the audit logger records the
outcome. Denials are returned as results, so the loop reports them instead
of crashing.

## Project structure

```
mcp-tool-agent/
├── main.py                  # CLI: run | demo | list-tools
├── requirements.txt
├── .env.example
├── src/
│   ├── config.py            # settings from env (dotenv optional, never fails at import)
│   ├── registry.py          # ToolRegistry: manifest loading, validation, dispatch
│   ├── policy.py            # permission scopes + approval gate
│   ├── audit.py             # append-only JSON-lines audit log
│   └── agent.py             # agent loop + rule-based planner (+ optional LLM planner)
├── tools/
│   └── manifest.json        # tool declarations: scope, params, approval, enabled
├── data/
│   ├── sample_users.json    # synthetic users (u001–u003)
│   ├── sample_tickets.json  # synthetic support tickets (T-101–T-104)
│   ├── sample_docs/         # 3 short fictional docs (password reset, on-call, triage)
│   └── notes.json           # notes appended by create_note (starts empty)
└── examples/
    └── sample_outputs.md    # real captured demo + list-tools output
```

## Tools

| Tool | Scope | Approval | What it does |
|---|---|---|---|
| `get_user_profile` | read_only | no | Profile for a user id from `data/sample_users.json` |
| `search_docs` | read_only | no | Keyword search over `data/sample_docs/` |
| `list_tickets` | read_only | no | Synthetic tickets, optionally filtered by status |
| `create_note` | write | **yes** | Appends a note to `data/notes.json` |
| `delete_user` | write | yes | **DISABLED** — declared only to demonstrate guardrails; always denied |

## Installation

```bash
git clone <your-repo-url> mcp-tool-agent
cd mcp-tool-agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt   # only needed for the optional LLM planner
cp .env.example .env              # optional: leave OPENAI_API_KEY blank for demo mode
```

**Demo mode needs no API key and no installed dependencies** — it runs on the
Python standard library plus this project's own modules. Install
`requirements.txt` only if you want the optional LLM planner.

## Usage

```bash
# See the tool manifest as a table
python main.py list-tools

# Run the canned demo: profile, tickets, docs, approved note, denied delete
python main.py demo

# Handle a single request
python main.py run "Show me the profile for user u001"
python main.py run "List the open tickets"
python main.py run "Search the docs for password reset"

# Write tools need explicit approval — without --approve this is blocked:
python main.py run "Create a note about the outage"
# With approval it runs and appends to data/notes.json:
python main.py run "Create a note about the outage" --approve

# Disallowed tools are always denied, approval or not:
python main.py run "Delete user u001"
```

Example session:

```
$ python main.py run "Show me the profile for user u001"
Request: Show me the profile for user u001
Planned tool call: get_user_profile({'user_id': 'u001'})
Allowed. Result: {'email': 'ada.okafor@example.com', 'id': 'u001', 'name': 'Ada Okafor', 'role': 'Support Engineer', 'status': 'active', 'team': 'Customer Success'}

$ python main.py run "Delete user u001"
Request: Delete user u001
Planned tool call: delete_user({'user_id': 'u001'})
Denied/blocked: Tool 'delete_user' is disabled in the manifest and can never be executed.
```

## Configuration

All settings live in `.env` (see `.env.example`):

| Variable | Default | Meaning |
|---|---|---|
| `OPENAI_API_KEY` | — | **Optional.** Leave blank for deterministic rule-based planning (demo mode). Set it to enable the optional LLM planner path. |
| `AUDIT_LOG` | `audit.log` | Path of the append-only audit log (JSON lines) |
| `CHAT_MODEL` | `gpt-4o-mini` | Chat model for the optional LLM planner |
| `MANIFEST_PATH` | `tools/manifest.json` | Path to the tool manifest |
| `DATA_DIR` | `data` | Directory holding the synthetic sample data |

Approval is **not** an environment variable: it comes only from the `--approve`
CLI flag (or an interactive y/n prompt when stdin is a terminal), so a write
can never be approved by a stray setting in `.env`.

## Sample outputs

See [examples/sample_outputs.md](examples/sample_outputs.md) for the full
captured `demo` and `list-tools` output, the blocked-without-approval case,
the denied delete, and the audit log entries the demo writes.

## Limitations & future work

- The rule-based planner is keyword routing, not real language understanding —
  it handles the five demo request shapes and reports anything else as
  "no matching tool".
- The LLM planner path is a stub that validates the key and imports
  langchain-openai lazily; wiring full ChatOpenAI tool-calling is the natural
  next step.
- The audit log is a local file with no signing or tamper-evidence; a
  production version would hash-chain entries.
- Single-user, single-tenant, file-backed data — no auth, no concurrency
  control, no real MCP protocol (by design; see the note above).
- Planned: real MCP SDK server/client mode, per-caller scopes, redaction of
  sensitive arguments in the audit log.

## License

MIT — see [LICENSE](LICENSE) (add one, e.g. via `gh repo create` template or choosealicense.com).
```

