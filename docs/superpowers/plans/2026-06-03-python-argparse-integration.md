# Python / argparse — Murli Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply murli middleware to the argparse skeleton (`python/argparse/main.py`) following the five-step WALKTHROUGH-INSTRUCTIONS methodology, producing a fully annotated, dual-audience CLI with structured errors, and a companion guide document.

**Architecture:** Five progressive commits on branch `python/argparse` (from main). The argparse adapter uses a different entry point: `murli.enable(parser)` adds flags and mounts built-in subcommands; `murli.parse(parser)` is a drop-in for `parse_args()` that returns `(namespace, writer)`. Because argparse has no decorator system, per-command annotations use `murli.annotate(subparser, Metadata(...))` on each subparser object. `shared/format.py` requires the same string-returning additions as the other plans.

**Tech Stack:** Python 3.10+, argparse (stdlib), murli (core, no extras needed for argparse), uv

**Prerequisite:** The murli-py adapter fixes plan must be complete and pushed (specifically the `build_describe_tree` recursion fix).

---

## File Map

| File | Change |
|---|---|
| `python/requirements.txt` | Add `murli` editable local install |
| `Makefile` | Split `build-py` so `uv pip install` always runs |
| `python/shared/format.py` | Add string-returning `format_*` variants and `sprint_report_data()` |
| `python/argparse/main.py` | Full murli integration across five steps |
| `PYTHON-ARGPARSE-GUIDE.md` | Step-by-step integration guide with terminal captures |

---

## Task 0: Create branch

- [ ] **Step 1: Branch from main**

```bash
cd /Users/allank/Dev/murli/murli-demo
git checkout main
git checkout -b python/argparse
```

---

## Task 1: Dependency + `murli.enable()` + `murli.parse()` — what you get for free

**Files:**
- Modify: `python/requirements.txt`
- Modify: `Makefile`
- Modify: `python/argparse/main.py`

- [ ] **Step 1: Add murli to requirements.txt**

Replace the contents of `python/requirements.txt`:

```
click>=8.0.0
typer>=0.9.0
tabulate>=0.9.0
rich>=13.0.0
-e ../../murli-py
```

(No extras needed — argparse adapter is in the core murli package.)

- [ ] **Step 2: Fix Makefile so deps always reinstall**

In `Makefile`, find in `build-py`:

```makefile
	[ -d .venv ] || (uv venv && uv pip install -r python/requirements.txt)
```

Replace with:

```makefile
	[ -d .venv ] || uv venv
	uv pip install -r python/requirements.txt
```

- [ ] **Step 3: Add `murli.enable()` and replace `parse_args()` with `murli.parse()`**

The argparse integration requires two changes to `main()`:
1. Call `murli.enable(parser)` AFTER `parser.add_subparsers()` is called (and after all user subparsers are defined), so the adapter finds the existing subparsers action.
2. Replace `args = parser.parse_args()` with `args, writer = murli.parse(parser)`.

Add `import murli` to the top imports in `python/argparse/main.py`.

The restructured `main()` function (only steps 1 and 2 shown — all other command-handling code stays identical for this task):

