# Rust / clap — Murli Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply murli middleware to the rust/clap skeleton (`rust/clap/src/main.rs`) following the five-step WALKTHROUGH-INSTRUCTIONS methodology, producing a fully annotated dual-audience CLI with structured errors and a companion guide.

**Architecture:** Five progressive commits on branch `rust/clap`. Step 1 adds the murli dependency, flattens `GlobalArgs` into `Cli`, and adds hidden `Describe`/`Doctor` variants to handle murli built-ins. Steps 2–5 incrementally replace `println!`/`eprintln!`/`process::exit` with the Writer API, add metadata annotations, verify structured errors, add telemetry, and write the guide. `format.rs` gains two string/value-returning helpers (`format_tasks_table`, `sprint_report_data`) for the TTY vs agent split in multi-format commands.

**Tech Stack:** Rust 2021, clap 4 (derive), serde_json 1, murli (local path, feature = "clap"), cargo

**Prerequisite:** The `2026-06-03-clap-derive-api-fixes` plan for murli-rs must be complete and pushed before starting this plan (it exposes `dispatch_profile` and `handle_subcommand`).

---

## File Map

| File | Change |
|---|---|
| `rust/clap/Cargo.toml` | Add `murli` and `serde_json` dependencies |
| `rust/clap/src/format.rs` | Add `format_tasks_table() -> String` and `sprint_report_data() -> Value` |
| `rust/clap/src/main.rs` | Full integration: GlobalArgs, Writer API, annotations, errors, telemetry |
| `RUST-CLAP-GUIDE.md` | Step-by-step guide with captured terminal output |

---

## Task 0: Create branch

- [ ] **Step 1: Branch from main**

```bash
cd /Users/allank/Dev/murli/murli-demo
git checkout main
git checkout -b rust/clap
```

---

## Task 1: Step 1 — Dependency + `GlobalArgs` + describe/doctor dispatch

**Files:**
- Modify: `rust/clap/Cargo.toml`
- Modify: `rust/clap/src/main.rs`

- [ ] **Step 1: Add murli and serde_json to `rust/clap/Cargo.toml`**

The current `[dependencies]` section is:
```toml
[dependencies]
clap = { version = "4.4", features = ["derive", "cargo"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
comfy-table = "7.0"
chrono = { version = "0.4", features = ["serde"] }
```

Add the murli line (serde_json is already present):
```toml
[dependencies]
clap = { version = "4.4", features = ["derive", "cargo"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
comfy-table = "7.0"
chrono = { version = "0.4", features = ["serde"] }
murli = { path = "../../../murli-rs", features = ["clap"] }
```

- [ ] **Step 2: Update `rust/clap/src/main.rs` — Cli struct, Commands enum, handle_builtins, describe/doctor dispatch**

Replace the entire top of `main.rs` up to and including the `main()` function opening. The complete new `main.rs` for this step (command handlers unchanged from skeleton, only struct definitions and start of main change):

