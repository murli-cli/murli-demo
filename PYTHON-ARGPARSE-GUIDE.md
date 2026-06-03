# Python / argparse — Murli Integration Guide

## argparse vs. click/typer: key differences

With **click** and **typer**, murli integrates via decorators applied to command functions. With **argparse**, there are no decorators — the integration is purely procedural:

1. **`murli.enable(parser)` must come after all `add_subparsers()` calls** — it walks the parser tree to register `--agent`, `--schema`, `--force`, `--dry-run`, and `--profile` flags, so the entire subparser tree must be built first.
2. **`murli.parse(parser)` replaces `parser.parse_args()`** — it returns a `(namespace, writer)` tuple instead of just the namespace. All command handlers receive the writer this way.
3. **Annotations are attached directly to subparser objects via `murli.annotate(subparser, Metadata(...))`** — there are no decorators, so each `add_parser()` result is stored in a variable and annotated explicitly.
4. **There is no shared context** — unlike click's `pass_writer`, the writer is returned once from `murli.parse()` and must be passed into handlers manually or used in the same function.

---

## Step 1: What You Get for Free

After calling `murli.enable(parser)` and `args, writer = murli.parse(parser)`, the following are available automatically with no additional code:

```python
murli.enable(parser)          # adds --agent, --schema, --force, --dry-run, --profile
args, writer = murli.parse(parser)  # returns (Namespace, Writer)
```

### `--help` output

```
usage: murli-work [-h] [--agent] [--schema] [--force] [--dry-run]
                  [--profile NAME]
                  {init,task,label,report,describe,doctor,profile} ...

murli-work - A sprint and project task tracker

positional arguments:
  {init,task,label,report,describe,doctor,profile}
                        Available subcommands
    init                Initialize/Reset the database and config
    task                Manage sprint tasks
    label               Manage global task labels
    report              Display progress report
    describe            Print full command schema as JSON
    doctor              Check naming conventions
    profile             Manage named flag profiles

options:
  -h, --help            show this help message and exit
  --agent               Force JSON output for agent/script use
  --schema              Print command schema as JSON and exit
  --force, --yes        Skip confirmation prompts
  --dry-run             Simulate without making changes
  --profile NAME        Load a named flag profile
```

### `describe` output (truncated to show structure)

```json
{
  "name": "murli-work",
  "summary": "murli-work - A sprint and project task tracker",
  "schema_version": "1.0",
  "tool_version": "",
  "capabilities": ["agent", "schema", "dry-run", "force", "profiles"],
  "commands": [
    {
      "name": "init",
      "agent_description": "Resets the database to seed data and writes default config.",
      "when_to_use": "First-time setup or to restore the database to a clean state.",
      "idempotent": true,
      "mutating": true,
      "returns": { "description": "Storage directory path", "type": "object", "properties": { "path": "string" } },
      "safety": { "read_only": false, "idempotent": true, "destructive": false, "dry_run_supported": false }
    },
    ...
  ]
}
```

---

## Step 2: Writer API

`murli.parse(parser)` returns a `(namespace, writer)` tuple. The writer is the single interface for all output:

```python
args, writer = murli.parse(parser)

# Log to stderr (visible in agent mode, useful for progress)
writer.log("Resetting database and seeding sample data...")

# Structured success envelope — message shown on TTY, JSON in agent mode
writer.write_success("Task 6 created successfully.", {"id": 6, "title": "Argparse test"})

# Structured error envelope with exit code
writer.write_error(AgentError.not_found("task with ID 999 not found", "Use task list to see valid IDs."))

# TTY branch for human-readable multi-format output
if writer.is_tty():
    print(format_ops.format_tasks_table(filtered))
else:
    writer.write_success(f"Found {len(filtered)} task(s).", {"tasks": filtered, "count": len(filtered)})
```

### Agent task list JSON

```
$ ./bin/murli-work-py-argparse --agent task list
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "ok",
  "message": "Found 5 task(s).",
  "result": {
    "tasks": [
      {
        "id": 1,
        "title": "Setup workspace layout",
        "desc": "Bootstrap directory structures for Go, Rust, Python and TS",
        "status": "done",
        "priority": "high",
        "labels": ["setup", "dev"],
        "created_at": "2026-05-28T18:00:00Z"
      },
      {
        "id": 2,
        "title": "Document CLI spec",
        "desc": "Draft the spec.md contracts and database JSON schemas",
        "status": "done",
        "priority": "medium",
        "labels": ["docs"],
        "created_at": "2026-05-28T18:30:00Z"
      },
      {
        "id": 3,
        "title": "Implement Cobra skeleton",
        "desc": "Build the Go Cobra reference implementation",
        "status": "doing",
        "priority": "high",
        "labels": ["dev", "go"],
        "created_at": "2026-05-29T04:00:00Z"
      },
      {
        "id": 4,
        "title": "Integrate Murli middleware",
        "desc": "Apply Murli wrappers to standard Go binaries",
        "status": "todo",
        "priority": "high",
        "labels": ["dev", "murli"],
        "created_at": "2026-05-29T05:00:00Z"
      },
      {
        "id": 5,
        "title": "Write Rust Clap reference",
        "desc": "Develop Rust-native Clap derive parser",
        "status": "todo",
        "priority": "medium",
        "labels": ["dev", "rust"],
        "created_at": "2026-05-29T06:00:00Z"
      }
    ],
    "count": 5
  }
}
```

