# Python / click — Murli Integration Guide

This guide walks through integrating the murli middleware into a click CLI application step by step. Each step shows the code change, explains the mechanic, and captures the terminal output.

The target application is `murli-work`, a sprint task tracker.

---

## Step 1: What You Get for Free

Calling `murli.enable(cli)` after all command definitions injects:

- `--agent` — forces JSON output without piping
- `--schema` — prints per-command JSON schema and exits
- `--force` / `--yes` — suppresses confirmation prompts
- `--dry-run` — marks the invocation as preview-only
- `--profile NAME` — loads a saved flag profile
- `describe` subcommand — prints the full command tree as JSON
- `doctor` subcommand — checks naming convention compliance
- `profile` subcommand — manages saved flag profiles

TTY detection is automatic: plain text at a terminal, JSON when piped or when `--agent` is passed.

**Note on `--output`:** murli normally injects `--output` for controlling its format (json/ndjson/text). Because `task list` defines its own `--output` flag, murli detects the collision via `_has_output_option()` and skips injecting its own. All other flags are unaffected.

### Code change

```python
import murli

# ... all command definitions ...

murli.enable(cli)   # after all commands are registered

if __name__ == "__main__":
    cli()
```

### `--help` output

```
Usage: murli-work-py-click [OPTIONS] COMMAND [ARGS]...

  murli-work - A sprint and project task tracker

Options:
  --agent         Force JSON output for agent/script use
  --schema        Print command schema as JSON and exit
  --force, --yes  Skip confirmation prompts
  --dry-run       Simulate without making changes
  --profile NAME  Load a named flag profile
  --help          Show this message and exit.

Commands:
  describe  Print the full command schema as JSON
  doctor    Check command and flag naming conventions
  init      Initialize/Reset the database and config
  label     Manage global task labels
  profile   Manage named flag profiles
  report    Display progress report
  task      Manage sprint tasks
```

---

## Step 2: Writer API

Replace `click.echo()` and `sys.exit()` with `writer.write_success()` and `writer.write_error()`. Use `@murli.pass_writer` to inject the writer:

```python
@cli.command()
@murli.pass_writer
def init(writer):
    db_ops.reset_db()
    dir_path = db_ops.get_storage_dir()
    writer.write_success(
        f"Initialized database in {dir_path}",
        {"path": str(dir_path)},
    )
```

For commands with display-format options (`task list`, `label list`, `report`), use `writer.is_tty()` to branch between human display and the JSON envelope:

```python
if writer.is_tty():
    print(format_ops.format_tasks_table(filtered))
else:
    writer.write_success(f"Found {len(filtered)} task(s).", {"tasks": filtered, "count": len(filtered)})
```

### TTY — task list

```
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "ok",
  "message": "Found 7 task(s).",
  "result": {
    "tasks": [
      {
        "id": 1,
        "title": "Setup workspace layout",
        "desc": "Bootstrap directory structures for Go, Rust, Python and TS",
        "status": "done",
        "priority": "high",
        "labels": [
          "setup",
          "dev"
        ],
        "created_at": "2026-05-28T18:00:00Z"
      },
      {
        "id": 2,
        "title": "Document CLI spec",
        "desc": "Draft the spec.md contracts and database JSON schemas",
        "status": "done",
        "priority": "medium",
        "labels": [
          "docs"
        ],
        "created_at": "2026-05-28T18:30:00Z"
      },
      {
        "id": 3,
        "title": "Implement Cobra skeleton",
        "desc": "Build the Go Cobra reference implementation",
        "status": "doing",
        "priority": "high",
        "labels": [
          "dev",
          "go"
        ],
        "created_at": "2026-05-29T04:00:00Z"
      },
      {
        "id": 4,
        "title": "Integrate Murli middleware",
        "desc": "Apply Murli wrappers to standard Go binaries",
        "status": "todo",
        "priority": "high",
        "labels": [
          "dev",
          "murli"
        ],
        "created_at": "2026-05-29T05:00:00Z"
      },
      {
        "id": 5,
        "title": "Write Rust Clap reference",
        "desc": "Develop Rust-native Clap derive parser",
        "status": "todo",
        "priority": "medium",
        "labels": [
          "dev",
          "rust"
        ],
        "created_at": "2026-05-29T06:00:00Z"
      },
      {
        "id": 6,
        "title": "Sprint item",
        "desc": "",
        "status": "todo",
        "priority": "high",
        "labels": [],
        "created_at": "2026-06-03T07:49:07Z"
      },
      {
        "id": 7,
        "title": "Agent sprint item",
        "desc": "",
        "status": "todo",
        "priority": "high",
        "labels": [],
        "created_at": "2026-06-03T07:49:07Z"
      }
    ],
    "count": 7
  }
}
```

