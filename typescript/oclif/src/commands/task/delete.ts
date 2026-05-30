import { Args, Command, Flags } from '@oclif/core';
import * as dbOps from '../../shared/db';

export default class TaskDelete extends Command {
  static description = 'Delete a task';

  static args = {
    id: Args.string({ description: 'Task ID', required: true }),
  };

  static flags = {
    force: Flags.boolean({ description: 'Force delete without warning' }),
  };

  async run(): Promise<void> {
    const { args } = await this.parse(TaskDelete);
    try {
      const id = parseInt(args.id, 10);
      if (isNaN(id)) {
        throw new Error(`invalid task ID: ${args.id}`);
      }

      const db = dbOps.loadDb();
      dbOps.deleteTask(db, id);
      this.log(`Task ${id} deleted successfully.`);
    } catch (err: any) {
      this.error(err.message, { exit: 1 });
    }
  }
}
