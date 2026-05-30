package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/urfave/cli/v2"
	"murli-work-shared"
)

func main() {
	app := &cli.App{
		Name:  "murli-work",
		Usage: "A sprint and project task tracker",
		Commands: []*cli.Command{
			{
				Name:    "init",
				Aliases: []string{"i"},
				Usage:   "Initialize/Reset the database and config",
				Action: func(c *cli.Context) error {
					if err := shared.ResetDatabase(); err != nil {
						return err
					}
					dir, _ := shared.GetStorageDir()
					fmt.Printf("Initialized/Reset murli-work database with sample data and configuration in %s\n", dir)
					return nil
				},
			},
			{
				Name:  "task",
				Usage: "Manage sprint tasks",
				Subcommands: []*cli.Command{
					{
						Name:      "create",
						Usage:     "Create a new task",
						ArgsUsage: "<title>",
						Flags: []cli.Flag{
							&cli.StringFlag{Name: "desc", Aliases: []string{"d"}, Usage: "Task description"},
							&cli.StringFlag{Name: "priority", Aliases: []string{"p"}, Usage: "Task priority (low|medium|high)"},
							&cli.StringSliceFlag{Name: "labels", Aliases: []string{"l"}, Usage: "Comma-separated labels"},
						},
						Action: func(c *cli.Context) error {
							if c.Args().Len() < 1 {
								return fmt.Errorf("missing required argument <title>")
							}
							title := c.Args().First()
							desc := c.String("desc")
							priority := c.String("priority")
							labels := c.StringSlice("labels")

							db, err := shared.LoadDatabase()
							if err != nil {
								return err
			}

							id, err := db.CreateTask(title, desc, priority, labels)
							if err != nil {
								return err
							}

							fmt.Printf("Task %d (\"%s\") created successfully.\n", id, title)
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
							&cli.StringFlag{Name: "output", Aliases: []string{"o"}, Value: "table", Usage: "Output format (table|json|csv)"},
						},
						Action: func(c *cli.Context) error {
							statusFilter := c.String("status")
							priorityFilter := c.String("priority")
							labelFilter := c.String("label")
							outputFmt := c.String("output")

							db, err := shared.LoadDatabase()
							if err != nil {
								return err
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

							switch strings.ToLower(outputFmt) {
							case "json":
								shared.PrintTasksJSON(filtered)
							case "csv":
								shared.PrintTasksCSV(filtered)
							default:
								shared.PrintTasksTable(filtered)
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
						Action: func(c *cli.Context) error {
							if c.Args().Len() < 1 {
								return fmt.Errorf("missing required argument <id>")
							}
							id, err := strconv.Atoi(c.Args().First())
							if err != nil {
								return fmt.Errorf("invalid task ID: %s", c.Args().First())
							}

							db, err := shared.LoadDatabase()
							if err != nil {
								return err
							}

							var titlePtr, descPtr, priorityPtr, statusPtr *string
							var labelsPtr *[]string

							if c.IsSet("title") {
								t := c.String("title")
								titlePtr = &t
							}
							if c.IsSet("desc") {
								d := c.String("desc")
								descPtr = &d
							}
							if c.IsSet("priority") {
								p := c.String("priority")
								priorityPtr = &p
							}
							if c.IsSet("status") {
								s := c.String("status")
								statusPtr = &s
							}
							if c.IsSet("labels") {
								l := c.StringSlice("labels")
								labelsPtr = &l
							}

							if err := db.UpdateTask(id, titlePtr, descPtr, priorityPtr, statusPtr, labelsPtr); err != nil {
								return err
							}

							fmt.Printf("Task %d updated successfully.\n", id)
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
						Action: func(c *cli.Context) error {
							if c.Args().Len() < 1 {
								return fmt.Errorf("missing required argument <id>")
							}
							id, err := strconv.Atoi(c.Args().First())
							if err != nil {
								return fmt.Errorf("invalid task ID: %s", c.Args().First())
							}

							db, err := shared.LoadDatabase()
							if err != nil {
								return err
							}

							if err := db.DeleteTask(id); err != nil {
								return err
							}

							fmt.Printf("Task %d deleted successfully.\n", id)
							return nil
						},
					},
				},
			},
			{
				Name:  "label",
				Usage: "Manage global task labels",
				Subcommands: []*cli.Command{
					{
						Name:  "list",
						Usage: "List all defined labels",
						Action: func(c *cli.Context) error {
							db, err := shared.LoadDatabase()
							if err != nil {
								return err
							}
							shared.PrintLabelsTable(db)
							return nil
						},
					},
					{
						Name:      "create",
						Usage:     "Create a custom label",
						ArgsUsage: "<name>",
						Action: func(c *cli.Context) error {
							if c.Args().Len() < 1 {
								return fmt.Errorf("missing required argument <name>")
							}
							name := c.Args().First()
							db, err := shared.LoadDatabase()
							if err != nil {
								return err
							}

							slug, err := db.CreateLabel(name)
							if err != nil {
								return err
							}

							fmt.Printf("Label \"%s\" created successfully.\n", slug)
							return nil
						},
					},
					{
						Name:      "delete",
						Usage:     "Delete a label",
						ArgsUsage: "<name>",
						Action: func(c *cli.Context) error {
							if c.Args().Len() < 1 {
								return fmt.Errorf("missing required argument <name>")
							}
							name := c.Args().First()
							db, err := shared.LoadDatabase()
							if err != nil {
								return err
							}

							if err := db.DeleteLabel(name); err != nil {
								return err
							}

							fmt.Printf("Label \"%s\" deleted successfully.\n", name)
							return nil
						},
					},
				},
			},
			{
				Name:  "report",
				Usage: "Display progress report",
				Action: func(c *cli.Context) error {
					db, err := shared.LoadDatabase()
					if err != nil {
						return err
					}
					shared.PrintSprintReport(db)
					return nil
				},
			},
		},
	}

	if err := app.Run(os.Args); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(2) // Exit code 2 for CLI parsing/validation errors
	}
}
