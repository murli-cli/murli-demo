"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.getStorageDir = getStorageDir;
exports.getDefaultDb = getDefaultDb;
exports.getDefaultConfig = getDefaultConfig;
exports.resetDb = resetDb;
exports.loadDb = loadDb;
exports.saveDb = saveDb;
exports.loadConfig = loadConfig;
exports.slugify = slugify;
exports.autoCreateLabel = autoCreateLabel;
exports.createTask = createTask;
exports.updateTask = updateTask;
exports.deleteTask = deleteTask;
exports.createLabel = createLabel;
exports.deleteLabel = deleteLabel;
const path = __importStar(require("path"));
const os = __importStar(require("os"));
const fs = __importStar(require("fs"));
function getStorageDir() {
    const homedir = os.homedir();
    if (process.platform === "win32") {
        return path.join(process.env.APPDATA || path.join(homedir, "AppData", "Roaming"), "murli-work");
    }
    else if (process.platform === "darwin") {
        return path.join(homedir, "Library", "Application Support", "murli-work");
    }
    else {
        return path.join(process.env.XDG_CONFIG_HOME || path.join(homedir, ".config"), "murli-work");
    }
}
function getDefaultDb() {
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
function getDefaultConfig() {
    return {
        default_output: "table",
        default_priority: "medium"
    };
}
function resetDb() {
    const dir = getStorageDir();
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, "config.json"), JSON.stringify(getDefaultConfig(), null, 2), "utf8");
    fs.writeFileSync(path.join(dir, "db.json"), JSON.stringify(getDefaultDb(), null, 2), "utf8");
}
function loadDb() {
    const dir = getStorageDir();
    const dbPath = path.join(dir, "db.json");
    if (!fs.existsSync(dbPath)) {
        resetDb();
    }
    return JSON.parse(fs.readFileSync(dbPath, "utf8"));
}
function saveDb(db) {
    const dir = getStorageDir();
    const dbPath = path.join(dir, "db.json");
    fs.writeFileSync(dbPath, JSON.stringify(db, null, 2), "utf8");
}
function loadConfig() {
    const dir = getStorageDir();
    const cfgPath = path.join(dir, "config.json");
    if (!fs.existsSync(cfgPath)) {
        resetDb();
    }
    return JSON.parse(fs.readFileSync(cfgPath, "utf8"));
}
function slugify(text) {
    return text
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
}
function autoCreateLabel(db, name) {
    const slug = slugify(name);
    if (!slug)
        return;
    if (db.labels.some((l) => l.name === slug))
        return;
    db.labels.push({ name: slug });
}
// Mutations
function createTask(db, title, desc = "", priority, rawLabels = []) {
    let prio = priority;
    if (!prio) {
        try {
            const cfg = loadConfig();
            prio = cfg.default_priority;
        }
        catch {
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
    const slugLabels = [];
    for (const l of rawLabels) {
        const slug = slugify(l);
        if (slug) {
            autoCreateLabel(db, slug);
            slugLabels.push(slug);
        }
    }
    const newTask = {
        id: nextId,
        title,
        desc,
        status: "todo",
        priority: prio,
        labels: slugLabels,
        created_at: new Date().toISOString()
    };
    db.tasks.push(newTask);
    saveDb(db);
    return nextId;
}
function updateTask(db, id, title, desc, priority, status, rawLabels) {
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
        target.priority = p;
    }
    if (status !== undefined && status !== "") {
        const s = status.toLowerCase();
        if (s !== "todo" && s !== "doing" && s !== "done") {
            throw new Error("invalid status (todo|doing|done)");
        }
        target.status = s;
    }
    if (rawLabels !== undefined) {
        const slugLabels = [];
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
function deleteTask(db, id) {
    const idx = db.tasks.findIndex((t) => t.id === id);
    if (idx === -1) {
        throw new Error(`task with ID ${id} not found`);
    }
    db.tasks.splice(idx, 1);
    saveDb(db);
}
function createLabel(db, name) {
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
function deleteLabel(db, name) {
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
