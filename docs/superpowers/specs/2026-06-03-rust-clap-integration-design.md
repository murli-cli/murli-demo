# Rust / clap — Murli Integration Design

**Date:** 2026-06-03
**Scope:** Two sequential work streams — (1) murli-rs library fixes, (2) rust/clap demo branch

---

## Background

murli-rs is the Rust middleware library for murli. Its clap adapter supports two paths:

- **Builder API** (`enable()` + `handle_matches()`) — fully automatic; injects `--agent`, `--schema`, `--force`, `--dry-run`, `--output`, `--profile` and mounts `describe`, `doctor`, `profile` subcommands automatically.
- **Derive API** (`#[command(flatten)] murli: GlobalArgs`) — injects flags only; `describe`/`doctor`/`profile` cannot be injected automatically because clap's derive macros do not allow post-hoc subcommand injection.

The murli-demo rust skeleton (`rust/clap/`) uses the **derive API** exclusively. The integration must work within that constraint while still providing the full murli surface.

---

## Part 1 — murli-rs Library Fixes

**Branch:** `fix/clap-derive-api` in `murli-cli/murli-rs`

### 1.1 Cargo.toml metadata

Add the missing package metadata fields:

```toml
repository    = "https://github.com/murli-cli/murli-rs"
homepage      = "https://murli-cli.github.io"
documentation = "https://docs.rs/murli"
keywords      = ["cli", "agent", "middleware", "json", "clap"]
categories    = ["command-line-interface", "command-line-utilities"]
```

No logic changes.

### 1.2 Expose `dispatch_profile` publicly

In `src/clap/profile.rs`, change `pub(super) fn dispatch_profile` to `pub fn dispatch_profile`. Re-export it from `src/clap/mod.rs`:

```rust
pub use profile::dispatch_profile;
```

This lets derive-API users handle the `profile` subcommand in their own `match` arm by calling `murli::clap::dispatch_profile(matches, tool_name)`.

### 1.3 Add `handle_subcommand()` helper

New public function in `src/clap/mod.rs`. The `profile` variant uses `allow_external_subcommands = true` in the derive enum, which gives raw `Vec<String>` args. The helper reconstructs a `Command` and calls `get_matches_from()` to build `ArgMatches` for the existing `dispatch_profile` function:

```rust
/// For derive-API users: dispatch describe/doctor/profile by subcommand name.
/// `name` is the matched variant name; `args` is the raw remaining args.
/// Exits the process if the subcommand was consumed. Never returns for built-ins.
pub fn handle_subcommand(
    name:     &str,
    args:     &[String],
    root_cmd: &::clap::Command,
) {
    match name {
        "describe" => {
            let agents_md = args.iter().any(|a| a == "--agents-md");
            if agents_md { emit_agents_md(root_cmd, ""); }
            else         { emit_describe(root_cmd, ""); }
            std::process::exit(0);
        }
        "doctor" => {
            let issues = doctor(root_cmd);
            if issues.is_empty() {
                println!("All naming conventions satisfied.");
                std::process::exit(0);
            } else {
                for issue in &issues { println!("{issue}"); }
                std::process::exit(1);
            }
        }
        "profile" => {
            // Reconstruct ArgMatches from raw args using the profile subcommand schema
            let profile_cmd = profile::build_profile_subcommand();
            let matches = profile_cmd.get_matches_from(
                std::iter::once("profile".to_string()).chain(args.iter().cloned())
            );
            dispatch_profile(&matches, root_cmd.get_name());
            std::process::exit(0);
        }
        _ => {}
    }
}
```

`build_profile_subcommand` is already public (re-exported via `enable`). `dispatch_profile` becomes public via 1.2.

### 1.4 Document argh describe limitation

Add a doc comment to `src/argh/describe.rs::emit_describe` noting that `commands` is always empty because argh does not support runtime command tree introspection. No code change.

### 1.5 Tests

Add two tests to `tests/clap_tests.rs`:
- `handle_subcommand_returns_false_for_unknown` — verifies `handle_subcommand("init", &[], &cmd)` returns `false`
- `dispatch_profile_is_public` — compile-only test confirming `murli::clap::dispatch_profile` is accessible

---

## Part 2 — rust/clap Demo Branch

**Branch:** `rust/clap` from `main` in `murli-cli/murli-demo`

Follows the five-step WALKTHROUGH-INSTRUCTIONS methodology, one commit per step.

### Step 1: Dependency + Initialization

**Cargo.toml** — add murli dependency:
```toml
murli = { path = "../../../murli-rs", features = ["clap"] }
```
(path from `murli-demo/rust/clap/` to `murli-rs/`; a published crate would use `version = "0.1"`)

**`Cli` struct** — flatten GlobalArgs:
```rust
#[derive(Parser)]
struct Cli {
    #[command(flatten)]
    murli: murli::clap::GlobalArgs,

    #[command(subcommand)]
    command: Commands,
}
```

**`Commands` enum** — add hidden murli built-in variants:
```rust
/// Murli built-ins — hidden from --help, fully functional
#[command(name = "describe", hide = true)]
Describe { #[arg(long)] agents_md: bool },
#[command(name = "doctor",   hide = true)]
Doctor,
#[command(name = "profile",  hide = true, allow_external_subcommands = true)]
Profile { args: Vec<String> },
```

