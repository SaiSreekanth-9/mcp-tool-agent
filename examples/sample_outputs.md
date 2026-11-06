# Sample outputs

> Captured from real runs on 2026-11-05 (Python 3.12, standard library only,
> no API key). Output is pasted verbatim. Note the `create_note` step appends
> a note to `data/notes.json`, so re-running the demo creates a new note id
> (`n001`, `n002`, …) and a new timestamp each time.

## `python main.py list-tools`

```
Tool               Scope      Approval   Description
------------------------------------------------------------------------------------------
get_user_profile   read_only  no         Return the synthetic profile for a user id (e.g. u001) from data/sample_users.json.
search_docs        read_only  no         Keyword search over the synthetic documents in data/sample_docs/. Returns matching snippets with source file names.
list_tickets       read_only  no         List synthetic support tickets from data/sample_tickets.json. Optionally filter by status (open, in_progress, resolved).
create_note        write      yes        Append a note to data/notes.json. A write tool: requires explicit approval before it runs.
delete_user        write      yes        Delete a user. DISALLOWED: this tool is declared in the manifest only to demonstrate guardrails. It is disabled and the registry always refuses to execute it. [DISABLED]
```

## `python main.py demo`

```

=== 1. Profile lookup (read_only, no approval needed) ===
Request: Show me the profile for user u001
Planned tool call: get_user_profile({'user_id': 'u001'})
Allowed. Result: {'email': 'ada.okafor@example.com', 'id': 'u001', 'name': 'Ada Okafor', 'role': 'Support Engineer', 'status': 'active', 'team': 'Customer Success'}

=== 2. Ticket list (read_only, no approval needed) ===
Request: List the open tickets
Planned tool call: list_tickets({'status': 'open'})
Allowed. Result: [{'assignee': 'u001', 'id': 'T-101', 'priority': 'high', 'status': 'open', 'title': 'Password reset email never arrives'}, {'assignee': 'u003', 'id': 'T-104', 'priority': 'high', 'status': 'open', 'title': 'Outage: API returns 500 for search endpoint'}]

=== 3. Doc search (read_only, no approval needed) ===
Request: Search the docs for password reset
Planned tool call: search_docs({'query': 'password reset'})
Allowed. Result: [{'file': 'password_reset.md', 'score': 7, 'snippet': '# Password Reset Guide'}]

=== 4. Create a note (write tool, approved for this demo step) ===
Request: Create a note about the outage
Planned tool call: create_note({'text': 'the outage'})
Allowed. Result: {'id': 'n001', 'text': 'the outage', 'created_at': '2026-11-05T15:02:20.951525+00:00'}

=== 5. Delete attempt (disallowed tool — expect a denial) ===
Request: Delete user u001
Planned tool call: delete_user({'user_id': 'u001'})
Denied/blocked: Tool 'delete_user' is disabled in the manifest and can never be executed.

Demo done. Audit log: audit.log (5 entries total)
```

## `python main.py run "Create a note about the outage"` (no `--approve`)

```
Request: Create a note about the outage
Planned tool call: create_note({'text': 'the outage'})
Denied/blocked: Tool 'create_note' is a write tool and requires explicit approval (re-run with --approve).
Blocked: create_note is a write tool and requires explicit approval.
Re-run with --approve to allow it, e.g.:
  python main.py run "Create a note about the outage" --approve
```

The note is **not** written — the approval gate stops the call before the
registry executes it — but the blocked attempt **is** recorded in `audit.log`
with `"allowed": false`, like the denied delete below. (Before this fix the
CLI printed "Blocked" and exited without auditing the attempt.)

## `python main.py run "Delete user u001"`

```
Request: Delete user u001
Planned tool call: delete_user({'user_id': 'u001'})
Denied/blocked: Tool 'delete_user' is disabled in the manifest and can never be executed.
```

The agent reports the denial instead of crashing, and the denial is recorded
in `audit.log` with `"allowed": false`.

## `audit.log` after the demo (one JSON line per planned call, verbatim)

```json
{"timestamp": "2026-11-05T15:02:20.949602+00:00", "tool": "get_user_profile", "caller": "agent", "arguments": {"user_id": "u001"}, "allowed": true, "result": "{\"email\": \"ada.okafor@example.com\", \"id\": \"u001\", \"name\": \"Ada Okafor\", \"role\": \"Support Engineer\", \"status\": \"active\", \"team\": \"Customer Success\"}"}
{"timestamp": "2026-11-05T15:02:20.950180+00:00", "tool": "list_tickets", "caller": "agent", "arguments": {"status": "open"}, "allowed": true, "result": "[{\"assignee\": \"u001\", \"id\": \"T-101\", \"priority\": \"high\", \"status\": \"open\", \"title\": \"Password reset email never arrives\"}, {\"assignee\": \"u003\", \"id\": \"T-104\", \"priority\": \"high\", \"status\": \"open\", \"ti"}
{"timestamp": "2026-11-05T15:02:20.951204+00:00", "tool": "search_docs", "caller": "agent", "arguments": {"query": "password reset"}, "allowed": true, "result": "[{\"file\": \"password_reset.md\", \"score\": 7, \"snippet\": \"# Password Reset Guide\"}]"}
{"timestamp": "2026-11-05T15:02:20.951696+00:00", "tool": "create_note", "caller": "agent", "arguments": {"text": "the outage"}, "allowed": true, "result": "{\"id\": \"n001\", \"text\": \"the outage\", \"created_at\": \"2026-11-05T15:02:20.951525+00:00\"}"}
{"timestamp": "2026-11-05T15:02:20.951817+00:00", "tool": "delete_user", "caller": "agent", "arguments": {"user_id": "u001"}, "allowed": false, "result": "Tool 'delete_user' is disabled in the manifest and can never be executed."}
```

> The `list_tickets` result above is truncated at 200 characters by the audit
> logger (`result` summaries are capped) — that is the real logged line.
> The `list-tools` and `demo` transcripts above are verbatim.
```