```rust
use clap::{Args, CommandFactory, Parser, Subcommand, ValueEnum};
use serde_json::json;
use std::process;
use murli::AgentError;

mod db;
mod format;

#[derive(Parser)]
#[command(name = "murli-work", about = "A sprint and project task tracker", long_about = None)]
struct Cli {
    #[command(flatten)]
    murli: murli::clap::GlobalArgs,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Initialize/Reset the database and config
    Init,
    /// Manage sprint tasks
    Task(TaskArgs),
    /// Manage global task labels
    Label(LabelArgs),
    /// Display progress report
    Report,
    // Murli built-ins — hidden from --help output
    #[command(name = "describe", hide = true)]
    Describe {
        /// Generate an AGENTS.md stub instead of JSON
        #[arg(long)]
        agents_md: bool,
    },
    #[command(name = "doctor", hide = true)]
    Doctor,
}

#[derive(Args)]
struct TaskArgs {
    #[command(subcommand)]
    command: TaskCommands,
}

#[derive(Subcommand)]
enum TaskCommands {
    /// Create a new task
    Create {
        /// Task title
        title: String,
        /// Task description
        #[arg(short, long)]
        desc: Option<String>,
        /// Task priority
        #[arg(short, long, value_enum)]
        priority: Option<Priority>,
        /// Comma-separated labels
        #[arg(short, long, value_delimiter = ',')]
        labels: Vec<String>,
    },
    /// List stored tasks
    List {
        /// Filter by status
        #[arg(short, long, value_enum)]
        status: Option<Status>,
        /// Filter by priority
        #[arg(short, long, value_enum)]
        priority: Option<Priority>,
        /// Filter by a label
        #[arg(short, long)]
        label: Option<String>,
        /// Output format (TTY only; agent mode always returns JSON envelope)
        #[arg(short, long, value_enum, default_value_t = Format::Table)]
        output: Format,
    },
    /// Update an existing task's fields
    Update {
        /// Task ID
        id: u32,
        /// New title
        #[arg(short, long)]
        title: Option<String>,
        /// New description
        #[arg(short, long)]
        desc: Option<String>,
        /// New priority
        #[arg(short, long, value_enum)]
        priority: Option<Priority>,
        /// New status
        #[arg(short, long, value_enum)]
        status: Option<Status>,
        /// Replacement labels
        #[arg(short, long, value_delimiter = ',')]
        labels: Option<Vec<String>>,
    },
    /// Delete a task
    Delete {
        /// Task ID
        id: u32,
        /// Force delete without warning
        #[arg(long)]
        force: bool,
    },
}

#[derive(Args)]
struct LabelArgs {
    #[command(subcommand)]
    command: LabelCommands,
}

#[derive(Subcommand)]
enum LabelCommands {
    /// List all defined labels
    List,
    /// Create a custom label
    Create {
        /// Label name
        name: String,
    },
    /// Delete a label
    Delete {
        /// Label name
        name: String,
    },
}

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum Priority { Low, Medium, High }

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum Status { Todo, Doing, Done }

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum Format { Table, Json, Csv }

fn prio_str(p: Priority) -> String {
    match p { Priority::Low => "low", Priority::Medium => "medium", Priority::High => "high" }.to_string()
}

fn status_str(s: Status) -> String {
    match s { Status::Todo => "todo", Status::Doing => "doing", Status::Done => "done" }.to_string()
}

fn main() {
    let cli = Cli::parse();
    let root_cmd = Cli::command();
    murli::clap::handle_builtins(&cli.murli, &root_cmd, None);

    match cli.command {
        Commands::Describe { agents_md } => {
            if agents_md { murli::clap::emit_agents_md(&root_cmd, ""); }
            else         { murli::clap::emit_describe(&root_cmd, ""); }
        }
        Commands::Doctor => {
            let issues = murli::clap::doctor(&root_cmd);
            if issues.is_empty() {
                println!("All naming conventions satisfied.");
            } else {
                for issue in &issues { println!("{issue}"); }
                process::exit(1);
            }
        }
        Commands::Init => {
            if let Err(e) = db::reset_db() {
                eprintln!("Error: {}", e);
                process::exit(1);
            }
            let dir = db::get_storage_dir();
            println!(
                "Initialized/Reset murli-work database with sample data and configuration in {}",
                dir.display()
            );
        }
        Commands::Task(task_args) => match task_args.command {
            TaskCommands::Create { title, desc, priority, labels } => {
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => { eprintln!("Error: {}", e); process::exit(1); }
                };
                let prio = priority.map(prio_str);
                match db::create_task(&mut db, &title, desc, prio, labels) {
                    Ok(id) => println!("Task {} (\"{}\") created successfully.", id, title),
                    Err(e) => { eprintln!("Error: {}", e); process::exit(2); }
                }
            }
            TaskCommands::List { status, priority, label, output } => {
                let db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => { eprintln!("Error: {}", e); process::exit(1); }
                };
                let mut output_fmt = match output {
                    Format::Table => "table", Format::Json => "json", Format::Csv => "csv",
                }.to_string();
                if output_fmt == "table" {
                    if let Ok(cfg) = db::load_config() { output_fmt = cfg.default_output; }
                }
                let mut filtered = db.tasks.clone();
                if let Some(s) = status { filtered.retain(|t| t.status == status_str(s)); }
                if let Some(p) = priority { filtered.retain(|t| t.priority == prio_str(p)); }
                if let Some(lbl) = label { filtered.retain(|t| t.labels.iter().any(|l| l.eq_ignore_ascii_case(&lbl))); }
                match output_fmt.as_str() {
                    "json" => format::print_tasks_json(&filtered),
                    "csv"  => format::print_tasks_csv(&filtered),
                    _      => format::print_tasks_table(&filtered),
                }
            }
            TaskCommands::Update { id, title, desc, priority, status, labels } => {
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => { eprintln!("Error: {}", e); process::exit(1); }
                };
                let prio = priority.map(prio_str);
                let stat = status.map(status_str);
                match db::update_task(&mut db, id, title, desc, prio, stat, labels) {
                    Ok(_) => println!("Task {} updated successfully.", id),
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        let msg = e.to_string();
                        process::exit(if msg.contains("not found") { 1 } else { 2 });
                    }
                }
            }
            TaskCommands::Delete { id, force: _ } => {
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => { eprintln!("Error: {}", e); process::exit(1); }
                };
                match db::delete_task(&mut db, id) {
                    Ok(_) => println!("Task {} deleted successfully.", id),
                    Err(e) => { eprintln!("Error: {}", e); process::exit(1); }
                }
            }
        }
        Commands::Label(label_args) => match label_args.command {
            LabelCommands::List => {
                let db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => { eprintln!("Error: {}", e); process::exit(1); }
                };
                format::print_labels_table(&db);
            }
            LabelCommands::Create { name } => {
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => { eprintln!("Error: {}", e); process::exit(1); }
                };
                match db::create_label(&mut db, &name) {
                    Ok(slug) => println!("Label \"{}\" created successfully.", slug),
                    Err(e) => { eprintln!("Error: {}", e); process::exit(1); }
                }
            }
            LabelCommands::Delete { name } => {
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => { eprintln!("Error: {}", e); process::exit(1); }
                };
                match db::delete_label(&mut db, &name) {
                    Ok(_) => println!("Label \"{}\" deleted successfully.", name),
                    Err(e) => { eprintln!("Error: {}", e); process::exit(1); }
                }
            }
        }
        Commands::Report => {
            let db = match db::load_db() {
                Ok(d) => d,
                Err(e) => { eprintln!("Error: {}", e); process::exit(1); }
            };
            format::print_sprint_report(&db);
        }
    }
}
```