```python
import argparse
import sys
import os
import murli

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import shared.db as db_ops
import shared.format as format_ops


def main():
    parser = argparse.ArgumentParser(
        prog="murli-work",
        description="murli-work - A sprint and project task tracker",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize/Reset the database and config")

    # task command and its subparsers
    task_parser = subparsers.add_parser("task", help="Manage sprint tasks")
    task_subparsers = task_parser.add_subparsers(dest="task_command", help="Task subcommands")

    task_create = task_subparsers.add_parser("create", help="Create a new task")
    task_create.add_argument("title", help="Task title")
    task_create.add_argument("--desc", "-d", help="Task description")
    task_create.add_argument("--priority", "-p", choices=["low", "medium", "high"], help="Task priority")
    task_create.add_argument("--labels", "-l", help="Comma-separated labels")

    task_list = task_subparsers.add_parser("list", help="List stored tasks")
    task_list.add_argument("--status", "-s", choices=["todo", "doing", "done"], help="Filter by status")
    task_list.add_argument("--priority", "-p", choices=["low", "medium", "high"], help="Filter by priority")
    task_list.add_argument("--label", "-l", help="Filter by label")
    task_list.add_argument("--output", "-o", choices=["table", "json", "csv"], default="table", help="Output format (TTY)")

    task_update = task_subparsers.add_parser("update", help="Update an existing task's fields")
    task_update.add_argument("id", type=int, help="Task ID")
    task_update.add_argument("--title", "-t", help="New title")
    task_update.add_argument("--desc", "-d", help="New description")
    task_update.add_argument("--priority", "-p", choices=["low", "medium", "high"], help="New priority")
    task_update.add_argument("--status", "-s", choices=["todo", "doing", "done"], help="New status")
    task_update.add_argument("--labels", "-l", help="Replacement labels")

    task_delete = task_subparsers.add_parser("delete", help="Delete a task")
    task_delete.add_argument("id", type=int, help="Task ID")
    task_delete.add_argument("--force", action="store_true", help="Force delete without warning")

    # label command and its subparsers
    label_parser = subparsers.add_parser("label", help="Manage global task labels")
    label_subparsers = label_parser.add_subparsers(dest="label_command", help="Label subcommands")

    label_list = label_subparsers.add_parser("list", help="List all defined labels")

    label_create = label_subparsers.add_parser("create", help="Create a custom label")
    label_create.add_argument("name", help="Label name")

    label_delete = label_subparsers.add_parser("delete", help="Delete a label")
    label_delete.add_argument("name", help="Label name")

    # report command
    report_parser = subparsers.add_parser("report", help="Display progress report")

    # ── murli integration ──────────────────────────────────────────────────────
    murli.enable(parser)   # must be after all add_subparsers calls
    # ──────────────────────────────────────────────────────────────────────────

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args, writer = murli.parse(parser)   # replaces parser.parse_args()

    # All existing command-handling code below is UNCHANGED for this task
    try:
        if args.command == "init":
            db_ops.reset_db()
            dir_path = db_ops.get_storage_dir()
            print(f"Initialized/Reset murli-work database with sample data and configuration in {dir_path}")

        elif args.command == "task":
            if not args.task_command:
                task_parser.print_help()
                sys.exit(0)

            if args.task_command == "create":
                db = db_ops.load_db()
                labels_list = args.labels.split(",") if args.labels else []
                new_id = db_ops.create_task(db, args.title, args.desc, args.priority, labels_list)
                print(f"Task {new_id} (\"{args.title}\") created successfully.")

            elif args.task_command == "list":
                db = db_ops.load_db()
                cfg = db_ops.load_config()
                output_fmt = args.output
                if output_fmt == "table" and cfg and cfg.get("default_output"):
                    output_fmt = cfg["default_output"]
                filtered = db["tasks"]
                if args.status:
                    filtered = [t for t in filtered if t["status"].lower() == args.status.lower()]
                if args.priority:
                    filtered = [t for t in filtered if t["priority"].lower() == args.priority.lower()]
                if args.label:
                    filtered = [t for t in filtered if any(l.lower() == args.label.lower() for l in t["labels"])]
                if output_fmt == "json":
                    format_ops.print_tasks_json(filtered)
                elif output_fmt == "csv":
                    format_ops.print_tasks_csv(filtered)
                else:
                    format_ops.print_tasks_table(filtered)

            elif args.task_command == "update":
                db = db_ops.load_db()
                labels_list = args.labels.split(",") if args.labels is not None else None
                db_ops.update_task(db, args.id, args.title, args.desc, args.priority, args.status, labels_list)
                print(f"Task {args.id} updated successfully.")

            elif args.task_command == "delete":
                db = db_ops.load_db()
                db_ops.delete_task(db, args.id)
                print(f"Task {args.id} deleted successfully.")

        elif args.command == "label":
            if not args.label_command:
                label_parser.print_help()
                sys.exit(0)
            if args.label_command == "list":
                db = db_ops.load_db()
                format_ops.print_labels_table(db)
            elif args.label_command == "create":
                db = db_ops.load_db()
                slug = db_ops.create_label(db, args.name)
                print(f"Label \"{slug}\" created successfully.")
            elif args.label_command == "delete":
                db = db_ops.load_db()
                db_ops.delete_label(db, args.name)
                print(f"Label \"{args.name}\" deleted successfully.")

        elif args.command == "report":
            db = db_ops.load_db()
            format_ops.print_sprint_report(db)
        else:
            parser.print_help()

    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Build and smoke-test**

```bash
cd /Users/allank/Dev/murli/murli-demo
make build-py
./bin/murli-work-py-argparse --help
```

Expected — murli flags appear:
```
usage: murli-work [-h] [--agent] [--schema] [--force] [--dry-run] [--profile NAME]
                  {init,task,label,report,describe,doctor,profile} ...

