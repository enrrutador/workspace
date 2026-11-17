/**
 * Atlas File Manager Tool - File CRUD operations
 * Cross-platform: macOS, Linux, Windows
 */

import fs from 'fs';
import path from 'path';
import { logger } from '../../common/logger.js';
import { toolGuardian } from '../../shield/tool_guardian.js';
import { assertAllowedPath } from '../../shield/path_guard.js';

export class FileManagerTool {
  private static instance: FileManagerTool;

  private constructor() {}

  static getInstance(): FileManagerTool {
    if (!FileManagerTool.instance) {
      FileManagerTool.instance = new FileManagerTool();
    }
    return FileManagerTool.instance;
  }

  readFile(filePath: string): string {
    try {
      const resolved = assertAllowedPath(filePath, 'read');
      const content = fs.readFileSync(resolved, 'utf-8');
      logger.info('file_manager', `Read: ${resolved}`);
      return content;
    } catch (err) {
      logger.error('file_manager', `Read failed: ${err}`);
      throw err;
    }
  }

  writeFile(filePath: string, content: string): void {
    const guard = toolGuardian.canUseTool('save_file');
    if (!guard.allowed) {
      throw new Error(guard.reason || 'File write not allowed');
    }

    try {
      const resolved = assertAllowedPath(filePath, 'write');
      const dir = path.dirname(resolved);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      fs.writeFileSync(resolved, content);
      logger.info('file_manager', `Wrote: ${resolved}`);
    } catch (err) {
      logger.error('file_manager', `Write failed: ${err}`);
      throw err;
    }
  }

  deleteFile(filePath: string): void {
    const guard = toolGuardian.canUseTool('delete_file');
    if (!guard.allowed) {
      throw new Error(guard.reason || 'File delete not allowed');
    }

    try {
      const resolved = assertAllowedPath(filePath, 'delete');
      fs.unlinkSync(resolved);
      logger.info('file_manager', `Deleted: ${resolved}`);
    } catch (err) {
      logger.error('file_manager', `Delete failed: ${err}`);
      throw err;
    }
  }

  listFiles(dirPath: string): string[] {
    try {
      const resolved = assertAllowedPath(dirPath, 'list');
      return fs.readdirSync(resolved);
    } catch (err) {
      logger.error('file_manager', `List failed: ${err}`);
      return [];
    }
  }
}

export const fileManagerTool = FileManagerTool.getInstance();