Note: command handlers still use `println!`/`eprintln!`/`process::exit` in this step — the Writer API comes in Step 2. The critical changes here are: `GlobalArgs` flatten, `Describe`/`Doctor` variants, `handle_builtins`, `prio_str`/`status_str` helpers, and `CommandFactory` import.

- [ ] **Step 3: Build and smoke-test**

```bash
cd /Users/allank/Dev/murli/murli-demo
cargo build --manifest-path rust/clap/Cargo.toml 2>&1
./bin/murli-work-rust-clap --help
```

Expected: `--agent`, `--schema`, `--force`, `--dry-run`, `--profile` appear. No `describe` or `doctor` in the visible help (they're hidden).

```bash
./bin/murli-work-rust-clap describe
./bin/murli-work-rust-clap init
./bin/murli-work-rust-clap task create "Test step 1" --priority high
./bin/murli-work-rust-clap task list
```

Expected: `describe` returns JSON with `init`, `task`, `label`, `report` commands. Other commands work as before.

Note: the binary is at `rust/clap/target/debug/work-clap` (or use `cargo run --manifest-path rust/clap/Cargo.toml -- describe`). Update the bin path if the Makefile build target differs.

- [ ] **Step 4: Commit**

```bash
git add rust/clap/Cargo.toml rust/clap/src/main.rs
git commit -m "$(cat <<'EOF'
feat(rust/clap): step 1 — add murli dependency and GlobalArgs, mount describe/doctor

Adds murli path dependency with clap feature. Flattens GlobalArgs into
Cli so --agent, --schema, --force, --dry-run, --output, --profile are
injected automatically. Adds hidden Describe and Doctor variants to
Commands enum; dispatches them using emit_describe/emit_agents_md and
murli::clap::doctor. handle_builtins() handles --schema and mutation
guard before the main match.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Step 2 — Writer API (format.rs additions + full handler rewrite)

**Files:**
- Modify: `rust/clap/src/format.rs`
- Modify: `rust/clap/src/main.rs`

- [ ] **Step 1: Add string/value-returning helpers to `rust/clap/src/format.rs`**

Add `use serde_json::{json, Value};` at the top of `src/format.rs` (after the existing `use crate::db::{Database, Task};` line):

```rust
use serde_json::{json, Value};
```

Then append to the end of `src/format.rs`:

```rust
/// Returns the task table as a String for use with writer.write_success in TTY mode.
/// `Task` and `Database` are already in scope from the top-level `use crate::db::...`.
pub fn format_tasks_table(tasks: &[Task]) -> String {
    let border = "+----+----------------------+--------+----------+------------+";
    let header = "| ID | Title                | Status | Priority | Labels     |";
    let mut lines = vec![border.to_string(), header.to_string(), border.to_string()];
    for t in tasks {
        let labels_str = t.labels.join(",");
        let status   = t.status.to_uppercase();
        let priority = t.priority.to_uppercase();
        let title_trunc  = if t.title.len()   > 20 { &t.title[..20]    } else { &t.title };
        let status_trunc = if status.len()     > 6  { &status[..6]      } else { &status };
        let prio_trunc   = if priority.len()   > 8  { &priority[..8]    } else { &priority };
        let labels_trunc = if labels_str.len() > 10 { &labels_str[..10] } else { &labels_str };
        lines.push(format!(
            "| {:<2} | {:<20} | {:<6} | {:<8} | {:<10} |",
            t.id, title_trunc, status_trunc, prio_trunc, labels_trunc,
        ));
    }
    lines.push(border.to_string());
    lines.join("\n")
}

/// Returns sprint statistics as a JSON Value for writer.write_success payload.
pub fn sprint_report_data(db: &Database) -> Value {
    let total = db.tasks.len();
    let (mut completed, mut todo, mut doing, mut done) = (0usize, 0usize, 0usize, 0usize);
    let (mut high, mut medium, mut low) = (0usize, 0usize, 0usize);
    for t in &db.tasks {
        match t.status.to_lowercase().as_str() {
            "todo"  => todo  += 1,
            "doing" => doing += 1,
            "done"  => { done += 1; completed += 1; }
            _       => {}
        }
        match t.priority.to_lowercase().as_str() {
            "low"    => low    += 1,
            "medium" => medium += 1,
            "high"   => high   += 1,
            _        => {}
        }
    }
    let percent = if total > 0 { (completed * 100) / total } else { 0 };
    json!({
        "total": total, "completed": completed, "percent": percent,
        "status":   { "todo": todo,   "doing": doing,  "done": done  },
        "priority": { "high": high,   "medium": medium, "low": low   },
    })
}
```

- [ ] **Step 2: Replace `main.rs` with the full Writer API version**

Replace the entire contents of `rust/clap/src/main.rs` with:

```rust
use clap::{Args, CommandFactory, Parser, Subcommand, ValueEnum};
use serde_json::json;
use murli::AgentError;

mod db;
mod format;

#[derive(Parser)]
#[command(name = "murli-work", about = "A sprint and project task tracker", long_about = None)]
struct Cli {
    #[command(flatten)]
    murli: murli::clap::GlobalArgs,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Initialize/Reset the database and config
    Init,
    /// Manage sprint tasks
    Task(TaskArgs),
    /// Manage global task labels
    Label(LabelArgs),
    /// Display progress report
    Report,
    #[command(name = "describe", hide = true)]
    Describe { #[arg(long)] agents_md: bool },
    #[command(name = "doctor", hide = true)]
    Doctor,
}

#[derive(Args)]
struct TaskArgs {
    #[command(subcommand)]
    command: TaskCommands,
}

#[derive(Subcommand)]
enum TaskCommands {
    /// Create a new task
    Create {
        title: String,
        #[arg(short, long)] desc: Option<String>,
        #[arg(short, long, value_enum)] priority: Option<Priority>,
        #[arg(short, long, value_delimiter = ',')] labels: Vec<String>,
    },
    /// List stored tasks
    List {
        #[arg(short, long, value_enum)] status: Option<Status>,
        #[arg(short, long, value_enum)] priority: Option<Priority>,
        #[arg(short, long)] label: Option<String>,
        /// Output format (TTY only; agent mode always returns JSON envelope)
        #[arg(short, long, value_enum, default_value_t = Format::Table)] output: Format,
    },
    /// Update an existing task's fields
    Update {
        id: u32,
        #[arg(short, long)] title: Option<String>,
        #[arg(short, long)] desc: Option<String>,
        #[arg(short, long, value_enum)] priority: Option<Priority>,
        #[arg(short, long, value_enum)] status: Option<Status>,
        #[arg(short, long, value_delimiter = ',')] labels: Option<Vec<String>>,
    },
    /// Delete a task
    Delete { id: u32, #[arg(long)] force: bool },
}

#[derive(Args)]
struct LabelArgs {
    #[command(subcommand)]
    command: LabelCommands,
}

#[derive(Subcommand)]
enum LabelCommands {
    /// List all defined labels
    List,
    /// Create a custom label
    Create { name: String },
    /// Delete a label
    Delete { name: String },
}

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum Priority { Low, Medium, High }

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum Status { Todo, Doing, Done }

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum Format { Table, Json, Csv }

fn prio_str(p: Priority) -> String {
    match p { Priority::Low => "low", Priority::Medium => "medium", Priority::High => "high" }.to_string()
}

fn status_str(s: Status) -> String {
    match s { Status::Todo => "todo", Status::Doing => "doing", Status::Done => "done" }.to_string()
}

fn map_err(e: Box<dyn std::error::Error>) -> AgentError {
    let msg = e.to_string();
    if msg.contains("not found") {
        AgentError::not_found(&msg, "Use task list or label list to see valid identifiers.")
    } else if msg.contains("already exists") {
        AgentError::conflict(&msg, "Use label list to see existing labels.")
    } else if msg.contains("invalid priority") || msg.contains("invalid status") || msg.contains("invalid label") {
        AgentError::user_error(&msg, "Check the valid values in --help.")
    } else {
        AgentError::tool_error(&msg)
    }
}

fn main() {
    let cli = Cli::parse();
    let root_cmd = Cli::command();
    murli::clap::handle_builtins(&cli.murli, &root_cmd, None);

    let mut writer = murli::clap::writer_from_args(&cli.murli);

    match cli.command {
        Commands::Describe { agents_md } => {
            if agents_md { murli::clap::emit_agents_md(&root_cmd, ""); }
            else         { murli::clap::emit_describe(&root_cmd, ""); }
        }
        Commands::Doctor => {
            let issues = murli::clap::doctor(&root_cmd);
            if issues.is_empty() {
                println!("All naming conventions satisfied.");
            } else {
                for issue in &issues { println!("{issue}"); }
                std::process::exit(1);
            }
        }
        Commands::Init => {
            match db::reset_db() {
                Ok(()) => {
                    let dir = db::get_storage_dir();
                    writer.write_success(
                        &format!("Initialized/Reset murli-work database with sample data and configuration in {}", dir.display()),
                        &json!({"path": dir.display().to_string()}),
                    );
                }
                Err(e) => writer.write_error(AgentError::tool_error(&e.to_string())),
            }
        }
        Commands::Task(task_args) => match task_args.command {
            TaskCommands::Create { title, desc, priority, labels } => {
                let prio = priority.map(prio_str);
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => writer.write_error(AgentError::tool_error(&e.to_string())),
                };
                match db::create_task(&mut db, &title, desc, prio, labels) {
                    Ok(id) => writer.write_success(
                        &format!("Task {} (\"{}\") created successfully.", id, title),
                        &json!({"id": id, "title": &title}),
                    ),
                    Err(e) => writer.write_error(map_err(e)),
                }
            }
            TaskCommands::List { status, priority, label, output } => {
                let db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => writer.write_error(AgentError::tool_error(&e.to_string())),
                };
                let mut output_fmt = match output {
                    Format::Table => "table", Format::Json => "json", Format::Csv => "csv",
                }.to_string();
                if output_fmt == "table" {
                    if let Ok(cfg) = db::load_config() { output_fmt = cfg.default_output; }
                }
                let mut filtered = db.tasks.clone();
                if let Some(s) = status   { filtered.retain(|t| t.status.eq_ignore_ascii_case(&status_str(s))); }
                if let Some(p) = priority { filtered.retain(|t| t.priority.eq_ignore_ascii_case(&prio_str(p))); }
                if let Some(lbl) = label  { filtered.retain(|t| t.labels.iter().any(|l| l.eq_ignore_ascii_case(&lbl))); }

                if writer.is_tty() {
                    match output_fmt.as_str() {
                        "json" => format::print_tasks_json(&filtered),
                        "csv"  => format::print_tasks_csv(&filtered),
                        _      => println!("{}", format::format_tasks_table(&filtered)),
                    }
                } else {
                    let tasks_val = serde_json::to_value(&filtered).unwrap_or(json!([]));
                    writer.write_success(
                        &format!("Found {} task(s).", filtered.len()),
                        &json!({"tasks": tasks_val, "count": filtered.len()}),
                    );
                }
            }
            TaskCommands::Update { id, title, desc, priority, status, labels } => {
                let prio = priority.map(prio_str);
                let stat = status.map(status_str);
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => writer.write_error(AgentError::tool_error(&e.to_string())),
                };
                match db::update_task(&mut db, id, title, desc, prio, stat, labels) {
                    Ok(()) => writer.write_success(
                        &format!("Task {} updated successfully.", id),
                        &json!({"id": id}),
                    ),
                    Err(e) => writer.write_error(map_err(e)),
                }
            }
            TaskCommands::Delete { id, force: _ } => {
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => writer.write_error(AgentError::tool_error(&e.to_string())),
                };
                match db::delete_task(&mut db, id) {
                    Ok(()) => writer.write_success(
                        &format!("Task {} deleted successfully.", id),
                        &json!({"id": id}),
                    ),
                    Err(e) => writer.write_error(map_err(e)),
                }
            }
        }
        Commands::Label(label_args) => match label_args.command {
            LabelCommands::List => {
                let db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => writer.write_error(AgentError::tool_error(&e.to_string())),
                };
                if writer.is_tty() {
                    format::print_labels_table(&db);
                } else {
                    let labels_val = serde_json::to_value(&db.labels).unwrap_or(json!([]));
                    writer.write_success(
                        &format!("Found {} label(s).", db.labels.len()),
                        &json!({"labels": labels_val}),
                    );
                }
            }
            LabelCommands::Create { name } => {
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => writer.write_error(AgentError::tool_error(&e.to_string())),
                };
                match db::create_label(&mut db, &name) {
                    Ok(slug) => writer.write_success(
                        &format!("Label \"{}\" created successfully.", slug),
                        &json!({"slug": &slug}),
                    ),
                    Err(e) => writer.write_error(map_err(e)),
                }
            }
            LabelCommands::Delete { name } => {
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => writer.write_error(AgentError::tool_error(&e.to_string())),
                };
                match db::delete_label(&mut db, &name) {
                    Ok(()) => writer.write_success(
                        &format!("Label \"{}\" deleted successfully.", name),
                        &json!({"name": &name}),
                    ),
                    Err(e) => writer.write_error(map_err(e)),
                }
            }
        }
        Commands::Report => {
            let db = match db::load_db() {
                Ok(d) => d,
                Err(e) => writer.write_error(AgentError::tool_error(&e.to_string())),
            };
            if writer.is_tty() {
                format::print_sprint_report(&db);
            } else {
                writer.write_success("Sprint report generated.", &format::sprint_report_data(&db));
            }
        }
    }
}
```

- [ ] **Step 3: Build and verify TTY and agent mode**

```bash
cd /Users/allank/Dev/murli/murli-demo
cargo build --manifest-path rust/clap/Cargo.toml 2>&1

