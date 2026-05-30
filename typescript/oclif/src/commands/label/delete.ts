import { Args, Command } from '@oclif/core';
import * as dbOps from '../../shared/db';

export default class LabelDelete extends Command {
  static description = 'Delete a label';

  static args = {
    name: Args.string({ description: 'Label name', required: true }),
  };

  async run(): Promise<void> {
    const { args } = await this.parse(LabelDelete);
    try {
      const db = dbOps.loadDb();
      dbOps.deleteLabel(db, args.name);
      this.log(`Label "${args.name}" deleted successfully.`);
    } catch (err: any) {
      this.error(err.message, { exit: 1 });
    }
  }
}
