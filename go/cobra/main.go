package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/spf13/cobra"
	"murli-work-shared"
)

func main() {
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
			if err := shared.ResetDatabase(); err != nil {
				return err
			}
			dir, _ := shared.GetStorageDir()
			fmt.Printf("Initialized/Reset murli-work database with sample data and configuration in %s\n", dir)
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
			title := args[0]
			desc, _ := cmd.Flags().GetString("desc")
			priority, _ := cmd.Flags().GetString("priority")
			labelsSlice, _ := cmd.Flags().GetStringSlice("labels")

			db, err := shared.LoadDatabase()
			if err != nil {
				return err
			}

			id, err := db.CreateTask(title, desc, priority, labelsSlice)
			if err != nil {
				return err
			}

			fmt.Printf("Task %d (\"%s\") created successfully.\n", id, title)
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
			statusFilter, _ := cmd.Flags().GetString("status")
			priorityFilter, _ := cmd.Flags().GetString("priority")
			labelFilter, _ := cmd.Flags().GetString("label")
			outputFmt, _ := cmd.Flags().GetString("output")

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
	}
	taskListCmd.Flags().StringP("status", "s", "", "Filter by status (todo|doing|done)")
	taskListCmd.Flags().StringP("priority", "p", "", "Filter by priority (low|medium|high)")
	taskListCmd.Flags().StringP("label", "l", "", "Filter by a label")
	taskListCmd.Flags().StringP("output", "o", "table", "Output format (table|json|csv)")

	var taskUpdateCmd = &cobra.Command{
		Use:   "update [id]",
		Short: "Update an existing task's fields",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			id, err := strconv.Atoi(args[0])
			if err != nil {
				return fmt.Errorf("invalid task ID: %s", args[0])
			}

			db, err := shared.LoadDatabase()
			if err != nil {
				return err
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
				return err
			}

			fmt.Printf("Task %d updated successfully.\n", id)
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
			id, err := strconv.Atoi(args[0])
			if err != nil {
				return fmt.Errorf("invalid task ID: %s", args[0])
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
			db, err := shared.LoadDatabase()
			if err != nil {
				return err
			}
			shared.PrintLabelsTable(db)
			return nil
		},
	}

	var labelCreateCmd = &cobra.Command{
		Use:   "create [name]",
		Short: "Create a custom label",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			name := args[0]
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
	}

	var labelDeleteCmd = &cobra.Command{
		Use:   "delete [name]",
		Short: "Delete a label",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			name := args[0]
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
	}

	labelCmd.AddCommand(labelListCmd, labelCreateCmd, labelDeleteCmd)

	var reportCmd = &cobra.Command{
		Use:   "report",
		Short: "Display progress report",
		RunE: func(cmd *cobra.Command, args []string) error {
			db, err := shared.LoadDatabase()
			if err != nil {
				return err
			}
			shared.PrintSprintReport(db)
			return nil
		},
	}

	rootCmd.AddCommand(initCmd, taskCmd, labelCmd, reportCmd)

	if err := rootCmd.Execute(); err != nil {
		os.Exit(2) // CLI parsing/validation error
	}
}
