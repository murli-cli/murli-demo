import os
import json
import re
from datetime import datetime

def get_storage_dir():
    # Solve standard user config path
    if os.name == 'nt':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    elif os.name == 'posix' and os.uname().sysname == 'Darwin':
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    return os.path.join(base, 'murli-work')

def get_default_db():
    return {
        "tasks": [
            {"id": 1, "title": "Setup workspace layout", "desc": "Bootstrap directory structures for Go, Rust, Python and TS", "status": "done", "priority": "high", "labels": ["setup", "dev"], "created_at": "2026-05-28T18:00:00Z"},
            {"id": 2, "title": "Document CLI spec", "desc": "Draft the spec.md contracts and database JSON schemas", "status": "done", "priority": "medium", "labels": ["docs"], "created_at": "2026-05-28T18:30:00Z"},
            {"id": 3, "title": "Implement Cobra skeleton", "desc": "Build the Go Cobra reference implementation", "status": "doing", "priority": "high", "labels": ["dev", "go"], "created_at": "2026-05-29T04:00:00Z"},
            {"id": 4, "title": "Integrate Murli middleware", "desc": "Apply Murli wrappers to standard Go binaries", "status": "todo", "priority": "high", "labels": ["dev", "murli"], "created_at": "2026-05-29T05:00:00Z"},
            {"id": 5, "title": "Write Rust Clap reference", "desc": "Develop Rust-native Clap derive parser", "status": "todo", "priority": "medium", "labels": ["dev", "rust"], "created_at": "2026-05-29T06:00:00Z"}
        ],
        "labels": [
            {"name": "setup"},
            {"name": "dev"},
            {"name": "docs"},
            {"name": "go"},
            {"name": "murli"},
            {"name": "rust"}
        ]
    }

def get_default_config():
    return {
        "default_output": "table",
        "default_priority": "medium"
    }

def reset_db():
    dir_path = get_storage_dir()
    os.makedirs(dir_path, exist_ok=True)
    
    with open(os.path.join(dir_path, 'config.json'), 'w') as f:
        json.dump(get_default_config(), f, indent=2)
        
    with open(os.path.join(dir_path, 'db.json'), 'w') as f:
        json.dump(get_default_db(), f, indent=2)

def load_db():
    dir_path = get_storage_dir()
    db_path = os.path.join(dir_path, 'db.json')
    if not os.path.exists(db_path):
        reset_db()
    with open(db_path, 'r') as f:
        return json.load(f)

def save_db(db):
    dir_path = get_storage_dir()
    db_path = os.path.join(dir_path, 'db.json')
    with open(db_path, 'w') as f:
        json.dump(db, f, indent=2)

def load_config():
    dir_path = get_storage_dir()
    cfg_path = os.path.join(dir_path, 'config.json')
    if not os.path.exists(cfg_path):
        reset_db()
    with open(cfg_path, 'r') as f:
        return json.load(f)

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def auto_create_label(db, name):
    slug = slugify(name)
    if not slug:
        return
    for l in db['labels']:
        if l['name'] == slug:
            return
    db['labels'].append({"name": slug})

# Mutations
def create_task(db, title, desc="", priority=None, raw_labels=None):
    if not priority:
        try:
            cfg = load_config()
            priority = cfg.get("default_priority", "medium")
        except:
            priority = "medium"
    
    priority = priority.lower()
    if priority not in ["low", "medium", "high"]:
        raise ValueError("invalid priority (low|medium|high)")
        
    next_id = 1
    for t in db['tasks']:
        if t['id'] >= next_id:
            next_id = t['id'] + 1
            
    slug_labels = []
    if raw_labels:
        for l in raw_labels:
            slug = slugify(l)
            if slug:
                auto_create_label(db, slug)
                slug_labels.append(slug)
                
    new_task = {
        "id": next_id,
        "title": title,
        "desc": desc or "",
        "status": "todo",
        "priority": priority,
        "labels": slug_labels,
        "created_at": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    }
    db['tasks'].append(new_task)
    save_db(db)
    return next_id

def update_task(db, id, title=None, desc=None, priority=None, status=None, raw_labels=None):
    target = None
    for t in db['tasks']:
        if t['id'] == id:
            target = t
            break
            
    if not target:
        raise KeyError(f"task with ID {id} not found")
        
    if title is not None and title != "":
        target['title'] = title
    if desc is not None:
        target['desc'] = desc
    if priority is not None and priority != "":
        p = priority.lower()
        if p not in ["low", "medium", "high"]:
            raise ValueError("invalid priority (low|medium|high)")
        target['priority'] = p
    if status is not None and status != "":
        s = status.lower()
        if s not in ["todo", "doing", "done"]:
            raise ValueError("invalid status (todo|doing|done)")
        target['status'] = s
    if raw_labels is not None:
        slug_labels = []
        for l in raw_labels:
            slug = slugify(l)
            if slug:
                auto_create_label(db, slug)
                slug_labels.append(slug)
        target['labels'] = slug_labels
        
    save_db(db)

def delete_task(db, id):
    idx = -1
    for i, t in enumerate(db['tasks']):
        if t['id'] == id:
            idx = i
            break
            
    if idx == -1:
        raise KeyError(f"task with ID {id} not found")
        
    db['tasks'].pop(idx)
    save_db(db)

def create_label(db, name):
    slug = slugify(name)
    if not slug:
        raise ValueError("invalid label name")
        
    for l in db['labels']:
        if l['name'] == slug:
            raise FileExistsError(f'label "{slug}" already exists')
            
    db['labels'].append({"name": slug})
    save_db(db)
    return slug

def delete_label(db, name):
    slug = slugify(name)
    idx = -1
    for i, l in enumerate(db['labels']):
        if l['name'] == slug:
            idx = i
            break
            
    if idx == -1:
        raise KeyError(f'label "{name}" not found')
        
    db['labels'].pop(idx)
    
    # Remove from tasks
    for t in db['tasks']:
        t['labels'] = [lbl for lbl in t['labels'] if lbl != slug]
        
    save_db(db)
