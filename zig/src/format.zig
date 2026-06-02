const std = @import("std");
const db_mod = @import("db.zig");
const Task = db_mod.Task;
const Database = db_mod.Database;

fn toUpperAlloc(allocator: std.mem.Allocator, str: []const u8) ![]const u8 {
    const result = try allocator.alloc(u8, str.len);
    for (str, 0..) |c, i| {
        result[i] = std.ascii.toUpper(c);
    }
    return result;
}

fn trunc(str: []const u8, max_len: usize) []const u8 {
    if (str.len > max_len) return str[0..max_len];
    return str;
}

pub fn printTasksTable(allocator: std.mem.Allocator, writer: anytype, tasks: []const Task) !void {
    const border = "+----+----------------------+--------+----------+------------+";
    const header = "| ID | Title                | Status | Priority | Labels     |";

    try writer.print("{s}\n", .{border});
    try writer.print("{s}\n", .{header});
    try writer.print("{s}\n", .{border});

    for (tasks) |t| {
        var labels_list = std.ArrayList(u8).empty;
        defer labels_list.deinit(allocator);
        for (t.labels, 0..) |l, i| {
            if (i > 0) try labels_list.append(allocator, ',');
            try labels_list.appendSlice(allocator, l);
        }

        const status_upper = try toUpperAlloc(allocator, t.status);
        defer allocator.free(status_upper);

        const priority_upper = try toUpperAlloc(allocator, t.priority);
        defer allocator.free(priority_upper);

        const title_val = trunc(t.title, 20);
        const status_val = trunc(status_upper, 6);
        const prio_val = trunc(priority_upper, 8);
        const labels_val = trunc(labels_list.items, 10);

        try writer.print("| {d:<2} | {s:<20} | {s:<6} | {s:<8} | {s:<10} |\n", .{
            t.id, title_val, status_val, prio_val, labels_val,
        });
    }
    try writer.print("{s}\n", .{border});
}

fn csvEscape(allocator: std.mem.Allocator, str: []const u8) ![]const u8 {
    var list = std.ArrayList(u8).empty;
    errdefer list.deinit(allocator);
    for (str) |c| {
        if (c == '"') {
            try list.appendSlice(allocator, "\"\"");
        } else {
            try list.append(allocator, c);
        }
    }
    return try list.toOwnedSlice(allocator);
}

pub fn printTasksCsv(allocator: std.mem.Allocator, writer: anytype, tasks: []const Task) !void {
    try writer.print("id,title,status,priority,labels\n", .{});
    for (tasks) |t| {
        var labels_list = std.ArrayList(u8).empty;
        defer labels_list.deinit(allocator);
        for (t.labels, 0..) |l, i| {
            if (i > 0) try labels_list.append(allocator, ';');
            try labels_list.appendSlice(allocator, l);
        }

        const esc_title = try csvEscape(allocator, t.title);
        defer allocator.free(esc_title);

        const esc_labels = try csvEscape(allocator, labels_list.items);
        defer allocator.free(esc_labels);

        try writer.print("{d},\"{s}\",{s},{s},\"{s}\"\n", .{
            t.id, esc_title, t.status, t.priority, esc_labels,
        });
    }
}

pub fn printTasksJson(allocator: std.mem.Allocator, writer: anytype, tasks: []const Task) !void {
    var aw = std.Io.Writer.Allocating.init(allocator);
    defer aw.deinit();

    try std.json.Stringify.value(tasks, .{}, &aw.writer);
    try writer.print("{s}\n", .{aw.written()});
}

pub fn printLabelsTable(allocator: std.mem.Allocator, writer: anytype, db: Database) !void {
    const border = "+-------------+-------------+";
    const header = "| Label Name  | Task Count  |";

    try writer.print("{s}\n", .{border});
    try writer.print("{s}\n", .{header});
    try writer.print("{s}\n", .{border});

    var counts = std.StringHashMap(u32).init(allocator);
    defer counts.deinit();

    for (db.labels) |l| {
        try counts.put(l.name, 0);
    }
    for (db.tasks) |t| {
        for (t.labels) |l| {
            if (counts.getPtr(l)) |ptr| {
                ptr.* += 1;
            }
        }
    }

    for (db.labels) |l| {
        const count = counts.get(l.name) orelse 0;
        const name_val = trunc(l.name, 11);
        try writer.print("| {s:<11} | {d:<11} |\n", .{ name_val, count });
    }
    try writer.print("{s}\n", .{border});
}

pub fn printSprintReport(writer: anytype, db: Database) !void {
    const total = db.tasks.len;
    var completed: usize = 0;
    var todo: usize = 0;
    var doing: usize = 0;
    var done: usize = 0;

    var high: usize = 0;
    var medium: usize = 0;
    var low: usize = 0;

    for (db.tasks) |t| {
        if (std.mem.eql(u8, t.status, "todo")) {
            todo += 1;
        } else if (std.mem.eql(u8, t.status, "doing")) {
            doing += 1;
        } else if (std.mem.eql(u8, t.status, "done")) {
            done += 1;
            completed += 1;
        }

        if (std.mem.eql(u8, t.priority, "low")) {
            low += 1;
        } else if (std.mem.eql(u8, t.priority, "medium")) {
            medium += 1;
        } else if (std.mem.eql(u8, t.priority, "high")) {
            high += 1;
        }
    }

    const percent = if (total > 0) (completed * 100) / total else 0;
    const progress_blocks = percent / 10;
    var i: usize = 0;

    try writer.print("========================================\n", .{});
    try writer.print("          MURLI-WORK SPRINT REPORT      \n", .{});
    try writer.print("========================================\n", .{});
    
    try writer.print("Completion Rate : [", .{});
    i = 0;
    while (i < 10) : (i += 1) {
        if (i < progress_blocks) {
            try writer.print("■", .{});
        } else {
            try writer.print("□", .{});
        }
    }
    try writer.print("] {d}% ({d}/{d} tasks)\n\n", .{ percent, completed, total });

    try writer.print("Status Breakdown:\n", .{});
    try writer.print("- TODO  : {d} tasks\n", .{todo});
    try writer.print("- DOING : {d} tasks\n", .{doing});
    try writer.print("- DONE  : {d} tasks\n\n", .{done});

    try writer.print("Priority Breakdown:\n", .{});
    try writer.print("- HIGH  : {d} tasks\n", .{high});
    try writer.print("- MEDIUM: {d} tasks\n", .{medium});
    try writer.print("- LOW   : {d} tasks\n", .{low});
    try writer.print("========================================\n", .{});
}
