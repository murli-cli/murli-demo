import { Args, Command, Flags } from '@oclif/core';
import * as dbOps from '../../shared/db';

export default class TaskUpdate extends Command {
  static description = "Update an existing task's fields";

  static args = {
    id: Args.string({ description: 'Task ID', required: true }),
  };

  static flags = {
    title: Flags.string({ char: 't', description: 'New title' }),
    desc: Flags.string({ char: 'd', description: 'New description' }),
    priority: Flags.string({ char: 'p', description: 'New priority', options: ['low', 'medium', 'high'] }),
    status: Flags.string({ char: 's', description: 'New status', options: ['todo', 'doing', 'done'] }),
    labels: Flags.string({ char: 'l', description: 'Replacement labels' }),
  };

  async run(): Promise<void> {
    const { args, flags } = await this.parse(TaskUpdate);
    try {
      const id = parseInt(args.id, 10);
      if (isNaN(id)) {
        throw new Error(`invalid task ID: ${args.id}`);
      }

      const db = dbOps.loadDb();

      const labelsList = flags.labels !== undefined ? (flags.labels ? flags.labels.split(',') : []) : undefined;

      dbOps.updateTask(
        db,
        id,
        flags.title,
        flags.desc,
        flags.priority,
        flags.status,
        labelsList
      );
      this.log(`Task ${id} updated successfully.`);
    } catch (err: any) {
      const msg = err.message || '';
      const exitCode = msg.includes('not found') ? 1 : (msg.includes('priority') || msg.includes('status') ? 2 : 1);
      this.error(err.message, { exit: exitCode });
    }
  }
}
