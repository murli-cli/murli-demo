use serde::{Deserialize, Serialize};
use std::env;
use std::fs;
use std::path::PathBuf;
use std::time::SystemTime;
use chrono::{DateTime, Utc};

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct Task {
    pub id: u32,
    pub title: String,
    pub desc: String,
    pub status: String,
    pub priority: String,
    pub labels: Vec<String>,
    pub created_at: String,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct Label {
    pub name: String,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct Database {
    pub tasks: Vec<Task>,
    pub labels: Vec<Label>,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct Config {
    pub default_output: String,
    pub default_priority: String,
}

pub fn get_storage_dir() -> PathBuf {
    let mut path = PathBuf::new();
    if cfg!(target_os = "windows") {
        if let Ok(app_data) = env::var("APPDATA") {
            path.push(app_data);
        } else if let Ok(home) = env::var("USERPROFILE") {
            path.push(home);
            path.push("AppData");
            path.push("Roaming");
        }
    } else if cfg!(target_os = "macos") {
        if let Ok(home) = env::var("HOME") {
            path.push(home);
            path.push("Library");
            path.push("Application Support");
        }
    } else {
        if let Ok(xdg) = env::var("XDG_CONFIG_HOME") {
            path.push(xdg);
        } else if let Ok(home) = env::var("HOME") {
            path.push(home);
            path.push(".config");
        }
    }
    path.push("murli-work");
    path
}

pub fn get_default_db() -> Database {
    Database {
        tasks: vec![
            Task { id: 1, title: "Setup workspace layout".into(), desc: "Bootstrap directory structures for Go, Rust, Python and TS".into(), status: "done".into(), priority: "high".into(), labels: vec!["setup".to_string(), "dev".to_string()], created_at: "2026-05-28T18:00:00Z".into() },
            Task { id: 2, title: "Document CLI spec".into(), desc: "Draft the spec.md contracts and database JSON schemas".into(), status: "done".into(), priority: "medium".into(), labels: vec!["docs".to_string()], created_at: "2026-05-28T18:30:00Z".into() },
            Task { id: 3, title: "Implement Cobra skeleton".into(), desc: "Build the Go Cobra reference implementation".into(), status: "doing".into(), priority: "high".into(), labels: vec!["dev".to_string(), "go".to_string()], created_at: "2026-05-29T04:00:00Z".into() },
            Task { id: 4, title: "Integrate Murli middleware".into(), desc: "Apply Murli wrappers to standard Go binaries".into(), status: "todo".into(), priority: "high".into(), labels: vec!["dev".to_string(), "murli".to_string()], created_at: "2026-05-29T05:00:00Z".into() },
            Task { id: 5, title: "Write Rust Clap reference".into(), desc: "Develop Rust-native Clap derive parser".into(), status: "todo".into(), priority: "medium".into(), labels: vec!["dev".to_string(), "rust".to_string()], created_at: "2026-05-29T06:00:00Z".into() },
        ],
        labels: vec![
            Label { name: "setup".into() },
            Label { name: "dev".into() },
            Label { name: "docs".into() },
            Label { name: "go".into() },
            Label { name: "murli".into() },
            Label { name: "rust".into() },
        ],
    }
}

pub fn get_default_config() -> Config {
    Config {
        default_output: "table".into(),
        default_priority: "medium".into(),
    }
}

pub fn reset_db() -> Result<(), Box<dyn std::error::Error>> {
    let dir = get_storage_dir();
    fs::create_dir_all(&dir)?;

    let config_data = serde_json::to_string_pretty(&get_default_config())?;
    fs::write(dir.join("config.json"), config_data)?;

    let db_data = serde_json::to_string_pretty(&get_default_db())?;
    fs::write(dir.join("db.json"), db_data)?;

    Ok(())
}

pub fn load_db() -> Result<Database, Box<dyn std::error::Error>> {
    let dir = get_storage_dir();
    let db_path = dir.join("db.json");
    if !db_path.exists() {
        reset_db()?;
    }
    let data = fs::read_to_string(db_path)?;
    let db: Database = serde_json::from_str(&data)?;
    Ok(db)
}

pub fn save_db(db: &Database) -> Result<(), Box<dyn std::error::Error>> {
    let dir = get_storage_dir();
    let db_path = dir.join("db.json");
    let data = serde_json::to_string_pretty(db)?;
    fs::write(db_path, data)?;
    Ok(())
}

pub fn load_config() -> Result<Config, Box<dyn std::error::Error>> {
    let dir = get_storage_dir();
    let cfg_path = dir.join("config.json");
    if !cfg_path.exists() {
        reset_db()?;
    }
    let data = fs::read_to_string(cfg_path)?;
    let cfg: Config = serde_json::from_str(&data)?;
    Ok(cfg)
}

pub fn slugify(text: &str) -> String {
    let text = text.to_lowercase();
    let mut result = String::new();
    let mut last_was_dash = false;
    for c in text.chars() {
        if c.is_alphanumeric() {
            result.push(c);
            last_was_dash = false;
        } else if !last_was_dash {
            result.push('-');
            last_was_dash = true;
        }
    }
    result.trim_matches('-').to_string()
}

pub fn auto_create_label(db: &mut Database, name: &str) {
    let slug = slugify(name);
    if slug.is_empty() {
        return;
    }
    if db.labels.iter().any(|l| l.name == slug) {
        return;
    }
    db.labels.push(Label { name: slug });
}

// Mutations
pub fn create_task(
    db: &mut Database,
    title: &str,
    desc: Option<String>,
    priority: Option<String>,
    raw_labels: Vec<String>,
) -> Result<u32, Box<dyn std::error::Error>> {
    let mut prio = match priority {
        Some(p) => p,
        None => {
            if let Ok(cfg) = load_config() {
                cfg.default_priority
            } else {
                "medium".to_string()
            }
        }
    };

    prio = prio.to_lowercase();
    if prio != "low" && prio != "medium" && prio != "high" {
        return Err("invalid priority (low|medium|high)".into());
    }

    let mut next_id = 1;
    for t in &db.tasks {
        if t.id >= next_id {
            next_id = t.id + 1;
        }
    }

    let mut slug_labels = Vec::new();
    for l in raw_labels {
        let slug = slugify(&l);
        if !slug.is_empty() {
            auto_create_label(db, &slug);
            slug_labels.push(slug);
        }
    }

    let now: DateTime<Utc> = SystemTime::now().into();
    let created_at = now.format("%Y-%m-%dT%H:%M:%SZ").to_string();

    let new_task = Task {
        id: next_id,
        title: title.to_string(),
        desc: desc.unwrap_or_default(),
        status: "todo".to_string(),
        priority: prio,
        labels: slug_labels,
        created_at,
    };

    db.tasks.push(new_task);
    save_db(db)?;
    Ok(next_id)
}

pub fn update_task(
    db: &mut Database,
    id: u32,
    title: Option<String>,
    desc: Option<String>,
    priority: Option<String>,
    status: Option<String>,
    raw_labels: Option<Vec<String>>,
) -> Result<(), Box<dyn std::error::Error>> {
    let idx = db.tasks.iter().position(|t| t.id == id);
    if idx.is_none() {
        return Err(format!("task with ID {} not found", id).into());
    }
    let idx = idx.unwrap();

    let mut slug_labels = Vec::new();
    let has_labels = raw_labels.is_some();
    if let Some(labels) = raw_labels {
        for l in labels {
            let slug = slugify(&l);
            if !slug.is_empty() {
                auto_create_label(db, &slug);
                slug_labels.push(slug);
            }
        }
    }

    let t = &mut db.tasks[idx];

    if let Some(val) = title {
        if !val.is_empty() {
            t.title = val;
        }
    }
    if let Some(val) = desc {
        t.desc = val;
    }
    if let Some(val) = priority {
        if !val.is_empty() {
            let p = val.to_lowercase();
            if p != "low" && p != "medium" && p != "high" {
                return Err("invalid priority (low|medium|high)".into());
            }
            t.priority = p;
        }
    }
    if let Some(val) = status {
        if !val.is_empty() {
            let s = val.to_lowercase();
            if s != "todo" && s != "doing" && s != "done" {
                return Err("invalid status (todo|doing|done)".into());
            }
            t.status = s;
        }
    }
    if has_labels {
        t.labels = slug_labels;
    }

    save_db(db)?;
    Ok(())
}

pub fn delete_task(db: &mut Database, id: u32) -> Result<(), Box<dyn std::error::Error>> {
    let idx = db.tasks.iter().position(|t| t.id == id);
    if idx.is_none() {
        return Err(format!("task with ID {} not found", id).into());
    }
    db.tasks.remove(idx.unwrap());
    save_db(db)?;
    Ok(())
}

pub fn create_label(db: &mut Database, name: &str) -> Result<String, Box<dyn std::error::Error>> {
    let slug = slugify(name);
    if slug.is_empty() {
        return Err("invalid label name".into());
    }
    if db.labels.iter().any(|l| l.name == slug) {
        return Err(format!("label \"{}\" already exists", slug).into());
    }
    db.labels.push(Label { name: slug.clone() });
    save_db(db)?;
    Ok(slug)
}

pub fn delete_label(db: &mut Database, name: &str) -> Result<(), Box<dyn std::error::Error>> {
    let slug = slugify(name);
    let idx = db.labels.iter().position(|l| l.name == slug);
    if idx.is_none() {
        return Err(format!("label \"{}\" not found", name).into());
    }
    db.labels.remove(idx.unwrap());

    // Remove from all tasks
    for t in &mut db.tasks {
        t.labels.retain(|lbl| lbl != &slug);
    }
    save_db(db)?;
    Ok(())
}
