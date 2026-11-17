import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import initSqlJs from 'sql.js';

test('SIGTERM flushes pending SQLite writes to disk', { timeout: 20_000 }, async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-db-'));
  const moduleUrl = pathToFileURL(path.resolve('src/memory/atlas_db.ts')).href;

  const script = `
    import { atlasDB } from ${JSON.stringify(moduleUrl)};
    await atlasDB.initialize();
    atlasDB.run(
      'INSERT INTO memories (id, content, layer, source, tags) VALUES (?, ?, ?, ?, ?)',
      ['m1', 'persist me', 'semantic', 'test', '[]']
    );
    setInterval(() => {}, 1000);
    process.kill(process.pid, 'SIGTERM');
  `;

  const child = spawn(process.execPath, ['--import', 'tsx', '--input-type=module', '--eval', script], {
    cwd: process.cwd(),
    env: { ...process.env, DATA_DIR: dataDir },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  let stderr = '';
  child.stderr?.on('data', chunk => { stderr += chunk.toString(); });

  const [code] = await once(child, 'exit');
  assert.equal(code, 0, stderr);

  const dbPath = path.join(dataDir, 'atlas.db');
  assert.ok(fs.existsSync(dbPath), `expected ${dbPath} to exist`);

  const SQL = await initSqlJs();
  const db = new SQL.Database(fs.readFileSync(dbPath));
  const result = db.exec("SELECT content FROM memories WHERE id = 'm1'");
  db.close();

  assert.equal(result[0]?.values[0]?.[0], 'persist me');
});
