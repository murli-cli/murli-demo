const std = @import("std");
const clap = @import("clap");
const db_mod = @import("db.zig");
const format_mod = @import("format.zig");

const Task = db_mod.Task;
const Label = db_mod.Label;
const Database = db_mod.Database;
const Config = db_mod.Config;

fn getIsoTimestamp(allocator: std.mem.Allocator, io: anytype) ![]const u8 {
    const ts = std.Io.Timestamp.now(io, .real);
    const epoch_s = ts.toSeconds();
    const epoch_days = @divFloor(epoch_s, 86400);
    const day_s = @mod(epoch_s, 86400);

    var year: i32 = 1970;
    var days = epoch_days;
    while (true) {
        const is_leap = (@mod(year, 4) == 0 and @mod(year, 100) != 0) or (@mod(year, 400) == 0);
        const y_days: i32 = if (is_leap) 366 else 365;
        if (days < y_days) break;
        days -= y_days;
        year += 1;
    }
    const is_leap = (@mod(year, 4) == 0 and @mod(year, 100) != 0) or (@mod(year, 400) == 0);
    const months_days = [12]i32{ 31, if (is_leap) 29 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };
    var month: i32 = 1;
    for (months_days, 0..) |m_days, idx| {
        if (days < m_days) {
            month = @intCast(idx + 1);
            break;
        }
        days -= m_days;
    }
    const day = days + 1;

    const hour = @divFloor(day_s, 3600);
    const minute = @divFloor(@mod(day_s, 3600), 60);
    const second = @mod(day_s, 60);

    return try std.fmt.allocPrint(allocator, "{d:0>4}-{d:0>2}-{d:0>2}T{d:0>2}:{d:0>2}:{d:0>2}Z", .{
        year, month, day, hour, minute, second,
    });
}

fn printUsage(writer: anytype) !void {
    try writer.writeAll(
        \\murli-work is a sprint and project task tracker
        \\
        \\Usage:
        \\  murli-work [command]
        \\
        \\Available Commands:
        \\  init        Initialize/Reset the database and config
        \\  task        Manage sprint tasks
        \\  label       Manage global task labels
        \\  report      Display progress report
        \\
        \\Flags:
        \\  -h, --help   Display this help message
        \\
    );
}

fn printTaskUsage(writer: anytype) !void {
    try writer.writeAll(
        \\Manage sprint tasks
        \\
        \\Usage:
        \\  murli-work task [command]
        \\
        \\Available Commands:
        \\  create      Create a new task
        \\  list        List stored tasks
        \\  update      Update an existing task's fields
        \\  delete      Delete a task
        \\
    );
}

fn printLabelUsage(writer: anytype) !void {
    try writer.writeAll(
        \\Manage global task labels
        \\
        \\Usage:
        \\  murli-work label [command]
        \\
        \\Available Commands:
        \\  create      Create a custom label
        \\  delete      Delete a label
        \\  list        List all defined labels
        \\
    );
}

fn exit(stdout: anytype, stderr: anytype, code: u8) noreturn {
    stdout.flush() catch {};
    stderr.flush() catch {};
    std.process.exit(code);
}