# TTY mode (run at a terminal)
cargo run --manifest-path rust/clap/Cargo.toml -- init
cargo run --manifest-path rust/clap/Cargo.toml -- task create "Writer API test" --priority high
cargo run --manifest-path rust/clap/Cargo.toml -- task list
cargo run --manifest-path rust/clap/Cargo.toml -- report

# Agent mode
cargo run --manifest-path rust/clap/Cargo.toml -- --agent task create "Agent test"
cargo run --manifest-path rust/clap/Cargo.toml -- --agent task list
cargo run --manifest-path rust/clap/Cargo.toml -- --agent report
```

Expected (TTY): same human-readable output as the skeleton.
Expected (agent): JSON envelopes with `"status": "ok"`.

Example agent task create output:
```json
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "ok",
  "message": "Task 7 (\"Agent test\") created successfully.",
  "result": {
    "id": 7,
    "title": "Agent test"
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add rust/clap/src/format.rs rust/clap/src/main.rs
git commit -m "$(cat <<'EOF'
feat(rust/clap): step 2 — Writer API replaces println!/eprintln!/process::exit

All command handlers now use writer.write_success() and writer.write_error()
from murli::clap::writer_from_args(). Commands with multi-format output
(task list, label list, report) use writer.is_tty() to branch: TTY uses
format helpers, agent/piped mode uses write_success with JSON payload.

map_err() centralises error-to-AgentError mapping:
  "not found"      -> AgentError::not_found()   exit 5
  "already exists" -> AgentError::conflict()    exit 7
  invalid input    -> AgentError::user_error()  exit 1
  other            -> AgentError::tool_error()  exit 2

format.rs gains format_tasks_table() -> String and sprint_report_data()
-> Value string/value-returning variants for the TTY/agent split.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Step 3 — Schema Annotations

**Files:**
- Modify: `rust/clap/src/main.rs`

- [ ] **Step 1: Add `register_annotations()` function and call it in `main()`**

Add this function to `main.rs` immediately before the `fn main()` definition. The `props_map` helper builds the `HashMap<String, Value>` that `ReturnSchema.properties` requires:

```rust
fn props_map(pairs: &[(&str, &str)]) -> std::collections::HashMap<String, serde_json::Value> {
    pairs.iter()
        .map(|(k, v)| (k.to_string(), serde_json::Value::String(v.to_string())))
        .collect()
}

fn register_annotations() {
    use clap::Command;
    use murli::schema::{Example, Metadata, ReturnSchema};

    murli::clap::annotate(&mut Command::new("init"), Metadata {
        agent_description: "Resets the database to seed data and writes default config.".into(),
        when_to_use: "First-time setup or to restore the database to a clean state.".into(),
        mutating: true, idempotent: true,
        returns: Some(ReturnSchema {
            description: "Storage directory path".into(),
            r#type: "object".into(),
            properties: props_map(&[("path", "string")]),
        }),
        ..Default::default()
    });

    murli::clap::annotate(&mut Command::new("create"), Metadata {
        agent_description: "Creates a new item. For tasks: assigns ID. For labels: slugifies the name.".into(),
        when_to_use: "Adding a new task to the backlog or defining a new label category.".into(),
        mutating: true, idempotent: false,
        returns: Some(ReturnSchema {
            description: "Created item identifier".into(),
            r#type: "object".into(),
            properties: props_map(&[("id", "int|string")]),
        }),
        examples: vec![Example {
            command: "murli-work task create \"Fix login bug\" --priority high --labels dev".into(),
            description: String::new(),
            expected_exit_code: 0,
        }],
        ..Default::default()
    });

    murli::clap::annotate(&mut Command::new("list"), Metadata {
        agent_description: "Lists items. For tasks: accepts --status, --priority, --label filters.".into(),
        when_to_use: "Querying the sprint backlog or checking available labels.".into(),
        mutating: false, idempotent: true,
        returns: Some(ReturnSchema {
            description: "Filtered items with count".into(),
            r#type: "object".into(),
            properties: props_map(&[("tasks", "array"), ("count", "int")]),
        }),
        examples: vec![Example {
            command: "murli-work task list --status doing --priority high".into(),
            description: String::new(),
            expected_exit_code: 0,
        }],
        ..Default::default()
    });

    murli::clap::annotate(&mut Command::new("update"), Metadata {
        agent_description: "Updates one or more fields on an existing task. Omitted flags are unchanged.".into(),
        when_to_use: "Changing the status, priority, title, or labels of a task.".into(),
        mutating: true, idempotent: true,
        returns: Some(ReturnSchema {
            description: "Updated task ID".into(),
            r#type: "object".into(),
            properties: props_map(&[("id", "int")]),
        }),
        examples: vec![Example {
            command: "murli-work task update 3 --status done".into(),
            description: String::new(),
            expected_exit_code: 0,
        }],
        ..Default::default()
    });

    murli::clap::annotate(&mut Command::new("delete"), Metadata {
        agent_description: "Permanently removes an item by ID or name. Also removes label refs from tasks.".into(),
        when_to_use: "Removing a cancelled task or cleaning up an unused label.".into(),
        mutating: true, idempotent: false, destructive: true,
        returns: Some(ReturnSchema {
            description: "Deleted item identifier".into(),
            r#type: "object".into(),
            properties: props_map(&[("id", "int|string")]),
        }),
        ..Default::default()
    });

    murli::clap::annotate(&mut Command::new("report"), Metadata {
        agent_description: "Computes and returns sprint completion statistics by status and priority.".into(),
        when_to_use: "Getting a structured summary of sprint progress.".into(),
        mutating: false, idempotent: true,
        returns: Some(ReturnSchema {
            description: "Sprint statistics".into(),
            r#type: "object".into(),
            properties: props_map(&[
                ("total", "int"), ("completed", "int"), ("percent", "int"),
                ("status", "object"), ("priority", "object"),
            ]),
        }),
        ..Default::default()
    });
}
```

In `fn main()`, add `register_annotations();` as the **very first line** (before `Cli::parse()`):

```rust
fn main() {
    register_annotations();
    let cli = Cli::parse();
    // ... rest unchanged
```

- [ ] **Step 2: Verify `--schema` and `describe` include annotations**

```bash
cargo run --manifest-path rust/clap/Cargo.toml -- task create --schema
cargo run --manifest-path rust/clap/Cargo.toml -- describe
```

In `task create --schema` output, verify `agent_description`, `mutating`, `returns` fields are populated.
In `describe` output, verify the `commands` array has `agent_description` on each command.

- [ ] **Step 3: Commit**

```bash
git add rust/clap/src/main.rs
git commit -m "$(cat <<'EOF'
feat(rust/clap): step 3 — schema annotations via murli::clap::annotate

Adds register_annotations() called before Cli::parse() so annotations
are in the registry when --schema or describe is invoked. Annotates
init, create, list, update, delete, report with agent_description,
when_to_use, mutating/idempotent/destructive flags, ReturnSchema, and
examples where applicable.

Note: the registry is keyed by command name string. Commands that share
a name across subgroups (e.g. "list" for both task and label) share the
same annotation entry — the descriptions are written to cover both cases.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Step 4 — Actionable Error Verification

All error paths are already in place from Task 2 (`map_err`). This task verifies the JSON envelopes and exit codes — no code changes.

- [ ] **Step 1: Verify not-found error (exit 5)**

```bash
cargo run --manifest-path rust/clap/Cargo.toml -- --agent task update 999 --status done 2>&1
echo "exit: $?"
```

Expected:
```json
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "error",
  "code": 5,
  "error": "not_found",
  "message": "task with ID 999 not found",
  "suggestion": "Use task list or label list to see valid identifiers.",
  "recoverable": false
}
exit: 5
```

- [ ] **Step 2: Verify conflict error (exit 7)**

```bash
cargo run --manifest-path rust/clap/Cargo.toml -- init
cargo run --manifest-path rust/clap/Cargo.toml -- --agent label create dev 2>&1
echo "exit: $?"
```

Expected:
```json
{
  "schema_version": "1.0",
  "tool_version": "",
  "status": "error",
  "code": 7,
  "error": "conflict",
  "message": "label \"dev\" already exists",
  "suggestion": "Use label list to see existing labels.",
  "recoverable": false
}
exit: 7
```

- [ ] **Step 3: Verify TTY error output**

```bash
cargo run --manifest-path rust/clap/Cargo.toml -- task update 999 --status done
```

Expected (plain text to stderr):
```
Error: task with ID 999 not found
Hint:  Use task list or label list to see valid identifiers.
```

- [ ] **Step 4: Commit (empty — records verification)**

```bash
git commit --allow-empty -m "$(cat <<'EOF'
feat(rust/clap): step 4 — structured error verification

