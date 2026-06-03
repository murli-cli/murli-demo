# Python / click — Murli Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply murli middleware to the click skeleton (`python/click/main.py`) following the five-step WALKTHROUGH-INSTRUCTIONS methodology, producing a fully annotated, dual-audience CLI with structured errors, and a companion guide document.

**Architecture:** Five progressive commits on branch `python/click`. Step 1 hooks the adapter; steps 2–4 incrementally replace raw output with the Writer API; step 5 adds telemetry and writes the guide. `shared/format.py` gains string-returning variants so handlers can pass formatted text to `writer.write_success()` for TTY output while agents receive the JSON envelope.

**Tech Stack:** Python 3.10+, click 8, murli[click] (local path install from `../murli-py`), uv, tabulate, rich

**Prerequisite:** The murli-py adapter fixes plan (`2026-06-03-adapter-fixes.md`) must be complete and pushed before starting this plan.

---

## File Map

| File | Change |
|---|---|
| `python/requirements.txt` | Add `murli[click]` editable local install |
| `Makefile` | Split `build-py` so `uv pip install` always runs |
| `python/shared/format.py` | Add string-returning `format_*` variants and `sprint_report_data()` |
| `python/click/main.py` | Full murli integration across five steps |
| `PYTHON-CLICK-GUIDE.md` | Step-by-step integration guide with terminal captures |

---

## Task 0: Create branch

- [ ] **Step 1: Branch from main**

```bash
cd /Users/allank/Dev/murli/murli-demo
git checkout main
git checkout -b python/click
```

---

## Task 1: Dependency + `murli.enable()` — what you get for free

**Files:**
- Modify: `python/requirements.txt`
- Modify: `Makefile`
- Modify: `python/click/main.py`

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

In `Makefile`, the `build-py` target currently only installs deps when `.venv` doesn't exist. Change the target so `uv pip install` always runs. Find this block:

```makefile
build-py:
	@echo "==> Setting up Python launchers in ./bin/ using uv..."
	mkdir -p bin
	[ -d .venv ] || (uv venv && uv pip install -r python/requirements.txt)
```

Replace it with:

```makefile
build-py:
	@echo "==> Setting up Python launchers in ./bin/ using uv..."
	mkdir -p bin
	[ -d .venv ] || uv venv
	uv pip install -r python/requirements.txt
```

(Leave the launcher script lines below unchanged.)

- [ ] **Step 3: Add `murli.enable(cli)` to `python/click/main.py`**

Add `import murli` after the existing imports and call `murli.enable(cli)` at the bottom of the file, after all command definitions and before `if __name__ == "__main__"`. The file currently ends with:

```python
if __name__ == "__main__":
    cli()
```

Change it to:

```python
import murli

# ... (all existing command definitions unchanged) ...

murli.enable(cli)

if __name__ == "__main__":
    cli()
```

The import goes at the top with the other imports. The `enable()` call must be placed AFTER all `@cli.command()` and `@task.command()` decorators so `_has_output_option()` can see the `task list --output` flag.

Full updated imports block (top of file):

```python
import click
import sys
import os
import murli

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import shared.db as db_ops
import shared.format as format_ops
```

- [ ] **Step 4: Build and smoke-test**

```bash
cd /Users/allank/Dev/murli/murli-demo
make build-py
./bin/murli-work-py-click --help
```

Expected — murli flags appear, `--output` is NOT present at root (because `task list` defines it):
```
Usage: cli [OPTIONS] COMMAND [ARGS]...

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

```bash
./bin/murli-work-py-click describe
```

Expected: valid JSON with `"name"`, `"commands"` array listing `init`, `task`, `label`, `report`.

```bash
./bin/murli-work-py-click init
./bin/murli-work-py-click task create "Test step 1"
./bin/murli-work-py-click task list
```

Expected: existing human-readable output unchanged (murli passes through in TTY mode).

- [ ] **Step 5: Commit**

```bash
git add python/requirements.txt Makefile python/click/main.py
git commit -m "$(cat <<'EOF'
feat(python/click): step 1 — add murli dependency and enable adapter

