# Murli Integration Guide: Go with Cobra

This guide explains how to systematically integrate the **Murli CLI middleware** (`github.com/murli-cli/murli-go`) into a Go application built with the popular **spf13/cobra** CLI framework.

---

## 🎁 What You Get for Free

By simply replacing Cobra's standard execution call (`rootCmd.Execute()`) with Murli's adapter entry point (`murliCobra.Execute(rootCmd)`), your CLI tool automatically inherits the following powerful features:

1. **Intelligent TTY Detection (Dual-Audience Output):**
   - When run by a human in a terminal (Stdout connected to a TTY), the tool outputs standard pretty text and formatted ASCII tables.
   - When the tool's output is piped to another process or run by an AI agent, Murli automatically switches to structured JSON.
2. **Auto-Injected Standard Flags:**
   - `--agent`: Forces structured JSON output regardless of TTY state.
   - `--schema`: Automatically intercept execution, print the JSON schema of the command, and exit.
   - `--force` / `--yes`: Bypasses any interactive prompts.
   - `--dry-run`: Registers intent to simulate changes (accessible via `w.IsDryRun()`).
   - `--profile <name>`: Loads a named profile.
3. **Auto-Mounted Subcommands:**
   - `describe`: Emits a recursive JSON command tree containing descriptions, safety properties, examples, and flags.
   - `profile`: Direct access to manage flag profile collections.
4. **Log Deduplication:**
   - Collapses duplicate telemetry/logs written to Stderr to optimize AI agent context window consumption.

---

## 🔧 What You Configure

To enable runtime introspection and documentation for AI agents, you attach **Metadata** and annotate command options outside the execution loop.

### 1. Attaching Command Metadata
We attach descriptive definitions to our commands using `murliCobra.Annotate()`:

```go
murliCobra.Annotate(taskCreateCmd, murli.Metadata{
    AgentDescription: "Create a new task in the database.",
    Mutating:         true,
    Arguments: []murli.ArgumentMetadata{
        {Name: "title", Type: "string", Required: true, Description: "Task title"},
    },
})
```

### 2. Attaching Flag Annotations
You can describe flags (such as validation constraints, environment variables, or enums) using `FlagAnnotations` in the command metadata:

```go
murliCobra.Annotate(taskListCmd, murli.Metadata{
    AgentDescription: "List stored sprint tasks with filters and formats.",
    Idempotent:       true,
    FlagAnnotations: map[string]murli.FlagAnnotation{
        "status": {
            Enum: []string{"todo", "doing", "done"},
        },
        "priority": {
            Enum: []string{"low", "medium", "high"},
        },
    },
})
```

---

## 🔨 What You Build

To enable the dual-audience switch and structured error recovery, you refactor your `RunE` handlers to utilize the **Writer API**.

### 1. Initializing the Writer
At the very beginning of your command handler, initialize the command's writer:

```go
w := murliCobra.NewWriter(cmd)
```

### 2. Emitting Success Results
Replace standard `fmt.Println` or logging calls with `w.WriteSuccess()`. Pass a human-friendly string as the first argument, and the structured Go payload as the second:

```go
w.WriteSuccess(
    fmt.Sprintf("Task %d (\"%s\") created successfully.", id, title),
    map[string]any{"id": id, "title": title},
)
```

### 3. Emitting Actionable Errors
Replace direct error returns with `w.WriteError()`. If an input validation fails, emit a structured error along with recovery suggestions so AI agents can self-correct:

```go
if err != nil {
    w.WriteError(&murli.AgentError{
        Code:        2,
        ErrorType:   "validation_error",
        Message:     err.Error(),
        Recoverable: false,
    })
    return nil
}
```

---

## 🚀 Step-by-Step Code Walkthrough

### Step 1: Update Imports
Add the Murli core and Cobra adapter to your imports in `main.go`:

```go
import (
	"github.com/murli-cli/murli-go"
	murliCobra "github.com/murli-cli/murli-go/cobra"
)
```

### Step 2: Swap the Executor
Modify the entry point in `main()` to route commands through Murli's wrapper:

```go
// Replace: rootCmd.Execute()
if err := murliCobra.Execute(rootCmd); err != nil {
	os.Exit(2)
}
```

### Step 3: Refactor Handlers (e.g. `init`)
Update your subcommand `RunE` blocks to capture and format outputs dynamically:

```diff
 	var initCmd = &cobra.Command{
 		Use:   "init",
 		Short: "Initialize/Reset the database and config",
 		RunE: func(cmd *cobra.Command, args []string) error {
+			w := murliCobra.NewWriter(cmd)
 			if err := shared.ResetDatabase(); err != nil {
-				return err
+				w.WriteError(murli.NewUserError(err.Error(), "Could not reset the database."))
+				return nil
 			}
 			dir, _ := shared.GetStorageDir()
-			fmt.Printf("Initialized/Reset murli-work database with sample data and configuration in %s\n", dir)
+			w.WriteSuccess(
+				fmt.Sprintf("Initialized/Reset murli-work database with sample data and configuration in %s", dir),
+				map[string]any{"status": "ok", "directory": dir},
+			)
 			return nil
 		},
 	}
```

---

## 🖥️ Command Execution & Verification Outputs

Here are the real, captured terminal outputs showing the integration behaviors in action!

### 1. Human TTY Help Command (`./bin/murli-work-go-cobra --help`)
```text
murli-work is a sprint and project task tracker

Usage:
  murli-work [flags]
  murli-work [command]

Available Commands:
  completion  Generate the autocompletion script for the specified shell
  describe    Print the full command tree and capabilities as a single JSON document
  help        Help about any command
  init        Initialize/Reset the database and config
  label       Manage global task labels
  profile     Manage saved flag profiles
  report      Display progress report
  task        Manage sprint tasks

Flags:
      --agent                     Force agent-optimized JSON mode
  -h, --help                      help for murli-work
      --output string             Output format: json|ndjson|text
      --profile string            Profile name to use for this invocation
      --protocol-version string   Protocol version (0.2)
      --schema                    Output agent-optimized JSON schema
```

### 2. Auto-Generated JSON Schema (`./bin/murli-work-go-cobra --schema`)
```json
{
  "name": "murli-work",
  "summary": "murli-work is a sprint and project task tracker",
  "idempotent": false,
  "flags": [
    {
      "name": "help",
      "type": "bool",
      "default": false,
      "description": "help for murli-work"
    }
  ],
  "subcommands": [
    {
      "name": "completion",
      "summary": "Generate the autocompletion script for the specified shell"
    },
    {
      "name": "describe",
      "summary": "Print the full command tree and capabilities as a single JSON document"
    },
    {
      "name": "init",
      "summary": "Initialize/Reset the database and config"
    },
    {
      "name": "label",
      "summary": "Manage global task labels"
    },
    {
      "name": "profile",
      "summary": "Manage saved flag profiles"
    },
    {
      "name": "report",
      "summary": "Display progress report"
    },
    {
      "name": "task",
      "summary": "Manage sprint tasks"
    }
  ],
  "safety": {
    "read_only": true,
    "idempotent": false
  }
}
```

### 3. Mutating Confirmation Prompt Safeguard (`./bin/murli-work-go-cobra init --agent`)
When a mutating command is run by an agent without explicit confirmation:
```json
{
  "code": 1,
  "error": "confirmation_required",
  "message": "This command mutates state and requires explicit confirmation.",
  "suggestion": "Pass --force or --yes to proceed without a TTY.",
  "recoverable": true,
  "schema_version": "1.0"
}
```

### 4. Bypassing Safeguard with Force (`./bin/murli-work-go-cobra init --agent --force`)
```json
{
  "result": {
    "directory": "/Users/allank/Library/Application Support/murli-work",
    "status": "ok"
  },
  "schema_version": "1.0",
  "status": "ok"
}
```

### 5. Creating a Task in Agent Mode (`./bin/murli-work-go-cobra task create "Verify Cobra" --priority high --agent --force`)
```json
{
  "result": {
    "id": 6,
    "title": "Verify Cobra"
  },
  "schema_version": "1.0",
  "status": "ok"
}
```

### 6. Listing Tasks in Agent Mode (`./bin/murli-work-go-cobra task list --agent`)
```json
{
  "result": [
    {
      "id": 1,
      "title": "Setup workspace layout",
      "desc": "Bootstrap directory structures for Go, Rust, Python and TS",
      "status": "done",
      "priority": "high",
      "labels": ["setup", "dev"],
      "created_at": "2026-05-28T18:00:00Z"
    },
    ...
    {
      "id": 6,
      "title": "Verify Cobra",
      "desc": "",
      "status": "todo",
      "priority": "high",
      "labels": [],
      "created_at": "2026-05-30T12:40:16Z"
    }
  ],
  "schema_version": "1.0",
  "status": "ok"
}
```

### 7. Sprint Report in Agent Mode (`./bin/murli-work-go-cobra report --agent`)
```json
{
  "result": {
    "completed_tasks": 2,
    "percent_complete": 33.333333333333336,
    "priority_breakdown": {
      "high": 4,
      "low": 0,
      "medium": 2
    },
    "status_breakdown": {
      "doing": 1,
      "done": 2,
      "todo": 3
    },
    "total_tasks": 6
  },
  "schema_version": "1.0",
  "status": "ok"
}
```
