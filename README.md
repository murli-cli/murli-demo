This repository serves as a unified blueprint to demonstrate the application of the **Murli CLI middleware** on top of standardized reference implementations across **five programming languages** and **nine distinct CLI frameworks**.

While the templates provide clean, skeletal implementations of a CLI tool, their true purpose is to demonstrate how **Murli** can be applied on top of them to achieve consistent, dual-audience (human and AI agent) capabilities across different languages and library ecosystems.

The target CLI application is named **`murli-work`** to prevent collisions with standard shell verb aliases.

---

## 🌿 Branch Strategy: Skeletons vs. Murli Integrations

To keep the repository clean and allow developers to compare the "before" and "after" state of the CLI tools:

1. **`main` Branch (Skeletons Only):**
   - Contains only the clean, framework-specific reference implementations (the skeletons) without any Murli middleware.
   - Ideal for starting a fresh integration or studying standard framework patterns.
2. **Feature Branches (Murli Integrations):**
   - The integration of **Murli CLI middleware** is managed on a dedicated feature branch for each language and library.
   - **Branch Naming:** `<language>/<library>` (e.g., `go/cobra`, `python/click`).
   - Each branch includes the fully wrapped application, a detailed integration guide (e.g., `PYTHON-CLICK-GUIDE.md`), and committed terminal outputs showing TTY-awareness and agent modes in action.

### Completed Integration Branches

| Branch | Language | Framework | Guide |
| :--- | :--- | :--- | :--- |
| [`go/cobra`](../../tree/go/cobra) | Go | spf13/cobra | `GO-COBRA-GUIDE.md` |
| [`go/urfavecliv2`](../../tree/go/urfavecliv2) | Go | urfave/cli v2 | `GO-URFAVECLIV2-GUIDE.md` |
| [`go/urfavecliv3`](../../tree/go/urfavecliv3) | Go | urfave/cli v3 | `GO-URFAVECLIV3-GUIDE.md` |
| [`python/click`](../../tree/python/click) | Python | click | `PYTHON-CLICK-GUIDE.md` |
| [`python/typer`](../../tree/python/typer) | Python | typer | `PYTHON-TYPER-GUIDE.md` |
| [`python/argparse`](../../tree/python/argparse) | Python | argparse | `PYTHON-ARGPARSE-GUIDE.md` |
| [`typescript/commander`](../../tree/typescript/commander) | TypeScript | commander | `TYPESCRIPT-COMMANDER-GUIDE.md` |

---

## 🎯 The Purpose: Consistent Murli Demonstrations

Integrating CLI tools with AI agents usually requires different boilerplate, schema structures, and error formats depending on the language and parser used. 

**Murli** solves this by standardizing CLI behaviors. This repository demonstrates Murli's ability to overlay a consistent interface on top of standard library structures:
1. **Introspection:** Auto-generating uniform command trees via `describe` schemas.
2. **Dual-Audience output:** Seamlessly switching between human-friendly ANSI text in a TTY and structured JSON envelopes (`{"status":"ok", ...}`) when piped or run by an AI agent (via `--agent`).
3. **Structured Errors:** Consistent exit code behavior and machine-readable error suggestion envelopes.
4. **Safety & Dry-runs:** Standardizing `--dry-run` and `--force` flags.

By utilizing the exact same reference CLI application (**`murli-work`** — a sprint task tracker) across all templates, we can showcase Murli's consistent developer experience regardless of the underlying stack (Go, Rust, Python, or TypeScript).

---

## 🚀 Getting Started with the Makefile

A unified [Makefile](Makefile) in the root directory allows you to manage dependencies, compile all binaries, and run implementations side-by-side. All compiled executables and scripts are compiled into a shared `./bin/` folder under the **`murli-work-*`** namespace.

### 1. Install Dependencies (Go modules, Python & TypeScript)
```bash
make install-deps
```

### 2. Build Skeletons (Outputs binaries and scripts to `./bin/`)
```bash
# Build Go, Rust, TS, and Zig, and set up Python direct execution scripts
make build-all

# Or build individually
make build-go          # Builds Go Cobra & urfave/cli (murli-work-go-*)
make build-rust-clap   # Compiles Rust Clap (murli-work-rust-clap)
make build-zig         # Compiles Zig Clap (murli-work-zig)
make build-ts          # Transpiles Commander, Yargs, and Oclif (murli-work-ts-*)
make build-py          # Scaffolds executable Python wrappers (murli-work-py-*)
```

### 3. Run and Compare Implementations
You can run any template directly from `./bin/` or using `make run-*`. Use the `CMD` variable to pass arguments and flags:

