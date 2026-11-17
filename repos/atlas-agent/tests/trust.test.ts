import test from 'node:test';
import assert from 'node:assert/strict';
import { trustLadder, classifyOperation, TRUST_LEVEL_NAMES } from '../src/shield/trust_ladder.js';
import { trustGate } from '../src/shield/trust_gate.js';
import { toolGuardian } from '../src/shield/tool_guardian.js';

const originalLevel = trustLadder.getLevel();

test.afterEach(() => {
  trustLadder.setLevel(originalLevel);
});

test('classifies tool and free-form operations by risk', () => {
  assert.equal(classifyOperation('read_file').risk, 'low');
  assert.equal(classifyOperation('save_file').risk, 'medium');
  assert.equal(classifyOperation('shell_execute').risk, 'high');
  assert.equal(classifyOperation('task', 'delete the production database').risk, 'critical');
  assert.equal(classifyOperation('task', 'explain how a for loop works').risk, 'low');
});

test('levels 1-5 enforce the documented thresholds', () => {
  trustLadder.setLevel(1);
  assert.equal(trustLadder.canExecute(classifyOperation('read_file')).allowed, true);
  assert.equal(trustLadder.canExecute(classifyOperation('save_file')).allowed, false);
  assert.equal(trustLadder.canExecute(classifyOperation('shell_execute')).allowed, false);

  trustLadder.setLevel(2);
  assert.equal(trustLadder.canExecute(classifyOperation('save_file')).allowed, true);
  assert.equal(trustLadder.canExecute(classifyOperation('shell_execute')).allowed, false);

  trustLadder.setLevel(3);
  assert.equal(trustLadder.canExecute(classifyOperation('shell_execute')).allowed, true);
  assert.equal(trustLadder.canExecute(classifyOperation('delete_file')).allowed, true);

  trustLadder.setLevel(4);
  assert.equal(trustLadder.canExecute(classifyOperation('task', 'deploy to production')).allowed, true);

  trustLadder.setLevel(5);
  assert.equal(trustLadder.getLevelName(), TRUST_LEVEL_NAMES[5]);
  const critical = trustLadder.canExecute(classifyOperation('task', 'rm -rf / and wipe disk'));
  assert.equal(critical.allowed, true);
});

test('trust gate proposes irreversible critical work at level 3', () => {
  trustLadder.setLevel(3);
  const gate = trustGate.evaluate('delete the production database');
  assert.equal(gate.decision, 'propose');
  assert.equal(gate.needsUserApproval, true);
  assert.equal(gate.operation.risk, 'critical');
});

test('trust gate allows ordinary reads and writes at level 3', () => {
  trustLadder.setLevel(3);
  assert.equal(trustGate.evaluate('read the README file').decision, 'proceed');
  assert.equal(trustGate.evaluate('save a summary to notes.md').decision, 'proceed');
});

test('tool guardian filters tools per level', () => {
  trustLadder.setLevel(2);
  assert.equal(toolGuardian.canUseTool('shell_execute').allowed, false);
  assert.equal(toolGuardian.canUseTool('save_file').allowed, true);
  assert.ok(!toolGuardian.getAvailableTools().includes('shell_execute'));

  trustLadder.setLevel(3);
  assert.equal(toolGuardian.canUseTool('shell_execute').allowed, true);
  assert.ok(toolGuardian.getAvailableTools().includes('shell_execute'));
  assert.ok(toolGuardian.getAvailableTools().includes('web_search'));
});