murli-work - A sprint and project task tracker

positional arguments:
  {init,task,label,report,describe,doctor,profile}

options:
  --agent           Force JSON output for agent/script use
  --schema          Print command schema as JSON and exit
  --force, --yes    Skip confirmation prompts
  --dry-run         Simulate without making changes
  --profile NAME    Load a named flag profile
```

```bash
./bin/murli-work-py-argparse describe
./bin/murli-work-py-argparse init
./bin/murli-work-py-argparse task create "Test step 1"
./bin/murli-work-py-argparse task list
```

Expected: `describe` returns JSON with all subcommands listed (thanks to the recursion fix). Existing commands work as before.

- [ ] **Step 5: Commit**

```bash
git add python/requirements.txt Makefile python/argparse/main.py
git commit -m "$(cat <<'EOF'
feat(python/argparse): step 1 — add murli dependency and enable adapter

Adds murli from local path install. Updates Makefile build-py.

murli.enable(parser) is called after all add_subparsers() calls so the
adapter finds the existing subparsers action and injects describe,
doctor, profile into it. murli.parse(parser) replaces parse_args() and
returns (namespace, writer).

Terminal output (./bin/murli-work-py-argparse --help):
[paste captured output here]

Terminal output (./bin/murli-work-py-argparse describe):
[paste captured JSON here]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Writer API — route all output through `writer.write_success()`

**Files:**
- Modify: `python/shared/format.py`
- Modify: `python/argparse/main.py`

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

- [ ] **Step 2: Rewrite `python/argparse/main.py` with Writer API in all handlers**

Replace the entire contents of `python/argparse/main.py`:

