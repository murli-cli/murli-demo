const std = @import("std");

pub const Task = struct {
    id: u32,
    title: []const u8,
    desc: []const u8,
    status: []const u8,
    priority: []const u8,
    labels: [][]const u8,
    created_at: []const u8,
};

pub const Label = struct {
    name: []const u8,
};

pub const Database = struct {
    tasks: []Task,
    labels: []Label,
};

pub const Config = struct {
    default_output: []const u8,
    default_priority: []const u8,
};

pub const default_config =
    \\{
    \\  "default_output": "table",
    \\  "default_priority": "medium"
    \\}
;

pub const default_db =
    \\{
    \\  "tasks": [
    \\    {
    \\      "id": 1,
    \\      "title": "Setup workspace layout",
    \\      "desc": "Bootstrap directory structures for Go, Rust, Python and TS",
    \\      "status": "done",
    \\      "priority": "high",
    \\      "labels": ["setup", "dev"],
    \\      "created_at": "2026-05-28T18:00:00Z"
    \\    },
    \\    {
    \\      "id": 2,
    \\      "title": "Document CLI specification",
    \\      "desc": "Draft the spec.md contracts and database JSON schemas",
    \\      "status": "done",
    \\      "priority": "medium",
    \\      "labels": ["docs"],
    \\      "created_at": "2026-05-28T18:30:00Z"
    \\    },
    \\    {
    \\      "id": 3,
    \\      "title": "Implement Cobra skeleton",
    \\      "desc": "Build the Go Cobra reference implementation",
    \\      "status": "doing",
    \\      "priority": "high",
    \\      "labels": ["dev", "go"],
    \\      "created_at": "2026-05-29T04:00:00Z"
    \\    },
    \\    {
    \\      "id": 4,
    \\      "title": "Integrate Murli middleware",
    \\      "desc": "Apply Murli wrappers to standard Go binaries",
    \\      "status": "todo",
    \\      "priority": "high",
    \\      "labels": ["dev", "murli"],
    \\      "created_at": "2026-05-29T05:00:00Z"
    \\    },
    \\    {
    \\      "id": 5,
    \\      "title": "Write Rust Clap reference",
    \\      "desc": "Develop Rust-native Clap derive parser",
    \\      "status": "todo",
    \\      "priority": "medium",
    \\      "labels": ["dev", "rust"],
    \\      "created_at": "2026-05-29T06:00:00Z"
    \\    }
    \\  ],
    \\  "labels": [
    \\    { "name": "setup" },
    \\    { "name": "dev" },
    \\    { "name": "docs" },
    \\    { "name": "go" },
    \\    { "name": "murli" },
    \\    { "name": "rust" }
    \\  ]
    \\}
;

pub fn getStorageDir(allocator: std.mem.Allocator, environ: anytype) ![]const u8 {
    const os_tag = @import("builtin").os.tag;
    if (os_tag == .windows) {
        if (environ.get("APPDATA")) |appdata| {
            return try std.fs.path.join(allocator, &.{ appdata, "murli-work" });
        }
        if (environ.get("USERPROFILE")) |profile| {
            return try std.fs.path.join(allocator, &.{ profile, "AppData", "Roaming", "murli-work" });
        }
    } else if (os_tag == .macos) {
        if (environ.get("HOME")) |home| {
            return try std.fs.path.join(allocator, &.{ home, "Library", "Application Support", "murli-work" });
        }
    } else {
        if (environ.get("XDG_CONFIG_HOME")) |xdg| {
            return try std.fs.path.join(allocator, &.{ xdg, "murli-work" });
        }
        if (environ.get("HOME")) |home| {
            return try std.fs.path.join(allocator, &.{ home, ".config", "murli-work" });
        }
    }
    return error.StorageDirNotFound;
}