Confirmed AgentError JSON envelopes with correct exit codes in agent mode:
  "not found"      -> code 5, error: not_found
  "already exists" -> code 7, error: conflict
  invalid input    -> code 1, error: user_error
  tool/IO errors   -> code 2, error: tool_error

TTY mode produces plain Error:/Hint: pairs on stderr.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Step 5 — Telemetry + Guide + Push

**Files:**
- Modify: `rust/clap/src/main.rs`
- Create: `RUST-CLAP-GUIDE.md`

- [ ] **Step 1: Add `writer.log()` to `init` and `report` handlers**

In the `Commands::Init` arm, add `writer.log(...)` as the first line inside the arm:

```rust
Commands::Init => {
    writer.log("Resetting database and seeding sample data...");
    match db::reset_db() {
        // ... rest unchanged
```

In the `Commands::Report` arm, add `writer.log(...)` before loading the db:

```rust
Commands::Report => {
    writer.log("Computing sprint statistics...");
    let db = match db::load_db() {
        // ... rest unchanged
```

- [ ] **Step 2: Verify log output in agent mode**

```bash
cargo build --manifest-path rust/clap/Cargo.toml
cargo run --manifest-path rust/clap/Cargo.toml -- --agent init 2>&1
```

Expected: stderr shows a JSON log entry; stdout shows the success envelope separately:
```
{"ts":"2026-06-03T...","level":"info","msg":"Resetting database and seeding sample data..."}
{
  "schema_version": "1.0",
  ...
  "status": "ok",
  "message": "Initialized/Reset murli-work database..."
}
```