```python
import argparse
import sys
import os
import murli
from murli import AgentError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import shared.db as db_ops
import shared.format as format_ops


def main():
    parser = argparse.ArgumentParser(
        prog="murli-work",
        description="murli-work - A sprint and project task tracker",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    init_parser = subparsers.add_parser("init", help="Initialize/Reset the database and config")

    task_parser = subparsers.add_parser("task", help="Manage sprint tasks")
    task_subparsers = task_parser.add_subparsers(dest="task_command", help="Task subcommands")

    task_create = task_subparsers.add_parser("create", help="Create a new task")
    task_create.add_argument("title", help="Task title")
    task_create.add_argument("--desc", "-d", help="Task description")
    task_create.add_argument("--priority", "-p", choices=["low", "medium", "high"], help="Task priority")
    task_create.add_argument("--labels", "-l", help="Comma-separated labels")

    task_list = task_subparsers.add_parser("list", help="List stored tasks")
    task_list.add_argument("--status", "-s", choices=["todo", "doing", "done"], help="Filter by status")
    task_list.add_argument("--priority", "-p", choices=["low", "medium", "high"], help="Filter by priority")
    task_list.add_argument("--label", "-l", help="Filter by label")
    task_list.add_argument("--output", "-o", choices=["table", "json", "csv"], default="table", help="Output format (TTY)")

    task_update = task_subparsers.add_parser("update", help="Update an existing task's fields")
    task_update.add_argument("id", type=int, help="Task ID")
    task_update.add_argument("--title", "-t", help="New title")
    task_update.add_argument("--desc", "-d", help="New description")
    task_update.add_argument("--priority", "-p", choices=["low", "medium", "high"], help="New priority")
    task_update.add_argument("--status", "-s", choices=["todo", "doing", "done"], help="New status")
    task_update.add_argument("--labels", "-l", help="Replacement labels")

    task_delete = task_subparsers.add_parser("delete", help="Delete a task")
    task_delete.add_argument("id", type=int, help="Task ID")
    task_delete.add_argument("--force", action="store_true", help="Force delete without warning")

    label_parser = subparsers.add_parser("label", help="Manage global task labels")
    label_subparsers = label_parser.add_subparsers(dest="label_command", help="Label subcommands")

    label_list = label_subparsers.add_parser("list", help="List all defined labels")

    label_create = label_subparsers.add_parser("create", help="Create a custom label")
    label_create.add_argument("name", help="Label name")

    label_delete = label_subparsers.add_parser("delete", help="Delete a label")
    label_delete.add_argument("name", help="Label name")

    report_parser = subparsers.add_parser("report", help="Display progress report")

    murli.enable(parser)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args, writer = murli.parse(parser)

    if args.command == "init":
        try:
            db_ops.reset_db()
            dir_path = db_ops.get_storage_dir()
        except Exception as e:
            writer.write_error(AgentError.tool_error(str(e)))
        writer.write_success(
            f"Initialized/Reset murli-work database with sample data and configuration in {dir_path}",
            {"path": str(dir_path)},
        )

    elif args.command == "task":
        if not args.task_command:
            task_parser.print_help()
            sys.exit(0)

        if args.task_command == "create":
            labels_list = args.labels.split(",") if args.labels else []
            try:
                db = db_ops.load_db()
                new_id = db_ops.create_task(db, args.title, args.desc, args.priority, labels_list)
            except ValueError as e:
                writer.write_error(AgentError.user_error(str(e), "Use --priority low|medium|high."))
            except Exception as e:
                writer.write_error(AgentError.tool_error(str(e)))
            writer.write_success(
                f'Task {new_id} ("{args.title}") created successfully.',
                {"id": new_id, "title": args.title},
            )

        elif args.task_command == "list":
            try:
                db = db_ops.load_db()
                cfg = db_ops.load_config()
            except Exception as e:
                writer.write_error(AgentError.tool_error(str(e)))
            output_fmt = args.output
            if output_fmt == "table" and cfg and cfg.get("default_output"):
                output_fmt = cfg["default_output"]
            filtered = db["tasks"]
            if args.status:
                filtered = [t for t in filtered if t["status"].lower() == args.status.lower()]
            if args.priority:
                filtered = [t for t in filtered if t["priority"].lower() == args.priority.lower()]
            if args.label:
                filtered = [t for t in filtered if any(l.lower() == args.label.lower() for l in t["labels"])]
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

        elif args.task_command == "update":
            labels_list = args.labels.split(",") if args.labels is not None else None
            try:
                db = db_ops.load_db()
                db_ops.update_task(db, args.id, args.title, args.desc, args.priority, args.status, labels_list)
            except KeyError as e:
                writer.write_error(AgentError.not_found(str(e), "Use task list to see valid IDs."))
            except ValueError as e:
                writer.write_error(AgentError.user_error(str(e), "Use --priority low|medium|high, --status todo|doing|done."))
            except Exception as e:
                writer.write_error(AgentError.tool_error(str(e)))
            writer.write_success(f"Task {args.id} updated successfully.", {"id": args.id})

        elif args.task_command == "delete":
            try:
                db = db_ops.load_db()
                db_ops.delete_task(db, args.id)
            except KeyError as e:
                writer.write_error(AgentError.not_found(str(e), "Use task list to see valid IDs."))
            except Exception as e:
                writer.write_error(AgentError.tool_error(str(e)))
            writer.write_success(f"Task {args.id} deleted successfully.", {"id": args.id})

    elif args.command == "label":
        if not args.label_command:
            label_parser.print_help()
            sys.exit(0)

        if args.label_command == "list":
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

        elif args.label_command == "create":
            try:
                db = db_ops.load_db()
                slug = db_ops.create_label(db, args.name)
            except FileExistsError as e:
                writer.write_error(AgentError.conflict_error(str(e), "Use label list to see existing labels."))
            except ValueError as e:
                writer.write_error(AgentError.user_error(str(e)))
            except Exception as e:
                writer.write_error(AgentError.tool_error(str(e)))
            writer.write_success(f'Label "{slug}" created successfully.', {"slug": slug})

        elif args.label_command == "delete":
            try:
                db = db_ops.load_db()
                db_ops.delete_label(db, args.name)
            except KeyError as e:
                writer.write_error(AgentError.not_found(str(e), "Use label list to see valid labels."))
            except Exception as e:
                writer.write_error(AgentError.tool_error(str(e)))
            writer.write_success(f'Label "{args.name}" deleted successfully.', {"name": args.name})

    elif args.command == "report":
        try:
            db = db_ops.load_db()
        except Exception as e:
            writer.write_error(AgentError.tool_error(str(e)))
        report_data = format_ops.sprint_report_data(db)
        if writer.is_tty():
            print(format_ops.format_sprint_report(db))
        else:
            writer.write_success("Sprint report generated.", report_data)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Rebuild and verify TTY output**

```bash
make build-py
./bin/murli-work-py-argparse init
./bin/murli-work-py-argparse task create "Writer API test" --priority high
./bin/murli-work-py-argparse task list
./bin/murli-work-py-argparse report
```

Expected: human-readable output identical to the skeleton.

- [ ] **Step 4: Verify agent mode output**

```bash
./bin/murli-work-py-argparse --agent task create "Agent test"
./bin/murli-work-py-argparse --agent task list
./bin/murli-work-py-argparse --agent report
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
git add python/shared/format.py python/argparse/main.py
git commit -m "$(cat <<'EOF'
feat(python/argparse): step 2 — Writer API replaces print/sys.exit

