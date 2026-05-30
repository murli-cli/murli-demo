import { Args, Command } from '@oclif/core';
import * as dbOps from '../../shared/db';

export default class LabelCreate extends Command {
  static description = 'Create a custom label';

  static args = {
    name: Args.string({ description: 'Label name', required: true }),
  };

  async run(): Promise<void> {
    const { args } = await this.parse(LabelCreate);
    try {
      const db = dbOps.loadDb();
      const slug = dbOps.createLabel(db, args.name);
      this.log(`Label "${slug}" created successfully.`);
    } catch (err: any) {
      this.error(err.message, { exit: 1 });
    }
  }
}
