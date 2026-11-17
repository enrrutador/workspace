/**
 * Atlas Downloader Tool - File download from URLs
 * Cross-platform: macOS, Linux, Windows
 */

import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { logger } from '../../common/logger.js';
import { toolGuardian } from '../../shield/tool_guardian.js';
import { assertAllowedPath } from '../../shield/path_guard.js';
import { dataDir } from '../../common/paths.js';

export class DownloaderTool {
  private static instance: DownloaderTool;
  private downloadDir: string;

  private constructor() {
    this.downloadDir = dataDir('downloads');
    if (!fs.existsSync(this.downloadDir)) {
      fs.mkdirSync(this.downloadDir, { recursive: true });
    }
  }

  static getInstance(): DownloaderTool {
    if (!DownloaderTool.instance) {
      DownloaderTool.instance = new DownloaderTool();
    }
    return DownloaderTool.instance;
  }

  async download(url: string, filename?: string): Promise<string> {
    const guard = toolGuardian.canUseTool('download_file');
    if (!guard.allowed) {
      throw new Error(guard.reason || 'Download not allowed');
    }

    try {
      const parsedUrl = new URL(url);
      if (parsedUrl.protocol !== 'http:' && parsedUrl.protocol !== 'https:') {
        throw new Error(`Unsupported URL protocol: ${parsedUrl.protocol}`);
      }

      const response = await axios.get(parsedUrl.toString(), {
        responseType: 'arraybuffer',
        timeout: 60000,
      });

      const requestedName = filename || path.basename(parsedUrl.pathname) || `download_${Date.now()}`;
      const finalName = path.basename(requestedName);
      if (!finalName || finalName === '.' || finalName === '..') {
        throw new Error('Invalid download filename');
      }
      const savePath = assertAllowedPath(path.join(this.downloadDir, finalName), 'write');

      fs.writeFileSync(savePath, response.data);
      logger.info('downloader', `Downloaded: ${url} → ${savePath}`);
      return savePath;
    } catch (err) {
      logger.error('downloader', `Download failed: ${err}`);
      throw err;
    }
  }
}

export const downloaderTool = DownloaderTool.getInstance();
