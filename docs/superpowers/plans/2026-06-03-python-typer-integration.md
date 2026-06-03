# Python / typer — Murli Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply murli middleware to the typer skeleton (`python/typer/main.py`) following the five-step WALKTHROUGH-INSTRUCTIONS methodology, producing a fully annotated, dual-audience CLI with structured errors, and a companion guide document.

**Architecture:** Five progressive commits on branch `python/typer` (from main). The typer adapter patches `typer.main.get_command` lazily, so `murli.enable(app)` must be called before `app()`. Writers are obtained in each handler via `murli.get_writer(ctx)` where `ctx: typer.Context` is added as the first parameter. `shared/format.py` requires the same string-returning additions as the click plan — these must be applied again since branches are independent.

**Tech Stack:** Python 3.10+, typer 0.9+, click 8 (typer dependency), murli[typer] (local path), uv

**Prerequisite:** The murli-py adapter fixes plan must be complete and pushed.

---

## File Map

| File | Change |
|---|---|
| `python/requirements.txt` | Add `murli[all]` editable local install (if not already present from click branch) |
| `Makefile` | Split `build-py` so `uv pip install` always runs (same as click plan) |
| `python/shared/format.py` | Add string-returning `format_*` variants and `sprint_report_data()` |
| `python/typer/main.py` | Full murli integration across five steps |
| `PYTHON-TYPER-GUIDE.md` | Step-by-step integration guide with terminal captures |

---

## Task 0: Create branch

- [ ] **Step 1: Branch from main**

```bash
cd /Users/allank/Dev/murli/murli-demo
git checkout main
git checkout -b python/typer
```

---

## Task 1: Dependency + `murli.enable()` — what you get for free

**Files:**
- Modify: `python/requirements.txt`
- Modify: `Makefile`
- Modify: `python/typer/main.py`

- [ ] **Step 1: Add murli to requirements.txt**

Replace the contents of `python/requirements.txt`:

```
click>=8.0.0
typer>=0.9.0
tabulate>=0.9.0
rich>=13.0.0
-e ../../murli-py[all]
```

- [ ] **Step 2: Fix Makefile so deps always reinstall**

In `Makefile`, find this block in `build-py`:

```makefile
	[ -d .venv ] || (uv venv && uv pip install -r python/requirements.txt)
```

Replace it with:

```makefile
	[ -d .venv ] || uv venv
	uv pip install -r python/requirements.txt
```

- [ ] **Step 3: Add `murli.enable(app)` to `python/typer/main.py`**

Add `import murli` to the top imports:

```python
from typing import Optional
from enum import Enum
import typer
import sys
import os
import murli

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import shared.db as db_ops
import shared.format as format_ops
```

Add `murli.enable(app)` immediately after the `app`, `task_app`, and `label_app` definitions and before the Enum class and command definitions. The typer adapter patches `typer.main.get_command` lazily, so the enable call can appear here — commands registered after this call are still picked up at invocation time.

```python
app = typer.Typer(help="murli-work - A sprint and project task tracker")

task_app = typer.Typer(help="Manage sprint tasks")
app.add_typer(task_app, name="task")

label_app = typer.Typer(help="Manage global task labels")
app.add_typer(label_app, name="label")

murli.enable(app)   # ← add this line here
```

- [ ] **Step 4: Build and smoke-test**

```bash
cd /Users/allank/Dev/murli/murli-demo
make build-py
./bin/murli-work-py-typer --help
```

Expected — murli flags appear in the root help:
```
Usage: main [OPTIONS] COMMAND [ARGS]...

  murli-work - A sprint and project task tracker

Options:
  --agent         Force JSON output for agent/script use
  --schema        Print command schema as JSON and exit
  --force, --yes  Skip confirmation prompts
  --dry-run       Simulate without making changes
  --profile NAME  Load a named flag profile
  --install-completion  ...
  --help          Show this message and exit.

Commands:
  describe
  doctor
  init
  label
  profile
  report
  task
```

```bash
./bin/murli-work-py-typer describe
./bin/murli-work-py-typer init
./bin/murli-work-py-typer task create "Test step 1"
./bin/murli-work-py-typer task list
```

Expected: existing human-readable output unchanged.

- [ ] **Step 5: Commit**

