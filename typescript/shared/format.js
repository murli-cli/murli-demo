"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.printTasksTable = printTasksTable;
exports.printTasksCSV = printTasksCSV;
exports.printTasksJSON = printTasksJSON;
exports.printLabelsTable = printLabelsTable;
exports.printSprintReport = printSprintReport;
function printTasksTable(tasks) {
    const border = "+----+----------------------+--------+----------+------------+";
    const header = "| ID | Title                | Status | Priority | Labels     |";
    console.log(border);
    console.log(header);
    console.log(border);
    for (const t of tasks) {
        const labelsStr = t.labels.join(",");
        const status = t.status.toUpperCase();
        const priority = t.priority.toUpperCase();
        // Exact fixed padding matching borders
        const idField = t.id.toString().padEnd(2).slice(0, 2);
        const titleField = t.title.padEnd(20).slice(0, 20);
        const statusField = status.padEnd(6).slice(0, 6);
        const prioField = priority.padEnd(8).slice(0, 8);
        const labelsField = labelsStr.padEnd(10).slice(0, 10);
        console.log(`| ${idField} | ${titleField} | ${statusField} | ${prioField} | ${labelsField} |`);
    }
    console.log(border);
}
function printTasksCSV(tasks) {
    console.log("id,title,status,priority,labels");
    for (const t of tasks) {
        const labelsStr = t.labels.join(";");
        // Standard minimal quoting for title and labels if needed:
        const qTitle = `"${t.title.replace(/"/g, '""')}"`;
        const qLabels = `"${labelsStr.replace(/"/g, '""')}"`;
        console.log(`${t.id},${qTitle},${t.status},${t.priority},${qLabels}`);
    }
}
function printTasksJSON(tasks) {
    console.log(JSON.stringify(tasks));
}
function printLabelsTable(db) {
    const border = "+-------------+-------------+";
    const header = "| Label Name  | Task Count  |";
    console.log(border);
    console.log(header);
    console.log(border);
    const counts = {};
    for (const l of db.labels) {
        counts[l.name] = 0;
    }
    for (const t of db.tasks) {
        for (const l of t.labels) {
            if (counts[l] !== undefined) {
                counts[l]++;
            }
        }
    }
    for (const l of db.labels) {
        const nameField = l.name.padEnd(11).slice(0, 11);
        const countField = counts[l.name].toString().padEnd(11).slice(0, 11);
        console.log(`| ${nameField} | ${countField} |`);
    }
    console.log(border);
}
function printSprintReport(db) {
    const total = db.tasks.length;
    let completed = 0;
    let todo = 0;
    let doing = 0;
    let done = 0;
    let high = 0;
    let medium = 0;
    let low = 0;
    for (const t of db.tasks) {
        const status = t.status.toLowerCase();
        if (status === "todo") {
            todo++;
        }
        else if (status === "doing") {
            doing++;
        }
        else if (status === "done") {
            done++;
            completed++;
        }
        const prio = t.priority.toLowerCase();
        if (prio === "low") {
            low++;
        }
        else if (prio === "medium") {
            medium++;
        }
        else if (prio === "high") {
            high++;
        }
    }
    let percent = 0;
    if (total > 0) {
        percent = Math.floor((completed * 100) / total);
    }
    const progressBlocks = Math.floor(percent / 10);
    const blocksStr = "■".repeat(progressBlocks) + "□".repeat(10 - progressBlocks);
    console.log("========================================");
    console.log("          MURLI-WORK SPRINT REPORT      ");
    console.log("========================================");
    console.log(`Completion Rate : [${blocksStr}] ${percent}% (${completed}/${total} tasks)\n`);
    console.log("Status Breakdown:");
    console.log(`- TODO  : ${todo} tasks`);
    console.log(`- DOING : ${doing} tasks`);
    console.log(`- DONE  : ${done} tasks\n`);
    console.log("Priority Breakdown:");
    console.log(`- HIGH  : ${high} tasks`);
    console.log(`- MEDIUM: ${medium} tasks`);
    console.log(`- LOW   : ${low} tasks`);
    console.log("========================================");
}
