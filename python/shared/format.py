import sys
import json
import csv

def print_tasks_table(tasks):
    border = "+----+----------------------+--------+----------+------------+"
    header = "| ID | Title                | Status | Priority | Labels     |"
    
    print(border)
    print(header)
    print(border)
    
    for t in tasks:
        labels_str = ",".join(t['labels'])
        status = t['status'].upper()
        priority = t['priority'].upper()
        
        # Exact fixed-width spacing matching borders:
        # Col 1: ID width 2 (pad spaces)
        # Col 2: Title width 20 (truncate)
        # Col 3: Status width 6
        # Col 4: Priority width 8
        # Col 5: Labels width 10
        print(f"| {t['id']:<2d} | {t['title'][:20]:<20s} | {status[:6]:<6s} | {priority[:8]:<8s} | {labels_str[:10]:<10s} |")
    print(border)

def print_tasks_csv(tasks):
    writer = csv.writer(sys.stdout, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["id", "title", "status", "priority", "labels"])
    for t in tasks:
        labels_str = ";".join(t['labels'])
        writer.writerow([
            t['id'],
            t['title'],
            t['status'],
            t['priority'],
            labels_str
        ])

def print_tasks_json(tasks):
    print(json.dumps(tasks, separators=(',', ':')))

def print_labels_table(db):
    border = "+-------------+-------------+"
    header = "| Label Name  | Task Count  |"
    
    print(border)
    print(header)
    print(border)
    
    counts = {l['name']: 0 for l in db['labels']}
    for t in db['tasks']:
        for l in t['labels']:
            if l in counts:
                counts[l] += 1
                
    for l in db['labels']:
        print(f"| {l['name'][:11]:<11s} | {counts[l['name']]:<11d} |")
    print(border)

def print_sprint_report(db):
    total = len(db['tasks'])
    completed = 0
    todo = 0
    doing = 0
    done = 0
    
    high = 0
    medium = 0
    low = 0
    
    for t in db['tasks']:
        status = t['status'].lower()
        if status == 'todo':
            todo += 1
        elif status == 'doing':
            doing += 1
        elif status == 'done':
            done += 1
            completed += 1
            
        prio = t['priority'].lower()
        if prio == 'low':
            low += 1
        elif prio == 'medium':
            medium += 1
        elif prio == 'high':
            high += 1
            
    percent = 0
    if total > 0:
        percent = (completed * 100) // total
        
    progress_blocks = percent // 10
    blocks_str = "■" * progress_blocks + "□" * (10 - progress_blocks)
    
    print("========================================")
    print("          MURLI-WORK SPRINT REPORT      ")
    print("========================================")
    print(f"Completion Rate : [{blocks_str}] {percent}% ({completed}/{total} tasks)\n")
    print("Status Breakdown:")
    print(f"- TODO  : {todo} tasks")
    print(f"- DOING : {doing} tasks")
    print(f"- DONE  : {done} tasks\n")
    print("Priority Breakdown:")
    print(f"- HIGH  : {high} tasks")
    print(f"- MEDIUM: {medium} tasks")
    print(f"- LOW   : {low} tasks")
    print("========================================")