```bash
git add python/requirements.txt Makefile python/typer/main.py
git commit -m "$(cat <<'EOF'
feat(python/typer): step 1 — add murli dependency and enable adapter

Adds murli[all] from local path install. Updates Makefile build-py so
uv pip install always runs. Calls murli.enable(app) after the Typer
app and sub-app definitions; the adapter patches typer.main.get_command
lazily so command registration order doesn't matter.

Injects --agent, --schema, --force, --dry-run, --profile at root level
and mounts describe, doctor, profile subcommands automatically.

Terminal output (./bin/murli-work-py-typer --help):
[paste captured output here]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Writer API — route all output through `writer.write_success()`

**Files:**
- Modify: `python/shared/format.py`
- Modify: `python/typer/main.py`

- [ ] **Step 1: Add string-returning format helpers to `shared/format.py`**

Append to `python/shared/format.py`:

```python
import io


def format_tasks_table(tasks: list) -> str:
    border = "+----+----------------------+--------+----------+------------+"
    header = "| ID | Title                | Status | Priority | Labels     |"
    lines = [border, header, border]
    for t in tasks:
        labels_str = ",".join(t["labels"])
        lines.append(
            f"| {t['id']:<2d} | {t['title'][:20]:<20s} | {t['status'].upper()[:6]:<6s}"
            f" | {t['priority'].upper()[:8]:<8s} | {labels_str[:10]:<10s} |"
        )
    lines.append(border)
    return "\n".join(lines)


