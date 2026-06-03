# Rust / clap — Murli Integration Guide

This guide walks through integrating murli middleware into a clap CLI using the **derive API**, step by step. Each step shows the code change, explains the mechanic, and captures the terminal output.

The target application is `murli-work`, a sprint task tracker.

---

## Rust derive API vs. builder API

murli-rs supports two clap paths:

- **Derive API** (used here): Add `#[command(flatten)] murli: murli::clap::GlobalArgs` to your `Cli` struct. Murli flags are injected automatically. Describe/doctor must be added as explicit hidden variants in your `Commands` enum.
- **Builder API**: Call `murli::clap::enable(&mut cmd)` on your `Command`. This adds flags AND mounts `describe`, `doctor`, `profile` subcommands automatically — no enum variants needed. More automatic, but requires the builder API throughout.

---

## Step 1: What You Get for Free

Flatten `GlobalArgs` into your `Cli` struct and add two hidden variants for the murli built-ins:

```rust
#[derive(Parser)]
struct Cli {
    #[command(flatten)]
    murli: murli::clap::GlobalArgs,  // --agent, --schema, --force, --dry-run, --output, --profile

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    // ... your commands ...

    // Hidden murli built-ins
    #[command(name = "describe", hide = true)]
    Describe { #[arg(long)] agents_md: bool },
    #[command(name = "doctor", hide = true)]
    Doctor,
}

fn main() {
    let cli = Cli::parse();
    let root_cmd = Cli::command();
    murli::clap::handle_builtins(&cli.murli, &root_cmd, None); // handles --schema + mutation guard
    // ...
    Commands::Describe { agents_md } => {
        if agents_md { murli::clap::emit_agents_md(&root_cmd, ""); }
        else         { murli::clap::emit_describe(&root_cmd, ""); }
    }
    Commands::Doctor => { /* murli::clap::doctor(&root_cmd) */ }
}
```

### `--help` output

```
A sprint and project task tracker

Usage: work-clap [OPTIONS] <COMMAND>

Commands:
  init    Initialize/Reset the database and config
  task    Manage sprint tasks
  label   Manage global task labels
  report  Display progress report
  help    Print this message or the help of the given subcommand(s)

Options:
      --agent            Force JSON output for agent/script use
      --schema           Print command schema as JSON and exit
      --force            Skip confirmation prompts [aliases: --yes]
      --dry-run          Simulate without making changes
      --output <FORMAT>  Output format: json | ndjson | text
      --profile <NAME>   Load a named flag profile
  -h, --help             Print help
```

### `describe` output (first 60 lines)

```json
{
  "name": "murli-work",
  "summary": "A sprint and project task tracker",
  "schema_version": "1.0",
  "capabilities": [
    "agent",
    "schema",
    "dry-run",
    "force",
    "profiles"
  ],
  "commands": [
    {
      "name": "init",
      "summary": "Initialize/Reset the database and config",
      "agent_description": "Resets the database to seed data and writes default config.",
      "when_to_use": "First-time setup or to restore the database to a clean state.",
      "idempotent": true,
      "mutating": true,
      "returns": {
        "description": "Storage directory path",
        "type": "object",
        "properties": {
          "path": "string"
        }
      },
      "safety": {
        "read_only": false,
        "idempotent": true
      }
    },
    {
      "name": "task",
      "summary": "Manage sprint tasks",
      "idempotent": false,
      "subcommands": [
        {
          "name": "create",
          "summary": "Create a new task",
          "agent_description": "Creates a new item. For tasks: assigns ID. For labels: slugifies the name.",
          ...
        }
      ]
    }
  ]
}
```

---

## Step 2: Writer API

Obtain a `Writer` from `GlobalArgs` and replace all `println!`/`eprintln!`/`process::exit` with writer calls. The writer automatically selects text or JSON envelope based on TTY detection and `--agent`:

```rust
let mut writer = murli::clap::writer_from_args(&cli.murli);

// Simple success:
writer.write_success("Task 1 created successfully.", &json!({"id": 1}));

// Error (never returns — calls process::exit internally):
writer.write_error(AgentError::not_found("task with ID 99 not found", "Use task list."));

// TTY/agent branch for multi-format commands:
if writer.is_tty() {
    println!("{}", format::format_tasks_table(&filtered));
} else {
    writer.write_success("Found N task(s).", &json!({"tasks": tasks_val, "count": N}));
}
```

