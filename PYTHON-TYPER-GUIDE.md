# Python / typer — Murli Integration Guide

This guide walks through integrating the [murli](https://github.com/murli-io/murli-py) middleware
library into a [Typer](https://typer.tiangolo.com/) CLI, using the `murli-work` sprint tracker
as a concrete example. Typer has one key structural difference from click that affects how the
Writer is obtained — everything else follows the same pattern.

---

## Typer vs. click: key difference

**Click** uses a decorator (`@murli.pass_writer`) to inject the writer as a function argument.

**Typer** patches `typer.main.get_command` lazily at invocation time, so it cannot inject
function-level decorators. Instead, the writer is stored in the Click context object and retrieved
via `murli.get_writer(ctx)`:

```python
# click pattern — NOT used in typer
@click.command()
@murli.pass_writer
def my_cmd(writer, ...):
    ...

# typer pattern — add ctx: typer.Context as the FIRST parameter
@app.command()
def my_cmd(ctx: typer.Context, ...):
    writer = murli.get_writer(ctx)
    ...
```

`murli.enable(app)` registers the `typer.Typer` instance and installs the patch. The injection
happens lazily when the click command is first built, so commands may be added to the app after
`enable()` is called.

---

## Step 1: What You Get for Free

After calling `murli.enable(app)`, every murli-enabled Typer app gets these flags automatically:

```python
murli.enable(app)
```

```
 Usage: murli-work-py-typer [OPTIONS] COMMAND [ARGS]...

 murli-work - A sprint and project task tracker

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion              Install completion for the current shell.  │
│ --show-completion                 Show completion for the current shell, to  │
│                                   copy it or customize the installation.     │
│ --agent                           Force JSON output for agent/script use     │
│ --schema                          Print command schema as JSON and exit      │
│ --force,--yes                     Skip confirmation prompts                  │
│ --dry-run                         Simulate without making changes            │
│ --profile                   NAME  Load a named flag profile                  │
│ --help                            Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ init      Initialize/Reset the database and config                           │
│ report    Display progress report                                            │
│ task      Manage sprint tasks                                                │
│ label     Manage global task labels                                          │
│ describe  Print the full command schema as JSON                              │
│ doctor    Check command and flag naming conventions                          │
│ profile   Manage named flag profiles                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

The `describe`, `doctor`, and `profile` subcommands are injected automatically.

---

## Step 2: Writer API

Replace `typer.echo()` with `writer.write_success()` and `writer.write_error()`. Use
`writer.is_tty()` to branch between human-readable and structured output.

### Pattern

```python
from murli import AgentError
import murli

@app.command()
def init(ctx: typer.Context):
    """Initialize/Reset the database and config"""
    writer = murli.get_writer(ctx)
    writer.log("Resetting database and seeding sample data...")
    try:
        db_ops.reset_db()
        dir_path = db_ops.get_storage_dir()
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
    writer.write_success(
        f"Initialized/Reset murli-work database with sample data and configuration in {dir_path}",
        {"path": str(dir_path)},
    )
```

### TTY mode (human terminal — table output)

When stdout is a terminal, `writer.is_tty()` returns `True` and the handler prints human-readable
output directly:

```
+----+----------------------+--------+----------+------------+
| ID | Title                | Status | Priority | Labels     |
+----+----------------------+--------+----------+------------+
| 1  | Setup workspace layo | DONE   | HIGH     | setup,dev  |
| 2  | Document CLI spec    | DONE   | MEDIUM   | docs       |
| 3  | Implement Cobra skel | DOING  | HIGH     | dev,go     |
| 4  | Integrate Murli midd | TODO   | HIGH     | dev,murli  |
| 5  | Write Rust Clap refe | TODO   | MEDIUM   | dev,rust   |
+----+----------------------+--------+----------+------------+
```

### Agent mode (piped / `--agent` flag)

When stdout is piped or `--agent` is passed, `writer.write_success()` emits a structured JSON
envelope:

```
$ murli-work-py-typer --agent task list
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
      }
    ],
    "count": 5
  }
}
```

### `task_list` dual-output implementation

```python
@task_app.command(name="list")
def task_list(
    ctx: typer.Context,
    status: Optional[Status] = typer.Option(None, "--status", "-s"),
    priority: Optional[Priority] = typer.Option(None, "--priority", "-p"),
    label: Optional[str] = typer.Option(None, "--label", "-l"),
    output: OutputFmt = typer.Option(OutputFmt.table, "--output", "-o"),
):
    """List stored tasks"""
    writer = murli.get_writer(ctx)
    ...
    if writer.is_tty():
        if output_fmt == "csv":
            print(format_ops.format_tasks_csv(filtered))
        elif output_fmt == "json":
            print(format_ops.format_tasks_json_str(filtered))
        else:
            print(format_ops.format_tasks_table(filtered))
    else:
        writer.write_success(
            f"Found {len(filtered)} task(s).",
            {"tasks": filtered, "count": len(filtered)},
        )
