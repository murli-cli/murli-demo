import argparse
import sys
import os
import murli
from murli import AgentError, Metadata, ReturnSchema, Example

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

    # ── Annotations (Step 3) ──────────────────────────────────────────────────
    murli.annotate(init_parser, Metadata(
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
    ))

    murli.annotate(task_update, Metadata(
        agent_description="Updates one or more fields on an existing task. Omitted flags are unchanged.",
        when_to_use="Changing status, priority, or labels on a task.",
        mutating=True,
        idempotent=True,
        returns=ReturnSchema(description="Updated task ID", type="object", properties={"id": "int"}),
        examples=[Example(command="murli-work task update 3 --status done")],
    ))

    murli.annotate(task_delete, Metadata(
        agent_description="Permanently removes a task by ID.",
        when_to_use="Removing a cancelled or obsolete task from the backlog.",
        mutating=True,
        idempotent=False,
        destructive=True,
        returns=ReturnSchema(description="Deleted task ID", type="object", properties={"id": "int"}),
    ))

    murli.annotate(label_list, Metadata(
        agent_description="Lists all labels defined in the database with task counts.",
        when_to_use="Discovering available labels before creating or filtering tasks.",
        mutating=False,
        idempotent=True,
        returns=ReturnSchema(description="Label array", type="object", properties={"labels": "array"}),
    ))

    murli.annotate(label_create, Metadata(
        agent_description="Creates a new label slug. Fails with conflict if it already exists.",
        when_to_use="Adding a label category before tagging tasks with it.",
        mutating=True,
        idempotent=False,
        returns=ReturnSchema(description="Created label slug", type="object", properties={"slug": "string"}),
    ))

    murli.annotate(label_delete, Metadata(
        agent_description="Deletes a label and removes it from all tasks.",
        when_to_use="Cleaning up unused or misnamed labels.",
        mutating=True,
        idempotent=False,
        destructive=True,
        returns=ReturnSchema(description="Deleted label name", type="object", properties={"name": "string"}),
    ))

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
    # ─────────────────────────────────────────────────────────────────────────

    murli.enable(parser)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args, writer = murli.parse(parser)

    if args.command == "init":
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
                return
            except Exception as e:
                writer.write_error(AgentError.tool_error(str(e)))
                return
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
                return
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
                return
            except ValueError as e:
                writer.write_error(AgentError.user_error(str(e), "Use --priority low|medium|high, --status todo|doing|done."))
                return
            except Exception as e:
                writer.write_error(AgentError.tool_error(str(e)))
                return
            writer.write_success(f"Task {args.id} updated successfully.", {"id": args.id})

        elif args.task_command == "delete":
            try:
                db = db_ops.load_db()
                db_ops.delete_task(db, args.id)
            except KeyError as e:
                writer.write_error(AgentError.not_found(str(e), "Use task list to see valid IDs."))
                return
            except Exception as e:
                writer.write_error(AgentError.tool_error(str(e)))
                return
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
                return
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
                return
            except ValueError as e:
                writer.write_error(AgentError.user_error(str(e)))
                return
            except Exception as e:
                writer.write_error(AgentError.tool_error(str(e)))
                return
            writer.write_success(f'Label "{slug}" created successfully.', {"slug": slug})

        elif args.label_command == "delete":
            try:
                db = db_ops.load_db()
                db_ops.delete_label(db, args.name)
            except KeyError as e:
                writer.write_error(AgentError.not_found(str(e), "Use label list to see valid labels."))
                return
            except Exception as e:
                writer.write_error(AgentError.tool_error(str(e)))
                return
            writer.write_success(f'Label "{args.name}" deleted successfully.', {"name": args.name})

    elif args.command == "report":
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

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