**`main()`** — call `handle_builtins` then dispatch built-ins:
```rust
let cli = Cli::parse();
murli::clap::handle_builtins(&cli.murli, &Cli::command(), None);

match &cli.command {
    Commands::Describe { agents_md } => {
        let cmd = Cli::command();
        if *agents_md { murli::clap::emit_agents_md(&cmd, ""); }
        else          { murli::clap::emit_describe(&cmd, ""); }
        return;
    }
    Commands::Doctor => {
        let issues = murli::clap::doctor(&Cli::command());
        if issues.is_empty() { println!("All naming conventions satisfied."); }
        else { for i in &issues { println!("{i}"); } std::process::exit(1); }
        return;
    }
    Commands::Profile { args } => {
        murli::clap::dispatch_profile(args, "murli-work");
        return;
    }
    _ => {}
}
```

**Verification:** `murli-work --help` shows `--agent`, `--schema`, `--force`, `--dry-run`, `--profile`. `murli-work describe` outputs full JSON command tree. Existing commands unchanged.

### Step 2: Writer API

**`format.rs`** — add string-returning variants alongside existing `print_*` functions:
- `format_tasks_table(tasks: &[Task]) -> String`
- `format_tasks_csv(tasks: &[Task]) -> String`
- `format_labels_table(db: &Database) -> String`
- `sprint_report_data(db: &Database) -> serde_json::Value`
- `format_sprint_report(db: &Database) -> String`

**`main.rs`** — replace all output in command handlers:
- `println!("{msg}")` → `writer.write_success(msg, &json!(payload))`
- `eprintln!("Error: {e}")` + `process::exit(N)` → `writer.write_error(AgentError::*(...))`
- `format_ops::print_tasks_table(...)` (in TTY path) → `println!("{}", format_ops::format_tasks_table(...))`

Writer obtained once per command: `let mut writer = murli::clap::writer_from_args(&cli.murli);`

Commands with multi-format output (`task list`, `label list`, `report`) use `writer.is_tty()` to branch: TTY path uses the string-returning format helpers; agent/piped path uses `write_success` with structured JSON payload.

### Step 3: Schema Annotations

`murli::clap::annotate()` called for each command after building the command tree. In the derive API, this uses the static registry keyed by command name string:

```rust
// Called once at program start, before Cli::parse()
fn register_annotations() {
    let mut cmd = Cli::command();
    murli::clap::annotate(
        cmd.find_subcommand_mut("init").unwrap(),
        Metadata {
            agent_description: "Resets the database...".into(),
            mutating: true,
            idempotent: true,
            ..Default::default()
        },
    );
    // ... repeat for each subcommand
}
```

The `annotate()` registry is keyed by command name string, so annotations can be registered without holding a reference to the full `Cli::command()` tree:

```rust
// Before Cli::parse() — just pass a temporary Command with the right name
murli::clap::annotate(&mut ::clap::Command::new("init"), Metadata {
    agent_description: "Resets the database to seed data and writes default config.".into(),
    mutating: true, idempotent: true,
    ..Default::default()
});
murli::clap::annotate(&mut ::clap::Command::new("create"), Metadata { ... });
// ... repeat for each command name
```

When `describe` is called, `build_describe_tree()` looks up each command name in the registry and merges the metadata into the schema output.

### Step 4: Actionable Error Handling

Verify structured error envelopes in agent mode. All error paths already in place from Step 2 — this step runs verification commands and captures output for the guide. No additional code changes.

Error mapping:
- Task/label not found → `AgentError::not_found(msg, suggestion)` → exit 5
- Duplicate label → `AgentError::conflict(msg, suggestion)` → exit 7
- Invalid enum value (already caught by clap) → clap exits 2
- DB/IO error → `AgentError::tool_error(msg)` → exit 2

### Step 5: Telemetry + Guide

Add `writer.log("...")` in `init` (before db reset) and `report` (before computation). Write `RUST-CLAP-GUIDE.md` at the demo root covering all five steps with captured terminal output showing TTY/agent duality, describe JSON, --schema, structured errors, and log deduplication.

---

## Error Handling Architecture

The Rust skeleton's current error handling uses `unwrap()` and `eprintln!` + `process::exit()`. The integration replaces these with:

```rust
match db_ops::load_db() {
    Ok(db) => { /* use db */ }
    Err(e) => writer.write_error(AgentError::tool_error(&e.to_string())),
}
```

`write_error` never returns (`-> !`), so no `return` statement is needed after it.

---

## Scope Boundaries

**In scope:**
- murli-rs: Cargo.toml metadata, `dispatch_profile` visibility, `handle_subcommand()`, argh doc comment, two new tests
- murli-demo: `rust/clap` branch with all five walkthrough steps and guide

**Out of scope:**
- argh skeleton or `rust/argh` branch
- murli-rs argh adapter improvements beyond the doc comment
- TypeScript or Zig integrations
- Publishing murli-rs to crates.io (path dependency is acceptable for demo)
