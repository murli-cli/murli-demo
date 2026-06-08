import { run, newWriter, annotate } from "@murli-cli/commander";
import { AgentError, newToolError, newUserError, setToolVersion } from "@murli-cli/core";
import { Command } from "commander";
import * as dbOps from "./shared/db";
import * as formatOps from "./shared/format";

setToolVersion("0.1.0");

// The murli-work spec gives `task list` an app-level content format flag
// (--output table|json|csv). Murli auto-injects its own --output (json|ndjson|text)
// and validates it. To avoid a collision, pre-process the app's content formats:
// rewrite csv/table to murli's `text` and stash the original in an env var that the
// list handler reads back. (json/ndjson/text pass straight through to murli.)
function preprocessOutputFormat(argv: string[]): void {
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--output" || arg === "-o") {
      const val = argv[i + 1];
      if (val === "csv" || val === "table") {
        argv[i + 1] = "text";
        process.env.MURLI_WORK_FORMAT = val;
      }
    } else if (arg.startsWith("--output=")) {
      const val = arg.slice("--output=".length);
      if (val === "csv" || val === "table") {
        argv[i] = "--output=text";
        process.env.MURLI_WORK_FORMAT = val;
      }
    } else if (arg.startsWith("-o=")) {
      const val = arg.slice("-o=".length);
      if (val === "csv" || val === "table") {
        argv[i] = "-o=text";
        process.env.MURLI_WORK_FORMAT = val;
      }
    }
  }
}

function errMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

// The shared db layer throws plain Error with human messages, so this is the single
// place that maps those messages onto murli's structured error taxonomy. Centralizing
// it keeps the exit-code/error-type choices consistent across every mutation handler.
function classifyDbError(err: unknown): AgentError {
  const message = errMessage(err);
  if (message.includes("not found")) {
    return new AgentError({ code: 1, error: "not_found", message, recoverable: false });
  }
  if (message.includes("priority") || message.includes("status")) {
    return new AgentError({ code: 2, error: "validation_error", message, recoverable: false });
  }
  return newToolError(message);
}

// Load the database or emit a structured tool error and signal the caller to bail.
// The TS-idiomatic equivalent of the reference demo's repeated `if err != nil` guard.
function loadOrFail(w: ReturnType<typeof newWriter>): dbOps.Database | undefined {
  try {
    return dbOps.loadDb();
  } catch (err) {
    w.writeError(newToolError(errMessage(err)));
    return undefined;
  }
}

// Resolve the positional id and database for the id-taking commands (update, delete),
// or emit the matching error and signal the caller to bail.
function resolveIdAndDb(
  w: ReturnType<typeof newWriter>,
  idStr: string,
): { id: number; db: dbOps.Database } | undefined {
  const id = Number.parseInt(idStr, 10);
  if (Number.isNaN(id)) {
    w.writeError(
      new AgentError({ code: 2, error: "validation_error", message: `invalid task ID: ${idStr}`, recoverable: false }),
    );
    return undefined;
  }
  const db = loadOrFail(w);
  if (!db) return undefined;
  return { id, db };
}

preprocessOutputFormat(process.argv);

const program = new Command();
program.name("murli-work").description("murli-work is a sprint and project task tracker").version("0.1.0");

// init
const initCmd = program
  .command("init")
  .description("Initialize/Reset the database and config")
  .action(() => {
    const w = newWriter(initCmd);
    try {
      dbOps.resetDb();
      const dir = dbOps.getStorageDir();
      w.writeSuccess(
        `Initialized/Reset murli-work database with sample data and configuration in ${dir}`,
        { status: "ok", directory: dir },
      );
    } catch (err) {
      w.writeError(newUserError(errMessage(err), "Could not reset the database."));
    }
  });
annotate(initCmd, {
  idempotent: true,
  mutating: true,
  agentDescription: "Initialize or reset the murli-work database with sample data.",
});

// task group
const taskCmd = new Command("task").description("Manage sprint tasks");

