package shared

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

type Task struct {
	ID        int      `json:"id"`
	Title     string   `json:"title"`
	Desc      string   `json:"desc"`
	Status    string   `json:"status"`
	Priority  string   `json:"priority"`
	Labels    []string `json:"labels"`
	CreatedAt string   `json:"created_at"`
}

type Label struct {
	Name string `json:"name"`
}

type Database struct {
	Tasks  []Task  `json:"tasks"`
	Labels []Label `json:"labels"`
}

type Config struct {
	DefaultOutput   string `json:"default_output"`
	DefaultPriority string `json:"default_priority"`
}

func GetStorageDir() (string, error) {
	configDir, err := os.UserConfigDir()
	if err != nil {
		return "", err
	}
	dir := filepath.Join(configDir, "murli-work")
	return dir, nil
}

func GetDefaultDatabase() *Database {
	return &Database{
		Tasks: []Task{
			{ID: 1, Title: "Setup workspace layout", Desc: "Bootstrap directory structures for Go, Rust, Python and TS", Status: "done", Priority: "high", Labels: []string{"setup", "dev"}, CreatedAt: "2026-05-28T18:00:00Z"},
			{ID: 2, Title: "Document CLI spec", Desc: "Draft the spec.md contracts and database JSON schemas", Status: "done", Priority: "medium", Labels: []string{"docs"}, CreatedAt: "2026-05-28T18:30:00Z"},
			{ID: 3, Title: "Implement Cobra skeleton", Desc: "Build the Go Cobra reference implementation", Status: "doing", Priority: "high", Labels: []string{"dev", "go"}, CreatedAt: "2026-05-29T04:00:00Z"},
			{ID: 4, Title: "Integrate Murli middleware", Desc: "Apply Murli wrappers to standard Go binaries", Status: "todo", Priority: "high", Labels: []string{"dev", "murli"}, CreatedAt: "2026-05-29T05:00:00Z"},
			{ID: 5, Title: "Write Rust Clap reference", Desc: "Develop Rust-native Clap derive parser", Status: "todo", Priority: "medium", Labels: []string{"dev", "rust"}, CreatedAt: "2026-05-29T06:00:00Z"},
		},
		Labels: []Label{
			{Name: "setup"},
			{Name: "dev"},
			{Name: "docs"},
			{Name: "go"},
			{Name: "murli"},
			{Name: "rust"},
		},
	}
}

func GetDefaultConfig() *Config {
	return &Config{
		DefaultOutput:   "table",
		DefaultPriority: "medium",
	}
}

func LoadDatabase() (*Database, error) {
	dir, err := GetStorageDir()
	if err != nil {
		return nil, err
	}

	dbPath := filepath.Join(dir, "db.json")
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		// Initialize
		if err := ResetDatabase(); err != nil {
			return nil, err
		}
	}

	data, err := os.ReadFile(dbPath)
	if err != nil {
		return nil, err
	}

	var db Database
	if err := json.Unmarshal(data, &db); err != nil {
		return nil, err
	}

	return &db, nil
}

func SaveDatabase(db *Database) error {
	dir, err := GetStorageDir()
	if err != nil {
		return err
	}

	dbPath := filepath.Join(dir, "db.json")
	data, err := json.MarshalIndent(db, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(dbPath, data, 0644)
}

func LoadConfig() (*Config, error) {
	dir, err := GetStorageDir()
	if err != nil {
		return nil, err
	}

	cfgPath := filepath.Join(dir, "config.json")
	if _, err := os.Stat(cfgPath); os.IsNotExist(err) {
		if err := ResetDatabase(); err != nil {
			return nil, err
		}
	}

	data, err := os.ReadFile(cfgPath)
	if err != nil {
		return nil, err
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}

func ResetDatabase() error {
	dir, err := GetStorageDir()
	if err != nil {
		return err
	}

	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}

	// Write config
	cfg := GetDefaultConfig()
	cfgData, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(dir, "config.json"), cfgData, 0644); err != nil {
		return err
	}

	// Write db
	db := GetDefaultDatabase()
	dbData, err := json.MarshalIndent(db, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(dir, "db.json"), dbData, 0644); err != nil {
		return err
	}

	return nil
}

func Slugify(text string) string {
	text = strings.ToLower(text)
	reg := regexp.MustCompile("[^a-z0-9]+")
	text = reg.ReplaceAllString(text, "-")
	text = strings.Trim(text, "-")
	return text
}

