import { Args, Command, Flags } from '@oclif/core';
import * as dbOps from '../../shared/db';

export default class TaskCreate extends Command {
  static description = 'Create a new task';

  static args = {
    title: Args.string({ description: 'Task title', required: true }),
  };

  static flags = {
    desc: Flags.string({ char: 'd', description: 'Task description', default: '' }),
    priority: Flags.string({ char: 'p', description: 'Task priority (low|medium|high)', options: ['low', 'medium', 'high'] }),
    labels: Flags.string({ char: 'l', description: 'Comma-separated labels' }),
  };

  async run(): Promise<void> {
    const { args, flags } = await this.parse(TaskCreate);
    try {
      const db = dbOps.loadDb();
      const labelList = flags.labels ? flags.labels.split(',') : [];
      const id = dbOps.createTask(db, args.title, flags.desc, flags.priority, labelList);
      this.log(`Task ${id} ("${args.title}") created successfully.`);
    } catch (err: any) {
      this.error(err.message, { exit: err.message.includes('priority') ? 2 : 1 });
    }
  }
}
