import { Command, Flags } from '@oclif/core';
import * as dbOps from '../../shared/db';
import * as formatOps from '../../shared/format';

export default class TaskList extends Command {
  static description = 'List stored tasks';

  static flags = {
    status: Flags.string({ char: 's', description: 'Filter by status (todo|doing|done)', options: ['todo', 'doing', 'done'] }),
    priority: Flags.string({ char: 'p', description: 'Filter by priority (low|medium|high)', options: ['low', 'medium', 'high'] }),
    label: Flags.string({ char: 'l', description: 'Filter by label' }),
    output: Flags.string({ char: 'o', description: 'Output format (table|json|csv)', default: 'table', options: ['table', 'json', 'csv'] }),
  };

  async run(): Promise<void> {
    const { flags } = await this.parse(TaskList);
    try {
      const db = dbOps.loadDb();
      const cfg = dbOps.loadConfig();

      let outputFmt = flags.output;
      if (outputFmt === 'table' && cfg && cfg.default_output) {
        outputFmt = cfg.default_output;
      }

      let filtered = db.tasks;
      if (flags.status) {
        filtered = filtered.filter((t) => t.status.toLowerCase() === flags.status!.toLowerCase());
      }
      if (flags.priority) {
        filtered = filtered.filter((t) => t.priority.toLowerCase() === flags.priority!.toLowerCase());
      }
      if (flags.label) {
        filtered = filtered.filter((t) => t.labels.some((l) => l.toLowerCase() === flags.label!.toLowerCase()));
      }

      switch (outputFmt.toLowerCase()) {
        case 'json':
          formatOps.printTasksJSON(filtered);
          break;
        case 'csv':
          formatOps.printTasksCSV(filtered);
          break;
        default:
          formatOps.printTasksTable(filtered);
          break;
      }
    } catch (err: any) {
      this.error(err.message, { exit: 1 });
    }
  }
}