- [ ] **Step 3: Capture all output for the guide**

Run each command and save its exact output. You will paste these into the guide in Step 4:

```bash
# 1. --help
cargo run --manifest-path rust/clap/Cargo.toml -- --help

# 2. describe
cargo run --manifest-path rust/clap/Cargo.toml -- describe

# 3. task create --schema
cargo run --manifest-path rust/clap/Cargo.toml -- task create --schema

# 4. init — TTY and agent
cargo run --manifest-path rust/clap/Cargo.toml -- init
cargo run --manifest-path rust/clap/Cargo.toml -- --agent init 2>&1

# 5. task create — TTY and agent
cargo run --manifest-path rust/clap/Cargo.toml -- task create "Sprint item" --priority high
cargo run --manifest-path rust/clap/Cargo.toml -- --agent task create "Agent sprint item" --priority high

# 6. task list — TTY and agent
cargo run --manifest-path rust/clap/Cargo.toml -- task list
cargo run --manifest-path rust/clap/Cargo.toml -- --agent task list

# 7. Errors — TTY and agent
cargo run --manifest-path rust/clap/Cargo.toml -- task update 999 --status done
cargo run --manifest-path rust/clap/Cargo.toml -- --agent task update 999 --status done 2>&1
echo "exit: $?"
```