### Agent — task create

```json
{
  "message": "Task 7 (\"Agent sprint item\") created successfully.",
  "result": {
    "id": 7,
    "title": "Agent sprint item"
  },
  "schema_version": "1.0",
  "status": "ok",
  "tool_version": ""
}
```

### Agent — task list

```json
{
  "message": "Found 7 task(s).",
  "result": {
    "count": 7,
    "tasks": [
      {
        "id": 1,
        "title": "Setup workspace layout",
        "status": "done",
        "priority": "high",
        "labels": ["setup", "dev"]
      },
      { "...": "5 more tasks" }
    ]
  },
  "schema_version": "1.0",
  "status": "ok",
  "tool_version": ""
}
```

---

## Step 3: Schema Annotations

Call `murli::clap::annotate()` with a `Metadata` struct before `Cli::parse()`. The annotation is stored in a global registry keyed by command name, and retrieved when `describe` or `--schema` builds the tree:

```rust
fn register_annotations() {
    use clap::Command;
    use murli::schema::{Metadata, ReturnSchema};

    murli::clap::annotate(&mut Command::new("init"), Metadata {
        agent_description: "Resets the database to seed data and writes default config.".into(),
        mutating: true, idempotent: true,
        ..Default::default()
    });
    // ... repeat for each command name
}

fn main() {
    register_annotations(); // must be first — before Cli::parse()
    let cli = Cli::parse();
    // ...
}
```

**Note on name collisions:** The registry is keyed by command name string. Commands with the same name across subgroups (e.g. `list` under both `task` and `label`) share the same registry entry. Write descriptions that apply to both, or use the builder API for per-command uniqueness.

### `--schema init` output (first 40 lines)

```json
{
  "name": "murli-work",
  "summary": "A sprint and project task tracker",
  "idempotent": false,
  "subcommands": [
    {
      "name": "init",
      "summary": "Initialize/Reset the database and config",
      "agent_description": "Resets the database to seed data and writes default config.",
      "when_to_use": "First-time setup or to restore the database to a clean state.",
      "idempotent": true,
      "mutating": true,
      "returns": {
        "description": "Storage directory path",
        "type": "object",
        "properties": {
          "path": "string"
        }
      },
      "safety": {
        "read_only": false,
        "idempotent": true
      }
    }
  ]
}
```

---

## Step 4: Structured Errors

All error paths use `AgentError` factory methods. In TTY mode the writer prints `Error: / Hint:`. In agent mode (or when piped) it emits a JSON error envelope and exits with the correct code:

| Error condition | AgentError method | Exit code |
|---|---|---|
| Item not found | `AgentError::not_found(msg, hint)` | 5 |
| Already exists | `AgentError::conflict(msg, hint)` | 7 |
| Invalid input | `AgentError::user_error(msg, hint)` | 1 |
| IO / tool error | `AgentError::tool_error(msg)` | 2 |

### Agent error output — not found (exit 5)

```json
{
  "code": 5,
  "error": "not_found",
  "message": "task with ID 999 not found",
  "recoverable": false,
  "schema_version": "1.0",
  "status": "error",
  "suggestion": "Use task list or label list to see valid identifiers.",
  "tool_version": ""
}
```

---

## Step 5: Telemetry

`writer.log(msg)` writes to stderr. In TTY mode it prints the message as-is. In agent mode it emits a structured JSON log entry with an ISO8601 timestamp. Consecutive identical messages are deduplicated with a `"repeated": N` count.

```rust
Commands::Init => {
    writer.log("Resetting database and seeding sample data...");
    writer.flush(); // flush the logger buffer to stderr before writing success to stdout
    // ...
}
```

### Agent init — stderr log + stdout envelope

```
{"level":"info","msg":"Resetting database and seeding sample data...","ts":"2026-06-03T15:53:11Z"}
{
  "message": "Initialized/Reset murli-work database with sample data and configuration in /Users/allank/Library/Application Support/murli-work",
  "result": {
    "path": "/Users/allank/Library/Application Support/murli-work"
  },
  "schema_version": "1.0",
  "status": "ok",
  "tool_version": ""
}
```
