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


import io


def format_tasks_table(tasks: list) -> str:
    border = "+----+----------------------+--------+----------+------------+"
    header = "| ID | Title                | Status | Priority | Labels     |"
    lines = [border, header, border]
    for t in tasks:
        labels_str = ",".join(t["labels"])
        lines.append(
            f"| {t['id']:<2d} | {t['title'][:20]:<20s} | {t['status'].upper()[:6]:<6s}"
            f" | {t['priority'].upper()[:8]:<8s} | {labels_str[:10]:<10s} |"
        )
    lines.append(border)
    return "\n".join(lines)


def format_tasks_csv(tasks: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    w.writerow(["id", "title", "status", "priority", "labels"])
    for t in tasks:
        w.writerow([t["id"], t["title"], t["status"], t["priority"], ";".join(t["labels"])])
    return buf.getvalue().rstrip()


def format_tasks_json_str(tasks: list) -> str:
    return json.dumps(tasks, separators=(",", ":"))


def format_labels_table(db: dict) -> str:
    counts = {l["name"]: 0 for l in db["labels"]}
    for t in db["tasks"]:
        for lbl in t["labels"]:
            if lbl in counts:
                counts[lbl] += 1
    border = "+-------------+-------------+"
    header = "| Label Name  | Task Count  |"
    lines = [border, header, border]
    for l in db["labels"]:
        lines.append(f"| {l['name'][:11]:<11s} | {counts[l['name']]:<11d} |")
    lines.append(border)
    return "\n".join(lines)


def sprint_report_data(db: dict) -> dict:
    total = len(db["tasks"])
    completed = todo = doing = done = high = medium = low = 0
    for t in db["tasks"]:
        s = t["status"].lower()
        if s == "todo":
            todo += 1
        elif s == "doing":
            doing += 1
        elif s == "done":
            done += 1
            completed += 1
        p = t["priority"].lower()
        if p == "low":
            low += 1
        elif p == "medium":
            medium += 1
        elif p == "high":
            high += 1
    percent = (completed * 100) // total if total > 0 else 0
    return {
        "total": total,
        "completed": completed,
        "percent": percent,
        "status": {"todo": todo, "doing": doing, "done": done},
        "priority": {"high": high, "medium": medium, "low": low},
    }


def format_sprint_report(db: dict) -> str:
    data = sprint_report_data(db)
    percent = data["percent"]
    blocks = "■" * (percent // 10) + "□" * (10 - percent // 10)
    s = data["status"]
    p = data["priority"]
    lines = [
        "========================================",
        "          MURLI-WORK SPRINT REPORT      ",
        "========================================",
        f"Completion Rate : [{blocks}] {percent}% ({data['completed']}/{data['total']} tasks)",
        "",
        "Status Breakdown:",
        f"- TODO  : {s['todo']} tasks",
        f"- DOING : {s['doing']} tasks",
        f"- DONE  : {s['done']} tasks",
        "",
        "Priority Breakdown:",
        f"- HIGH  : {p['high']} tasks",
        f"- MEDIUM: {p['medium']} tasks",
        f"- LOW   : {p['low']} tasks",
        "========================================",
    ]
    return "\n".join(lines)
