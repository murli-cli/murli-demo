import { Command } from '@oclif/core';
import * as dbOps from '../shared/db';
import * as formatOps from '../shared/format';

export default class Report extends Command {
  static description = 'Display progress report';

  async run(): Promise<void> {
    try {
      const db = dbOps.loadDb();
      formatOps.printSprintReport(db);
    } catch (err: any) {
      this.error(err.message, { exit: 1 });
    }
  }
}