def format_tasks_csv(tasks: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    w.writerow(["id", "title", "status", "priority", "labels"])
    for t in tasks:
        w.writerow([t["id"], t["title"], t["status"], t["priority"], ";".join(t["labels"])])
    return buf.getvalue().rstrip()


def format_tasks_json_str(tasks: list) -> str:
    return json.dumps(tasks, separators=(",", ":"))


def format_labels_table(db: dict) -> str:
    counts = {l["name"]: 0 for l in db["labels"]}
    for t in db["tasks"]:
        for lbl in t["labels"]:
            if lbl in counts:
                counts[lbl] += 1
    border = "+-------------+-------------+"
    header = "| Label Name  | Task Count  |"
    lines = [border, header, border]
    for l in db["labels"]:
        lines.append(f"| {l['name'][:11]:<11s} | {counts[l['name']]:<11d} |")
    lines.append(border)
    return "\n".join(lines)


def sprint_report_data(db: dict) -> dict:
    total = len(db["tasks"])
    completed = todo = doing = done = high = medium = low = 0
    for t in db["tasks"]:
        s = t["status"].lower()
        if s == "todo":
            todo += 1
        elif s == "doing":
            doing += 1
        elif s == "done":
            done += 1
            completed += 1
        p = t["priority"].lower()
        if p == "low":
            low += 1
        elif p == "medium":
            medium += 1
        elif p == "high":
            high += 1
    percent = (completed * 100) // total if total > 0 else 0
    return {
        "total": total,
        "completed": completed,
        "percent": percent,
        "status": {"todo": todo, "doing": doing, "done": done},
        "priority": {"high": high, "medium": medium, "low": low},
    }


def format_sprint_report(db: dict) -> str:
    data = sprint_report_data(db)
    percent = data["percent"]
    blocks = "■" * (percent // 10) + "□" * (10 - percent // 10)
    s = data["status"]
    p = data["priority"]
    lines = [
        "========================================",
        "          MURLI-WORK SPRINT REPORT      ",
        "========================================",
        f"Completion Rate : [{blocks}] {percent}% ({data['completed']}/{data['total']} tasks)",
        "",
        "Status Breakdown:",
        f"- TODO  : {s['todo']} tasks",
        f"- DOING : {s['doing']} tasks",
        f"- DONE  : {s['done']} tasks",
        "",
        "Priority Breakdown:",
        f"- HIGH  : {p['high']} tasks",
        f"- MEDIUM: {p['medium']} tasks",
        f"- LOW   : {p['low']} tasks",
        "========================================",
    ]
    return "\n".join(lines)
```

- [ ] **Step 2: Rewrite `python/typer/main.py` with Writer API**

Replace the entire contents of `python/typer/main.py`:

```python
from typing import Optional
from enum import Enum
import typer
import sys
import os
import murli
from murli import AgentError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import shared.db as db_ops
import shared.format as format_ops

app = typer.Typer(help="murli-work - A sprint and project task tracker")

task_app = typer.Typer(help="Manage sprint tasks")
app.add_typer(task_app, name="task")

label_app = typer.Typer(help="Manage global task labels")
app.add_typer(label_app, name="label")

murli.enable(app)


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Status(str, Enum):
    todo = "todo"
    doing = "doing"
    done = "done"


class OutputFmt(str, Enum):
    table = "table"
    json = "json"
    csv = "csv"


@app.command()
def init(ctx: typer.Context):
    """Initialize/Reset the database and config"""
    writer = murli.get_writer(ctx)
    try:
        db_ops.reset_db()
        dir_path = db_ops.get_storage_dir()
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    writer.write_success(
        f"Initialized/Reset murli-work database with sample data and configuration in {dir_path}",
        {"path": str(dir_path)},
    )


@task_app.command(name="create")
def task_create(
    ctx: typer.Context,
    title: str = typer.Argument(..., help="Task title"),
    desc: Optional[str] = typer.Option(None, "--desc", "-d", help="Task description"),
    priority: Optional[Priority] = typer.Option(None, "--priority", "-p", help="Task priority"),
    labels: Optional[str] = typer.Option(None, "--labels", "-l", help="Comma-separated labels"),
):
    """Create a new task"""
    writer = murli.get_writer(ctx)
    labels_list = labels.split(",") if labels else []
    prio_val = priority.value if priority else None
    try:
        db = db_ops.load_db()
        new_id = db_ops.create_task(db, title, desc, prio_val, labels_list)
    except ValueError as e:
        writer.write_error(AgentError.user_error(str(e), "Use --priority low|medium|high."))
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    writer.write_success(
        f'Task {new_id} ("{title}") created successfully.',
        {"id": new_id, "title": title},
    )


@task_app.command(name="list")
def task_list(
    ctx: typer.Context,
    status: Optional[Status] = typer.Option(None, "--status", "-s", help="Filter by status"),
    priority: Optional[Priority] = typer.Option(None, "--priority", "-p", help="Filter by priority"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="Filter by label"),
    output: OutputFmt = typer.Option(OutputFmt.table, "--output", "-o", help="Output format (TTY)"),
):
    """List stored tasks"""
    writer = murli.get_writer(ctx)
    try:
        db = db_ops.load_db()
        cfg = db_ops.load_config()
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))

    output_fmt = output.value
    if output_fmt == "table" and cfg and cfg.get("default_output"):
        output_fmt = cfg["default_output"]

    filtered = db["tasks"]
    if status:
        filtered = [t for t in filtered if t["status"].lower() == status.value.lower()]
    if priority:
        filtered = [t for t in filtered if t["priority"].lower() == priority.value.lower()]
    if label:
        filtered = [t for t in filtered if any(l.lower() == label.lower() for l in t["labels"])]

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


@task_app.command(name="update")
def task_update(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Task ID"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="New title"),
    desc: Optional[str] = typer.Option(None, "--desc", "-d", help="New description"),
    priority: Optional[Priority] = typer.Option(None, "--priority", "-p", help="New priority"),
    status: Optional[Status] = typer.Option(None, "--status", "-s", help="New status"),
    labels: Optional[str] = typer.Option(None, "--labels", "-l", help="Replacement labels"),
):
    """Update an existing task's fields"""
    writer = murli.get_writer(ctx)
    prio_val = priority.value if priority else None
    status_val = status.value if status else None
    labels_list = labels.split(",") if labels is not None else None
    try:
        db = db_ops.load_db()
        db_ops.update_task(db, id, title, desc, prio_val, status_val, labels_list)
    except KeyError as e:
        writer.write_error(AgentError.not_found(str(e), "Use task list to see valid IDs."))
    except ValueError as e:
        writer.write_error(AgentError.user_error(str(e), "Use --priority low|medium|high, --status todo|doing|done."))
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    writer.write_success(f"Task {id} updated successfully.", {"id": id})


