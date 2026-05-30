package shared

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

func PrintTasksTable(tasks []Task) {
	border := "+----+----------------------+--------+----------+------------+"
	header := "| ID | Title                | Status | Priority | Labels     |"
	
	fmt.Println(border)
	fmt.Println(header)
	fmt.Println(border)
	
	for _, t := range tasks {
		labelsStr := strings.Join(t.Labels, ",")
		
		status := strings.ToUpper(t.Status)
		priority := strings.ToUpper(t.Priority)
		
		fmt.Printf("| %-2d | %-20.20s | %-6.6s | %-8.8s | %-10.10s |\n", 
			t.ID, t.Title, status, priority, labelsStr)
	}
	fmt.Println(border)
}

func PrintTasksCSV(tasks []Task) {
	writer := csv.NewWriter(os.Stdout)
	_ = writer.Write([]string{"id", "title", "status", "priority", "labels"})
	
	for _, t := range tasks {
		labelsStr := strings.Join(t.Labels, ";")
		_ = writer.Write([]string{
			fmt.Sprintf("%d", t.ID),
			t.Title,
			t.Status,
			t.Priority,
			labelsStr,
		})
	}
	writer.Flush()
}

func PrintTasksJSON(tasks []Task) {
	data, _ := json.Marshal(tasks)
	fmt.Println(string(data))
}

func PrintLabelsTable(db *Database) {
	border := "+-------------+-------------+"
	header := "| Label Name  | Task Count  |"
	
	fmt.Println(border)
	fmt.Println(header)
	fmt.Println(border)
	
	// Count occurrences
	counts := make(map[string]int)
	for _, l := range db.Labels {
		counts[l.Name] = 0
	}
	for _, t := range db.Tasks {
		for _, l := range t.Labels {
			counts[l]++
		}
	}
	
	for _, l := range db.Labels {
		fmt.Printf("| %-11.11s | %-11d |\n", l.Name, counts[l.Name])
	}
	fmt.Println(border)
}

func PrintSprintReport(db *Database) {
	total := len(db.Tasks)
	completed := 0
	todo := 0
	doing := 0
	done := 0
	
	high := 0
	medium := 0
	low := 0
	
	for _, t := range db.Tasks {
		switch t.Status {
		case "todo":
			todo++
		case "doing":
			doing++
		case "done":
			done++
			completed++
		}
		
		switch t.Priority {
		case "low":
			low++
		case "medium":
			medium++
		case "high":
			high++
		}
	}
	
	percent := 0
	if total > 0 {
		percent = (completed * 100) / total
	}
	
	// Print visual dashboard
	progressBlocks := percent / 10
	blocksStr := ""
	for i := 0; i < 10; i++ {
		if i < progressBlocks {
			blocksStr += "■"
		} else {
			blocksStr += "□"
		}
	}
	
	fmt.Println("========================================")
	fmt.Println("          MURLI-WORK SPRINT REPORT      ")
	fmt.Println("========================================")
	fmt.Printf("Completion Rate : [%s] %d%% (%d/%d tasks)\n\n", blocksStr, percent, completed, total)
	fmt.Println("Status Breakdown:")
	fmt.Printf("- TODO  : %d tasks\n", todo)
	fmt.Printf("- DOING : %d tasks\n", doing)
	fmt.Printf("- DONE  : %d tasks\n\n", done)
	fmt.Println("Priority Breakdown:")
	fmt.Printf("- HIGH  : %d tasks\n", high)
	fmt.Printf("- MEDIUM: %d tasks\n", medium)
	fmt.Printf("- LOW   : %d tasks\n", low)
	fmt.Println("========================================")
}