pub fn resetDb(allocator: std.mem.Allocator, io: anytype, environ: anytype) !void {
    const dir = try getStorageDir(allocator, environ);
    defer allocator.free(dir);

    try std.Io.Dir.cwd().createDirPath(io, dir);

    const config_path = try std.fs.path.join(allocator, &.{ dir, "config.json" });
    defer allocator.free(config_path);
    const config_file = try std.Io.Dir.cwd().createFile(io, config_path, .{});
    defer config_file.close(io);
    try config_file.writeStreamingAll(io, default_config);

    const db_path = try std.fs.path.join(allocator, &.{ dir, "db.json" });
    defer allocator.free(db_path);
    const db_file = try std.Io.Dir.cwd().createFile(io, db_path, .{});
    defer db_file.close(io);
    try db_file.writeStreamingAll(io, default_db);
}

pub fn loadDb(allocator: std.mem.Allocator, io: anytype, environ: anytype) !std.json.Parsed(Database) {
    const dir = try getStorageDir(allocator, environ);
    defer allocator.free(dir);

    const db_path = try std.fs.path.join(allocator, &.{ dir, "db.json" });
    defer allocator.free(db_path);

    const file = std.Io.Dir.cwd().openFile(io, db_path, .{}) catch blk: {
        try resetDb(allocator, io, environ);
        break :blk try std.Io.Dir.cwd().openFile(io, db_path, .{});
    };
    defer file.close(io);

    const file_stat = try file.stat(io);
    const size = file_stat.size;
    const buffer = try allocator.alloc(u8, size);
    defer allocator.free(buffer);

    _ = try file.readPositionalAll(io, buffer, 0);

    return try std.json.parseFromSlice(Database, allocator, buffer, .{ .ignore_unknown_fields = true, .allocate = .alloc_always });
}

pub fn saveDb(allocator: std.mem.Allocator, io: anytype, environ: anytype, db: Database) !void {
    const dir = try getStorageDir(allocator, environ);
    defer allocator.free(dir);

    const db_path = try std.fs.path.join(allocator, &.{ dir, "db.json" });
    defer allocator.free(db_path);

    var aw = std.Io.Writer.Allocating.init(allocator);
    defer aw.deinit();

    try std.json.Stringify.value(db, .{ .whitespace = .indent_2 }, &aw.writer);

    const file = try std.Io.Dir.cwd().createFile(io, db_path, .{});
    defer file.close(io);
    try file.writeStreamingAll(io, aw.written());
}

pub fn loadConfig(allocator: std.mem.Allocator, io: anytype, environ: anytype) !std.json.Parsed(Config) {
    const dir = try getStorageDir(allocator, environ);
    defer allocator.free(dir);

    const cfg_path = try std.fs.path.join(allocator, &.{ dir, "config.json" });
    defer allocator.free(cfg_path);

    const file = std.Io.Dir.cwd().openFile(io, cfg_path, .{}) catch blk: {
        try resetDb(allocator, io, environ);
        break :blk try std.Io.Dir.cwd().openFile(io, cfg_path, .{});
    };
    defer file.close(io);

    const file_stat = try file.stat(io);
    const size = file_stat.size;
    const buffer = try allocator.alloc(u8, size);
    defer allocator.free(buffer);

    _ = try file.readPositionalAll(io, buffer, 0);

    return try std.json.parseFromSlice(Config, allocator, buffer, .{ .ignore_unknown_fields = true, .allocate = .alloc_always });
}

pub fn slugify(allocator: std.mem.Allocator, text: []const u8) ![]const u8 {
    var result = std.ArrayList(u8).empty;
    errdefer result.deinit(allocator);

    var last_was_hyphen = true;
    for (text) |c| {
        const lower = std.ascii.toLower(c);
        if (std.ascii.isAlphanumeric(lower)) {
            try result.append(allocator, lower);
            last_was_hyphen = false;
        } else {
            if (!last_was_hyphen) {
                try result.append(allocator, '-');
                last_was_hyphen = true;
            }
        }
    }

    var slice = result.items;
    while (slice.len > 0 and slice[slice.len - 1] == '-') {
        slice = slice[0 .. slice.len - 1];
    }
    return try allocator.dupe(u8, slice);
}
