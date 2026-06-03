from typing import Optional
from enum import Enum
import typer
import sys
import os
import murli
from murli import AgentError, Metadata, ReturnSchema, Example

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
        return
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
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
        return

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
        return
    except ValueError as e:
        writer.write_error(AgentError.user_error(str(e), "Use --priority low|medium|high, --status todo|doing|done."))
        return
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
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
        return
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
    writer.write_success(f"Task {id} deleted successfully.", {"id": id})


@label_app.command(name="list")
def label_list(ctx: typer.Context):
    """List all defined labels"""
    writer = murli.get_writer(ctx)
    try:
        db = db_ops.load_db()
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
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
        return
    except ValueError as e:
        writer.write_error(AgentError.user_error(str(e)))
        return
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
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
        return
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
    writer.write_success(f'Label "{name}" deleted successfully.', {"name": name})


@app.command()
def report(ctx: typer.Context):
    """Display progress report"""
    writer = murli.get_writer(ctx)
    writer.log("Computing sprint statistics...")
    try:
        db = db_ops.load_db()
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
    report_data = format_ops.sprint_report_data(db)
    if writer.is_tty():
        print(format_ops.format_sprint_report(db))
    else:
        writer.write_success("Sprint report generated.", report_data)


murli.annotate(app, Metadata(
    agent_description=(
        "murli-work sprint task tracker. Manages tasks (create/list/update/delete) "
        "and labels. All mutating commands accept --force and --dry-run."
    ),
    when_to_use="Managing sprint tasks and labels from the command line or an AI agent.",
    mutating=False,
    idempotent=True,
))

if __name__ == "__main__":
    app()