pub fn main(init: std.process.Init) !void {
    const allocator = init.gpa;
    const io = init.io;

    var stdout_buf: [4096]u8 = undefined;
    var stdout_file_writer = std.Io.File.stdout().writer(io, &stdout_buf);
    const stdout = &stdout_file_writer.interface;

    var stderr_buf: [4096]u8 = undefined;
    var stderr_file_writer = std.Io.File.stderr().writer(io, &stderr_buf);
    const stderr = &stderr_file_writer.interface;

    var iter = try init.minimal.args.iterateAllocator(allocator);
    defer iter.deinit();

    _ = iter.next(); // Skip executable name

    const cmd = iter.next() orelse {
        try printUsage(stdout);
        exit(stdout, stderr, 0);
    };

    if (std.mem.eql(u8, cmd, "-h") or std.mem.eql(u8, cmd, "--help")) {
        try printUsage(stdout);
        exit(stdout, stderr, 0);
    }

    if (std.mem.eql(u8, cmd, "init")) {
        const params = comptime clap.parseParamsComptime(
            \\-h, --help             Display help.
            \\
        );
        var diag = clap.Diagnostic{};
        var res = clap.parseEx(clap.Help, &params, clap.parsers.default, &iter, .{
            .diagnostic = &diag,
            .allocator = allocator,
        }) catch |err| {
            try diag.reportToFile(init.io, .stderr(), err);
            exit(stdout, stderr, 2);
        };
        defer res.deinit();

        if (res.args.help != 0) {
            try stdout.print("Initialize/Reset the database and config\n", .{});
            exit(stdout, stderr, 0);
        }

        db_mod.resetDb(allocator, init.io, init.environ_map) catch |err| {
            try stderr.print("Error: Could not reset the database: {any}\n", .{err});
            exit(stdout, stderr, 1);
        };

        const dir = try db_mod.getStorageDir(allocator, init.environ_map);
        defer allocator.free(dir);
        try stdout.print("Initialized/Reset murli-work database with sample data and configuration in {s}\n", .{dir});
        exit(stdout, stderr, 0);
    } else if (std.mem.eql(u8, cmd, "task")) {
        const task_cmd = iter.next() orelse {
            try printTaskUsage(stdout);
            exit(stdout, stderr, 0);
        };

        if (std.mem.eql(u8, task_cmd, "-h") or std.mem.eql(u8, task_cmd, "--help")) {
            try printTaskUsage(stdout);
            exit(stdout, stderr, 0);
        }

        if (std.mem.eql(u8, task_cmd, "create")) {
            const params = comptime clap.parseParamsComptime(
                \\-h, --help             Display help.
                \\-d, --desc <str>       Description.
                \\-p, --priority <str>   Priority.
                \\-l, --labels <str>     Comma-separated labels.
                \\<str>                  Title.
                \\
            );
            var diag = clap.Diagnostic{};
            var res = clap.parseEx(clap.Help, &params, clap.parsers.default, &iter, .{
                .diagnostic = &diag,
                .allocator = allocator,
            }) catch |err| {
                try diag.reportToFile(init.io, .stderr(), err);
                exit(stdout, stderr, 2);
            };
            defer res.deinit();

            if (res.args.help != 0) {
                try stdout.print("Create a new task\n", .{});
                exit(stdout, stderr, 0);
            }

            const title = res.positionals[0] orelse {
                try stderr.print("Error: Missing task title.\n", .{});
                exit(stdout, stderr, 2);
            };

            const desc = res.args.desc orelse "";
            var priority = res.args.priority orelse "";

            var parsed_db = try db_mod.loadDb(allocator, init.io, init.environ_map);
            defer parsed_db.deinit();

            if (priority.len == 0) {
                if (db_mod.loadConfig(allocator, init.io, init.environ_map)) |parsed_cfg| {
                    priority = parsed_cfg.value.default_priority;
                } else |_| {
                    priority = "medium";
                }
            }

            const prio_lower = try allocator.alloc(u8, priority.len);
            defer allocator.free(prio_lower);
            for (priority, 0..) |c, idx| {
                prio_lower[idx] = std.ascii.toLower(c);
            }

            if (!std.mem.eql(u8, prio_lower, "low") and !std.mem.eql(u8, prio_lower, "medium") and !std.mem.eql(u8, prio_lower, "high")) {
                try stderr.print("Error: invalid priority (low|medium|high)\n", .{});
                exit(stdout, stderr, 2);
            }

            var label_array = std.ArrayList([]const u8).empty;
            defer label_array.deinit(allocator);

            if (res.args.labels) |raw_labels| {
                var l_iter = std.mem.splitScalar(u8, raw_labels, ',');
                while (l_iter.next()) |l| {
                    const slug = try db_mod.slugify(allocator, l);
                    if (slug.len > 0) {
                        try label_array.append(allocator, slug);

                        // Auto create in global label array
                        var exists = false;
                        for (parsed_db.value.labels) |gl| {
                            if (std.mem.eql(u8, gl.name, slug)) {
                                exists = true;
                                break;
                            }
                        }
                        if (!exists) {
                            var new_labels = try allocator.alloc(Label, parsed_db.value.labels.len + 1);
                            @memcpy(new_labels[0..parsed_db.value.labels.len], parsed_db.value.labels);
                            new_labels[parsed_db.value.labels.len] = Label{ .name = slug };
                            parsed_db.value.labels = new_labels;
                        }
                    }
                }
            }

            var next_id: u32 = 1;
            for (parsed_db.value.tasks) |t| {
                if (t.id >= next_id) next_id = t.id + 1;
            }

            const created_at = try getIsoTimestamp(allocator, init.io);
            defer allocator.free(created_at);

            const new_task = Task{
                .id = next_id,
                .title = title,
                .desc = desc,
                .status = "todo",
                .priority = prio_lower,
                .labels = label_array.items,
                .created_at = created_at,
            };

            var new_tasks = try allocator.alloc(Task, parsed_db.value.tasks.len + 1);
            @memcpy(new_tasks[0..parsed_db.value.tasks.len], parsed_db.value.tasks);
            new_tasks[parsed_db.value.tasks.len] = new_task;
            parsed_db.value.tasks = new_tasks;

            try db_mod.saveDb(allocator, init.io, init.environ_map, parsed_db.value);

            try stdout.print("Task {d} (\"{s}\") created successfully.\n", .{ next_id, title });
            exit(stdout, stderr, 0);
        } else if (std.mem.eql(u8, task_cmd, "list")) {
            const params = comptime clap.parseParamsComptime(
                \\-h, --help             Display help.
                \\-s, --status <str>     Status.
                \\-p, --priority <str>   Priority.
                \\-l, --label <str>      Label.
                \\-o, --output <str>     Output format.
                \\
            );
            var diag = clap.Diagnostic{};
            var res = clap.parseEx(clap.Help, &params, clap.parsers.default, &iter, .{
                .diagnostic = &diag,
                .allocator = allocator,
            }) catch |err| {
                try diag.reportToFile(init.io, .stderr(), err);
                exit(stdout, stderr, 2);
            };
            defer res.deinit();

            if (res.args.help != 0) {
                try stdout.print("List stored tasks\n", .{});
                exit(stdout, stderr, 0);
            }

            var parsed_db = try db_mod.loadDb(allocator, init.io, init.environ_map);
            defer parsed_db.deinit();

            var filtered = std.ArrayList(Task).empty;
            defer filtered.deinit(allocator);

            for (parsed_db.value.tasks) |t| {
                if (res.args.status) |s| {
                    if (!std.mem.eql(u8, t.status, s)) continue;
                }
                if (res.args.priority) |p| {
                    if (!std.mem.eql(u8, t.priority, p)) continue;
                }
                if (res.args.label) |l| {
                    var found = false;
                    for (t.labels) |tl| {
                        if (std.mem.eql(u8, tl, l)) {
                            found = true;
                            break;
                        }
                    }
                    if (!found) continue;
                }
                try filtered.append(allocator, t);
            }

            var output_fmt = res.args.output orelse "";
            if (output_fmt.len == 0) {
                if (db_mod.loadConfig(allocator, init.io, init.environ_map)) |parsed_cfg| {
                    output_fmt = parsed_cfg.value.default_output;
                } else |_| {
                    output_fmt = "table";
                }
            }

            if (std.mem.eql(u8, output_fmt, "csv")) {
                try format_mod.printTasksCsv(allocator, stdout, filtered.items);
            } else if (std.mem.eql(u8, output_fmt, "json")) {
                try format_mod.printTasksJson(allocator, stdout, filtered.items);
            } else {
                try format_mod.printTasksTable(allocator, stdout, filtered.items);
            }
            exit(stdout, stderr, 0);
        } else if (std.mem.eql(u8, task_cmd, "update")) {
            const params = comptime clap.parseParamsComptime(
                \\-h, --help             Display help.
                \\-t, --title <str>      Title.
                \\-d, --desc <str>       Description.
                \\-p, --priority <str>   Priority.
                \\-s, --status <str>     Status.
                \\-l, --labels <str>     Labels.
                \\<usize>                Task ID.
                \\
            );
            var diag = clap.Diagnostic{};
            var res = clap.parseEx(clap.Help, &params, clap.parsers.default, &iter, .{
                .diagnostic = &diag,
                .allocator = allocator,
            }) catch |err| {
                try diag.reportToFile(init.io, .stderr(), err);
                exit(stdout, stderr, 2);
            };
            defer res.deinit();

            if (res.args.help != 0) {
                try stdout.print("Update an existing task\n", .{});
                exit(stdout, stderr, 0);
            }

            const id = res.positionals[0] orelse {
                try stderr.print("Error: Missing task ID.\n", .{});
                exit(stdout, stderr, 2);
            };

            var parsed_db = try db_mod.loadDb(allocator, init.io, init.environ_map);
            defer parsed_db.deinit();

            var task_idx: ?usize = null;
            for (parsed_db.value.tasks, 0..) |t, idx| {
                if (t.id == id) {
                    task_idx = idx;
                    break;
                }
            }

            if (task_idx == null) {
                try stderr.print("Error: Task with ID {d} not found.\n", .{id});
                exit(stdout, stderr, 1);
            }

            const idx = task_idx.?;
            var t = &parsed_db.value.tasks[idx];

            if (res.args.title) |title| {
                t.title = title;
            }
            if (res.args.desc) |desc| {
                t.desc = desc;
            }
            if (res.args.priority) |prio| {
                const prio_lower = try allocator.alloc(u8, prio.len);
                defer allocator.free(prio_lower);
                for (prio, 0..) |c, i| {
                    prio_lower[i] = std.ascii.toLower(c);
                }
                if (!std.mem.eql(u8, prio_lower, "low") and !std.mem.eql(u8, prio_lower, "medium") and !std.mem.eql(u8, prio_lower, "high")) {
                    try stderr.print("Error: invalid priority (low|medium|high)\n", .{});
                    exit(stdout, stderr, 2);
                }
                t.priority = try allocator.dupe(u8, prio_lower);
            }
            if (res.args.status) |status| {
                const stat_lower = try allocator.alloc(u8, status.len);
                defer allocator.free(stat_lower);
                for (status, 0..) |c, i| {
                    stat_lower[i] = std.ascii.toLower(c);
                }
                if (!std.mem.eql(u8, stat_lower, "todo") and !std.mem.eql(u8, stat_lower, "doing") and !std.mem.eql(u8, stat_lower, "done")) {
                    try stderr.print("Error: invalid status (todo|doing|done)\n", .{});
                    exit(stdout, stderr, 2);
                }
                t.status = try allocator.dupe(u8, stat_lower);
            }
            if (res.args.labels) |raw_labels| {
                var label_array = std.ArrayList([]const u8).empty;
                defer label_array.deinit(allocator);
                var l_iter = std.mem.splitScalar(u8, raw_labels, ',');
                while (l_iter.next()) |l| {
                    const slug = try db_mod.slugify(allocator, l);
                    if (slug.len > 0) {
                        try label_array.append(allocator, slug);

                        var exists = false;
                        for (parsed_db.value.labels) |gl| {
                            if (std.mem.eql(u8, gl.name, slug)) {
                                exists = true;
                                break;
                            }
                        }
                        if (!exists) {
                            var new_labels = try allocator.alloc(Label, parsed_db.value.labels.len + 1);
                            @memcpy(new_labels[0..parsed_db.value.labels.len], parsed_db.value.labels);
                            new_labels[parsed_db.value.labels.len] = Label{ .name = slug };
                            parsed_db.value.labels = new_labels;
                        }
                    }
                }
                t.labels = label_array.items;
            }

            try db_mod.saveDb(allocator, init.io, init.environ_map, parsed_db.value);

            try stdout.print("Task {d} updated successfully.\n", .{id});
            exit(stdout, stderr, 0);
        } else if (std.mem.eql(u8, task_cmd, "delete")) {
            const params = comptime clap.parseParamsComptime(
                \\-h, --help             Display help.
                \\--force                Force.
                \\<usize>                ID.
                \\
            );
            var diag = clap.Diagnostic{};
            var res = clap.parseEx(clap.Help, &params, clap.parsers.default, &iter, .{
                .diagnostic = &diag,
                .allocator = allocator,
            }) catch |err| {
                try diag.reportToFile(init.io, .stderr(), err);
                exit(stdout, stderr, 2);
            };
            defer res.deinit();

            if (res.args.help != 0) {
                try stdout.print("Delete a task\n", .{});
                exit(stdout, stderr, 0);
            }

            const id = res.positionals[0] orelse {
                try stderr.print("Error: Missing task ID.\n", .{});
                exit(stdout, stderr, 2);
            };

            var parsed_db = try db_mod.loadDb(allocator, init.io, init.environ_map);
            defer parsed_db.deinit();

            var task_idx: ?usize = null;
            for (parsed_db.value.tasks, 0..) |t, idx| {
                if (t.id == id) {
                    task_idx = idx;
                    break;
                }
            }

            if (task_idx == null) {
                try stderr.print("Error: Task with ID {d} not found.\n", .{id});
                exit(stdout, stderr, 1);
            }

            const idx = task_idx.?;

            var new_tasks = try allocator.alloc(Task, parsed_db.value.tasks.len - 1);
            @memcpy(new_tasks[0..idx], parsed_db.value.tasks[0..idx]);
            @memcpy(new_tasks[idx..], parsed_db.value.tasks[idx + 1 ..]);
            parsed_db.value.tasks = new_tasks;

            try db_mod.saveDb(allocator, init.io, init.environ_map, parsed_db.value);

            try stdout.print("Task {d} deleted successfully.\n", .{id});
            exit(stdout, stderr, 0);
        } else {
            try printTaskUsage(stdout);
            exit(stdout, stderr, 2);
        }
    } else if (std.mem.eql(u8, cmd, "label")) {
        const label_cmd = iter.next() orelse {
            try printLabelUsage(stdout);
            exit(stdout, stderr, 0);
        };

        if (std.mem.eql(u8, label_cmd, "-h") or std.mem.eql(u8, label_cmd, "--help")) {
            try printLabelUsage(stdout);
            exit(stdout, stderr, 0);
        }

        if (std.mem.eql(u8, label_cmd, "list")) {
            const params = comptime clap.parseParamsComptime(
                \\-h, --help             Display help.
                \\
            );
            var diag = clap.Diagnostic{};
            var res = clap.parseEx(clap.Help, &params, clap.parsers.default, &iter, .{
                .diagnostic = &diag,
                .allocator = allocator,
            }) catch |err| {
                try diag.reportToFile(init.io, .stderr(), err);
                exit(stdout, stderr, 2);
            };
            defer res.deinit();

            if (res.args.help != 0) {
                try stdout.print("List all labels\n", .{});
                exit(stdout, stderr, 0);
            }

            var parsed_db = try db_mod.loadDb(allocator, init.io, init.environ_map);
            defer parsed_db.deinit();

            try format_mod.printLabelsTable(allocator, stdout, parsed_db.value);
            exit(stdout, stderr, 0);
        } else if (std.mem.eql(u8, label_cmd, "create")) {
            const params = comptime clap.parseParamsComptime(
                \\-h, --help             Display help.
                \\<str>                  Label name.
                \\
            );
            var diag = clap.Diagnostic{};
            var res = clap.parseEx(clap.Help, &params, clap.parsers.default, &iter, .{
                .diagnostic = &diag,
                .allocator = allocator,
            }) catch |err| {
                try diag.reportToFile(init.io, .stderr(), err);
                exit(stdout, stderr, 2);
            };
            defer res.deinit();

            if (res.args.help != 0) {
                try stdout.print("Create a label\n", .{});
                exit(stdout, stderr, 0);
            }

            const name = res.positionals[0] orelse {
                try stderr.print("Error: Missing label name.\n", .{});
                exit(stdout, stderr, 2);
            };

            const slug = try db_mod.slugify(allocator, name);
            if (slug.len == 0) {
                try stderr.print("Error: invalid label name.\n", .{});
                exit(stdout, stderr, 2);
            }

            var parsed_db = try db_mod.loadDb(allocator, init.io, init.environ_map);
            defer parsed_db.deinit();

            for (parsed_db.value.labels) |l| {
                if (std.mem.eql(u8, l.name, slug)) {
                    try stderr.print("Error: Label \"{s}\" already exists.\n", .{slug});
                    exit(stdout, stderr, 1);
                }
            }

            var new_labels = try allocator.alloc(Label, parsed_db.value.labels.len + 1);
            @memcpy(new_labels[0..parsed_db.value.labels.len], parsed_db.value.labels);
            new_labels[parsed_db.value.labels.len] = Label{ .name = slug };
            parsed_db.value.labels = new_labels;

            try db_mod.saveDb(allocator, init.io, init.environ_map, parsed_db.value);

            try stdout.print("Label \"{s}\" created successfully.\n", .{slug});
            exit(stdout, stderr, 0);
        } else if (std.mem.eql(u8, label_cmd, "delete")) {
            const params = comptime clap.parseParamsComptime(
                \\-h, --help             Display help.
                \\<str>                  Label name.
                \\
            );
            var diag = clap.Diagnostic{};
            var res = clap.parseEx(clap.Help, &params, clap.parsers.default, &iter, .{
                .diagnostic = &diag,
                .allocator = allocator,
            }) catch |err| {
                try diag.reportToFile(init.io, .stderr(), err);
                exit(stdout, stderr, 2);
            };
            defer res.deinit();

            if (res.args.help != 0) {
                try stdout.print("Delete a label\n", .{});
                exit(stdout, stderr, 0);
            }

            const name = res.positionals[0] orelse {
                try stderr.print("Error: Missing label name.\n", .{});
                exit(stdout, stderr, 2);
            };

            const slug = try db_mod.slugify(allocator, name);

            var parsed_db = try db_mod.loadDb(allocator, init.io, init.environ_map);
            defer parsed_db.deinit();

            var label_idx: ?usize = null;
            for (parsed_db.value.labels, 0..) |l, idx| {
                if (std.mem.eql(u8, l.name, slug)) {
                    label_idx = idx;
                    break;
                }
            }

            if (label_idx == null) {
                try stderr.print("Error: Label \"{s}\" not found.\n", .{name});
                exit(stdout, stderr, 1);
            }

            const idx = label_idx.?;

            var new_labels = try allocator.alloc(Label, parsed_db.value.labels.len - 1);
            @memcpy(new_labels[0..idx], parsed_db.value.labels[0..idx]);
            @memcpy(new_labels[idx..], parsed_db.value.labels[idx + 1 ..]);
            parsed_db.value.labels = new_labels;

            // Remove label reference from all tasks
            for (parsed_db.value.tasks, 0..) |t, t_idx| {
                var label_list = std.ArrayList([]const u8).empty;
                defer label_list.deinit(allocator);
                for (t.labels) |tl| {
                    if (!std.mem.eql(u8, tl, slug)) {
                        try label_list.append(allocator, tl);
                    }
                }
                parsed_db.value.tasks[t_idx].labels = try allocator.dupe([]const u8, label_list.items);
            }

            try db_mod.saveDb(allocator, init.io, init.environ_map, parsed_db.value);

            try stdout.print("Label \"{s}\" deleted successfully.\n", .{slug});
            exit(stdout, stderr, 0);
        } else {
            try printLabelUsage(stdout);
            exit(stdout, stderr, 2);
        }
    } else if (std.mem.eql(u8, cmd, "report")) {
        const params = comptime clap.parseParamsComptime(
            \\-h, --help             Display help.
            \\
        );
        var diag = clap.Diagnostic{};
        var res = clap.parseEx(clap.Help, &params, clap.parsers.default, &iter, .{
            .diagnostic = &diag,
            .allocator = allocator,
        }) catch |err| {
            try diag.reportToFile(init.io, .stderr(), err);
            exit(stdout, stderr, 2);
        };
        defer res.deinit();

        if (res.args.help != 0) {
            try stdout.print("Display sprint progress report\n", .{});
            exit(stdout, stderr, 0);
        }

        var parsed_db = try db_mod.loadDb(allocator, init.io, init.environ_map);
        defer parsed_db.deinit();

        try format_mod.printSprintReport(stdout, parsed_db.value);
        exit(stdout, stderr, 0);
    } else {
        try printUsage(stdout);
        exit(stdout, stderr, 2);
    }
}