Adds murli[click] from local path install to python/requirements.txt.
Updates Makefile build-py target so uv pip install always runs (was
only running on first venv creation).

Calls murli.enable(cli) after all command definitions so the output-
collision detection sees the full command tree. This injects --agent,
--schema, --force, --dry-run, --profile at the root group level and
mounts describe, doctor, profile subcommands automatically.

Terminal output (make build-py && ./bin/murli-work-py-click --help):
[paste captured output here]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Writer API — route all output through `writer.write_success()`

**Files:**
- Modify: `python/shared/format.py`
- Modify: `python/click/main.py`

- [ ] **Step 1: Add string-returning format helpers to `shared/format.py`**

Append the following to the end of `python/shared/format.py`:

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

- [ ] **Step 2: Rewrite `python/click/main.py` with Writer API**

Replace the entire contents of `python/click/main.py`:

```python
import click
import sys
import os
import murli
from murli import AgentError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import shared.db as db_ops
import shared.format as format_ops


@click.group()
def cli():
    """murli-work - A sprint and project task tracker"""
    pass


@cli.command()
@murli.pass_writer
def init(writer):
    """Initialize/Reset the database and config"""
    db_ops.reset_db()
    dir_path = db_ops.get_storage_dir()
    writer.write_success(
        f"Initialized/Reset murli-work database with sample data and configuration in {dir_path}",
        {"path": str(dir_path)},
    )


@cli.group()
def task():
    """Manage sprint tasks"""
    pass


@task.command(name="create")
@click.argument("title")
@click.option("--desc", "-d", help="Task description")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Task priority")
@click.option("--labels", "-l", help="Comma-separated labels")
@murli.pass_writer
def task_create(writer, title, desc, priority, labels):
    """Create a new task"""
    labels_list = labels.split(",") if labels else []
    try:
        db = db_ops.load_db()
        new_id = db_ops.create_task(db, title, desc, priority, labels_list)
    except ValueError as e:
        writer.write_error(AgentError.user_error(str(e), "Use --priority low|medium|high."))
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    writer.write_success(
        f'Task {new_id} ("{title}") created successfully.',
        {"id": new_id, "title": title},
    )


@task.command(name="list")
@click.option("--status", "-s", type=click.Choice(["todo", "doing", "done"]), help="Filter by status")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Filter by priority")
@click.option("--label", "-l", help="Filter by label")
@click.option("--output", "-o", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format (TTY)")
@murli.pass_writer
def task_list(writer, status, priority, label, output):
    """List stored tasks"""
    try:
        db = db_ops.load_db()
        cfg = db_ops.load_config()
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))

    output_fmt = output
    if output_fmt == "table" and cfg and cfg.get("default_output"):
        output_fmt = cfg["default_output"]

    filtered = db["tasks"]
    if status:
        filtered = [t for t in filtered if t["status"].lower() == status.lower()]
    if priority:
        filtered = [t for t in filtered if t["priority"].lower() == priority.lower()]
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


@task.command(name="update")
@click.argument("id", type=int)
@click.option("--title", "-t", help="New title")
@click.option("--desc", "-d", help="New description")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="New priority")
@click.option("--status", "-s", type=click.Choice(["todo", "doing", "done"]), help="New status")
@click.option("--labels", "-l", help="Replacement labels")
@murli.pass_writer
def task_update(writer, id, title, desc, priority, status, labels):
    """Update an existing task's fields"""
    labels_list = labels.split(",") if labels is not None else None
    try:
        db = db_ops.load_db()
        db_ops.update_task(db, id, title, desc, priority, status, labels_list)
    except KeyError as e:
        writer.write_error(AgentError.not_found(str(e), "Use task list to see valid IDs."))
    except ValueError as e:
        writer.write_error(AgentError.user_error(str(e), "Use --priority low|medium|high, --status todo|doing|done."))
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    writer.write_success(f"Task {id} updated successfully.", {"id": id})


@task.command(name="delete")
@click.argument("id", type=int)
@click.option("--force", is_flag=True, help="Force delete without warning")
@murli.pass_writer
def task_delete(writer, id, force):
    """Delete a task"""
    try:
        db = db_ops.load_db()
        db_ops.delete_task(db, id)
    except KeyError as e:
        writer.write_error(AgentError.not_found(str(e), "Use task list to see valid IDs."))
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    writer.write_success(f"Task {id} deleted successfully.", {"id": id})


@cli.group()
def label():
    """Manage global task labels"""
    pass


@label.command(name="list")
@murli.pass_writer
def label_list(writer):
    """List all defined labels"""
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


@label.command(name="create")
@click.argument("name")
@murli.pass_writer
def label_create(writer, name):
    """Create a custom label"""
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


@label.command(name="delete")
@click.argument("name")
@murli.pass_writer
def label_delete(writer, name):
    """Delete a label"""
    try:
        db = db_ops.load_db()
        db_ops.delete_label(db, name)
    except KeyError as e:
        writer.write_error(AgentError.not_found(str(e), "Use label list to see valid labels."))
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    writer.write_success(f'Label "{name}" deleted successfully.', {"name": name})


@cli.command()
@murli.pass_writer
def report(writer):
    """Display progress report"""
    try:
        db = db_ops.load_db()
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
    report_data = format_ops.sprint_report_data(db)
    if writer.is_tty():
        print(format_ops.format_sprint_report(db))
    else:
        writer.write_success("Sprint report generated.", report_data)


murli.enable(cli)

if __name__ == "__main__":
    cli()
```