@task_app.command(name="delete")
def task_delete(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Task ID"),
    force: bool = typer.Option(False, "--force", help="Force delete without warning"),
):
    """Delete a task"""
    writer = murli.get_writer(ctx)
    try:
        db = db_ops.load_db()
        db_ops.delete_task(db, id)
    except KeyError as e:
        writer.write_error(AgentError.not_found(str(e), "Use task list to see valid IDs."))
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    writer.write_success(f"Task {id} deleted successfully.", {"id": id})


@label_app.command(name="list")
def label_list(ctx: typer.Context):
    """List all defined labels"""
    writer = murli.get_writer(ctx)
    try:
        db = db_ops.load_db()
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    if writer.is_tty():
        print(format_ops.format_labels_table(db))
    else:
        writer.write_success(
            f"Found {len(db['labels'])} label(s).",
            {"labels": db["labels"]},
        )


@label_app.command(name="create")
def label_create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Label name"),
):
    """Create a custom label"""
    writer = murli.get_writer(ctx)
    try:
        db = db_ops.load_db()
        slug = db_ops.create_label(db, name)
    except FileExistsError as e:
        writer.write_error(AgentError.conflict_error(str(e), "Use label list to see existing labels."))
    except ValueError as e:
        writer.write_error(AgentError.user_error(str(e)))
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    writer.write_success(f'Label "{slug}" created successfully.', {"slug": slug})


@label_app.command(name="delete")
def label_delete(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Label name"),
):
    """Delete a label"""
    writer = murli.get_writer(ctx)
    try:
        db = db_ops.load_db()
        db_ops.delete_label(db, name)
    except KeyError as e:
        writer.write_error(AgentError.not_found(str(e), "Use label list to see valid labels."))
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    writer.write_success(f'Label "{name}" deleted successfully.', {"name": name})


@app.command()
def report(ctx: typer.Context):
    """Display progress report"""
    writer = murli.get_writer(ctx)
    try:
        db = db_ops.load_db()
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    report_data = format_ops.sprint_report_data(db)
    if writer.is_tty():
        print(format_ops.format_sprint_report(db))
    else:
        writer.write_success("Sprint report generated.", report_data)


if __name__ == "__main__":
    app()
```

- [ ] **Step 3: Rebuild and verify TTY output**

```bash
make build-py
./bin/murli-work-py-typer init
./bin/murli-work-py-typer task create "Writer API test" --priority high
./bin/murli-work-py-typer task list
./bin/murli-work-py-typer report
```

Expected: human-readable output identical to the skeleton.

- [ ] **Step 4: Verify agent mode**

```bash
./bin/murli-work-py-typer --agent task create "Agent test"
./bin/murli-work-py-typer --agent task list
./bin/murli-work-py-typer --agent report
```

Expected JSON envelopes:
```json
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "ok",
  "message": "Task 7 (\"Agent test\") created successfully.",
  "result": {"id": 7, "title": "Agent test"}
}
```

- [ ] **Step 5: Commit**

```bash
git add python/shared/format.py python/typer/main.py
git commit -m "$(cat <<'EOF'
feat(python/typer): step 2 — Writer API replaces direct stdout

All handlers receive ctx: typer.Context as the first parameter and
obtain the writer via murli.get_writer(ctx). writer.write_success()
replaces typer.echo() throughout. Commands with multi-format output
(task list, label list, report) use writer.is_tty() to select display
path: TTY uses format_ops string helpers, agent mode uses JSON envelope.

shared/format.py gains string-returning format_* helpers and
sprint_report_data() (same additions as the click branch).

Terminal output (--agent task list):
[paste captured JSON here]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Schema + Annotations

**Files:**
- Modify: `python/typer/main.py`

**Note:** Typer builds click commands lazily. `murli.annotate()` for the root `app` stores metadata on the Typer instance, which is transferred to the click command during injection. Per-command annotation is not supported through the public API in the current murli-py version — annotate the root app to describe the tool as a whole.

- [ ] **Step 1: Add annotation for the root app**

Add the following after `murli.enable(app)` and before the Enum class definitions:

```python
from murli import Metadata, ReturnSchema, Example

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

- [ ] **Step 2: Test `describe` and `--schema`**

```bash
./bin/murli-work-py-typer describe
./bin/murli-work-py-typer --schema
```

Expected: `describe` outputs a JSON tree; `agent_description` on the root is populated. Individual command descriptions come from the docstrings.

- [ ] **Step 3: Commit**

```bash
git add python/typer/main.py
git commit -m "$(cat <<'EOF'
feat(python/typer): step 3 — root app annotation

