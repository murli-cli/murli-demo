# Murli Integration Guide: Go with urfave/cli v3

This guide explains how to systematically integrate the **Murli CLI middleware** (`github.com/murli-cli/murli-go`) into a Go application built with the **urfave/cli/v3** CLI framework.

---

## 🎁 What You Get for Free

By simply wrapping your urfave/cli v3 root command execution with Murli's adapter entry point (`murliCli.Run(rootCmd, os.Args)`), your CLI tool automatically inherits the following powerful features:

1. **Intelligent TTY Detection (Dual-Audience Output):**
   - Humans in a terminal (Stdout connected to a TTY) receive pretty text and formatted ASCII tables.
   - AI agents or piped processes receive structured JSON envelopes.
2. **Auto-Injected Standard Flags:**
   - `--agent`: Forces structured JSON output regardless of TTY state.
   - `--schema`: Intercepts execution, prints the JSON schema of the command, and exits.
   - `--force` / `--yes`: Bypasses non-interactive mutation confirmation guards.
   - `--profile <name>`: Loads a named profile.
3. **Auto-Mounted Subcommands:**
   - `describe`: Emits a recursive JSON command tree containing descriptions, safety properties, examples, and flags.
   - `profile`: Direct access to manage flag profile collections.
4. **Log Deduplication:**
   - Collapses duplicate telemetry/logs written to Stderr to optimize AI agent context window consumption.

---

## 🔧 What You Configure

To enable schema introspection and documentation for AI agents, you attach **Metadata** outside the execution loop.

### 1. Attaching Command Metadata
We attach descriptive definitions to our commands using `murliCli.Annotate()`:

```go
murliCli.Annotate(app.Commands[1].Subcommands[0], murli.Metadata{
    AgentDescription: "Create a new task in the database.",
    Mutating:         true,
    Arguments: []murli.ArgumentMetadata{
        {Name: "title", Type: "string", Required: true, Description: "Task title"},
    },
})
```

---

## 🔨 What You Build

To enable the dual-audience switch and structured error recovery, you refactor your `Action` handlers to utilize the **Writer API**.

### 1. Initializing the Writer
At the very beginning of your command handler, initialize the command's writer:

```go
w := murliCli.NewWriter(cmd)
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
Replace direct error returns with `w.WriteError()`. If an input validation fails, emit a structured error along with recovery suggestions:

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
Add the Murli core and urfave/cli v3 adapter to your imports in `main.go`:

```go
import (
	"github.com/murli-cli/murli-go"
	murliCli "github.com/murli-cli/murli-go/cli/v3"
)
```

### Step 2: Swap the Executor
Modify the entry point in `main()` to route commands through Murli's wrapper:

```go
// Replace: app.Run(ctx, os.Args)
if err := murliCli.Run(app, os.Args); err != nil {
	os.Exit(2)
}
```

### Step 3: Refactor Handlers (e.g. `init`)
Update your subcommand `Action` blocks to capture and format outputs dynamically. Note that in urfave v3, `Action` functions accept `context.Context` as their first parameter:

```diff
 			{
 				Name:    "init",
 				Aliases: []string{"i"},
 				Usage:   "Initialize/Reset the database and config",
-				Action: func(c *cli.Context) error {
+				Action: func(ctx context.Context, cmd *cli.Command) error {
+					w := murliCli.NewWriter(cmd)
 					if err := shared.ResetDatabase(); err != nil {
-						return err
+						w.WriteError(murli.NewUserError(err.Error(), "Could not reset the database."))
+						return nil
 					}
 					dir, _ := shared.GetStorageDir()
-					fmt.Printf("Initialized/Reset murli-work database with sample data and configuration in %s\n", dir)
+					w.WriteSuccess(
+						fmt.Sprintf("Initialized/Reset murli-work database with sample data and configuration in %s", dir),
+						map[string]any{"status": "ok", "directory": dir},
+					)
 					return nil
 				},
 			},
```

---

## 🖥️ Command Execution & Verification Outputs

Here are the terminal outputs showing the urfave/cli v3 integration behaviors in action!

### 1. Human TTY Help Command (`./bin/murli-work-go-urfavev3 --help`)
```text
NAME:
   murli-work - A sprint and project task tracker

USAGE:
   murli-work [global options] command [command options]

COMMANDS:
   init, i   Initialize/Reset the database and config
   task      Manage sprint tasks
   label     Manage global task labels
   report    Display progress report
   describe  Print the full command tree and capabilities as a single JSON document
   profile   Manage saved flag profiles
   help, h   Shows a list of commands or help for one command

GLOBAL OPTIONS:
   --profile value  Profile name to use for this invocation
   --agent          Force agent-optimized JSON mode (default: false)
   --help, -h       show help
```

### 2. Mutating Confirmation Prompt Safeguard (`./bin/murli-work-go-urfavev3 init --agent`)
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

### 3. Bypassing Safeguard with Force (`./bin/murli-work-go-urfavev3 init --agent --force`)
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

### 4. Creating a Task in Agent Mode (`./bin/murli-work-go-urfavev3 task create --agent --force --priority high "Verify Urfave V3"`)
```json
{
  "result": {
    "id": 6,
    "title": "Verify Urfave V3"
  },
  "schema_version": "1.0",
  "status": "ok"
}
```

### 5. Listing Tasks in Agent Mode (`./bin/murli-work-go-urfavev3 task list --agent`)
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
      "title": "Verify Urfave V3",
      "desc": "",
      "status": "todo",
      "priority": "high",
      "labels": [],
      "created_at": "2026-05-30T13:00:17Z"
    }
  ],
  "schema_version": "1.0",
  "status": "ok"
}
```

### 6. Sprint Report in Agent Mode (`./bin/murli-work-go-urfavev3 report --agent`)
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
