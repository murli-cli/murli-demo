# Walkthrough Instructions: Adding Murli Middleware to CLI Skeletons

This document codifies the systematic plan to integrate the **Murli CLI middleware** into reference implementations across multiple languages and libraries.

The primary reference documentation is available at:
- Documentation Home: [murli.allankent.com](https://murli.allankent.com/)
- Comprehensive Developer Reference: [llms-full.txt](https://murli.allankent.com/llms-full.txt)

## 📋 Methodology Rules

### 1. Sequential & Library-Specific Branches
For any given programming language, we will work on each CLI framework implementation individually in its own dedicated feature branch:
- **Branch Format:** `<language>/<library>` (e.g., `go/cobra`, `go/urfavecliv2`, `go/urfavecliv3`)

Each framework integration must be fully completed, tested, and documented before moving on to the next.

### 2. Progressive Feature Implementation
We will introduce Murli features progressively to track and capture the exact behavioral changes at each stage:
- **Step 1: Dependency & Initialization:** Add the library dependency and hook the adapter's entry point (`murli.Execute`, `murli.Run`, etc.) into the main function as a drop-in replacement.
- **Step 2: Mode Decoupling & Writer API:** Refactor command/action handlers to use `murli.NewWriter()` instead of direct standard output, enabling TTY auto-detection and `--agent` mode.
- **Step 3: Schema & Annotations:** Define command and flag metadata using `murli.Annotate()` to enable the `--schema` flag and `describe` command.
- **Step 4: Actionable Error Handling:** Intercept user/tool errors using `w.WriteError` and appropriate exit codes/suggestions.
- **Step 5: Telemetry & Token Optimization:** Leverage progressive logs (`w.Log()`) and progress indicators (`w.WriteProgress()`) with log deduplication features.

### 3. Commit and Testing Standards
- **No Early Commits:** Do not commit a change until the feature is complete and verified correct.
- **Test-Driven Output Captures:** Run the compiled binary/wrapper script directly in the shell to execute commands for the new feature and capture the stdout/stderr.
- **Congruence & State Continuity:** If the DB/environment is reset, replay the exact preceding operations (e.g. creating tasks) before capturing test output. The state must remain continuous and congruent across the walkthrough steps.
- **Commit Message Format:** Every commit message must include:
  1. A detailed title and description of the change.
  2. What feature was enabled.
  3. A raw capture of the terminal output showing the success/error behavior.

### 4. Interactive Step Guides
For each integration, we will build a detailed step-by-step guide saved as:
`<LANGUAGE>-<LIBRARY>-GUIDE.md` (e.g., `GO-COBRA-GUIDE.md` or `GO-URFAVECLIV2-GUIDE.md`).

This guide must trace every code modification, explain the mechanics, and show the exact command output so someone can follow along easily. Structurally, the guide must emulate the official Murli explanation pattern:
- **What You Get for Free:** Explain the automatic capabilities added by merely replacing the framework's executor with Murli's adapter (e.g. `--agent`, `--schema`, `--force`, `--dry-run`, `describe` subcommand, TTY auto-detection, log deduplication).
- **What You Configure:** Describe the manual metadata configuration and flag/argument annotations registered outside the handler context.
- **What You Build:** Walk through refactoring the actual command action handlers to utilize the Writer API (`WriteSuccess`, `WritePlan`, `WriteError`, `WriteProgress`, and progressive loggers).
