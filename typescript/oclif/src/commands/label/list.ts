import { Command } from '@oclif/core';
import * as dbOps from '../../shared/db';
import * as formatOps from '../../shared/format';

export default class LabelList extends Command {
  static description = 'List all defined labels';

  async run(): Promise<void> {
    try {
      const db = dbOps.loadDb();
      formatOps.printLabelsTable(db);
    } catch (err: any) {
      this.error(err.message, { exit: 1 });
    }
  }
}
