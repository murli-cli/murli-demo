import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import * as dbOps from "./shared/db";
import * as formatOps from "./shared/format";

yargs(hideBin(process.argv))
  .scriptName("murli-work")
  .usage("$0 <cmd> [args]")
  // Init command
  .command(
    "init",
    "Initialize/Reset the database and config",
    () => {},
    () => {
      try {
        dbOps.resetDb();
        const dir = dbOps.getStorageDir();
        console.log(`Initialized/Reset murli-work database with sample data and configuration in ${dir}`);
      } catch (err: any) {
        console.error(`Error: ${err.message}`);
        process.exit(1);
      }
    }
  )
  // Task command subgroup
  .command(
    "task <action>",
    "Manage sprint tasks",
    (yargs) => {
      return yargs
        .command(
          "create <title>",
          "Create a new task",
          (y) => {
            return y
              .positional("title", { type: "string", describe: "Task title" })
              .option("desc", { alias: "d", type: "string", describe: "Task description", default: "" })
              .option("priority", { alias: "p", type: "string", choices: ["low", "medium", "high"], describe: "Task priority" })
              .option("labels", { alias: "l", type: "string", describe: "Comma-separated labels" });
          },
          (argv) => {
            try {
              const db = dbOps.loadDb();
              const labelsList = argv.labels ? (argv.labels as string).split(",") : [];
              const id = dbOps.createTask(db, argv.title as string, argv.desc as string, argv.priority as string, labelsList);
              console.log(`Task %d ("%s") created successfully.`, id, argv.title);
            } catch (err: any) {
              console.error(`Error: ${err.message}`);
              process.exit(err.message.includes("priority") ? 2 : 1);
            }
          }
        )
        .command(
          "list",
          "List stored tasks",
          (y) => {
            return y
              .option("status", { alias: "s", type: "string", choices: ["todo", "doing", "done"], describe: "Filter by status" })
              .option("priority", { alias: "p", type: "string", choices: ["low", "medium", "high"], describe: "Filter by priority" })
              .option("label", { alias: "l", type: "string", describe: "Filter by label" })
              .option("output", { alias: "o", type: "string", choices: ["table", "json", "csv"], default: "table", describe: "Output format" });
          },
          (argv) => {
            try {
              const db = dbOps.loadDb();
              const cfg = dbOps.loadConfig();

              let outputFmt = argv.output as string;
              if (outputFmt === "table" && cfg && cfg.default_output) {
                outputFmt = cfg.default_output;
              }

              let filtered = db.tasks;
              if (argv.status) {
                filtered = filtered.filter((t) => t.status.toLowerCase() === (argv.status as string).toLowerCase());
              }
              if (argv.priority) {
                filtered = filtered.filter((t) => t.priority.toLowerCase() === (argv.priority as string).toLowerCase());
              }
              if (argv.label) {
                filtered = filtered.filter((t) => t.labels.some((l) => l.toLowerCase() === (argv.label as string).toLowerCase()));
              }

              switch (outputFmt.toLowerCase()) {
                case "json":
                  formatOps.printTasksJSON(filtered);
                  break;
                case "csv":
                  formatOps.printTasksCSV(filtered);
                  break;
                default:
                  formatOps.printTasksTable(filtered);
                  break;
              }
            } catch (err: any) {
              console.error(`Error: ${err.message}`);
              process.exit(1);
            }
          }
        )
        .command(
          "update <id>",
          "Update an existing task's fields",
          (y) => {
            return y
              .positional("id", { type: "number", describe: "Task ID" })
              .option("title", { alias: "t", type: "string", describe: "New title" })
              .option("desc", { alias: "d", type: "string", describe: "New description" })
              .option("priority", { alias: "p", type: "string", choices: ["low", "medium", "high"], describe: "New priority" })
              .option("status", { alias: "s", type: "string", choices: ["todo", "doing", "done"], describe: "New status" })
              .option("labels", { alias: "l", type: "string", describe: "Replacement labels" });
          },
          (argv) => {
            try {
              const id = parseInt(argv.id as any, 10);
              if (isNaN(id)) {
                throw new Error(`invalid task ID: ${argv.id}`);
              }

              const db = dbOps.loadDb();

              const titleVal = argv.title !== undefined ? (argv.title as string) : undefined;
              const descVal = argv.desc !== undefined ? (argv.desc as string) : undefined;
              const priorityVal = argv.priority !== undefined ? (argv.priority as string) : undefined;
              const statusVal = argv.status !== undefined ? (argv.status as string) : undefined;
              
              let labelsList: string[] | undefined = undefined;
              if (argv.labels !== undefined) {
                labelsList = argv.labels ? (argv.labels as string).split(",") : [];
              }

              dbOps.updateTask(db, id, titleVal, descVal, priorityVal, statusVal, labelsList);
              console.log(`Task %d updated successfully.`, id);
            } catch (err: any) {
              console.error(`Error: ${err.message}`);
              process.exit(err.message.includes("not found") ? 1 : (err.message.includes("priority") || err.message.includes("status") ? 2 : 1));
            }
          }
        )
        .command(
          "delete <id>",
          "Delete a task",
          (y) => {
            return y
              .positional("id", { type: "number", describe: "Task ID" })
              .option("force", { type: "boolean", describe: "Force delete without warning" });
          },
          (argv) => {
            try {
              const id = parseInt(argv.id as any, 10);
              if (isNaN(id)) {
                throw new Error(`invalid task ID: ${argv.id}`);
              }

              const db = dbOps.loadDb();
              dbOps.deleteTask(db, id);
              console.log(`Task %d deleted successfully.`, id);
            } catch (err: any) {
              console.error(`Error: ${err.message}`);
              process.exit(1);
            }
          }
        )
        .demandCommand(1, "You must provide a valid task action.");
    }
  )
  // Label command subgroup
  .command(
    "label <action>",
    "Manage global task labels",
    (yargs) => {
      return yargs
        .command(
          "list",
          "List all defined labels",
          () => {},
          () => {
            try {
              const db = dbOps.loadDb();
              formatOps.printLabelsTable(db);
            } catch (err: any) {
              console.error(`Error: ${err.message}`);
              process.exit(1);
            }
          }
        )
        .command(
          "create <name>",
          "Create a custom label",
          (y) => {
            return y.positional("name", { type: "string", describe: "Label name" });
          },
          (argv) => {
            try {
              const db = dbOps.loadDb();
              const slug = dbOps.createLabel(db, argv.name as string);
              console.log(`Label "%s" created successfully.`, slug);
            } catch (err: any) {
              console.error(`Error: ${err.message}`);
              process.exit(1);
            }
          }
        )
        .command(
          "delete <name>",
          "Delete a label",
          (y) => {
            return y.positional("name", { type: "string", describe: "Label name" });
          },
          (argv) => {
            try {
              const db = dbOps.loadDb();
              dbOps.deleteLabel(db, argv.name as string);
              console.log(`Label "%s" deleted successfully.`, argv.name);
            } catch (err: any) {
              console.error(`Error: ${err.message}`);
              process.exit(1);
            }
          }
        )
        .demandCommand(1, "You must provide a valid label action.");
    }
  )
  // Report command
  .command(
    "report",
    "Display progress report",
    () => {},
    () => {
      try {
        const db = dbOps.loadDb();
        formatOps.printSprintReport(db);
      } catch (err: any) {
        console.error(`Error: ${err.message}`);
        process.exit(1);
      }
    }
  )
  .demandCommand(1, "You must specify a command.")
  .strict()
  .help()
  .alias("h", "help")
  .parse();