```

---

## Step 3: Annotations

For Typer apps, `murli.annotate()` stores the metadata on the `Typer` instance. It is transferred
to the generated click command at invocation time via the lazy patch. Root-app annotation only —
per-subcommand annotation is not exposed via the public murli-py API for Typer sub-apps.

```python
from murli import Metadata

murli.annotate(app, Metadata(
    agent_description=(
        "murli-work sprint task tracker. Manages tasks (create/list/update/delete) "
        "and labels. All mutating commands accept --force and --dry-run."
    ),
    when_to_use="Managing sprint tasks and labels from the command line or an AI agent.",
    mutating=False,
    idempotent=True,
))
```

### `describe` output

```
$ murli-work-py-typer describe
{
  "name": "unknown",
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
  "commands": [
    {
      "name": "init",
      "summary": "Initialize/Reset the database and config",
      "agent_description": "",
      "when_to_use": "",
      "idempotent": false,
      "mutating": false
    },
    {
      "name": "report",
      "summary": "Display progress report",
      "agent_description": "",
      "when_to_use": "",
      "idempotent": false,
      "mutating": false
    },
    {
      "name": "task",
      "summary": "Manage sprint tasks",
      "agent_description": "",
      "when_to_use": "",
      "idempotent": false,
      "mutating": false
    },
    {
      "name": "label",
      "summary": "Manage global task labels",
      "agent_description": "",
      "when_to_use": "",
      "idempotent": false,
      "mutating": false
    }
  ]
}
```

---

## Step 4: Structured Errors

All error paths use `AgentError` factory methods. Exit codes are semantic:

| Factory | Exit code | Meaning |
|---|---|---|
| `AgentError.user_error(msg, suggestion)` | 1 | Bad input from user |
| `AgentError.tool_error(msg)` | 2 | Internal/IO failure |
| `AgentError.not_found(msg, suggestion)` | 5 | Resource missing |
| `AgentError.conflict_error(msg, suggestion)` | 7 | Duplicate/conflict |

### Not-found error — agent mode

```
$ murli-work-py-typer --agent task update 999 --status done
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

### Error handler pattern

```python
@task_app.command(name="update")
def task_update(ctx: typer.Context, id: int = typer.Argument(...), ...):
    """Update an existing task's fields"""
    writer = murli.get_writer(ctx)
    try:
        db = db_ops.load_db()
        db_ops.update_task(db, id, ...)
    except KeyError as e:
        writer.write_error(AgentError.not_found(str(e), "Use task list to see valid IDs."))
        return
    except ValueError as e:
        writer.write_error(AgentError.user_error(str(e), "Use --priority low|medium|high, --status todo|doing|done."))
        return
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
    writer.write_success(f"Task {id} updated successfully.", {"id": id})
```

---

## Step 5: Telemetry

`writer.log(msg)` writes progress messages to **stderr**, keeping stdout clean for machine parsing.
This is particularly useful for long-running operations.

### Usage in `init` and `report`

```python
@app.command()
def init(ctx: typer.Context):
    writer = murli.get_writer(ctx)
    writer.log("Resetting database and seeding sample data...")  # → stderr
    ...
    writer.write_success(...)  # → stdout
```

### Captured output — `--agent init` (stderr + stdout interleaved)

```
$ murli-work-py-typer --agent init
Resetting database and seeding sample data...           ← stderr
{                                                       ← stdout
  "schema_version": "1.0",
  "tool_version": "",
  "status": "ok",
  "message": "Initialized/Reset murli-work database with sample data and configuration in /Users/allank/Library/Application Support/murli-work",
  "result": {
    "path": "/Users/allank/Library/Application Support/murli-work"
  }
}
```

When streams are separated (`2>/dev/null`), only the JSON envelope reaches stdout — safe for
piping into `jq` or any JSON parser.