```bash
# Get help menus
make run-go-cobra
make run-rust-clap
make run-zig
make run-py-typer

# Pass active parameters
make run-go-cobra CMD="task create 'My New Task' --priority high"
make run-rust-clap CMD="task create 'My New Task' --priority high"
make run-zig CMD="task create 'My New Task' --priority high"
make run-py-typer CMD="task create 'My New Task' --priority high"
make run-ts-commander CMD="task create 'My New Task' --priority high"
```

### 4. Cleanup Build Artifacts
```bash
make clean
```

---

## 🚀 The CLI Specification: `murli-work`

For a rigorous, detailed guide on the reference command parameters, validation rules, output structures, and data schemas, read the specification:
👉 **[spec.md](spec.md)**

---

## 📂 Repository Layout

```
├── README.md               # You are here
├── Makefile                # Unified build/run system
├── spec.md                 # Definitive command specification (Source of Truth)
├── data-schemas/           # Shared JSON validation schemas
│   ├── config.schema.json  # Schema for configuration settings
│   └── db.schema.json      # Schema for database tasks/labels list
│
├── go/                     # Go Skeletons (Ready for murli wrap)
│   ├── cobra/              # spf13/cobra modules
│   └── urfave/             # urfave/cli modules
│
├── rust/                   # Rust Skeletons (Target for murli-rust ports)
│   └── clap/               # Rust Cargo + clap structures
│
├── python/                 # Python Skeletons (Target for murli-python ports)
│   ├── click/              # click definitions
│   ├── typer/              # typer definitions
│   └── argparse/           # argparse standard library mappings
│
└── typescript/             # TypeScript / Node.js Skeletons (Target for murli-ts ports)
    ├── commander/          # commander structure
    ├── yargs/              # yargs fluent chain
    └── oclif/              # oclif enterprise framework structure
│
└── zig/                    # Zig Skeleton (Target for murli-zig port)
    ├── src/                # Stateless database, format, and main implementation files
    └── build.zig           # Modular build system for Zig 0.16.0
```

---

## 🛠️ Technology Stack & Library Comparison Matrix

Each template represents a benchmark for applying Murli. Below is the matrix of libraries to be wrapped:

| Language | CLI Parser Framework | JSON / Serialization | Recommended Table Library | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Go** | `spf13/cobra` | `encoding/json` (stdlib) | `github.com/olekukonko/tablewriter` | Easily wrapped via the official `murli/cobra` adapter. |
| **Go** | `urfave/cli/v2` | `encoding/json` (stdlib) | `github.com/olekukonko/tablewriter` | Easily wrapped via the official `murli/cli/v2` adapter. |
| **Rust** | `clap` (v4) | `serde_json` | `comfy-table` | Target for future Rust-native Murli adapters. |
| **Python** | `click` | `json` (stdlib) | `tabulate` | Wrapped via `murli[click]` — see [`python/click`](../../tree/python/click). |
| **Python** | `typer` | `json` (stdlib) | `rich` (or `tabulate`) | Wrapped via `murli[typer]` — see [`python/typer`](../../tree/python/typer). |
| **Python** | `argparse` | `json` (stdlib) | manual / `tabulate` | Wrapped via `murli` core — see [`python/argparse`](../../tree/python/argparse). |
| **TypeScript**| `commander` | `JSON` (stdlib) | `cli-table3` | Wrapped via `@murli-cli/commander` — see [`typescript/commander`](../../tree/typescript/commander). |
| **TypeScript**| `yargs` | `JSON` (stdlib) | `cli-table3` | Target for fluent TS-native Murli adapters. |
| **TypeScript**| `oclif` | `JSON` (stdlib) | `@oclif/table` | Multi-command directory framework integration. |
| **Zig**        | `zig-clap` | `std.json` (stdlib)| Manual formatting | Native stateless implementation under Zig 0.16.0. |

---

## 🎯 Implementation Goals for Skeletons

To ensure Murli wrapper demonstrations are consistent across all skeletons, verify the following conditions:

1. **Exact Commands Match:** `murli-work init`, `murli-work task create`, `murli-work task list`, `murli-work task update`, `murli-work task delete`, `murli-work label list`, `murli-work label create`, `murli-work label delete`, and `murli-work report` must exist.
2. **Arguments & Flags Match:** Option names (e.g. `--priority`, `-p`) and short flags must match exactly.
3. **Enum Validation:** Passing values other than `todo|doing|done` to `--status` or `low|medium|high` to `--priority` must fail with an argument validation message and **exit code 2**.
4. **Shared Database Behavior:** Since all implementations target the same storage directory (`~/.config/murli-work/db.json`), writing a task using Python click and running `list` using Go Cobra must work seamlessly!
5. **Output Conformance:** Verify tables, CSV, JSON, and Progress reports align perfectly with the formats shown in the **[spec.md](spec.md)**.
6. **Exit Codes:** Implement standard exits: `0` for success, `1` for logic/database errors, `2` for syntax/argument errors.
