import click
import sys
import os

# Add sibling folder path to imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import shared.db as db_ops
import shared.format as format_ops

@click.group()
def cli():
    """murli-work - A sprint and project task tracker"""
    pass

@cli.command()
def init():
    """Initialize/Reset the database and config"""
    try:
        db_ops.reset_db()
        dir_path = db_ops.get_storage_dir()
        click.echo(f"Initialized/Reset murli-work database with sample data and configuration in {dir_path}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@cli.group()
def task():
    """Manage sprint tasks"""
    pass

@task.command(name="create")
@click.argument("title")
@click.option("--desc", "-d", help="Task description")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Task priority")
@click.option("--labels", "-l", help="Comma-separated labels")
def task_create(title, desc, priority, labels):
    """Create a new task"""
    try:
        db = db_ops.load_db()
        labels_list = labels.split(",") if labels else []
        new_id = db_ops.create_task(db, title, desc, priority, labels_list)
        click.echo(f"Task {new_id} (\"{title}\") created successfully.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2 if isinstance(e, ValueError) else 1)

@task.command(name="list")
@click.option("--status", "-s", type=click.Choice(["todo", "doing", "done"]), help="Filter by status")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="Filter by priority")
@click.option("--label", "-l", help="Filter by label")
@click.option("--output", "-o", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
def task_list(status, priority, label, output):
    """List stored tasks"""
    try:
        db = db_ops.load_db()
        cfg = db_ops.load_config()
        
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
            
        if output_fmt == "json":
            format_ops.print_tasks_json(filtered)
        elif output_fmt == "csv":
            format_ops.print_tasks_csv(filtered)
        else:
            format_ops.print_tasks_table(filtered)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@task.command(name="update")
@click.argument("id", type=int)
@click.option("--title", "-t", help="New title")
@click.option("--desc", "-d", help="New description")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high"]), help="New priority")
@click.option("--status", "-s", type=click.Choice(["todo", "doing", "done"]), help="New status")
@click.option("--labels", "-l", help="Replacement labels")
@click.pass_context
def task_update(ctx, id, title, desc, priority, status, labels):
    """Update an existing task's fields"""
    try:
        db = db_ops.load_db()
        
        # In Click, optional arguments can be checked using the parameter parameters
        # However, to only update if flags are explicitly provided on cli:
        # Click stores this in ctx.params
        title_val = title if ctx.params.get("title") is not None else None
        desc_val = desc if ctx.params.get("desc") is not None else None
        priority_val = priority if ctx.params.get("priority") is not None else None
        status_val = status if ctx.params.get("status") is not None else None
        
        labels_list = None
        if ctx.params.get("labels") is not None:
            labels_list = labels.split(",") if labels else []
            
        db_ops.update_task(db, id, title_val, desc_val, priority_val, status_val, labels_list)
        click.echo(f"Task {id} updated successfully.")
    except KeyError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2 if isinstance(e, ValueError) else 1)

@task.command(name="delete")
@click.argument("id", type=int)
@click.option("--force", is_flag=True, help="Force delete without warning")
def task_delete(id, force):
    """Delete a task"""
    try:
        db = db_ops.load_db()
        db_ops.delete_task(db, id)
        click.echo(f"Task {id} deleted successfully.")
    except KeyError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@cli.group()
def label():
    """Manage global task labels"""
    pass

@label.command(name="list")
def label_list():
    """List all defined labels"""
    try:
        db = db_ops.load_db()
        format_ops.print_labels_table(db)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@label.command(name="create")
@click.argument("name")
def label_create(name):
    """Create a custom label"""
    try:
        db = db_ops.load_db()
        slug = db_ops.create_label(db, name)
        click.echo(f"Label \"{slug}\" created successfully.")
    except FileExistsError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@label.command(name="delete")
@click.argument("name")
def label_delete(name):
    """Delete a label"""
    try:
        db = db_ops.load_db()
        db_ops.delete_label(db, name)
        click.echo(f"Label \"{name}\" deleted successfully.")
    except KeyError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@cli.command()
def report():
    """Display progress report"""
    try:
        db = db_ops.load_db()
        format_ops.print_sprint_report(db)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    cli()