All handlers use writer.write_success() and writer.write_error() via
the (namespace, writer) tuple returned by murli.parse(). Commands with
multi-format output (task list, label list, report) use writer.is_tty()
to select the display path: TTY format_ops helpers vs JSON envelope.

shared/format.py gains string-returning format_* helpers and
sprint_report_data() (same additions as click and typer branches).

Terminal output (--agent task list):
[paste captured JSON here]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Schema + Annotations

**Files:**
- Modify: `python/argparse/main.py`

In argparse there is no decorator system. Annotations are attached directly to the subparser objects using `murli.annotate(subparser, Metadata(...))` after each subparser is defined.

- [ ] **Step 1: Add annotation imports and annotate each subparser**

Add to imports:
```python
from murli import Metadata, ReturnSchema, Example
```

In `main()`, add annotations directly after the subparser variable assignments. Insert these blocks at the indicated positions:

After `init_parser = subparsers.add_parser(...)`:
```python
murli.annotate(init_parser, Metadata(
    agent_description="Resets the database to seed data and writes default config.",
    when_to_use="First-time setup or to restore the database to a clean state.",
    mutating=True,
    idempotent=True,
    returns=ReturnSchema(description="Storage directory path", type="object",
                         properties={"path": "string"}),
))
```

After `task_create = task_subparsers.add_parser("create", ...)` and its `.add_argument()` calls:
```python
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
```

After `task_list = task_subparsers.add_parser("list", ...)` and its `.add_argument()` calls:
```python
murli.annotate(task_list, Metadata(
    agent_description="Returns filtered tasks. Use --status, --priority, --label to narrow results.",
    when_to_use="Querying the backlog or checking sprint progress.",
    mutating=False,
    idempotent=True,
    returns=ReturnSchema(description="Filtered task list", type="object",
                         properties={"tasks": "array", "count": "int"}),
))
```

After `task_update = task_subparsers.add_parser("update", ...)` and its `.add_argument()` calls:
```python
murli.annotate(task_update, Metadata(
    agent_description="Updates one or more fields on an existing task. Omitted flags are unchanged.",
    when_to_use="Changing status, priority, or labels on a task.",
    mutating=True,
    idempotent=True,
    returns=ReturnSchema(description="Updated task ID", type="object", properties={"id": "int"}),
))
```

After `task_delete = task_subparsers.add_parser("delete", ...)` and its `.add_argument()` calls:
```python
murli.annotate(task_delete, Metadata(
    agent_description="Permanently removes a task by ID.",
    when_to_use="Removing a cancelled or obsolete task from the backlog.",
    mutating=True,
    idempotent=False,
    destructive=True,
    returns=ReturnSchema(description="Deleted task ID", type="object", properties={"id": "int"}),
))
```

