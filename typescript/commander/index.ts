import { Command } from "commander";
import * as dbOps from "./shared/db";
import * as formatOps from "./shared/format";

const program = new Command();

program
  .name("murli-work")
  .description("murli-work - A sprint and project task tracker")
  .version("0.1.0");

// Init command
program
  .command("init")
  .description("Initialize/Reset the database and config")
  .action(() => {
    try {
      dbOps.resetDb();
      const dir = dbOps.getStorageDir();
      console.log(`Initialized/Reset murli-work database with sample data and configuration in ${dir}`);
    } catch (err: any) {
      console.error(`Error: ${err.message}`);
      process.exit(1);
    }
  });

// Task command and its subcommands
const taskCmd = new Command("task").description("Manage sprint tasks");

taskCmd
  .command("create <title>")
  .description("Create a new task")
  .option("-d, --desc <description>", "Task description", "")
  .option("-p, --priority <priority>", "Task priority (low|medium|high)")
  .option("-l, --labels <labels>", "Comma-separated labels")
  .action((title, options) => {
    try {
      const db = dbOps.loadDb();
      const labelsList = options.labels ? options.labels.split(",") : [];
      const id = dbOps.createTask(db, title, options.desc, options.priority, labelsList);
      console.log(`Task %d ("%s") created successfully.`, id, title);
    } catch (err: any) {
      console.error(`Error: ${err.message}`);
      process.exit(err.message.includes("priority") ? 2 : 1);
    }
  });

taskCmd
  .command("list")
  .description("List stored tasks")
  .option("-s, --status <status>", "Filter by status (todo|doing|done)")
  .option("-p, --priority <priority>", "Filter by priority (low|medium|high)")
  .option("-l, --label <label>", "Filter by label")
  .option("-o, --output <output>", "Output format (table|json|csv)", "table")
  .action((options) => {
    try {
      const db = dbOps.loadDb();
      const cfg = dbOps.loadConfig();

      let outputFmt = options.output;
      if (outputFmt === "table" && cfg && cfg.default_output) {
        outputFmt = cfg.default_output;
      }

      let filtered = db.tasks;
      if (options.status) {
        filtered = filtered.filter((t) => t.status.toLowerCase() === options.status.toLowerCase());
      }
      if (options.priority) {
        filtered = filtered.filter((t) => t.priority.toLowerCase() === options.priority.toLowerCase());
      }
      if (options.label) {
        filtered = filtered.filter((t) => t.labels.some((l) => l.toLowerCase() === options.label.toLowerCase()));
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
  });

taskCmd
  .command("update <id>")
  .description("Update an existing task's fields")
  .option("-t, --title <title>", "New title")
  .option("-d, --desc <description>", "New description")
  .option("-p, --priority <priority>", "New priority")
  .option("-s, --status <status>", "New status")
  .option("-l, --labels <labels>", "Replacement labels")
  .action((idStr, options, cmd) => {
    try {
      const id = parseInt(idStr, 10);
      if (isNaN(id)) {
        throw new Error(`invalid task ID: ${idStr}`);
      }

      const db = dbOps.loadDb();

      // Check if option was explicitly provided by using command raw checks or options presence
      const titleVal = cmd.opts().title !== undefined ? options.title : undefined;
      const descVal = cmd.opts().desc !== undefined ? options.desc : undefined;
      const priorityVal = cmd.opts().priority !== undefined ? options.priority : undefined;
      const statusVal = cmd.opts().status !== undefined ? options.status : undefined;
      
      let labelsList: string[] | undefined = undefined;
      if (cmd.opts().labels !== undefined) {
        labelsList = options.labels ? options.labels.split(",") : [];
      }

      dbOps.updateTask(db, id, titleVal, descVal, priorityVal, statusVal, labelsList);
      console.log(`Task %d updated successfully.`, id);
    } catch (err: any) {
      console.error(`Error: ${err.message}`);
      process.exit(err.message.includes("not found") ? 1 : (err.message.includes("priority") || err.message.includes("status") ? 2 : 1));
    }
  });

taskCmd
  .command("delete <id>")
  .description("Delete a task")
  .option("--force", "Force delete without warning")
  .action((idStr) => {
    try {
      const id = parseInt(idStr, 10);
      if (isNaN(id)) {
        throw new Error(`invalid task ID: ${idStr}`);
      }

      const db = dbOps.loadDb();
      dbOps.deleteTask(db, id);
      console.log(`Task %d deleted successfully.`, id);
    } catch (err: any) {
      console.error(`Error: ${err.message}`);
      process.exit(1);
    }
  });

program.addCommand(taskCmd);

// Label command and its subcommands
const labelCmd = new Command("label").description("Manage global task labels");

labelCmd
  .command("list")
  .description("List all defined labels")
  .action(() => {
    try {
      const db = dbOps.loadDb();
      formatOps.printLabelsTable(db);
    } catch (err: any) {
      console.error(`Error: ${err.message}`);
      process.exit(1);
    }
  });

labelCmd
  .command("create <name>")
  .description("Create a custom label")
  .action((name) => {
    try {
      const db = dbOps.loadDb();
      const slug = dbOps.createLabel(db, name);
      console.log(`Label "%s" created successfully.`, slug);
    } catch (err: any) {
      console.error(`Error: ${err.message}`);
      process.exit(1);
    }
  });

labelCmd
  .command("delete <name>")
  .description("Delete a label")
  .action((name) => {
    try {
      const db = dbOps.loadDb();
      dbOps.deleteLabel(db, name);
      console.log(`Label "%s" deleted successfully.`, name);
    } catch (err: any) {
      console.error(`Error: ${err.message}`);
      process.exit(1);
    }
  });

program.addCommand(labelCmd);

// Report command
program
  .command("report")
  .description("Display progress report")
  .action(() => {
    try {
      const db = dbOps.loadDb();
      formatOps.printSprintReport(db);
    } catch (err: any) {
      console.error(`Error: ${err.message}`);
      process.exit(1);
    }
  });

try {
  program.parse(process.argv);
} catch (err) {
  process.exit(2);
}