func (db *Database) AutoCreateLabel(name string) {
	slug := Slugify(name)
	if slug == "" {
		return
	}
	for _, l := range db.Labels {
		if l.Name == slug {
			return
		}
	}
	db.Labels = append(db.Labels, Label{Name: slug})
}

// CRUD operations
func (db *Database) CreateTask(title, desc, priority string, rawLabels []string) (int, error) {
	if priority == "" {
		cfg, _ := LoadConfig()
		if cfg != nil {
			priority = cfg.DefaultPriority
		} else {
			priority = "medium"
		}
	}
	priority = strings.ToLower(priority)
	if priority != "low" && priority != "medium" && priority != "high" {
		return 0, errors.New("invalid priority (low|medium|high)")
	}

	// Get next ID
	nextID := 1
	for _, t := range db.Tasks {
		if t.ID >= nextID {
			nextID = t.ID + 1
		}
	}

	slugLabels := []string{}
	for _, l := range rawLabels {
		slug := Slugify(l)
		if slug != "" {
			db.AutoCreateLabel(slug)
			slugLabels = append(slugLabels, slug)
		}
	}

	newTask := Task{
		ID:        nextID,
		Title:     title,
		Desc:      desc,
		Status:    "todo",
		Priority:  priority,
		Labels:    slugLabels,
		CreatedAt: time.Now().UTC().Format(time.RFC3339),
	}

	db.Tasks = append(db.Tasks, newTask)
	if err := SaveDatabase(db); err != nil {
		return 0, err
	}

	return nextID, nil
}

func (db *Database) UpdateTask(id int, title, desc, priority, status *string, rawLabels *[]string) error {
	idx := -1
	for i, t := range db.Tasks {
		if t.ID == id {
			idx = i
			break
		}
	}

	if idx == -1 {
		return fmt.Errorf("task with ID %d not found", id)
	}

	t := &db.Tasks[idx]

	if title != nil && *title != "" {
		t.Title = *title
	}
	if desc != nil {
		t.Desc = *desc
	}
	if priority != nil && *priority != "" {
		p := strings.ToLower(*priority)
		if p != "low" && p != "medium" && p != "high" {
			return errors.New("invalid priority (low|medium|high)")
		}
		t.Priority = p
	}
	if status != nil && *status != "" {
		s := strings.ToLower(*status)
		if s != "todo" && s != "doing" && s != "done" {
			return errors.New("invalid status (todo|doing|done)")
		}
		t.Status = s
	}
	if rawLabels != nil {
		slugLabels := []string{}
		for _, l := range *rawLabels {
			slug := Slugify(l)
			if slug != "" {
				db.AutoCreateLabel(slug)
				slugLabels = append(slugLabels, slug)
			}
		}
		t.Labels = slugLabels
	}

	return SaveDatabase(db)
}

func (db *Database) DeleteTask(id int) error {
	idx := -1
	for i, t := range db.Tasks {
		if t.ID == id {
			idx = i
			break
		}
	}

	if idx == -1 {
		return fmt.Errorf("task with ID %d not found", id)
	}

	db.Tasks = append(db.Tasks[:idx], db.Tasks[idx+1:]...)
	return SaveDatabase(db)
}

func (db *Database) CreateLabel(name string) (string, error) {
	slug := Slugify(name)
	if slug == "" {
		return "", errors.New("invalid label name")
	}

	for _, l := range db.Labels {
		if l.Name == slug {
			return "", fmt.Errorf("label \"%s\" already exists", slug)
		}
	}

	db.Labels = append(db.Labels, Label{Name: slug})
	if err := SaveDatabase(db); err != nil {
		return "", err
	}
	return slug, nil
}

func (db *Database) DeleteLabel(name string) error {
	slug := Slugify(name)
	idx := -1
	for i, l := range db.Labels {
		if l.Name == slug {
			idx = i
			break
		}
	}

	if idx == -1 {
		return fmt.Errorf("label \"%s\" not found", name)
	}

	db.Labels = append(db.Labels[:idx], db.Labels[idx+1:]...)

	// Remove label from all tasks
	for i, t := range db.Tasks {
		newLabels := []string{}
		for _, l := range t.Labels {
			if l != slug {
				newLabels = append(newLabels, l)
			}
		}
		db.Tasks[i].Labels = newLabels
	}

	return SaveDatabase(db)
}