After `label_list = label_subparsers.add_parser("list", ...)`:
```python
murli.annotate(label_list, Metadata(
    agent_description="Lists all labels defined in the database with task counts.",
    when_to_use="Discovering available labels before creating or filtering tasks.",
    mutating=False,
    idempotent=True,
    returns=ReturnSchema(description="Label array", type="object", properties={"labels": "array"}),
))
```

After `label_create = label_subparsers.add_parser("create", ...)` and its `.add_argument()`:
```python
murli.annotate(label_create, Metadata(
    agent_description="Creates a new label slug. Fails with conflict if it already exists.",
    when_to_use="Adding a label category before tagging tasks with it.",
    mutating=True,
    idempotent=False,
    returns=ReturnSchema(description="Created label slug", type="object", properties={"slug": "string"}),
))
```

After `label_delete = label_subparsers.add_parser("delete", ...)` and its `.add_argument()`:
```python
murli.annotate(label_delete, Metadata(
    agent_description="Deletes a label and removes it from all tasks.",
    when_to_use="Cleaning up unused or misnamed labels.",
    mutating=True,
    idempotent=False,
    destructive=True,
    returns=ReturnSchema(description="Deleted label name", type="object", properties={"name": "string"}),
))
```

After `report_parser = subparsers.add_parser("report", ...)`:
```python
murli.annotate(report_parser, Metadata(
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

- [ ] **Step 2: Verify annotations appear in describe output**

```bash
./bin/murli-work-py-argparse describe
./bin/murli-work-py-argparse --schema
```

Expected: `describe` output contains `agent_description`, `returns`, and `examples` for each subcommand.

- [ ] **Step 3: Commit**

```bash
git add python/argparse/main.py
git commit -m "$(cat <<'EOF'
feat(python/argparse): step 3 — schema annotations for all subcommands

Adds murli.annotate(subparser, Metadata(...)) for every subparser with
agent_description, when_to_use, mutating/idempotent/destructive flags,
ReturnSchema, and examples where applicable.

In argparse, annotations are attached directly to the subparser objects
(not decorators), placed immediately after each add_parser() block.

Terminal output (./bin/murli-work-py-argparse describe):
[paste captured JSON here]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Verify Actionable Error Handling

Writer API calls in Task 2 already include structured errors. This task verifies the envelopes and exit codes.

**Files:** No code changes — verification only.

- [ ] **Step 1: Verify not-found error (exit 5)**

```bash
./bin/murli-work-py-argparse --agent task update 999 --status done
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
./bin/murli-work-py-argparse init
./bin/murli-work-py-argparse --agent label create dev
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
git add python/argparse/main.py
git commit -m "$(cat <<'EOF'
feat(python/argparse): step 4 — structured error verification

Confirmed error envelopes with correct exit codes in agent mode.
In argparse, errors that occur before murli.parse() (e.g. unrecognised
arguments) are reported by argparse itself and exit 2. Errors in
command handlers use AgentError via writer.write_error().

Terminal output (--agent task update 999 --status done):
[paste captured JSON here]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Telemetry + Guide

**Files:**
- Modify: `python/argparse/main.py`
- Create: `PYTHON-ARGPARSE-GUIDE.md`

- [ ] **Step 1: Add `writer.log()` to `init` and `report` handlers**

In the `args.command == "init"` block:

```python
    if args.command == "init":
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

In the `args.command == "report"` block:

```python
    elif args.command == "report":
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
./bin/murli-work-py-argparse --agent init 2>&1
```

Expected: stderr log entry followed by stdout success envelope:
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

- [ ] **Step 3: Write `PYTHON-ARGPARSE-GUIDE.md`**

Create `/Users/allank/Dev/murli/murli-demo/PYTHON-ARGPARSE-GUIDE.md`:

```markdown
# Python / argparse — Murli Integration Guide

This guide walks through integrating murli middleware into an argparse CLI, step by step.

The target application is `murli-work`, a sprint task tracker.

---

## argparse vs. click/typer: key differences

argparse has no decorator system. The murli integration uses two function calls instead of decorators:

1. `murli.enable(parser)` — adds murli flags and mounts `describe`, `doctor`, `profile` subcommands into the existing subparsers action. Must be called **after** `add_subparsers()`.
2. `args, writer = murli.parse(parser)` — drop-in replacement for `parse_args()`. Returns the namespace and a configured Writer.

Annotations use `murli.annotate(subparser, Metadata(...))` directly on subparser objects.

---

## What You Get for Free (Step 1)

```python
murli.enable(parser)          # after all add_subparsers() calls
args, writer = murli.parse(parser)   # replaces parser.parse_args()
```

Injects: `--agent`, `--schema`, `--force`, `--dry-run`, `--profile`
Adds to existing subparsers: `describe`, `doctor`, `profile`

### Terminal output — `--help`

```
[paste ./bin/murli-work-py-argparse --help output here]
```

### Terminal output — `describe`

```json
[paste ./bin/murli-work-py-argparse describe output here]
```

---

## What You Configure (Step 3)

Annotations are attached directly to subparser objects immediately after their `.add_argument()` calls:

```python
task_create = task_subparsers.add_parser("create", help="Create a new task")
task_create.add_argument("title", help="Task title")
# ... more add_argument() calls ...

murli.annotate(task_create, Metadata(
    agent_description="Creates a new task and assigns it a unique integer ID.",
    when_to_use="Adding a new item to the sprint backlog.",
    mutating=True,
    idempotent=False,
    returns=ReturnSchema(description="New task ID and title", type="object",
                         properties={"id": "int", "title": "string"}),
))
```

### Terminal output — `describe` with annotations

```json
[paste ./bin/murli-work-py-argparse describe output here]
```

---

## What You Build (Steps 2 + 4)

### Writer API

The `writer` comes from `murli.parse(parser)`. Use it throughout the command handlers:

```python
args, writer = murli.parse(parser)

if args.command == "init":
    writer.log("Resetting database...")
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
$ ./bin/murli-work-py-argparse task create "Sprint item" --priority high
Task 6 ("Sprint item") created successfully.

# Agent
$ ./bin/murli-work-py-argparse --agent task create "Sprint item" --priority high
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
[paste ./bin/murli-work-py-argparse task list output here]
```

### Terminal output — agent task list

```json
[paste ./bin/murli-work-py-argparse --agent task list output here]
```

### Structured errors (Step 4)

```
# TTY
$ ./bin/murli-work-py-argparse task update 999 --status done
Error: task with ID 999 not found
Hint:  Use task list to see valid IDs.

# Agent
$ ./bin/murli-work-py-argparse --agent task update 999 --status done
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

`writer.log()` writes to stderr. In agent mode it emits structured JSON log entries with deduplication.

### Terminal output — init in agent mode (stderr log + stdout envelope)

```
[paste ./bin/murli-work-py-argparse --agent init 2>&1 output here]
```
```

- [ ] **Step 4: Capture all output for guide and fill in placeholders**

```bash
make build-py
./bin/murli-work-py-argparse --help
./bin/murli-work-py-argparse describe
./bin/murli-work-py-argparse init
./bin/murli-work-py-argparse task create "Sprint item" --priority high
./bin/murli-work-py-argparse task list
./bin/murli-work-py-argparse --agent task create "Agent sprint item" --priority high
./bin/murli-work-py-argparse --agent task list
./bin/murli-work-py-argparse task update 999 --status done
./bin/murli-work-py-argparse --agent task update 999 --status done
./bin/murli-work-py-argparse --agent init 2>&1
```

- [ ] **Step 5: Commit and push**

```bash
git add python/argparse/main.py PYTHON-ARGPARSE-GUIDE.md
git commit -m "$(cat <<'EOF'
feat(python/argparse): step 5 — telemetry and integration guide

Adds writer.log() to init and report handlers. Adds PYTHON-ARGPARSE-
GUIDE.md documenting the argparse-specific integration pattern:
enable(parser) ordering, murli.parse() as parse_args() replacement,
and direct subparser annotation via murli.annotate(subparser, Metadata).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
git push -u origin python/argparse
```
