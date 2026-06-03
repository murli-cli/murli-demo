import click
import sys
import os
import murli
from murli import AgentError, Metadata, ReturnSchema, Example

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
    writer.log("Resetting database and seeding sample data...")
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
        return
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
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
        return

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
        return
    except ValueError as e:
        writer.write_error(AgentError.user_error(str(e), "Use --priority low|medium|high, --status todo|doing|done."))
        return
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
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
        return
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
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
        return
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
        return
    except ValueError as e:
        writer.write_error(AgentError.user_error(str(e)))
        return
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
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
        return
    except Exception as e:
        writer.write_error(AgentError.tool_error(str(e)))
        return
    writer.write_success(f'Label "{name}" deleted successfully.', {"name": name})


@cli.command()
@murli.pass_writer
def report(writer):
    """Display progress report"""
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

murli.enable(cli)

if __name__ == "__main__":
    cli()