- [ ] **Step 3: Rebuild and test TTY output**

```bash
make build-py
./bin/murli-work-py-click init
./bin/murli-work-py-click task create "Writer API test" --priority high
./bin/murli-work-py-click task list
./bin/murli-work-py-click task list --output csv
./bin/murli-work-py-click report
```

Expected (TTY): same human-readable output as before — table, plain text success messages, sprint report block.

- [ ] **Step 4: Test agent mode output**

```bash
./bin/murli-work-py-click --agent task create "Agent test"
./bin/murli-work-py-click --agent task list
./bin/murli-work-py-click --agent report
```

Expected — JSON envelopes:
```json
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "ok",
  "message": "Task 7 (\"Agent test\") created successfully.",
  "result": {
    "id": 7,
    "title": "Agent test"
  }
}
```

```json
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "ok",
  "message": "Found 6 task(s).",
  "result": {
    "tasks": [...],
    "count": 6
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add python/shared/format.py python/click/main.py
git commit -m "$(cat <<'EOF'
feat(python/click): step 2 — Writer API replaces direct stdout

All handlers now use @murli.pass_writer and writer.write_success().
Commands that produce tabular or multi-format output (task list, label
list, report) use writer.is_tty() to select the display path:
  - TTY: existing format_ops string-returning helpers (new variants added)
  - Agent/piped: writer.write_success(human_text, json_payload)

shared/format.py gains format_tasks_table(), format_tasks_csv(),
format_tasks_json_str(), format_labels_table(), format_sprint_report(),
sprint_report_data() — string/dict variants of the existing print_* fns.

Terminal output (TTY task list):
[paste captured output here]

Terminal output (--agent task list):
[paste captured JSON here]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Schema + Annotations

**Files:**
- Modify: `python/click/main.py`

- [ ] **Step 1: Add annotations for all commands**

Add `from murli import AgentError, Metadata, ReturnSchema, Example` to imports (replace the existing `from murli import AgentError` line).

Insert the following annotation block between the last command definition (`report`) and the `murli.enable(cli)` call:

```python
from murli import Metadata, ReturnSchema, Example

murli.annotate(init, Metadata(
    agent_description="Resets the database to seed data and writes default config.",
    when_to_use="First-time setup or to restore the database to a clean state.",
    mutating=True,
    idempotent=True,
    returns=ReturnSchema(description="Storage directory path", type="object",
                         properties={"path": "string"}),
))

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