Annotates the root Typer app with agent_description and when_to_use
via murli.annotate(app, Metadata(...)). Per-command annotation is not
currently supported through the murli-py public API for typer sub-apps;
individual command metadata is derived from docstrings.

Terminal output (./bin/murli-work-py-typer describe):
[paste captured JSON here]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Verify Actionable Error Handling

The Writer API changes in Task 2 include `write_error(AgentError...)` in all handlers. This task verifies the error envelopes and confirms correct exit codes.

**Files:** No code changes — verification only.

- [ ] **Step 1: Verify not-found error (exit 5)**

```bash
./bin/murli-work-py-typer --agent task update 999 --status done
echo "exit: $?"
```

Expected:
```json
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "error",
  "code": 5,
  "error": "not_found",
  "message": "task with ID 999 not found",
  "suggestion": "Use task list to see valid IDs.",
  "recoverable": false
}
exit: 5
```

- [ ] **Step 2: Verify conflict error on duplicate label**

```bash
./bin/murli-work-py-typer init
./bin/murli-work-py-typer --agent label create dev
echo "exit: $?"
```

Expected:
```json
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

- [ ] **Step 3: Commit**

```bash
git add python/typer/main.py
git commit -m "$(cat <<'EOF'
feat(python/typer): step 4 — structured error verification

Confirms all error paths emit AgentError JSON envelopes in agent mode
and plain Error:/Hint: pairs in TTY mode with correct exit codes.

Error type mapping:
  KeyError              -> AgentError.not_found()      exit 5
  FileExistsError       -> AgentError.conflict_error()  exit 7
  ValueError            -> AgentError.user_error()      exit 1
  Exception             -> AgentError.tool_error()      exit 2

Terminal output (--agent task update 999 --status done):
[paste captured JSON here]

Terminal output (--agent label create dev, already exists):
[paste captured JSON here]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Telemetry + Guide

**Files:**
- Modify: `python/typer/main.py`
- Create: `PYTHON-TYPER-GUIDE.md`

- [ ] **Step 1: Add `writer.log()` to `init` and `report`**

In `init`, add the log line before `db_ops.reset_db()`:

```python
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
    writer.write_success(
        f"Initialized/Reset murli-work database with sample data and configuration in {dir_path}",
        {"path": str(dir_path)},
    )
```

In `report`, add the log line before loading the db:

```python
@app.command()
def report(ctx: typer.Context):
    """Display progress report"""
    writer = murli.get_writer(ctx)
    writer.log("Computing sprint statistics...")
    try:
        db = db_ops.load_db()
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    report_data = format_ops.sprint_report_data(db)
    if writer.is_tty():
        print(format_ops.format_sprint_report(db))
    else:
        writer.write_success("Sprint report generated.", report_data)
```

- [ ] **Step 2: Verify log output in agent mode**

```bash
./bin/murli-work-py-typer --agent init 2>&1
```

Expected: stderr contains JSON log entry; stdout contains success envelope:
```
{"ts": "2026-06-03T...", "level": "info", "msg": "Resetting database and seeding sample data..."}
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "ok",
  "message": "Initialized/Reset murli-work database ...",
  "result": {"path": "..."}
}
```

- [ ] **Step 3: Write `PYTHON-TYPER-GUIDE.md`**

Create `/Users/allank/Dev/murli/murli-demo/PYTHON-TYPER-GUIDE.md`:

```markdown
# Python / typer — Murli Integration Guide

This guide walks through integrating murli middleware into a typer CLI, step by step.

The target application is `murli-work`, a sprint task tracker.

---

## Typer vs. click: key difference

Typer builds click commands lazily via `typer.main.get_command()`. The murli typer adapter patches that function at enable() time, so the murli options and subcommands are injected into the click command when it is first built — not when `enable()` is called. This means `murli.enable(app)` can be placed anywhere before `app()`.

Writers are obtained per-handler via `murli.get_writer(ctx)` where `ctx: typer.Context` is added as the first parameter. The writer is stored on the root context object and retrieved via `ctx.find_root().obj`.

---

## What You Get for Free (Step 1)

```python
murli.enable(app)  # ← one line, placed after app/task_app/label_app definitions
```

Injects: `--agent`, `--schema`, `--force`, `--dry-run`, `--profile`
Mounts: `describe`, `doctor`, `profile` subcommands

### Terminal output — `--help`

```
[paste ./bin/murli-work-py-typer --help output here]
```

### Terminal output — `describe`

```json
[paste ./bin/murli-work-py-typer describe output here]
```

---

## What You Configure (Step 3)

Typer sub-app commands are built lazily, so per-command annotation via `murli.annotate()` is not available through the public API. Annotate the root app to provide agent-level metadata for the tool as a whole.

```python
murli.annotate(app, Metadata(
    agent_description="murli-work sprint task tracker ...",
    when_to_use="Managing sprint tasks ...",
))
```

### Terminal output — `describe` with annotation

```json
[paste ./bin/murli-work-py-typer describe output here]
```

---

## What You Build (Steps 2 + 4)

### Writer API

Add `ctx: typer.Context` as the first parameter to every command, then call `murli.get_writer(ctx)`:

```python
@app.command()
def init(ctx: typer.Context):
    writer = murli.get_writer(ctx)
    db_ops.reset_db()
    dir_path = db_ops.get_storage_dir()
    writer.write_success(
        f"Initialized database in {dir_path}",
        {"path": str(dir_path)},
    )
```

### Dual-audience output

```
# TTY
$ ./bin/murli-work-py-typer task create "Sprint item" --priority high
Task 6 ("Sprint item") created successfully.

# Agent
$ ./bin/murli-work-py-typer --agent task create "Sprint item" --priority high
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "ok",
  "message": "Task 6 (\"Sprint item\") created successfully.",
  "result": {"id": 6, "title": "Sprint item"}
}
```

### Terminal output — TTY task list

```
[paste ./bin/murli-work-py-typer task list output here]
```

### Terminal output — agent task list

```json
[paste ./bin/murli-work-py-typer --agent task list output here]
```

### Structured errors (Step 4)

```
# TTY
$ ./bin/murli-work-py-typer task update 999 --status done
Error: task with ID 999 not found
Hint:  Use task list to see valid IDs.

# Agent
$ ./bin/murli-work-py-typer --agent task update 999 --status done
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "error",
  "code": 5,
  "error": "not_found",
  "message": "task with ID 999 not found",
  "suggestion": "Use task list to see valid IDs.",
  "recoverable": false
}
```

### Terminal output — error in agent mode

```json
[paste --agent task update 999 output here]
```

---

## Step 5 — Telemetry

`writer.log()` emits to stderr. In agent mode it emits structured JSON with deduplication.

### Terminal output — init in agent mode (stderr log + stdout envelope)

```
[paste ./bin/murli-work-py-typer --agent init 2>&1 output here]
```
```

- [ ] **Step 4: Capture all output for guide and fill in placeholders**

Run each command, capture output, replace `[paste ...]` sections in `PYTHON-TYPER-GUIDE.md`:

```bash
make build-py
./bin/murli-work-py-typer --help
./bin/murli-work-py-typer describe
./bin/murli-work-py-typer init
./bin/murli-work-py-typer task create "Sprint item" --priority high
./bin/murli-work-py-typer task list
./bin/murli-work-py-typer --agent task create "Agent sprint item" --priority high
./bin/murli-work-py-typer --agent task list
./bin/murli-work-py-typer task update 999 --status done
./bin/murli-work-py-typer --agent task update 999 --status done
./bin/murli-work-py-typer --agent init 2>&1
```

- [ ] **Step 5: Commit and push**

```bash
git add python/typer/main.py PYTHON-TYPER-GUIDE.md
git commit -m "$(cat <<'EOF'
feat(python/typer): step 5 — telemetry and integration guide

Adds writer.log() to init and report for structured stderr logging
with dedup in agent mode.

Adds PYTHON-TYPER-GUIDE.md documenting the typer-specific integration
pattern (ctx: typer.Context + get_writer, lazy patching, root-level
annotation) with captured terminal output.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
git push -u origin python/typer
```
