# Murli Integration Guide: TypeScript with Commander

This guide explains how to systematically integrate the **Murli CLI middleware** (the TypeScript port, [`@murli-cli/commander`](https://github.com/murli-cli/murli-ts)) into a Node.js application built with the popular **[tj/commander.js](https://github.com/tj/commander.js)** CLI framework.

The wire format is identical across every murli implementation, so a task written by `murli-work` (Go/cobra) lists cleanly under this TypeScript/commander build and vice-versa.

---

## 📦 Wiring the Dependency

`murli-ts` ships two packages — `@murli-cli/core` (the framework-agnostic engine) and `@murli-cli/commander` (the commander adapter). `commander` is a peer dependency.

Once `murli-ts` is published to npm, depend on it the same way the Go demo depends on the published `murli-go` module:

```jsonc
// package.json
"dependencies": {
  "@murli-cli/commander": "^0.1.0",
  "@murli-cli/core": "^0.1.0",
  "commander": "^12.1.0"
}
```

Until then, this branch vendors pinned `0.1.0` tarballs (built from `murli-ts`) under `typescript/commander/vendor/` and references them with `file:` specifiers, so `make build-ts-commander` works with no external checkout:

```jsonc
"dependencies": {
  "@murli-cli/commander": "file:vendor/murli-cli-commander-0.1.0.tgz",
  "@murli-cli/core": "file:vendor/murli-cli-core-0.1.0.tgz",
  "commander": "^12.1.0"
}
```

---

## 🎁 What You Get for Free

By replacing Commander's standard `program.parse(process.argv)` with Murli's adapter entry point `run(program, process.argv)`, your CLI automatically inherits:

1. **Intelligent TTY Detection (Dual-Audience Output):**
   - A human in a terminal gets pretty text and formatted ASCII tables.
   - When output is piped or `--agent` is passed, Murli emits structured JSON envelopes.
2. **Auto-Injected Standard Flags:**
   - `--agent`: forces structured JSON output regardless of TTY state.
   - `--schema`: prints the JSON schema of the command and exits (positional-argument validation is bypassed).
   - `--force` / `--yes`: bypass the non-interactive mutation guard.
   - `--dry-run`: registers intent to simulate changes (read via `w.isDryRun()`).
   - `--profile <name>`: loads a named flag profile.
3. **Auto-Mounted Subcommands:**
   - `describe`: emits the recursive JSON command tree with capabilities, safety, and metadata.
   - `profile`: manage saved flag-profile collections (mounted when any flag is `profileable`).
4. **Log Deduplication:** consecutive duplicate stderr log lines collapse with a `repeated` count to conserve agent context.

---

## 🔧 What You Configure

Attach **Metadata** to commands and annotate flags *outside* the action handlers, with `annotate()`.

### 1. Attaching Command Metadata

```ts
import { annotate } from "@murli-cli/commander";

annotate(taskCreate, {
  mutating: true,
  agentDescription: "Create a new task in the database.",
  arguments: [{ name: "title", type: "string", required: true, description: "Task title" }],
});
```

### 2. Attaching Flag Annotations

Describe enums, env vars, and constraints via `flagAnnotations` — they surface in `--schema` and `describe`:

```ts
annotate(taskList, {
  idempotent: true,
  agentDescription: "List stored sprint tasks with optional filters.",
  flagAnnotations: {
    status: { enum: ["todo", "doing", "done"] },
    priority: { enum: ["low", "medium", "high"] },
  },
});
```

---

## 🔨 What You Build

Refactor each handler to use the **Writer API** for the dual-audience switch and structured errors.

### 1. Initialize the Writer

```ts
import { newWriter } from "@murli-cli/commander";
const w = newWriter(taskCreate);
```

### 2. Emit Success Results

Pass a human string first, the structured payload second. Murli routes by audience — the payload becomes the JSON `result`; the human string is shown only in TTY/text mode.

```ts
w.writeSuccess(`Task ${id} ("${title}") created successfully.`, { id, title });
```

### 3. Emit Actionable Errors

Invalid enum values are an argument/validation failure — emit `validation_error` with **exit code 2** (per the `murli-work` spec) so an agent can self-correct:

```ts
import { AgentError } from "@murli-cli/core";

w.writeError(new AgentError({
  code: 2,
  error: "validation_error",
  message: "invalid priority (low|medium|high)",
  recoverable: false,
}));
```

For dual-audience listing, branch on `w.isTTY()`: agents get the array; humans get the rendered table/CSV.

```ts
if (!w.isTTY()) {
  w.writeSuccess("List of sprint tasks", filtered);
  return;
}
formatOps.printTasksTable(filtered);
```

---

## 🚀 Step-by-Step Code Walkthrough

### Step 1: Update Imports

```ts
import { run, newWriter, annotate } from "@murli-cli/commander";
import { AgentError, newToolError, newUserError, setToolVersion } from "@murli-cli/core";
```

### Step 2: Swap the Executor

```ts
// Replace: program.parse(process.argv)
run(program, process.argv);
```

Optionally stamp a tool version onto every envelope:

```ts
setToolVersion("0.1.0");
```

### Step 3: Reconcile the `--output` flag

The `murli-work` spec gives `task list` an app-level content format (`--output table|json|csv`), while Murli auto-injects its own `--output` (`json|ndjson|text`). Drop the app-level flag from `task list` (let Murli own `--output`) and pre-process the content formats before parsing — rewriting `csv`/`table` to Murli's `text` while stashing the original in an env var the handler reads back:

```ts
function preprocessOutputFormat(argv: string[]): void {
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--output" || arg === "-o") {
      const val = argv[i + 1];
      if (val === "csv" || val === "table") {
        argv[i + 1] = "text";
        process.env.MURLI_WORK_FORMAT = val;
      }
    }
    // (also handle --output=… / -o=… forms)
  }
}
preprocessOutputFormat(process.argv);
```

### Step 4: Refactor Handlers (e.g. `init`)

```diff
 program
   .command("init")
   .description("Initialize/Reset the database and config")
-  .action(() => {
-    try {
-      dbOps.resetDb();
-      const dir = dbOps.getStorageDir();
-      console.log(`Initialized/Reset murli-work database ... in ${dir}`);
-    } catch (err) {
-      console.error(`Error: ${err.message}`);
-      process.exit(1);
-    }
-  });
+  .action(() => {
+    const w = newWriter(initCmd);
+    try {
+      dbOps.resetDb();
+      const dir = dbOps.getStorageDir();
+      w.writeSuccess(
+        `Initialized/Reset murli-work database ... in ${dir}`,
+        { status: "ok", directory: dir },
+      );
+    } catch (err) {
+      w.writeError(newUserError(String(err), "Could not reset the database."));
+    }
+  });
+annotate(initCmd, { mutating: true, agentDescription: "Initialize or reset the database." });
```

---

## 🔢 Exit Code Mapping

| Situation | murli-ts behavior | Exit code |
| :--- | :--- | :--- |
| Success | `writeSuccess` / `writePlan` | `0` |
| Invalid enum / bad argument | handler emits `validation_error` | `2` |
| Resource not found | handler emits `not_found` | `1` |
| Conflict (label exists) | handler emits `conflict` | `1` |
| DB / environment failure | `newToolError` | `2` |
| Framework flag-parse error | Murli's auto-wrapped `flag_error` | `1` |

> **Note:** Murli-ts standardizes *framework* flag-parse failures as a recoverable `flag_error` (exit `1`). The `murli-work` spec's "exit 2 for argument errors" is enforced at the **domain** layer — invalid `--priority` / `--status` enum values raise `validation_error` (exit `2`), which is the case the spec calls out explicitly. (The Go demo instead intercepts at the entry point to force exit `2` on every parse error; murli-ts keeps the framework error inside its standard taxonomy.)

---

## 🧪 Developer-Only Surface

`doctor` and naming-convention advisories are stripped by default. Enable them with the `dev` option or `MURLI_DEV=1`:

```ts
run(program, process.argv, { dev: true });
```

---

## 🖥️ Command Execution & Verification Outputs

Real, captured terminal outputs from `./bin/murli-work-ts-commander`.

### 1. Human Help (`--help`)
```text
Usage: murli-work [options] [command]

murli-work is a sprint and project task tracker

Options:
  -V, --version       output the version number
  -h, --help          display help for command

Commands:
  init [options]      Initialize/Reset the database and config
  task [options]      Manage sprint tasks
  label [options]     Manage global task labels
  report [options]    Display progress report
  describe [options]  print the full command tree as JSON
  help [command]      display help for command
```

### 2. Auto-Generated JSON Schema (`--schema`)
```json
{
  "name": "murli-work",
  "summary": "murli-work is a sprint and project task tracker",
  "idempotent": false,
  "flags": [
    { "name": "agent", "type": "bool", "default": null, "description": "force JSON agent output" },
    { "name": "output", "type": "string", "default": null, "description": "output format: json|ndjson|text" },
    { "name": "schema", "type": "bool", "default": null, "description": "print this command's JSON schema and exit" },
    { "name": "profile", "type": "string", "default": null, "description": "use a named flag profile" }
  ],
  "subcommands": [
    { "name": "init", "summary": "Initialize/Reset the database and config" },
    { "name": "task", "summary": "Manage sprint tasks" },
    { "name": "label", "summary": "Manage global task labels" },
    { "name": "report", "summary": "Display progress report" }
  ],
  "safety": { "read_only": true, "idempotent": false }
}
```

### 3. Mutating Confirmation Safeguard (`init --agent`)
Exit code `1`:
```json
{
  "code": 1,
  "error": "confirmation_required",
  "message": "This command mutates state and requires explicit confirmation.",
  "suggestion": "Pass --force or --yes to proceed without a TTY.",
  "recoverable": true,
  "schema_version": "1.0",
  "tool_version": "0.1.0"
}
```

### 4. Bypassing the Safeguard (`init --agent --force`)
```json
{
  "result": { "status": "ok", "directory": "/Users/you/Library/Application Support/murli-work" },
  "schema_version": "1.0",
  "status": "ok",
  "tool_version": "0.1.0"
}
```

### 5. Creating a Task (`task create "Verify Commander" --priority high --agent --force`)
```json
{
  "result": { "id": 6, "title": "Verify Commander" },
  "schema_version": "1.0",
  "status": "ok",
  "tool_version": "0.1.0"
}
```

### 6. Enum Validation — Exit Code 2 (`task create "Bad" --priority bogus --agent --force`)
Exit code `2`:
```json
{
  "code": 2,
  "error": "validation_error",
  "message": "invalid priority (low|medium|high)",
  "recoverable": false,
  "schema_version": "1.0",
  "tool_version": "0.1.0"
}
```

### 7. Listing Tasks in Agent Mode (`task list --agent`)
```json
{
  "result": [
    {
      "id": 1,
      "title": "Setup workspace layout",
      "desc": "Bootstrap directory structures for Go, Rust, Python and TS",
      "status": "done",
      "priority": "high",
      "labels": ["setup", "dev"],
      "created_at": "2026-05-28T18:00:00Z"
    }
  ],
  "schema_version": "1.0",
  "status": "ok",
  "tool_version": "0.1.0"
}
```

### 8. Listing Tasks for a Human (`task list --output table`)
```text
+----+----------------------+--------+----------+------------+
| ID | Title                | Status | Priority | Labels     |
+----+----------------------+--------+----------+------------+
| 1  | Setup workspace layo | DONE   | HIGH     | setup,dev  |
| 2  | Document CLI spec    | DONE   | MEDIUM   | docs       |
| 3  | Implement Cobra skel | DOING  | HIGH     | dev,go     |
| 4  | Integrate Murli midd | TODO   | HIGH     | dev,murli  |
| 5  | Write Rust Clap refe | TODO   | MEDIUM   | dev,rust   |
| 6  | Verify Commander     | TODO   | HIGH     |            |
+----+----------------------+--------+----------+------------+
```

### 9. Dry-Run Delete (`task delete 6 --agent --force --dry-run`)
```json
{
  "result": { "would_delete": 6 },
  "schema_version": "1.0",
  "status": "plan",
  "tool_version": "0.1.0"
}
```

### 10. Sprint Report in Agent Mode (`report --agent`)
```json
{
  "result": {
    "total_tasks": 6,
    "completed_tasks": 2,
    "percent_complete": 33.333333333333336,
    "status_breakdown": { "todo": 3, "doing": 1, "done": 2 },
    "priority_breakdown": { "high": 4, "medium": 2, "low": 0 }
  },
  "schema_version": "1.0",
  "status": "ok",
  "tool_version": "0.1.0"
}
```

### 11. Full Command Tree (`describe`, excerpt)
```json
{
  "name": "murli-work",
  "summary": "murli-work is a sprint and project task tracker",
  "schema_version": "1.0",
  "tool_version": "0.1.0",
  "capabilities": {
    "streaming": true,
    "dry_run": true,
    "output_formats": ["json", "ndjson", "text"],
    "schema_version": "1.0",
    "protocol_version": "0.2",
    "profiles": true
  },
  "commands": [
    {
      "name": "init",
      "summary": "Initialize/Reset the database and config",
      "agent_description": "Initialize or reset the murli-work database with sample data.",
      "idempotent": false,
      "mutating": true,
      "safety": { "read_only": false, "idempotent": false }
    }
  ]
}
```
