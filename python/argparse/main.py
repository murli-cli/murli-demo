import argparse
import sys
import os
import murli

# Add sibling folder path to imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import shared.db as db_ops
import shared.format as format_ops

def main():
    parser = argparse.ArgumentParser(prog="murli-work", description="murli-work - A sprint and project task tracker")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize/Reset the database and config")

    # task command and its subparsers
    task_parser = subparsers.add_parser("task", help="Manage sprint tasks")
    task_subparsers = task_parser.add_subparsers(dest="task_command", help="Task subcommands")

    # task create
    task_create = task_subparsers.add_parser("create", help="Create a new task")
    task_create.add_argument("title", help="Task title")
    task_create.add_argument("--desc", "-d", help="Task description")
    task_create.add_argument("--priority", "-p", choices=["low", "medium", "high"], help="Task priority")
    task_create.add_argument("--labels", "-l", help="Comma-separated labels")

    # task list
    task_list = task_subparsers.add_parser("list", help="List stored tasks")
    task_list.add_argument("--status", "-s", choices=["todo", "doing", "done"], help="Filter by status")
    task_list.add_argument("--priority", "-p", choices=["low", "medium", "high"], help="Filter by priority")
    task_list.add_argument("--label", "-l", help="Filter by label")
    task_list.add_argument("--output", "-o", choices=["table", "json", "csv"], default="table", help="Output format")

    # task update
    task_update = task_subparsers.add_parser("update", help="Update an existing task's fields")
    task_update.add_argument("id", type=int, help="Task ID")
    task_update.add_argument("--title", "-t", help="New title")
    task_update.add_argument("--desc", "-d", help="New description")
    task_update.add_argument("--priority", "-p", choices=["low", "medium", "high"], help="New priority")
    task_update.add_argument("--status", "-s", choices=["todo", "doing", "done"], help="New status")
    task_update.add_argument("--labels", "-l", help="Replacement labels")

    # task delete
    task_delete = task_subparsers.add_parser("delete", help="Delete a task")
    task_delete.add_argument("id", type=int, help="Task ID")
    task_delete.add_argument("--force", action="store_true", help="Force delete without warning")

    # label command and its subparsers
    label_parser = subparsers.add_parser("label", help="Manage global task labels")
    label_subparsers = label_parser.add_subparsers(dest="label_command", help="Label subcommands")

    # label list
    label_list = label_subparsers.add_parser("list", help="List all defined labels")

    # label create
    label_create = label_subparsers.add_parser("create", help="Create a custom label")
    label_create.add_argument("name", help="Label name")

    # label delete
    label_delete = label_subparsers.add_parser("delete", help="Delete a label")
    label_delete.add_argument("name", help="Label name")

    # report command
    report_parser = subparsers.add_parser("report", help="Display progress report")

    # Register murli adapter (must be after all add_subparsers() calls)
    murli.enable(parser)

    # Parse arguments
    # If no arguments passed, print help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args, writer = murli.parse(parser)

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
