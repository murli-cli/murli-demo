import * as path from "path";
import * as os from "os";
import * as fs from "fs";

export interface Task {
  id: number;
  title: string;
  desc: string;
  status: "todo" | "doing" | "done";
  priority: "low" | "medium" | "high";
  labels: string[];
  created_at: string;
}

export interface Label {
  name: string;
}

export interface Database {
  tasks: Task[];
  labels: Label[];
}

export interface Config {
  default_output: string;
  default_priority: string;
}

export function getStorageDir(): string {
  const homedir = os.homedir();
  if (process.platform === "win32") {
    return path.join(process.env.APPDATA || path.join(homedir, "AppData", "Roaming"), "murli-work");
  } else if (process.platform === "darwin") {
    return path.join(homedir, "Library", "Application Support", "murli-work");
  } else {
    return path.join(process.env.XDG_CONFIG_HOME || path.join(homedir, ".config"), "murli-work");
  }
}

export function getDefaultDb(): Database {
  return {
    tasks: [
      { id: 1, title: "Setup workspace layout", desc: "Bootstrap directory structures for Go, Rust, Python and TS", status: "done", priority: "high", labels: ["setup", "dev"], created_at: "2026-05-28T18:00:00Z" },
      { id: 2, title: "Document CLI spec", desc: "Draft the spec.md contracts and database JSON schemas", status: "done", priority: "medium", labels: ["docs"], created_at: "2026-05-28T18:30:00Z" },
      { id: 3, title: "Implement Cobra skeleton", desc: "Build the Go Cobra reference implementation", status: "doing", priority: "high", labels: ["dev", "go"], created_at: "2026-05-29T04:00:00Z" },
      { id: 4, title: "Integrate Murli middleware", desc: "Apply Murli wrappers to standard Go binaries", status: "todo", priority: "high", labels: ["dev", "murli"], created_at: "2026-05-29T05:00:00Z" },
      { id: 5, title: "Write Rust Clap reference", desc: "Develop Rust-native Clap derive parser", status: "todo", priority: "medium", labels: ["dev", "rust"], created_at: "2026-05-29T06:00:00Z" }
    ],
    labels: [
      { name: "setup" },
      { name: "dev" },
      { name: "docs" },
      { name: "go" },
      { name: "murli" },
      { name: "rust" }
    ]
  };
}

export function getDefaultConfig(): Config {
  return {
    default_output: "table",
    default_priority: "medium"
  };
}

export function resetDb(): void {
  const dir = getStorageDir();
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "config.json"), JSON.stringify(getDefaultConfig(), null, 2), "utf8");
  fs.writeFileSync(path.join(dir, "db.json"), JSON.stringify(getDefaultDb(), null, 2), "utf8");
}

export function loadDb(): Database {
  const dir = getStorageDir();
  const dbPath = path.join(dir, "db.json");
  if (!fs.existsSync(dbPath)) {
    resetDb();
  }
  return JSON.parse(fs.readFileSync(dbPath, "utf8"));
}

export function saveDb(db: Database): void {
  const dir = getStorageDir();
  const dbPath = path.join(dir, "db.json");
  fs.writeFileSync(dbPath, JSON.stringify(db, null, 2), "utf8");
}

export function loadConfig(): Config {
  const dir = getStorageDir();
  const cfgPath = path.join(dir, "config.json");
  if (!fs.existsSync(cfgPath)) {
    resetDb();
  }
  return JSON.parse(fs.readFileSync(cfgPath, "utf8"));
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function autoCreateLabel(db: Database, name: string): void {
  const slug = slugify(name);
  if (!slug) return;
  if (db.labels.some((l) => l.name === slug)) return;
  db.labels.push({ name: slug });
}

// Mutations
export function createTask(
  db: Database,
  title: string,
  desc = "",
  priority?: string,
  rawLabels: string[] = []
): number {
  let prio = priority;
  if (!prio) {
    try {
      const cfg = loadConfig();
      prio = cfg.default_priority;
    } catch {
      prio = "medium";
    }
  }

  prio = prio.toLowerCase();
  if (prio !== "low" && prio !== "medium" && prio !== "high") {
    throw new Error("invalid priority (low|medium|high)");
  }

  let nextId = 1;
  for (const t of db.tasks) {
    if (t.id >= nextId) {
      nextId = t.id + 1;
    }
  }

  const slugLabels: string[] = [];
  for (const l of rawLabels) {
    const slug = slugify(l);
    if (slug) {
      autoCreateLabel(db, slug);
      slugLabels.push(slug);
    }
  }

  const newTask: Task = {
    id: nextId,
    title,
    desc,
    status: "todo",
    priority: prio as any,
    labels: slugLabels,
    created_at: new Date().toISOString()
  };

  db.tasks.push(newTask);
  saveDb(db);
  return nextId;
}

export function updateTask(
  db: Database,
  id: number,
  title?: string,
  desc?: string,
  priority?: string,
  status?: string,
  rawLabels?: string[]
): void {
  const target = db.tasks.find((t) => t.id === id);
  if (!target) {
    throw new Error(`task with ID ${id} not found`);
  }

  if (title !== undefined && title !== "") {
    target.title = title;
  }
  if (desc !== undefined) {
    target.desc = desc;
  }
  if (priority !== undefined && priority !== "") {
    const p = priority.toLowerCase();
    if (p !== "low" && p !== "medium" && p !== "high") {
      throw new Error("invalid priority (low|medium|high)");
    }
    target.priority = p as any;
  }
  if (status !== undefined && status !== "") {
    const s = status.toLowerCase();
    if (s !== "todo" && s !== "doing" && s !== "done") {
      throw new Error("invalid status (todo|doing|done)");
    }
    target.status = s as any;
  }
  if (rawLabels !== undefined) {
    const slugLabels: string[] = [];
    for (const l of rawLabels) {
      const slug = slugify(l);
      if (slug) {
        autoCreateLabel(db, slug);
        slugLabels.push(slug);
      }
    }
    target.labels = slugLabels;
  }

  saveDb(db);
}

export function deleteTask(db: Database, id: number): void {
  const idx = db.tasks.findIndex((t) => t.id === id);
  if (idx === -1) {
    throw new Error(`task with ID ${id} not found`);
  }
  db.tasks.splice(idx, 1);
  saveDb(db);
}

export function createLabel(db: Database, name: string): string {
  const slug = slugify(name);
  if (!slug) {
    throw new Error("invalid label name");
  }
  if (db.labels.some((l) => l.name === slug)) {
    throw new Error(`label "${slug}" already exists`);
  }
  db.labels.push({ name: slug });
  saveDb(db);
  return slug;
}

export function deleteLabel(db: Database, name: string): void {
  const slug = slugify(name);
  const idx = db.labels.findIndex((l) => l.name === slug);
  if (idx === -1) {
    throw new Error(`label "${name}" not found`);
  }
  db.labels.splice(idx, 1);

  // Remove from all tasks
  for (const t of db.tasks) {
    t.labels = t.labels.filter((lbl) => lbl !== slug);
  }
  saveDb(db);
}