---

## Step 3: Schema Annotations

Annotations are applied directly to subparser objects returned by `add_subparsers().add_parser()`. They must be placed **before** `murli.enable(parser)`:

```python
# Store the subparser reference
task_create = task_subparsers.add_parser("create", help="Create a new task")
task_create.add_argument("title", help="Task title")
task_create.add_argument("--priority", "-p", choices=["low", "medium", "high"])

# Annotate the subparser object directly — no decorators
murli.annotate(task_create, Metadata(
    agent_description="Creates a new task and assigns it a unique integer ID.",
    when_to_use="Adding a new item to the sprint backlog.",
    mutating=True,
    idempotent=False,
    returns=ReturnSchema(description="New task ID and title", type="object",
                         properties={"id": "int", "title": "string"}),
    examples=[
        Example(command='murli-work task create "Fix login bug" --priority high --labels dev,backend'),
    ],
))

# After ALL annotations are attached:
murli.enable(parser)
```

### `describe` output with `agent_description` fields populated

```
$ ./bin/murli-work-py-argparse describe | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'  {c[\"name\"]}: {c.get(\"agent_description\",\"\")}') for c in d['commands']]"
  init: Resets the database to seed data and writes default config.
  task:
  label:
  report: Computes and returns sprint completion statistics by status and priority.
```

Note: `task` and `label` intermediate parsers are not annotated (only their subcommands are). The full nested `task create`, `task list`, etc. annotations appear within the `subcommands` array of each parent.

---

## Step 4: Structured Errors

Each `AgentError` factory method maps to a specific exit code:

| Factory method                          | Exit code | `error` field   |
|-----------------------------------------|-----------|-----------------|
| `AgentError.user_error(msg, suggestion)`| 1         | `user_error`    |
| `AgentError.tool_error(msg)`            | 2         | `tool_error`    |
| `AgentError.not_found(msg, suggestion)` | 5         | `not_found`     |
| `AgentError.conflict_error(msg, suggestion)` | 7    | `conflict`      |

### Not-found error (task ID 999 doesn't exist)

```
$ ./bin/murli-work-py-argparse --agent task update 999 --status done; echo "exit: $?"
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "error",
  "code": 5,
  "error": "not_found",
  "message": "'task with ID 999 not found'",
  "suggestion": "Use task list to see valid IDs.",
  "recoverable": false
}
exit: 5
```

### Conflict error (duplicate label)

```
$ ./bin/murli-work-py-argparse --agent label create dev; echo "exit: $?"
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "error",
  "code": 7,
  "error": "conflict",
  "message": "label \"dev\" already exists",
  "suggestion": "Use label list to see existing labels.",
  "recoverable": false
}
exit: 7
```

---

## Step 5: Telemetry

`writer.log()` writes to **stderr** so it doesn't pollute the JSON envelope on stdout. This is useful for progress messages that an agent can see in its stderr stream while parsing the structured JSON from stdout.

```python
elif args.command == "init":
    writer.log("Resetting database and seeding sample data...")  # -> stderr
    db_ops.reset_db()
    writer.write_success("Initialized/Reset...", {"path": str(dir_path)})  # -> stdout JSON

elif args.command == "report":
    writer.log("Computing sprint statistics...")  # -> stderr
    report_data = format_ops.sprint_report_data(db)
    writer.write_success("Sprint report generated.", report_data)
```

### `--agent init` showing stderr log and stdout envelope

Running with `2>&1` to interleave both streams:

```
$ ./bin/murli-work-py-argparse --agent init 2>&1
Resetting database and seeding sample data...
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "ok",
  "message": "Initialized/Reset murli-work database with sample data and configuration in /Users/allank/Library/Application Support/murli-work",
  "result": {
    "path": "/Users/allank/Library/Application Support/murli-work"
  }
}
```

When streams are kept separate (stdout piped, stderr visible in terminal), the agent receives clean JSON on stdin while the log message appears in the terminal for observability.
