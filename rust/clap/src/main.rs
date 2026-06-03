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