murli.annotate(task_list, Metadata(
    agent_description="Returns filtered tasks. Use --status, --priority, --label to narrow results.",
    when_to_use="Querying the backlog or checking sprint progress.",
    mutating=False,
    idempotent=True,
    returns=ReturnSchema(description="Filtered task list", type="object",
                         properties={"tasks": "array", "count": "int"}),
    examples=[
        Example(command="murli-work task list --status doing --priority high"),
    ],
))

murli.annotate(task_update, Metadata(
    agent_description="Updates one or more fields on an existing task. Omitted flags are unchanged.",
    when_to_use="Changing status, priority, or labels on a task.",
    mutating=True,
    idempotent=True,
    returns=ReturnSchema(description="Updated task ID", type="object",
                         properties={"id": "int"}),
    examples=[
        Example(command="murli-work task update 3 --status done"),
    ],
))

murli.annotate(task_delete, Metadata(
    agent_description="Permanently removes a task by ID.",
    when_to_use="Removing a cancelled or obsolete task from the backlog.",
    mutating=True,
    idempotent=False,
    destructive=True,
    returns=ReturnSchema(description="Deleted task ID", type="object",
                         properties={"id": "int"}),
))

murli.annotate(label_list, Metadata(
    agent_description="Lists all labels defined in the database with task counts.",
    when_to_use="Discovering available labels before creating or filtering tasks.",
    mutating=False,
    idempotent=True,
    returns=ReturnSchema(description="Label array", type="object",
                         properties={"labels": "array"}),
))

murli.annotate(label_create, Metadata(
    agent_description="Creates a new label slug. Fails with conflict if it already exists.",
    when_to_use="Adding a label category before tagging tasks with it.",
    mutating=True,
    idempotent=False,
    returns=ReturnSchema(description="Created label slug", type="object",
                         properties={"slug": "string"}),
))

murli.annotate(label_delete, Metadata(
    agent_description="Deletes a label and removes it from all tasks.",
    when_to_use="Cleaning up unused or misnamed labels.",
    mutating=True,
    idempotent=False,
    destructive=True,
    returns=ReturnSchema(description="Deleted label name", type="object",
                         properties={"name": "string"}),
))

murli.annotate(report, Metadata(
    agent_description="Computes and returns sprint completion statistics by status and priority.",
    when_to_use="Getting a structured summary of sprint progress.",
    mutating=False,
    idempotent=True,
    returns=ReturnSchema(
        description="Sprint statistics",
        type="object",
        properties={"total": "int", "completed": "int", "percent": "int",
                    "status": "object", "priority": "object"},
    ),
))
```

- [ ] **Step 2: Test `--schema` on individual commands**

```bash
./bin/murli-work-py-click task create --schema
./bin/murli-work-py-click task list --schema
```

Expected — JSON schema with `agent_description`, `returns`, `examples` populated.

- [ ] **Step 3: Test `describe` shows full annotated tree**

```bash
./bin/murli-work-py-click describe
```

Expected: top-level `commands` array with all commands, each with `agent_description` and `returns`.

- [ ] **Step 4: Commit**

```bash
git add python/click/main.py
git commit -m "$(cat <<'EOF'
feat(python/click): step 3 — schema annotations for all commands

Adds murli.annotate() for every command and subcommand with
agent_description, when_to_use, mutating/idempotent/destructive flags,
ReturnSchema, and examples where applicable.

--schema and describe now expose full machine-readable metadata enabling
agents to discover capabilities without documentation.

Terminal output (./bin/murli-work-py-click describe):
[paste captured JSON here]

Terminal output (./bin/murli-work-py-click task create --schema):
[paste captured JSON here]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Actionable Error Handling

The Writer API calls in Task 2 already include `write_error(AgentError...)` in all handlers. This task verifies the error envelopes and confirms correct exit codes.

**Files:** No code changes — verification only.