### Agent — task create

```json
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "ok",
  "message": "Task 7 (\"Agent sprint item\") created successfully.",
  "result": {
    "id": 7,
    "title": "Agent sprint item"
  }
}
```

### Agent — task list

```json
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "ok",
  "message": "Found 7 task(s).",
  "result": {
    "tasks": [
      {
        "id": 1,
        "title": "Setup workspace layout",
        "desc": "Bootstrap directory structures for Go, Rust, Python and TS",
        "status": "done",
        "priority": "high",
        "labels": [
          "setup",
          "dev"
        ],
        "created_at": "2026-05-28T18:00:00Z"
      },
      {
        "id": 2,
        "title": "Document CLI spec",
        "desc": "Draft the spec.md contracts and database JSON schemas",
        "status": "done",
        "priority": "medium",
        "labels": [
          "docs"
        ],
        "created_at": "2026-05-28T18:30:00Z"
      },
      {
        "id": 3,
        "title": "Implement Cobra skeleton",
        "desc": "Build the Go Cobra reference implementation",
        "status": "doing",
        "priority": "high",
        "labels": [
          "dev",
          "go"
        ],
        "created_at": "2026-05-29T04:00:00Z"
      },
      {
        "id": 4,
        "title": "Integrate Murli middleware",
        "desc": "Apply Murli wrappers to standard Go binaries",
        "status": "todo",
        "priority": "high",
        "labels": [
          "dev",
          "murli"
        ],
        "created_at": "2026-05-29T05:00:00Z"
      },
      {
        "id": 5,
        "title": "Write Rust Clap reference",
        "desc": "Develop Rust-native Clap derive parser",
        "status": "todo",
        "priority": "medium",
        "labels": [
          "dev",
          "rust"
        ],
        "created_at": "2026-05-29T06:00:00Z"
      },
      {
        "id": 6,
        "title": "Sprint item",
        "desc": "",
        "status": "todo",
        "priority": "high",
        "labels": [],
        "created_at": "2026-06-03T07:49:07Z"
      },
      {
        "id": 7,
        "title": "Agent sprint item",
        "desc": "",
        "status": "todo",
        "priority": "high",
        "labels": [],
        "created_at": "2026-06-03T07:49:07Z"
      }
    ],
    "count": 7
  }
}
```

---

## Step 3: Schema Annotations

`murli.annotate(cmd, Metadata(...))` attaches machine-readable metadata. Call it on the click command object (the variable after `@task.command()` decoration), placed between the last handler and `murli.enable(cli)`:

```python
murli.annotate(task_create, Metadata(
    agent_description="Creates a new task and assigns it a unique integer ID.",
    when_to_use="Adding a new item to the sprint backlog.",
    mutating=True,
    idempotent=False,
    returns=ReturnSchema(description="New task ID and title", type="object",
                         properties={"id": "int", "title": "string"}),
    examples=[Example(command='murli-work task create "Fix login bug" --priority high')],
))
```

### `describe` output (first 40 lines)

