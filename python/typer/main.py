from typing import Optional
from enum import Enum
import typer
import sys
import os
import murli

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import shared.db as db_ops
import shared.format as format_ops

app = typer.Typer(help="murli-work - A sprint and project task tracker")

task_app = typer.Typer(help="Manage sprint tasks")
app.add_typer(task_app, name="task")

label_app = typer.Typer(help="Manage global task labels")
app.add_typer(label_app, name="label")

murli.enable(app)   # ← add this line

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
def init():
    """Initialize/Reset the database and config"""
    try:
        db_ops.reset_db()
        dir_path = db_ops.get_storage_dir()
        typer.echo(f"Initialized/Reset murli-work database with sample data and configuration in {dir_path}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@task_app.command(name="create")
def task_create(
    title: str = typer.Argument(..., help="Task title"),
    desc: Optional[str] = typer.Option(None, "--desc", "-d", help="Task description"),
    priority: Optional[Priority] = typer.Option(None, "--priority", "-p", help="Task priority"),
    labels: Optional[str] = typer.Option(None, "--labels", "-l", help="Comma-separated labels"),
):
    """Create a new task"""
    try:
        db = db_ops.load_db()
        labels_list = labels.split(",") if labels else []
        prio_val = priority.value if priority else None
        new_id = db_ops.create_task(db, title, desc, prio_val, labels_list)
        typer.echo(f"Task {new_id} (\"{title}\") created successfully.")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=2 if isinstance(e, ValueError) else 1)

@task_app.command(name="list")
def task_list(
    status: Optional[Status] = typer.Option(None, "--status", "-s", help="Filter by status"),
    priority: Optional[Priority] = typer.Option(None, "--priority", "-p", help="Filter by priority"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="Filter by label"),
    output: OutputFmt = typer.Option(OutputFmt.table, "--output", "-o", help="Output format"),
):
    """List stored tasks"""
    try:
        db = db_ops.load_db()
        cfg = db_ops.load_config()
        
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
            
        if output_fmt == "json":
            format_ops.print_tasks_json(filtered)
        elif output_fmt == "csv":
            format_ops.print_tasks_csv(filtered)
        else:
            format_ops.print_tasks_table(filtered)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@task_app.command(name="update")
def task_update(
    id: int = typer.Argument(..., help="Task ID"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="New title"),
    desc: Optional[str] = typer.Option(None, "--desc", "-d", help="New description"),
    priority: Optional[Priority] = typer.Option(None, "--priority", "-p", help="New priority"),
    status: Optional[Status] = typer.Option(None, "--status", "-s", help="New status"),
    labels: Optional[str] = typer.Option(None, "--labels", "-l", help="Replacement labels"),
):
    """Update an existing task's fields"""
    try:
        db = db_ops.load_db()
        
        prio_val = priority.value if priority else None
        status_val = status.value if status else None
        labels_list = labels.split(",") if labels is not None else None
        
        db_ops.update_task(db, id, title, desc, prio_val, status_val, labels_list)
        typer.echo(f"Task {id} updated successfully.")
    except KeyError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=2 if isinstance(e, ValueError) else 1)

@task_app.command(name="delete")
def task_delete(
    id: int = typer.Argument(..., help="Task ID"),
    force: bool = typer.Option(False, "--force", help="Force delete without warning"),
):
    """Delete a task"""
    try:
        db = db_ops.load_db()
        db_ops.delete_task(db, id)
        typer.echo(f"Task {id} deleted successfully.")
    except KeyError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@label_app.command(name="list")
def label_list():
    """List all defined labels"""
    try:
        db = db_ops.load_db()
        format_ops.print_labels_table(db)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@label_app.command(name="create")
def label_create(name: str = typer.Argument(..., help="Label name")):
    """Create a custom label"""
    try:
        db = db_ops.load_db()
        slug = db_ops.create_label(db, name)
        typer.echo(f"Label \"{slug}\" created successfully.")
    except FileExistsError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@label_app.command(name="delete")
def label_delete(name: str = typer.Argument(..., help="Label name")):
    """Delete a label"""
    try:
        db = db_ops.load_db()
        db_ops.delete_label(db, name)
        typer.echo(f"Label \"{name}\" deleted successfully.")
    except KeyError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def report():
    """Display progress report"""
    try:
        db = db_ops.load_db()
        format_ops.print_sprint_report(db)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