- [ ] **Step 1: Verify not-found error (exit 5)**

```bash
./bin/murli-work-py-click --agent task update 999 --status done
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

- [ ] **Step 2: Verify user error (exit 1)**

```bash
./bin/murli-work-py-click --agent task create "Bad prio" --priority extreme
echo "exit: $?"
```

Expected: click's own Choice validation fires before the handler, so the exit code is click's standard error. Verify the error message appears on stderr.

- [ ] **Step 3: Verify conflict error on duplicate label**

```bash
./bin/murli-work-py-click init
./bin/murli-work-py-click --agent label create dev
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

- [ ] **Step 4: Commit**

```bash
git add python/click/main.py
git commit -m "$(cat <<'EOF'
feat(python/click): step 4 — actionable structured errors via AgentError

All error paths use writer.write_error(AgentError.*()) which emits a
structured JSON envelope in agent mode and a plain Error:/Hint: pair in
TTY mode, then calls sys.exit(code).

Error type mapping:
  KeyError (not found)  -> AgentError.not_found()      exit 5
  FileExistsError       -> AgentError.conflict_error()  exit 7
  ValueError (bad input)-> AgentError.user_error()      exit 1
  Exception (tool err)  -> AgentError.tool_error()      exit 2

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
- Modify: `python/click/main.py`
- Create: `PYTHON-CLICK-GUIDE.md`

- [ ] **Step 1: Add `writer.log()` to `init` and `writer.write_progress()` to `report`**

In `init`, add a log line before the db reset:

```python
@cli.command()
@murli.pass_writer
def init(writer):
    """Initialize/Reset the database and config"""
    writer.log("Resetting database and seeding sample data...")
    db_ops.reset_db()
    dir_path = db_ops.get_storage_dir()
    writer.write_success(
        f"Initialized/Reset murli-work database with sample data and configuration in {dir_path}",
        {"path": str(dir_path)},
    )
```

In `report`, add progress before computation:

```python
@cli.command()
@murli.pass_writer
def report(writer):
    """Display progress report"""
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

- [ ] **Step 2: Verify log deduplication in agent mode**

```bash
./bin/murli-work-py-click --agent init | cat
```

Expected: the `writer.log()` line appears as a JSON log entry on stderr (not in the JSON envelope on stdout):
```
{"ts": "2026-06-03T...", "level": "info", "msg": "Resetting database and seeding sample data..."}
```
And stdout contains only the success envelope.

- [ ] **Step 3: Write `PYTHON-CLICK-GUIDE.md`**

Create `/Users/allank/Dev/murli/murli-demo/PYTHON-CLICK-GUIDE.md` with the following content, filling in the captured terminal output at each `[capture]` marker from the outputs recorded in tasks 1–4:

```markdown
# Python / click — Murli Integration Guide

This guide walks through integrating the murli middleware into a click CLI application, step by step. Each step shows the code change, explains the mechanic, and captures the terminal output.

The target application is `murli-work`, a sprint task tracker.

---

## What You Get for Free (Step 1)

Replacing `cli()` with `murli.enable(cli)` before invocation injects:

- `--agent` — forces JSON output without piping
- `--schema` — prints per-command JSON schema and exits
- `--force` / `--yes` — suppresses confirmation prompts
- `--dry-run` — marks the invocation as preview-only
- `--profile NAME` — loads a saved flag profile
- `describe` subcommand — prints the full command tree as JSON
- `doctor` subcommand — checks naming convention compliance
- `profile` subcommand — manages saved flag profiles

TTY detection is automatic: plain text at a terminal, JSON when piped or when `--agent` is passed.

**Note on `--output`:** murli normally also injects `--output` for controlling its own format (json/ndjson/text). Because `task list` defines its own `--output` flag (for table/csv/json display), murli detects the collision and skips injecting its own. This is the `_has_output_option()` guard introduced in the adapter fixes.

### Code change

```python
import murli

# ... all command definitions ...

murli.enable(cli)   # ← one line after all commands are registered

