package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/allank/murli"
	murliCobra "github.com/allank/murli/cobra"
	"github.com/spf13/cobra"
	"murli-work-shared"
)

func main() {
	// Pre-process --output=csv / --output=table to prevent Murli validation errors
	for i, arg := range os.Args {
		if arg == "--output" || arg == "-o" {
			if i+1 < len(os.Args) {
				val := os.Args[i+1]
				if val == "csv" || val == "table" {
					os.Args[i+1] = "text"
					os.Setenv("MURLI_WORK_FORMAT", val)
				}
			}
		} else if strings.HasPrefix(arg, "--output=") {
			val := strings.TrimPrefix(arg, "--output=")
			if val == "csv" || val == "table" {
				os.Args[i] = "--output=text"
				os.Setenv("MURLI_WORK_FORMAT", val)
			}
		} else if strings.HasPrefix(arg, "-o=") {
			val := strings.TrimPrefix(arg, "-o=")
			if val == "csv" || val == "table" {
				os.Args[i] = "-o=text"
				os.Setenv("MURLI_WORK_FORMAT", val)
			}
		}
	}

	var rootCmd = &cobra.Command{
		Use:   "murli-work",
		Short: "murli-work is a sprint and project task tracker",
		Run: func(cmd *cobra.Command, args []string) {
			_ = cmd.Help()
		},
	}

	var initCmd = &cobra.Command{
		Use:   "init",
		Short: "Initialize/Reset the database and config",
		RunE: func(cmd *cobra.Command, args []string) error {
			w := murliCobra.NewWriter(cmd)
			if err := shared.ResetDatabase(); err != nil {
				w.WriteError(murli.NewUserError(err.Error(), "Could not reset the database."))
				return nil
			}
			dir, _ := shared.GetStorageDir()
			w.WriteSuccess(
				fmt.Sprintf("Initialized/Reset murli-work database with sample data and configuration in %s", dir),
				map[string]any{"status": "ok", "directory": dir},
			)
			return nil
		},
	}

	// Task command groups
	var taskCmd = &cobra.Command{
		Use:   "task",
		Short: "Manage sprint tasks",
		Run: func(cmd *cobra.Command, args []string) {
			_ = cmd.Help()
		},
	}

	var taskCreateCmd = &cobra.Command{
		Use:   "create [title]",
		Short: "Create a new task",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			w := murliCobra.NewWriter(cmd)
			title := args[0]
			desc, _ := cmd.Flags().GetString("desc")
			priority, _ := cmd.Flags().GetString("priority")
			labelsSlice, _ := cmd.Flags().GetStringSlice("labels")

			db, err := shared.LoadDatabase()
			if err != nil {
				w.WriteError(murli.NewToolError(err.Error()))
				return nil
			}

			id, err := db.CreateTask(title, desc, priority, labelsSlice)
			if err != nil {
				w.WriteError(&murli.AgentError{
					Code:        2,
					ErrorType:   "validation_error",
					Message:     err.Error(),
					Recoverable: false,
				})
				return nil
			}

			w.WriteSuccess(
				fmt.Sprintf("Task %d (\"%s\") created successfully.", id, title),
				map[string]any{"id": id, "title": title},
			)
			return nil
		},
	}
	taskCreateCmd.Flags().StringP("desc", "d", "", "Task description")
	taskCreateCmd.Flags().StringP("priority", "p", "", "Task priority (low|medium|high)")
	taskCreateCmd.Flags().StringSliceP("labels", "l", []string{}, "Comma-separated labels")

	var taskListCmd = &cobra.Command{
		Use:   "list",
		Short: "List stored tasks",
		RunE: func(cmd *cobra.Command, args []string) error {
			w := murliCobra.NewWriter(cmd)
			statusFilter, _ := cmd.Flags().GetString("status")
			priorityFilter, _ := cmd.Flags().GetString("priority")
			labelFilter, _ := cmd.Flags().GetString("label")
			outputFmt := os.Getenv("MURLI_WORK_FORMAT")
			if outputFmt == "" {
				outputFmt, _ = cmd.Flags().GetString("output")
			}
			if outputFmt == "text" || outputFmt == "" {
				outputFmt = "table"
			}

			db, err := shared.LoadDatabase()
			if err != nil {
				w.WriteError(murli.NewToolError(err.Error()))
				return nil
			}

			cfg, _ := shared.LoadConfig()
			if outputFmt == "table" && cfg != nil && cfg.DefaultOutput != "" {
				outputFmt = cfg.DefaultOutput
			}

			// Filter in memory
			filtered := []shared.Task{}
			for _, t := range db.Tasks {
				if statusFilter != "" && strings.ToLower(t.Status) != strings.ToLower(statusFilter) {
					continue
				}
				if priorityFilter != "" && strings.ToLower(t.Priority) != strings.ToLower(priorityFilter) {
					continue
				}
				if labelFilter != "" {
					found := false
					for _, l := range t.Labels {
						if strings.ToLower(l) == strings.ToLower(labelFilter) {
							found = true
							break
						}
					}
					if !found {
						continue
					}
				}
				filtered = append(filtered, t)
			}

			agentMode, _ := cmd.Flags().GetBool("agent")
			if agentMode || !w.IsTTY() || w.Format() == murli.OutputFormatJSON || w.Format() == murli.OutputFormatNDJSON {
				w.WriteSuccess("List of sprint tasks", filtered)
			} else {
				switch strings.ToLower(outputFmt) {
				case "json":
					shared.PrintTasksJSON(filtered)
				case "csv":
					shared.PrintTasksCSV(filtered)
				default:
					shared.PrintTasksTable(filtered)
				}
			}
			return nil
		},
	}
	taskListCmd.Flags().StringP("status", "s", "", "Filter by status (todo|doing|done)")
	taskListCmd.Flags().StringP("priority", "p", "", "Filter by priority (low|medium|high)")
	taskListCmd.Flags().StringP("label", "l", "", "Filter by a label")

	var taskUpdateCmd = &cobra.Command{
		Use:   "update [id]",
		Short: "Update an existing task's fields",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			w := murliCobra.NewWriter(cmd)
			id, err := strconv.Atoi(args[0])
			if err != nil {
				w.WriteError(&murli.AgentError{
					Code:        2,
					ErrorType:   "validation_error",
					Message:     fmt.Sprintf("invalid task ID: %s", args[0]),
					Recoverable: false,
				})
				return nil
			}

			db, err := shared.LoadDatabase()
			if err != nil {
				w.WriteError(murli.NewToolError(err.Error()))
				return nil
			}

			var titlePtr, descPtr, priorityPtr, statusPtr *string
			var labelsPtr *[]string

			if cmd.Flags().Changed("title") {
				t, _ := cmd.Flags().GetString("title")
				titlePtr = &t
			}
			if cmd.Flags().Changed("desc") {
				d, _ := cmd.Flags().GetString("desc")
				descPtr = &d
			}
			if cmd.Flags().Changed("priority") {
				p, _ := cmd.Flags().GetString("priority")
				priorityPtr = &p
			}
			if cmd.Flags().Changed("status") {
				s, _ := cmd.Flags().GetString("status")
				statusPtr = &s
			}
			if cmd.Flags().Changed("labels") {
				l, _ := cmd.Flags().GetStringSlice("labels")
				labelsPtr = &l
			}

			if err := db.UpdateTask(id, titlePtr, descPtr, priorityPtr, statusPtr, labelsPtr); err != nil {
				code := 1
				if strings.Contains(err.Error(), "priority") || strings.Contains(err.Error(), "status") {
					code = 2
				}
				w.WriteError(&murli.AgentError{
					Code:        code,
					ErrorType:   "update_error",
					Message:     err.Error(),
					Recoverable: false,
				})
				return nil
			}

			w.WriteSuccess(fmt.Sprintf("Task %d updated successfully.", id), map[string]any{"id": id})
			return nil
		},
	}
	taskUpdateCmd.Flags().StringP("title", "t", "", "New title")
	taskUpdateCmd.Flags().StringP("desc", "d", "", "New description")
	taskUpdateCmd.Flags().StringP("priority", "p", "", "New priority")
	taskUpdateCmd.Flags().StringP("status", "s", "", "New status")
	taskUpdateCmd.Flags().StringSliceP("labels", "l", []string{}, "Replacement labels")

	var taskDeleteCmd = &cobra.Command{
		Use:   "delete [id]",
		Short: "Delete a task",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			w := murliCobra.NewWriter(cmd)
			id, err := strconv.Atoi(args[0])
			if err != nil {
				w.WriteError(&murli.AgentError{
					Code:        2,
					ErrorType:   "validation_error",
					Message:     fmt.Sprintf("invalid task ID: %s", args[0]),
					Recoverable: false,
				})
				return nil
			}

			db, err := shared.LoadDatabase()
			if err != nil {
				w.WriteError(murli.NewToolError(err.Error()))
				return nil
			}

			if err := db.DeleteTask(id); err != nil {
				w.WriteError(&murli.AgentError{
					Code:        1,
					ErrorType:   "delete_error",
					Message:     err.Error(),
					Recoverable: false,
				})
				return nil
			}

			w.WriteSuccess(fmt.Sprintf("Task %d deleted successfully.", id), map[string]any{"id": id})
			return nil
		},
	}
	taskDeleteCmd.Flags().Bool("force", false, "Force delete without warning")

	taskCmd.AddCommand(taskCreateCmd, taskListCmd, taskUpdateCmd, taskDeleteCmd)

	// Label command groups
	var labelCmd = &cobra.Command{
		Use:   "label",
		Short: "Manage global task labels",
		Run: func(cmd *cobra.Command, args []string) {
			_ = cmd.Help()
		},
	}

	var labelListCmd = &cobra.Command{
		Use:   "list",
		Short: "List all defined labels",
		RunE: func(cmd *cobra.Command, args []string) error {
			w := murliCobra.NewWriter(cmd)
			db, err := shared.LoadDatabase()
			if err != nil {
				w.WriteError(murli.NewToolError(err.Error()))
				return nil
			}

			agentMode, _ := cmd.Flags().GetBool("agent")
			if agentMode || !w.IsTTY() || w.Format() == murli.OutputFormatJSON || w.Format() == murli.OutputFormatNDJSON {
				w.WriteSuccess("List of defined labels", db.Labels)
			} else {
				shared.PrintLabelsTable(db)
			}
			return nil
		},
	}

	var labelCreateCmd = &cobra.Command{
		Use:   "create [name]",
		Short: "Create a custom label",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			w := murliCobra.NewWriter(cmd)
			name := args[0]
			db, err := shared.LoadDatabase()
			if err != nil {
				w.WriteError(murli.NewToolError(err.Error()))
				return nil
			}

			slug, err := db.CreateLabel(name)
			if err != nil {
				w.WriteError(&murli.AgentError{
					Code:        1,
					ErrorType:   "create_label_error",
					Message:     err.Error(),
					Recoverable: false,
				})
				return nil
			}

			w.WriteSuccess(fmt.Sprintf("Label \"%s\" created successfully.", slug), map[string]any{"label": slug})
			return nil
		},
	}

	var labelDeleteCmd = &cobra.Command{
		Use:   "delete [name]",
		Short: "Delete a label",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			w := murliCobra.NewWriter(cmd)
			name := args[0]
			db, err := shared.LoadDatabase()
			if err != nil {
				w.WriteError(murli.NewToolError(err.Error()))
				return nil
			}

			if err := db.DeleteLabel(name); err != nil {
				w.WriteError(&murli.AgentError{
					Code:        1,
					ErrorType:   "delete_label_error",
					Message:     err.Error(),
					Recoverable: false,
				})
				return nil
			}

			w.WriteSuccess(fmt.Sprintf("Label \"%s\" deleted successfully.", name), map[string]any{"label": name})
			return nil
		},
	}

	labelCmd.AddCommand(labelListCmd, labelCreateCmd, labelDeleteCmd)

	var reportCmd = &cobra.Command{
		Use:   "report",
		Short: "Display progress report",
		RunE: func(cmd *cobra.Command, args []string) error {
			w := murliCobra.NewWriter(cmd)
			db, err := shared.LoadDatabase()
			if err != nil {
				w.WriteError(murli.NewToolError(err.Error()))
				return nil
			}

			agentMode, _ := cmd.Flags().GetBool("agent")
			if agentMode || !w.IsTTY() || w.Format() == murli.OutputFormatJSON || w.Format() == murli.OutputFormatNDJSON {
				total := len(db.Tasks)
				completed := 0
				todo := 0
				doing := 0
				done := 0
				high := 0
				medium := 0
				low := 0

				for _, t := range db.Tasks {
					switch strings.ToLower(t.Status) {
					case "todo":
						todo++
					case "doing":
						doing++
					case "done":
						done++
						completed++
					}

					switch strings.ToLower(t.Priority) {
					case "low":
						low++
					case "medium":
						medium++
					case "high":
						high++
					}
				}

				percent := 0.0
				if total > 0 {
					percent = float64(completed*100) / float64(total)
				}

				reportPayload := map[string]any{
					"total_tasks":     total,
					"completed_tasks": completed,
					"percent_complete": percent,
					"status_breakdown": map[string]int{
						"todo":  todo,
						"doing": doing,
						"done":  done,
					},
					"priority_breakdown": map[string]int{
						"high":   high,
						"medium": medium,
						"low":    low,
					},
				}
				w.WriteSuccess("Sprint progress report", reportPayload)
			} else {
				shared.PrintSprintReport(db)
			}
			return nil
		},
	}

	rootCmd.AddCommand(initCmd, taskCmd, labelCmd, reportCmd)

	murliCobra.Annotate(initCmd, murli.Metadata{
		AgentDescription: "Initialize/Reset the database and config to default state with 5 tasks and 6 labels.",
		Idempotent:       true,
		Mutating:         true,
	})

	murliCobra.Annotate(taskCreateCmd, murli.Metadata{
		AgentDescription: "Create a new task in the database.",
		Mutating:         true,
		Arguments: []murli.ArgumentMetadata{
			{Name: "title", Type: "string", Required: true, Description: "Task title"},
		},
	})

	murliCobra.Annotate(taskListCmd, murli.Metadata{
		AgentDescription: "List stored sprint tasks with filters and formats.",
		Idempotent:       true,
	})

	murliCobra.Annotate(taskUpdateCmd, murli.Metadata{
		AgentDescription: "Update properties of an existing task.",
		Mutating:         true,
		Arguments: []murli.ArgumentMetadata{
			{Name: "id", Type: "integer", Required: true, Description: "ID of task to update"},
		},
	})

	murliCobra.Annotate(taskDeleteCmd, murli.Metadata{
		AgentDescription: "Delete a task by ID.",
		Mutating:         true,
		Destructive:      true,
		Arguments: []murli.ArgumentMetadata{
			{Name: "id", Type: "integer", Required: true, Description: "ID of task to delete"},
		},
	})

	murliCobra.Annotate(labelListCmd, murli.Metadata{
		AgentDescription: "List all defined task labels.",
		Idempotent:       true,
	})

	murliCobra.Annotate(labelCreateCmd, murli.Metadata{
		AgentDescription: "Create a custom task label.",
		Mutating:         true,
		Arguments: []murli.ArgumentMetadata{
			{Name: "name", Type: "string", Required: true, Description: "Label name"},
		},
	})

	murliCobra.Annotate(labelDeleteCmd, murli.Metadata{
		AgentDescription: "Delete a custom label and disassociate it from tasks.",
		Mutating:         true,
		Destructive:      true,
		Arguments: []murli.ArgumentMetadata{
			{Name: "name", Type: "string", Required: true, Description: "Label name to delete"},
		},
	})

	murliCobra.Annotate(reportCmd, murli.Metadata{
		AgentDescription: "Display sprint completion dashboard statistics.",
		Idempotent:       true,
	})

	if err := murliCobra.Execute(rootCmd); err != nil {
		os.Exit(2) // CLI parsing/validation error
	}
}
