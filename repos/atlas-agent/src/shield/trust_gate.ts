/**
 * Atlas Trust Gate - Evaluates whether an operation can proceed at the
 * current trust level. High-risk operations are returned as proposals instead
 * of being executed.
 */

import { Operation } from '../common/types.js';
import { logger } from '../common/logger.js';
import { classifyOperation, trustLadder } from './trust_ladder.js';

export type GateDecision = 'proceed' | 'forge' | 'autonomous' | 'propose';

export interface GateResult {
  decision: GateDecision;
  reason: string;
  needsUserApproval: boolean;
  operation: Operation;
}

export class TrustGate {
  private static instance: TrustGate;

  private constructor() {}

  static getInstance(): TrustGate {
    if (!TrustGate.instance) {
      TrustGate.instance = new TrustGate();
    }
    return TrustGate.instance;
  }

  evaluate(taskDescription: string, operation?: Operation): GateResult {
    const op = operation ?? classifyOperation('task', taskDescription);
    const check = trustLadder.canExecute(op);
    const needsUserApproval = !check.allowed || check.needsConfirmation;
    const decision: GateDecision = needsUserApproval ? 'propose' : 'proceed';
    const reason = check.reason ?? `Allowed at trust level ${trustLadder.getLevel()}`;

    logger.info(
      'trust_gate',
      `${decision.toUpperCase()} (${op.risk}${op.reversible ? '' : ', irreversible'}) — ${taskDescription.slice(0, 100)}`,
    );

    return { decision, reason, needsUserApproval, operation: op };
  }
}

export const trustGate = TrustGate.getInstance();
