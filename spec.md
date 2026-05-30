# CLI Specification: `murli-work` (Sprint/Project Task Tracker)

This document is the definitive specification for the `murli-work` CLI tool. Every implementation (Go, Rust, Python, TypeScript) must match this specification **exactly** in commands, subcommands, options, validation rules, data persistence, and terminal output formats.

To keep the template skeletons simple yet fully functional:
- The application stores data in a flat JSON file (`db.json`) and reads preferences from `config.json`.
- **Active Flat-File Writing is Supported:** All mutating commands (like `create`, `update`, and `delete`) read the database file from disk, validate parameters, apply changes in-memory, and overwrite the JSON file.
- **`murli-work init` acts as a Clean Reset:** Calling `murli-work init` creates the default config and **overwrites/resets** the database back to a pre-configured baseline of **5 rich sample tasks and 6 labels**. This serves as a self-healing tool or a quick way to restore the database to a predictable baseline for live **Murli** demonstrations.
- **Self-Healing on Missing Database:** If any command is run and `db.json` or `config.json` is missing, the application automatically initializes them with the default pre-populated dataset.

---

## 1. Storage & Persistence Configuration

The application reads from and writes to a local JSON database file (`db.json`) and a configuration file (`config.json`).

### 1.1 Storage Directory Paths
Implementations must use the standard user configuration directory for the respective OS:
- **macOS**: `~/Library/Application Support/murli-work/`
- **Linux**: `~/.config/murli-work/` (or respect `$XDG_CONFIG_HOME/murli-work/` if set)
- **Windows**: `%APPDATA%\murli-work\`

### 1.2 Flat File Initialization Schemas

#### Configuration File: `config.json`
If the file does not exist (or when `murli-work init` is called), implementations must write the following default:
```json
{
  "default_output": "table",
  "default_priority": "medium"
}
```

#### Database File: `db.json`
If the file does not exist (or when `murli-work init` is called), implementations must write/reset it with the following pre-populated sample sprint data:
```json
{
  "tasks": [
    {
      "id": 1,
      "title": "Setup workspace layout",
      "desc": "Bootstrap directory structures for Go, Rust, Python and TS",
      "status": "done",
      "priority": "high",
      "labels": ["setup", "dev"],
      "created_at": "2026-05-28T18:00:00Z"
    },
    {
      "id": 2,
      "title": "Document CLI specification",
      "desc": "Draft the spec.md contracts and database JSON schemas",
      "status": "done",
      "priority": "medium",
      "labels": ["docs"],
      "created_at": "2026-05-28T18:30:00Z"
    },
    {
      "id": 3,
      "title": "Implement Cobra skeleton",
      "desc": "Build the Go Cobra reference implementation",
      "status": "doing",
      "priority": "high",
      "labels": ["dev", "go"],
      "created_at": "2026-05-29T04:00:00Z"
    },
    {
      "id": 4,
      "title": "Integrate Murli middleware",
      "desc": "Apply Murli wrappers to standard Go binaries",
      "status": "todo",
      "priority": "high",
      "labels": ["dev", "murli"],
      "created_at": "2026-05-29T05:00:00Z"
    },
    {
      "id": 5,
      "title": "Write Rust Clap reference",
      "desc": "Develop Rust-native Clap derive parser",
      "status": "todo",
      "priority": "medium",
      "labels": ["dev", "rust"],
      "created_at": "2026-05-29T06:00:00Z"
    }
  ],
  "labels": [
    { "name": "setup" },
    { "name": "dev" },
    { "name": "docs" },
    { "name": "go" },
    { "name": "murli" },
    { "name": "rust" }
  ]
}
```

---

## 2. Command Tree & Options Specification

All commands must output help messages if invoked with `--help` or `-h`.

### 2.1 `murli-work init`
Resets/initializes the storage directory, writing/overwriting `config.json` and `db.json` back to their default pre-populated states.
- **Arguments**: None.
- **Output (Stdout)**:
  - `Initialized/Reset murli-work database with sample data and configuration in <directory_path>`
- **Exit Code**: `0` on success, `1` on write failure.

### 2.2 `murli-work task create <title>`
Adds a new task to the database.
- **Arguments**:
  - `title`: Positional string (required). If omitted, parsing error (Exit Code 2).
- **Options/Flags**:
  - `--desc`, `-d`: String description. Default: `""`.
  - `--priority`, `-p`: String choice. Allowed: `low`, `medium`, `high`. If an invalid value is passed, print validation error (Exit Code 2).
  - `--labels`, `-l`: String of comma-separated labels (e.g. `dev,bug`).
- **Behavior**:
  - Validates options (checks if priority is `low|medium|high`).
  - Automatically initializes the database with default sample data if missing.
  - Reads `db.json`. Computes the next task ID by finding the highest current task ID and adding 1.
  - Slugifies new labels and adds them to the global labels array in `db.json` if not already present.
  - Appends the new task object with `created_at` set to the current ISO-8601 UTC timestamp.
  - Overwrites the flat `db.json` file.
- **Output (Stdout)**:
  - `Task <id> ("<title>") created successfully.`
- **Exit Code**: `0` on success, `1` on write failure, `2` on parsing/validation error.

### 2.3 `murli-work task list`
Lists stored tasks, supporting filtering and formatting.
- **Arguments**: None.
- **Options/Flags**:
  - `--status`, `-s`: String choice. Allowed: `todo`, `doing`, `done`.
  - `--priority`, `-p`: String choice. Allowed: `low`, `medium`, `high`.
  - `--label`, `-l`: String filter by a single label.
  - `--output`, `-o`: String choice. Allowed: `table`, `json`, `csv`. Default: `table` (or value in `config.json` if present).
- **Output (Stdout)**:
  - Output must match the requested format. See **Section 3** for exact formats.
- **Exit Code**: `0` on success, `1` on reading error, `2` on validation/parsing error.

### 2.4 `murli-work task update <id>`
Updates one or more fields of an existing task.
- **Arguments**:
  - `id`: Positional integer (required).
- **Options/Flags**:
  - `--title`, `-t`: New title.
  - `--desc`, `-d`: New description.
  - `--priority`, `-p`: New priority choice (`low`, `medium`, `high`).
  - `--status`, `-s`: New status choice (`todo`, `doing`, `done`).
  - `--labels`, `-l`: Comma-separated labels to replace the current labels completely.
- **Behavior**:
  - Reads `db.json`. Validates that `<id>` exists. If not found, print `Error: Task with ID <id> not found.` to stderr (Exit Code 1).
  - Validates priority/status flags if provided.
  - Updates only the specified flags. Any omitted options are left unchanged in the database.
  - Slugifies new labels and auto-adds them to the global labels list if not already present.
  - Overwrites the flat `db.json` file.
- **Output (Stdout)**:
  - `Task <id> updated successfully.`
- **Exit Code**: `0` on success, `1` on runtime error (task not found / write failure), `2` on argument parsing/validation error.

### 2.5 `murli-work task delete <id>`
Deletes a task from the database.
- **Arguments**:
  - `id`: Positional integer (required).
- **Behavior**:
  - Reads `db.json`. Validates that `<id>` exists. If not found, print `Error: Task with ID <id> not found.` to stderr (Exit Code 1).
  - Removes the task object matching the `<id>` from the tasks array.
  - Overwrites the flat `db.json` file.
- **Output (Stdout)**:
  - `Task <id> deleted successfully.`
- **Exit Code**: `0` on success, `1` on runtime error, `2` on parsing error.

### 2.6 `murli-work label list`
Lists all defined labels and how many tasks they are assigned to.
- **Arguments**: None.
- **Output (Stdout)**:
  - Table or list of labels with their usage count. See **Section 3** for format.
- **Exit Code**: `0` on success, `1` on database reading error.

### 2.7 `murli-work label create <name>`
Creates a new custom label.
- **Arguments**:
  - `name`: Positional string (required).
- **Behavior**:
  - Reads `db.json`. Slugifies the label name (lowercase, converts spaces/special chars to hyphens).
  - If the label already exists in the labels list, print `Error: Label "<slugified_name>" already exists.` to stderr (Exit Code 1).
  - Appends `{ "name": "<slugified_name>" }` to the labels array.
  - Overwrites the flat `db.json` file.
- **Output (Stdout)**:
  - `Label "<slugified_name>" created successfully.`
- **Exit Code**: `0` on success, `1` on runtime error (already exists / write failure), `2` on parsing error.

### 2.8 `murli-work label delete <name>`
Deletes a label from the database.
- **Arguments**:
  - `name`: Positional string (required).
- **Behavior**:
  - Reads `db.json`. Checks if label exists in the labels list. If not, print `Error: Label "<name>" not found.` to stderr (Exit Code 1).
  - Deletes the label object from the labels array.
  - Scans all tasks and removes the string reference to this label from their `labels` arrays.
  - Overwrites the flat `db.json` file.
- **Output (Stdout)**:
  - `Label "<name>" deleted successfully.`
- **Exit Code**: `0` on success, `1` on runtime error, `2` on parsing error.

### 2.9 `murli-work report`
Outputs a high-level summary of the tasks currently in the database and exits.
- **Arguments**: None.
- **Output (Stdout)**:
  - Print summary metrics (completed vs total, percentage complete, count by priority) based on actual live items in `db.json`. See **Section 3** for exact formats.
- **Exit Code**: `0` on success, `1` on database reading error.

---

## 3. Output Formatting Standards

To ensure uniformity across all implementations, outputs must follow these guidelines:

### 3.1 Standard Tables (`--output table`)
When displaying tasks, use a simple ASCII table. 
Headers: `ID | Title | Status | Priority | Labels`
- Columns should be aligned with spaces.
- Separators can be `-` and `|` characters.
- Statuses must have consistent casing: `TODO`, `DOING`, `DONE`.
- Priorities must have consistent casing: `LOW`, `MEDIUM`, `HIGH`.
- Labels must be joined by commas (e.g. `dev,bug`).

Example matching the default initialized database:
```text
+----+----------------------+--------+----------+------------+
| ID | Title                | Status | Priority | Labels     |
+----+----------------------+--------+----------+------------+
| 1  | Setup workspace layout| DONE   | HIGH     | setup,dev  |
| 2  | Document CLI spec    | DONE   | MEDIUM   | docs       |
| 3  | Implement Cobra skeleton| DOING  | HIGH     | dev,go     |
| 4  | Integrate Murli      | TODO   | HIGH     | dev,murli  |
| 5  | Write Rust Clap      | TODO   | MEDIUM   | dev,rust   |
+----+----------------------+--------+----------+------------+
```

### 3.2 CSV Output (`--output csv`)
Comma-separated values with headers on the first line. Optional values must be printed as empty strings. Labels must be separated by semicolons (`;`) inside the double-quotes to avoid CSV parsing collision.

Example:
```csv
id,title,status,priority,labels
1,"Setup workspace layout",done,high,"setup;dev"
2,"Document CLI spec",done,medium,docs
3,"Implement Cobra skeleton",doing,high,"dev;go"
4,"Integrate Murli",todo,high,"dev;murli"
5,"Write Rust Clap",todo,medium,"dev;rust"
```

### 3.3 JSON Output (`--output json`)
Outputs a raw minified or pretty-printed JSON array of task objects matching the JSON Database Task structure.

Example:
```json
[
  {
    "id": 1,
    "title": "Setup workspace layout",
    "desc": "Bootstrap directory structures for Go, Rust, Python and TS",
    "status": "done",
    "priority": "high",
    "labels": ["setup", "dev"],
    "created_at": "2026-05-28T18:00:00Z"
  }
]
```

### 3.4 Label List Layout
For `murli-work label list`, output a simple table:
```text
+-------------+-------------+
| Label Name  | Task Count  |
+-------------+-------------+
| setup       | 1           |
| dev         | 4           |
| docs        | 1           |
| go          | 1           |
| murli       | 1           |
| rust        | 1           |
+-------------+-------------+
```

### 3.5 Progress Report Layout
For `murli-work report`, output a structured, visual dashboard (values adjust dynamically based on actual tasks in `db.json`):
```text
========================================
          MURLI-WORK SPRINT REPORT      
========================================
Completion Rate : [■■■■□□□□□□] 40% (2/5 tasks)

Status Breakdown:
- TODO  : 2 tasks
- DOING : 1 tasks
- DONE  : 2 tasks

Priority Breakdown:
- HIGH  : 3 tasks
- MEDIUM: 2 tasks
- LOW   : 0 tasks
========================================
```

---

## 4. Exit Code Contract

All implementations must follow strict exit codes to allow robust scripting:

- **`0`**: Successful execution.
- **`1`**: Runtime application errors (e.g., requested task or label ID not found, write permissions failure).
- **`2`**: Command parsing or argument/flag validation errors (e.g., missing required argument, passing invalid value to `--priority` or `--status`).
