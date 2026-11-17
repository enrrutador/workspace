/**
 * Ejecuta una propuesta ya aprobada por el usuario.
 *
 * La aprobación desbloquea a nivel de gate (TrustGate/ForgeGate ya no vuelven a
 * proponer la misma tarea), pero ToolGuardian y PathGuard siguen aplicando a
 * nivel de herramienta: aprobar no eleva el nivel de confianza global.
 */

import { logger } from '../../common/logger.js';
import { ForgeProposal, Message } from '../../common/types.js';

export async function executeApprovedProposal(proposal: ForgeProposal): Promise<string> {
  if (proposal.status !== 'approved') {
    throw new Error(`La propuesta ${proposal.id} no está aprobada (estado: ${proposal.status})`);
  }

  const problem = proposal.task || proposal.description;
  logger.info('proposal_executor', `Executing approved proposal ${proposal.id}: "${problem.slice(0, 80)}"`);

  const { taskHandler } = await import('../../brain/task_handler.js');
  const messages: Message[] = [{ role: 'user', content: problem, timestamp: Date.now() }];
  const result = await taskHandler.handle(messages, `proposal_${proposal.id}`);

  return result.response;
}
