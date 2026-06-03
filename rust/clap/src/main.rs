use clap::{Args, CommandFactory, Parser, Subcommand, ValueEnum};
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