- [ ] **Step 4: Write `RUST-CLAP-GUIDE.md`**

Create `/Users/allank/Dev/murli/murli-demo/RUST-CLAP-GUIDE.md` with the following structure, filling **all** `[PASTE ...]` markers with the actual captured output from Step 3:

```markdown
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
[PASTE --help output here]
```

### `describe` output (first 40 lines)

```json
[PASTE describe output here]
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

### TTY — task list

```
[PASTE task list TTY output here]
```

### Agent — task create

```json
[PASTE --agent task create output here]
```

### Agent — task list

```json
[PASTE --agent task list output here]
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

### `task create --schema` output

```json
[PASTE task create --schema output here]
```

---

## Step 4: Structured Errors

All error paths use `AgentError` factory methods. In TTY mode the writer prints `Error: / Hint:`. In agent mode it emits a JSON error envelope and exits with the correct code:

| Error condition | AgentError method | Exit code |
|---|---|---|
| Item not found | `AgentError::not_found(msg, hint)` | 5 |
| Already exists | `AgentError::conflict(msg, hint)` | 7 |
| Invalid input | `AgentError::user_error(msg, hint)` | 1 |
| IO / tool error | `AgentError::tool_error(msg)` | 2 |

### TTY error output

```
[PASTE task update 999 TTY error output here]
```

### Agent error output

```json
[PASTE --agent task update 999 error output here]
```

---

## Step 5: Telemetry

`writer.log(msg)` writes to stderr. In TTY mode it prints the message as-is. In agent mode it emits a structured JSON log entry with an ISO8601 timestamp. Consecutive identical messages are deduplicated with a `"repeated": N` count.

```rust
Commands::Init => {
    writer.log("Resetting database and seeding sample data...");
    // ...
}
```

### Agent init — stderr log + stdout envelope

```
[PASTE --agent init 2>&1 output here]
```
```

- [ ] **Step 5: Commit everything and push**

```bash
git add rust/clap/src/main.rs RUST-CLAP-GUIDE.md
git commit -m "$(cat <<'EOF'
feat(rust/clap): steps 4+5 — telemetry and integration guide

Adds writer.log() to init and report handlers for structured stderr
logging with dedup in agent mode.

Adds RUST-CLAP-GUIDE.md documenting all five integration steps with
captured terminal output showing TTY/agent duality, --schema, describe,
structured errors, and log deduplication. Documents derive API patterns
and the command-name registry limitation for annotations.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
git push -u origin rust/clap
```