const taskCreate = taskCmd
  .command("create <title>")
  .description("Create a new task")
  .option("-d, --desc <description>", "Task description", "")
  .option("-p, --priority <priority>", "Task priority (low|medium|high)")
  .option("-l, --labels <labels>", "Comma-separated labels")
  .action((title: string, options: { desc: string; priority?: string; labels?: string }) => {
    const w = newWriter(taskCreate);
    const db = loadOrFail(w);
    if (!db) return;
    const labelsList = options.labels ? options.labels.split(",") : [];
    try {
      const id = dbOps.createTask(db, title, options.desc, options.priority, labelsList);
      w.writeSuccess(`Task ${id} ("${title}") created successfully.`, { id, title });
    } catch (err) {
      w.writeError(classifyDbError(err));
    }
  });
annotate(taskCreate, {
  mutating: true,
  agentDescription: "Create a new task in the database.",
  arguments: [{ name: "title", type: "string", required: true, description: "Task title" }],
  flagAnnotations: { priority: { enum: ["low", "medium", "high"] } },
});

const taskList = taskCmd
  .command("list")
  .description("List stored tasks")
  .option("-s, --status <status>", "Filter by status (todo|doing|done)")
  .option("-p, --priority <priority>", "Filter by priority (low|medium|high)")
  .option("-l, --label <label>", "Filter by label")
  // No app-level --output here: murli injects --output (json|ndjson|text). The
  // human content format (table|csv|json) is recovered from MURLI_WORK_FORMAT.
  .action((options: { status?: string; priority?: string; label?: string }) => {
    const w = newWriter(taskList);
    const db = loadOrFail(w);
    if (!db) return;

    let filtered = db.tasks;
    if (options.status) {
      filtered = filtered.filter((t) => t.status.toLowerCase() === options.status?.toLowerCase());
    }
    if (options.priority) {
      filtered = filtered.filter((t) => t.priority.toLowerCase() === options.priority?.toLowerCase());
    }
    if (options.label) {
      filtered = filtered.filter((t) => t.labels.some((l) => l.toLowerCase() === options.label?.toLowerCase()));
    }

    // Agent / piped: structured JSON envelope (the result is the task array).
    if (!w.isTTY()) {
      w.writeSuccess("List of sprint tasks", filtered);
      return;
    }

    // Human TTY: render the content format the user (or config) asked for.
    let fmt = process.env.MURLI_WORK_FORMAT ?? "table";
    if (fmt === "table") {
      try {
        const cfg = dbOps.loadConfig();
        if (cfg?.default_output) fmt = cfg.default_output;
      } catch {
        // fall back to the table default
      }
    }
    switch (fmt.toLowerCase()) {
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
  });
annotate(taskList, {
  idempotent: true,
  agentDescription: "List stored sprint tasks with optional status/priority/label filters.",
  flagAnnotations: {
    status: { enum: ["todo", "doing", "done"] },
    priority: { enum: ["low", "medium", "high"] },
  },
});

const taskUpdate = taskCmd
  .command("update <id>")
  .description("Update an existing task's fields")
  .option("-t, --title <title>", "New title")
  .option("-d, --desc <description>", "New description")
  .option("-p, --priority <priority>", "New priority")
  .option("-s, --status <status>", "New status")
  .option("-l, --labels <labels>", "Replacement labels")
  .action(
    (
      idStr: string,
      options: { title?: string; desc?: string; priority?: string; status?: string; labels?: string },
    ) => {
      const w = newWriter(taskUpdate);
      const resolved = resolveIdAndDb(w, idStr);
      if (!resolved) return;
      const { id, db } = resolved;
      const labelsList = options.labels !== undefined ? options.labels.split(",").filter(Boolean) : undefined;
      try {
        dbOps.updateTask(db, id, options.title, options.desc, options.priority, options.status, labelsList);
        w.writeSuccess(`Task ${id} updated successfully.`, { id });
      } catch (err) {
        w.writeError(classifyDbError(err));
      }
    },
  );
annotate(taskUpdate, {
  mutating: true,
  agentDescription: "Update fields of an existing task.",
  arguments: [{ name: "id", type: "integer", required: true, description: "ID of task to update" }],
  flagAnnotations: {
    priority: { enum: ["low", "medium", "high"] },
    status: { enum: ["todo", "doing", "done"] },
  },
});

const taskDelete = taskCmd
  .command("delete <id>")
  .description("Delete a task")
  .action((idStr: string) => {
    const w = newWriter(taskDelete);
    const resolved = resolveIdAndDb(w, idStr);
    if (!resolved) return;
    const { id, db } = resolved;
    if (w.isDryRun()) {
      w.writePlan(`Would delete task ${id} (no changes made)`, { would_delete: id });
      return;
    }
    try {
      dbOps.deleteTask(db, id);
      w.writeSuccess(`Task ${id} deleted successfully.`, { id });
    } catch (err) {
      w.writeError(classifyDbError(err));
    }
  });
annotate(taskDelete, {
  mutating: true,
  destructive: true,
  dryRunnable: true,
  agentDescription: "Delete a task by ID.",
  arguments: [{ name: "id", type: "integer", required: true, description: "ID of task to delete" }],
});

program.addCommand(taskCmd);

// label group
const labelCmd = new Command("label").description("Manage global task labels");

const labelList = labelCmd
  .command("list")
  .description("List all defined labels")
  .action(() => {
    const w = newWriter(labelList);
    const db = loadOrFail(w);
    if (!db) return;
    if (!w.isTTY()) {
      const rows = db.labels.map((l) => ({
        name: l.name,
        count: db.tasks.filter((t) => t.labels.includes(l.name)).length,
      }));
      w.writeSuccess("List of labels", rows);
      return;
    }
    formatOps.printLabelsTable(db);
  });
annotate(labelList, { idempotent: true, agentDescription: "List labels with their task counts." });

const labelCreate = labelCmd
  .command("create <name>")
  .description("Create a custom label")
  .action((name: string) => {
    const w = newWriter(labelCreate);
    const db = loadOrFail(w);
    if (!db) return;
    try {
      const slug = dbOps.createLabel(db, name);
      w.writeSuccess(`Label "${slug}" created successfully.`, { label: slug });
    } catch (err) {
      w.writeError(new AgentError({ code: 1, error: "conflict", message: errMessage(err), recoverable: false }));
    }
  });
annotate(labelCreate, {
  mutating: true,
  agentDescription: "Create a new label.",
  arguments: [{ name: "name", type: "string", required: true, description: "Label name" }],
});

const labelDelete = labelCmd
  .command("delete <name>")
  .description("Delete a label")
  .action((name: string) => {
    const w = newWriter(labelDelete);
    const db = loadOrFail(w);
    if (!db) return;
    try {
      dbOps.deleteLabel(db, name);
      w.writeSuccess(`Label "${name}" deleted successfully.`, { label: name });
    } catch (err) {
      w.writeError(classifyDbError(err));
    }
  });
annotate(labelDelete, {
  mutating: true,
  destructive: true,
  agentDescription: "Delete a label.",
  arguments: [{ name: "name", type: "string", required: true, description: "Label name to delete" }],
});

program.addCommand(labelCmd);

// report
const reportCmd = program
  .command("report")
  .description("Display progress report")
  .action(() => {
    const w = newWriter(reportCmd);
    const db = loadOrFail(w);
    if (!db) return;
    if (!w.isTTY()) {
      const statusBreakdown = { todo: 0, doing: 0, done: 0 };
      const priorityBreakdown = { high: 0, medium: 0, low: 0 };
      let completed = 0;
      for (const t of db.tasks) {
        statusBreakdown[t.status] += 1;
        priorityBreakdown[t.priority] += 1;
        if (t.status === "done") completed += 1;
      }
      const total = db.tasks.length;
      w.writeSuccess("Sprint progress report", {
        total_tasks: total,
        completed_tasks: completed,
        percent_complete: total > 0 ? (completed * 100) / total : 0,
        status_breakdown: statusBreakdown,
        priority_breakdown: priorityBreakdown,
      });
      return;
    }
    formatOps.printSprintReport(db);
  });
annotate(reportCmd, {
  idempotent: true,
  agentDescription: "Summarize sprint task completion and status/priority breakdowns.",
});

// Replaces `program.parse(process.argv)`. murli wires dual-audience output,
// describe/--schema introspection, the mutation guard, and structured errors.
run(program, process.argv);
