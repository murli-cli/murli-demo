use clap::{Args, Parser, Subcommand, ValueEnum};
use std::process;

mod db;
mod format;

#[derive(Parser)]
#[command(name = "murli-work")]
#[command(about = "A sprint and project task tracker", long_about = None)]
struct Cli {
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
        /// Output format
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
enum Priority {
    Low,
    Medium,
    High,
}

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum Status {
    Todo,
    Doing,
    Done,
}

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum Format {
    Table,
    Json,
    Csv,
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
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
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        process::exit(1);
                    }
                };

                let prio_str = priority.map(|p| match p {
                    Priority::Low => "low".to_string(),
                    Priority::Medium => "medium".to_string(),
                    Priority::High => "high".to_string(),
                });

                match db::create_task(&mut db, &title, desc, prio_str, labels) {
                    Ok(id) => {
                        println!("Task {} (\"{}\") created successfully.", id, title);
                    }
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        process::exit(2);
                    }
                }
            }
            TaskCommands::List { status, priority, label, output } => {
                let db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        process::exit(1);
                    }
                };

                let mut output_fmt = match output {
                    Format::Table => "table".to_string(),
                    Format::Json => "json".to_string(),
                    Format::Csv => "csv".to_string(),
                };

                if output_fmt == "table" {
                    if let Ok(cfg) = db::load_config() {
                        output_fmt = cfg.default_output;
                    }
                }

                // Filter in-memory
                let mut filtered = db.tasks.clone();

                if let Some(s) = status {
                    let s_str = match s {
                        Status::Todo => "todo",
                        Status::Doing => "doing",
                        Status::Done => "done",
                    };
                    filtered.retain(|t| t.status.to_lowercase() == s_str);
                }

                if let Some(p) = priority {
                    let p_str = match p {
                        Priority::Low => "low",
                        Priority::Medium => "medium",
                        Priority::High => "high",
                    };
                    filtered.retain(|t| t.priority.to_lowercase() == p_str);
                }

                if let Some(lbl) = label {
                    filtered.retain(|t| t.labels.iter().any(|l| l.to_lowercase() == lbl.to_lowercase()));
                }

                match output_fmt.to_lowercase().as_str() {
                    "json" => format::print_tasks_json(&filtered),
                    "csv" => format::print_tasks_csv(&filtered),
                    _ => format::print_tasks_table(&filtered),
                }
            }
            TaskCommands::Update { id, title, desc, priority, status, labels } => {
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        process::exit(1);
                    }
                };

                let prio_str = priority.map(|p| match p {
                    Priority::Low => "low".to_string(),
                    Priority::Medium => "medium".to_string(),
                    Priority::High => "high".to_string(),
                });

                let status_str = status.map(|s| match s {
                    Status::Todo => "todo".to_string(),
                    Status::Doing => "doing".to_string(),
                    Status::Done => "done".to_string(),
                });

                match db::update_task(&mut db, id, title, desc, prio_str, status_str, labels) {
                    Ok(_) => {
                        println!("Task {} updated successfully.", id);
                    }
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        let msg = e.to_string();
                        let exit_code = if msg.contains("not found") {
                            1
                        } else if msg.contains("priority") || msg.contains("status") {
                            2
                        } else {
                            1
                        };
                        process::exit(exit_code);
                    }
                }
            }
            TaskCommands::Delete { id, force: _ } => {
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        process::exit(1);
                    }
                };

                match db::delete_task(&mut db, id) {
                    Ok(_) => {
                        println!("Task {} deleted successfully.", id);
                    }
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        process::exit(1);
                    }
                }
            }
        },
        Commands::Label(label_args) => match label_args.command {
            LabelCommands::List => {
                let db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        process::exit(1);
                    }
                };
                format::print_labels_table(&db);
            }
            LabelCommands::Create { name } => {
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        process::exit(1);
                    }
                };

                match db::create_label(&mut db, &name) {
                    Ok(slug) => {
                        println!("Label \"{}\" created successfully.", slug);
                    }
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        process::exit(1);
                    }
                }
            }
            LabelCommands::Delete { name } => {
                let mut db = match db::load_db() {
                    Ok(d) => d,
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        process::exit(1);
                    }
                };

                match db::delete_label(&mut db, &name) {
                    Ok(_) => {
                        println!("Label \"{}\" deleted successfully.", name);
                    }
                    Err(e) => {
                        eprintln!("Error: {}", e);
                        process::exit(1);
                    }
                }
            }
        },
        Commands::Report => {
            let db = match db::load_db() {
                Ok(d) => d,
                Err(e) => {
                    eprintln!("Error: {}", e);
                    process::exit(1);
                }
            };
            format::print_sprint_report(&db);
        }
    }
}
