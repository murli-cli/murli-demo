package main

import (
	"context"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/allank/murli"
	murliCli "github.com/allank/murli/cli/v3"
	"github.com/urfave/cli/v3"
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

	app := &cli.Command{
		Name:  "murli-work",
		Usage: "A sprint and project task tracker",
		Commands: []*cli.Command{
			{
				Name:    "init",
				Aliases: []string{"i"},
				Usage:   "Initialize/Reset the database and config",
				Action: func(ctx context.Context, cmd *cli.Command) error {
					w := murliCli.NewWriter(cmd)
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
			},
			{
				Name:  "task",
				Usage: "Manage sprint tasks",
				Commands: []*cli.Command{
					{
						Name:      "create",
						Usage:     "Create a new task",
						ArgsUsage: "<title>",
						Flags: []cli.Flag{
							&cli.StringFlag{Name: "desc", Aliases: []string{"d"}, Usage: "Task description"},
							&cli.StringFlag{Name: "priority", Aliases: []string{"p"}, Usage: "Task priority (low|medium|high)"},
							&cli.StringSliceFlag{Name: "labels", Aliases: []string{"l"}, Usage: "Comma-separated labels"},
						},
						Action: func(ctx context.Context, cmd *cli.Command) error {
							w := murliCli.NewWriter(cmd)
							if cmd.Args().Len() < 1 {
								w.WriteError(&murli.AgentError{
									Code:        2,
									ErrorType:   "validation_error",
									Message:     "missing required argument <title>",
									Recoverable: false,
								})
								return nil
							}
							title := cmd.Args().First()
							desc := cmd.String("desc")
							priority := cmd.String("priority")
							labels := cmd.StringSlice("labels")

							db, err := shared.LoadDatabase()
							if err != nil {
								w.WriteError(murli.NewToolError(err.Error()))
								return nil
							}

							id, err := db.CreateTask(title, desc, priority, labels)
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
					},
					{
						Name:  "list",
						Usage: "List stored tasks",
						Flags: []cli.Flag{
							&cli.StringFlag{Name: "status", Aliases: []string{"s"}, Usage: "Filter by status (todo|doing|done)"},
							&cli.StringFlag{Name: "priority", Aliases: []string{"p"}, Usage: "Filter by priority (low|medium|high)"},
							&cli.StringFlag{Name: "label", Aliases: []string{"l"}, Usage: "Filter by a label"},
						},
						Action: func(ctx context.Context, cmd *cli.Command) error {
							w := murliCli.NewWriter(cmd)
							statusFilter := cmd.String("status")
							priorityFilter := cmd.String("priority")
							labelFilter := cmd.String("label")

							outputFmt := os.Getenv("MURLI_WORK_FORMAT")
							if outputFmt == "" {
								outputFmt = cmd.String("output")
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

							if cmd.Bool("agent") || !w.IsTTY() || w.Format() == murli.OutputFormatJSON || w.Format() == murli.OutputFormatNDJSON {
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
					},
					{
						Name:      "update",
						Usage:     "Update an existing task's fields",
						ArgsUsage: "<id>",
						Flags: []cli.Flag{
							&cli.StringFlag{Name: "title", Aliases: []string{"t"}, Usage: "New title"},
							&cli.StringFlag{Name: "desc", Aliases: []string{"d"}, Usage: "New description"},
							&cli.StringFlag{Name: "priority", Aliases: []string{"p"}, Usage: "New priority"},
							&cli.StringFlag{Name: "status", Aliases: []string{"s"}, Usage: "New status"},
							&cli.StringSliceFlag{Name: "labels", Aliases: []string{"l"}, Usage: "Replacement labels"},
						},
						Action: func(ctx context.Context, cmd *cli.Command) error {
							w := murliCli.NewWriter(cmd)
							if cmd.Args().Len() < 1 {
								w.WriteError(&murli.AgentError{
									Code:        2,
									ErrorType:   "validation_error",
									Message:     "missing required argument <id>",
									Recoverable: false,
								})
								return nil
							}
							id, err := strconv.Atoi(cmd.Args().First())
							if err != nil {
								w.WriteError(&murli.AgentError{
									Code:        2,
									ErrorType:   "validation_error",
									Message:     fmt.Sprintf("invalid task ID: %s", cmd.Args().First()),
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

							// In urfave/cli v3, c.IsSet is cmd.IsSet
							if cmd.IsSet("title") {
								t := cmd.String("title")
								titlePtr = &t
							}
							if cmd.IsSet("desc") {
								d := cmd.String("desc")
								descPtr = &d
							}
							if cmd.IsSet("priority") {
								p := cmd.String("priority")
								priorityPtr = &p
							}
							if cmd.IsSet("status") {
								s := cmd.String("status")
								statusPtr = &s
							}
							if cmd.IsSet("labels") {
								l := cmd.StringSlice("labels")
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
					},
					{
						Name:      "delete",
						Usage:     "Delete a task",
						ArgsUsage: "<id>",
						Flags: []cli.Flag{
							&cli.BoolFlag{Name: "force", Usage: "Force delete without warning"},
						},
						Action: func(ctx context.Context, cmd *cli.Command) error {
							w := murliCli.NewWriter(cmd)
							if cmd.Args().Len() < 1 {
								w.WriteError(&murli.AgentError{
									Code:        2,
									ErrorType:   "validation_error",
									Message:     "missing required argument <id>",
									Recoverable: false,
								})
								return nil
							}
							id, err := strconv.Atoi(cmd.Args().First())
							if err != nil {
								w.WriteError(&murli.AgentError{
									Code:        2,
									ErrorType:   "validation_error",
									Message:     fmt.Sprintf("invalid task ID: %s", cmd.Args().First()),
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
					},
				},
			},
			{
				Name:  "label",
				Usage: "Manage global task labels",
				Commands: []*cli.Command{
					{
						Name:  "list",
						Usage: "List all defined labels",
						Action: func(ctx context.Context, cmd *cli.Command) error {
							w := murliCli.NewWriter(cmd)
							db, err := shared.LoadDatabase()
							if err != nil {
								w.WriteError(murli.NewToolError(err.Error()))
								return nil
							}

							if cmd.Bool("agent") || !w.IsTTY() || w.Format() == murli.OutputFormatJSON || w.Format() == murli.OutputFormatNDJSON {
								w.WriteSuccess("List of defined labels", db.Labels)
							} else {
								shared.PrintLabelsTable(db)
							}
							return nil
						},
					},
					{
						Name:      "create",
						Usage:     "Create a custom label",
						ArgsUsage: "<name>",
						Action: func(ctx context.Context, cmd *cli.Command) error {
							w := murliCli.NewWriter(cmd)
							if cmd.Args().Len() < 1 {
								w.WriteError(&murli.AgentError{
									Code:        2,
									ErrorType:   "validation_error",
									Message:     "missing required argument <name>",
									Recoverable: false,
								})
								return nil
							}
							name := cmd.Args().First()
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
					},
					{
						Name:      "delete",
						Usage:     "Delete a label",
						ArgsUsage: "<name>",
						Action: func(ctx context.Context, cmd *cli.Command) error {
							w := murliCli.NewWriter(cmd)
							if cmd.Args().Len() < 1 {
								w.WriteError(&murli.AgentError{
									Code:        2,
									ErrorType:   "validation_error",
									Message:     "missing required argument <name>",
									Recoverable: false,
								})
								return nil
							}
							name := cmd.Args().First()
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
					},
				},
			},
			{
				Name:  "report",
				Usage: "Display progress report",
				Action: func(ctx context.Context, cmd *cli.Command) error {
					w := murliCli.NewWriter(cmd)
					db, err := shared.LoadDatabase()
					if err != nil {
						w.WriteError(murli.NewToolError(err.Error()))
						return nil
					}

					if cmd.Bool("agent") || !w.IsTTY() || w.Format() == murli.OutputFormatJSON || w.Format() == murli.OutputFormatNDJSON {
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
			},
		},
	}

	// Annotations for urfave/cli v3
	murliCli.Annotate(app.Commands[0], murli.Metadata{
		AgentDescription: "Initialize/Reset the database and config to default state with 5 tasks and 6 labels.",
		Idempotent:       true,
		Mutating:         true,
	})

	murliCli.Annotate(app.Commands[1].Commands[0], murli.Metadata{
		AgentDescription: "Create a new task in the database.",
		Mutating:         true,
		Arguments: []murli.ArgumentMetadata{
			{Name: "title", Type: "string", Required: true, Description: "Task title"},
		},
	})

	murliCli.Annotate(app.Commands[1].Commands[1], murli.Metadata{
		AgentDescription: "List stored sprint tasks with filters and formats.",
		Idempotent:       true,
	})

	murliCli.Annotate(app.Commands[1].Commands[2], murli.Metadata{
		AgentDescription: "Update properties of an existing task.",
		Mutating:         true,
		Arguments: []murli.ArgumentMetadata{
			{Name: "id", Type: "integer", Required: true, Description: "ID of task to update"},
		},
	})

	murliCli.Annotate(app.Commands[1].Commands[3], murli.Metadata{
		AgentDescription: "Delete a task by ID.",
		Mutating:         true,
		Destructive:      true,
		Arguments: []murli.ArgumentMetadata{
			{Name: "id", Type: "integer", Required: true, Description: "ID of task to delete"},
		},
	})

	murliCli.Annotate(app.Commands[2].Commands[0], murli.Metadata{
		AgentDescription: "List all defined task labels.",
		Idempotent:       true,
	})

	murliCli.Annotate(app.Commands[2].Commands[1], murli.Metadata{
		AgentDescription: "Create a custom task label.",
		Mutating:         true,
		Arguments: []murli.ArgumentMetadata{
			{Name: "name", Type: "string", Required: true, Description: "Label name"},
		},
	})

	murliCli.Annotate(app.Commands[2].Commands[2], murli.Metadata{
		AgentDescription: "Delete a custom label and disassociate it from tasks.",
		Mutating:         true,
		Destructive:      true,
		Arguments: []murli.ArgumentMetadata{
			{Name: "name", Type: "string", Required: true, Description: "Label name to delete"},
		},
	})

	murliCli.Annotate(app.Commands[3], murli.Metadata{
		AgentDescription: "Display sprint completion dashboard statistics.",
		Idempotent:       true,
	})

	if err := murliCli.Run(app, os.Args); err != nil {
		os.Exit(2)
	}
}