```json
{
  "name": "cli",
  "summary": "murli-work - A sprint and project task tracker",
  "schema_version": "1.0",
  "tool_version": "",
  "capabilities": [
    "agent",
    "schema",
    "dry-run",
    "force",
    "profiles"
  ],
  "profiles": [],
  "commands": [
    {
      "name": "init",
      "summary": "Initialize/Reset the database and config",
      "agent_description": "Resets the database to seed data and writes default config.",
      "when_to_use": "First-time setup or to restore the database to a clean state.",
      "idempotent": true,
      "mutating": true,
      "arguments": [],
      "flags": [],
      "returns": {
        "description": "Storage directory path",
        "type": "object",
        "properties": {
          "path": "string"
        }
      },
      "examples": [],
      "subcommands": [],
      "safety": {
        "read_only": false,
        "idempotent": true,
        "destructive": false,
        "dry_run_supported": false
      }
    },
    {
```

### `task create --schema` output

`--schema` is a root-level flag that prints the full command tree. The `task create` entry from `murli-work-py-click --schema`:

```json
{
  "name": "create",
  "summary": "Create a new task",
  "agent_description": "Creates a new task and assigns it a unique integer ID.",
  "when_to_use": "Adding a new item to the sprint backlog.",
  "idempotent": false,
  "mutating": true,
  "arguments": [
    {
      "name": "title",
      "description": "",
      "required": true,
      "type": "string"
    }
  ],
  "flags": [
    {
      "name": "desc",
      "description": "Task description",
      "type": "string",
      "required": false,
      "default": "Sentinel.UNSET",
      "short": "",
      "env": "",
      "sensitive": false,
      "persistent": false,
      "mutually_exclusive_with": [],
      "enum": [],
      "pattern": "",
      "profileable": false
    },
    {
      "name": "priority",
      "description": "Task priority",
      "type": "string",
      "required": false,
      "default": "Sentinel.UNSET",
      "short": "",
      "env": "",
      "sensitive": false,
      "persistent": false,
      "mutually_exclusive_with": [],
      "enum": [],
      "pattern": "",
      "profileable": false
    },
    {
      "name": "labels",
      "description": "Comma-separated labels",
      "type": "string",
      "required": false,
      "default": "Sentinel.UNSET",
      "short": "",
      "env": "",
      "sensitive": false,
      "persistent": false,
      "mutually_exclusive_with": [],
      "enum": [],
      "pattern": "",
      "profileable": false
    }
  ],
  "returns": {
    "description": "New task ID and title",
    "type": "object",
    "properties": {
      "id": "int",
      "title": "string"
    }
  },
  "examples": [
    {
      "command": "murli-work task create \"Fix login bug\" --priority high --labels dev,backend",
      "description": "",
      "expected_exit_code": 0
    }
  ],
  "subcommands": [],
  "safety": {
    "read_only": false,
    "idempotent": false,
    "destructive": false,
    "dry_run_supported": false
  }
}
```

---

## Step 4: Structured Errors

Replace bare `sys.exit(N)` with `writer.write_error(AgentError.*(msg, suggestion))`. The writer emits `Error: / Hint:` in TTY mode and a JSON envelope in agent mode, then calls `sys.exit(code)`.

Error type mapping:
- `KeyError` → `AgentError.not_found()` exit 5
- `FileExistsError` → `AgentError.conflict_error()` exit 7
- `ValueError` → `AgentError.user_error()` exit 1
- `Exception` → `AgentError.tool_error()` exit 2

### TTY error output

```
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

### Agent error output

```json
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
```

---

## Step 5: Telemetry

`writer.log(msg)` writes to stderr. In TTY mode it prints plainly. In agent/piped mode it also prints plainly to stderr (the `Logger` class in `murli._core.logger` provides structured JSON dedup logging if used directly). Consecutive duplicate messages are collapsed with a `"repeated": N` count when using `Logger`.

```python
@cli.command()
@murli.pass_writer
def init(writer):
    writer.log("Resetting database and seeding sample data...")
    db_ops.reset_db()
    ...
```

### Agent init — stderr log + stdout envelope

Running `./bin/murli-work-py-click --agent init 2>&1` (stderr and stdout merged):

```
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

The log line arrives on stderr before the JSON success envelope on stdout. In agent mode the log text is plain (not JSON-wrapped), keeping the success envelope on stdout cleanly machine-parseable.
