use crate::db::{Database, Task};
use std::collections::HashMap;

pub fn print_tasks_table(tasks: &[Task]) {
    let border = "+----+----------------------+--------+----------+------------+";
    let header = "| ID | Title                | Status | Priority | Labels     |";

    println!("{}", border);
    println!("{}", header);
    println!("{}", border);

    for t in tasks {
        let labels_str = t.labels.join(",");
        let status = t.status.to_uppercase();
        let priority = t.priority.to_uppercase();

        // Safe truncation to avoid panicked out-of-bounds slicing:
        let title_trunc = if t.title.len() > 20 { &t.title[..20] } else { &t.title };
        let status_trunc = if status.len() > 6 { &status[..6] } else { &status };
        let prio_trunc = if priority.len() > 8 { &priority[..8] } else { &priority };
        let labels_trunc = if labels_str.len() > 10 { &labels_str[..10] } else { &labels_str };

        println!(
            "| {:<2} | {:<20} | {:<6} | {:<8} | {:<10} |",
            t.id, title_trunc, status_trunc, prio_trunc, labels_trunc
        );
    }
    println!("{}", border);
}

pub fn print_tasks_csv(tasks: &[Task]) {
    println!("id,title,status,priority,labels");
    for t in tasks {
        let labels_str = t.labels.join(";");
        // Standard double quotes escaping:
        let q_title = format!("\"{}\"", t.title.replace('"', "\"\""));
        let q_labels = format!("\"{}\"", labels_str.replace('"', "\"\""));
        println!("{},{},{},{},{}", t.id, q_title, t.status, t.priority, q_labels);
    }
}

pub fn print_tasks_json(tasks: &[Task]) {
    if let Ok(data) = serde_json::to_string(tasks) {
        println!("{}", data);
    }
}

pub fn print_labels_table(db: &Database) {
    let border = "+-------------+-------------+";
    let header = "| Label Name  | Task Count  |";

    println!("{}", border);
    println!("{}", header);
    println!("{}", border);

    let mut counts = HashMap::new();
    for l in &db.labels {
        counts.insert(l.name.clone(), 0);
    }
    for t in &db.tasks {
        for l in &t.labels {
            if let Some(c) = counts.get_mut(l) {
                *c += 1;
            }
        }
    }

    for l in &db.labels {
        let name_trunc = if l.name.len() > 11 { &l.name[..11] } else { &l.name };
        let count = counts.get(&l.name).cloned().unwrap_or(0);
        println!("| {:<11} | {:<11} |", name_trunc, count);
    }
    println!("{}", border);
}

pub fn print_sprint_report(db: &Database) {
    let total = db.tasks.len();
    let mut completed = 0;
    let mut todo = 0;
    let mut doing = 0;
    let mut done = 0;

    let mut high = 0;
    let mut medium = 0;
    let mut low = 0;

    for t in &db.tasks {
        match t.status.to_lowercase().as_str() {
            "todo" => todo += 1,
            "doing" => doing += 1,
            "done" => {
                done += 1;
                completed += 1;
            }
            _ => {}
        }

        match t.priority.to_lowercase().as_str() {
            "low" => low += 1,
            "medium" => medium += 1,
            "high" => high += 1,
            _ => {}
        }
    }

    let percent = if total > 0 { (completed * 100) / total } else { 0 };
    let progress_blocks = percent / 10;
    
    let mut blocks_str = String::new();
    for i in 0..10 {
        if i < progress_blocks {
            blocks_str.push('■');
        } else {
            blocks_str.push('□');
        }
    }

    println!("========================================");
    println!("          MURLI-WORK SPRINT REPORT      ");
    println!("========================================");
    println!("Completion Rate : [{}] {}% ({}/{}/ tasks)\n", blocks_str, percent, completed, total);
    println!("Status Breakdown:");
    println!("- TODO  : {} tasks", todo);
    println!("- DOING : {} tasks", doing);
    println!("- DONE  : {} tasks\n", done);
    println!("Priority Breakdown:");
    println!("- HIGH  : {} tasks", high);
    println!("- MEDIUM: {} tasks", medium);
    println!("- LOW   : {} tasks", low);
    println!("========================================");
}