if __name__ == "__main__":
    cli()
```

### Terminal output — `--help`

```
[paste ./bin/murli-work-py-click --help output here]
```

### Terminal output — `describe`

```json
[paste ./bin/murli-work-py-click describe output here]
```

---

## What You Configure (Step 3)

`murli.annotate(cmd, Metadata(...))` attaches machine-readable metadata to each command. This powers `--schema` and the `describe` tree.

Key fields:
- `agent_description` — plain-English description for an AI agent reading the schema
- `when_to_use` — disambiguation guide between similar commands
- `mutating` / `idempotent` / `destructive` — safety classification
- `returns` — shape of the JSON result payload
- `examples` — invocation examples with expected exit codes

### Terminal output — `task create --schema`

```json
[paste ./bin/murli-work-py-click task create --schema output here]
```

---

## What You Build (Steps 2 + 4)

### Writer API

Replace `click.echo()` and `sys.exit()` with `writer.write_success()` and `writer.write_error()`:

```python
@cli.command()
@murli.pass_writer          # ← injects writer as first argument
def init(writer):
    db_ops.reset_db()
    dir_path = db_ops.get_storage_dir()
    writer.write_success(   # ← text for humans, JSON for agents
        f"Initialized database in {dir_path}",
        {"path": str(dir_path)},
    )
```

For commands that need both context and writer, use `@click.pass_context` and `murli.get_writer(ctx)`:

```python
@click.pass_context
def my_cmd(ctx, ...):
    writer = murli.get_writer(ctx)
```

### Dual-audience output

```
# TTY
$ ./bin/murli-work-py-click task create "Sprint item" --priority high
Task 6 ("Sprint item") created successfully.

# Agent
$ ./bin/murli-work-py-click --agent task create "Sprint item" --priority high
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
[paste ./bin/murli-work-py-click task list output here]
```

### Terminal output — agent task list

```json
[paste ./bin/murli-work-py-click --agent task list output here]
```

### Structured errors (Step 4)

```
# TTY
$ ./bin/murli-work-py-click task update 999 --status done
Error: task with ID 999 not found
Hint:  Use task list to see valid IDs.

# Agent
$ ./bin/murli-work-py-click --agent task update 999 --status done
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

`writer.log(msg)` writes to stderr. In TTY mode it prints plainly. In agent mode it emits a structured JSON log entry with deduplication — repeated identical messages are collapsed with a `"repeated": N` count.

```python
writer.log("Computing sprint statistics...")
```

### Terminal output — init in agent mode (stderr log)

```
[paste ./bin/murli-work-py-click --agent init 2>&1 output here]
```
```

- [ ] **Step 4: Rebuild and do a full smoke run for the guide captures**

Run each command below, capture the output, and paste it into the corresponding `[paste ...]` section of `PYTHON-CLICK-GUIDE.md`:

```bash
make build-py
./bin/murli-work-py-click --help
./bin/murli-work-py-click describe
./bin/murli-work-py-click task create --schema
./bin/murli-work-py-click init
./bin/murli-work-py-click task create "Sprint item" --priority high
./bin/murli-work-py-click task list
./bin/murli-work-py-click --agent task create "Agent sprint item" --priority high
./bin/murli-work-py-click --agent task list
./bin/murli-work-py-click task update 999 --status done
./bin/murli-work-py-click --agent task update 999 --status done
./bin/murli-work-py-click --agent init 2>&1
```

- [ ] **Step 5: Commit guide and telemetry changes**

```bash
git add python/click/main.py PYTHON-CLICK-GUIDE.md
git commit -m "$(cat <<'EOF'
feat(python/click): step 5 — telemetry and integration guide

Adds writer.log() to init (db reset) and report (statistics) for
structured stderr logging with dedup in agent mode.

Adds PYTHON-CLICK-GUIDE.md documenting all five integration steps with
captured terminal output showing TTY/agent duality, --schema output,
structured errors, and log deduplication.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: Push branch**

```bash
git push -u origin python/click
```
