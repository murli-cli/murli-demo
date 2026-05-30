import { Command } from '@oclif/core';
import * as dbOps from '../shared/db';

export default class Init extends Command {
  static description = 'Initialize/Reset the database and config';

  async run(): Promise<void> {
    try {
      dbOps.resetDb();
      const dir = dbOps.getStorageDir();
      this.log(`Initialized/Reset murli-work database with sample data and configuration in ${dir}`);
    } catch (err: any) {
      this.error(err.message, { exit: 1 });
    }
  }
}
