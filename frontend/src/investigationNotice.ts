import type {Investigation} from './types';

interface InvestigationNotice {reason: string; nextStep: string}

export function investigationNotice(investigation: Pick<Investigation,'status'|'stop_reason'> | null): InvestigationNotice | null {
  if (investigation?.status !== 'partial') return null;
  switch (investigation.stop_reason) {
    case 'repeated_action_limit':
      return {reason:'The AI repeated analyses that had already succeeded.',
        nextStep:'Review the existing evidence, then narrow your question or specify a different calculation before starting again.'};
    case 'step_budget_exhausted':
      return {reason:'The investigation reached its step limit.',
        nextStep:'Review which calculations finished, then ask one focused comparison at a time.'};
    case 'tool_failure_limit':
      return {reason:'Several analytical tool requests failed.',
        nextStep:'Open Execution notices below, check the column names and requested calculation, then refine your question.'};
    case 'model_unavailable':
      return {reason:'The AI model could not continue.',
        nextStep:'Check that the selected model is available, click Reconnect, then retry. Offline analytics is also available for fixed-rule analysis.'};
    case 'cancelled':
      return {reason:'The investigation was interrupted.',
        nextStep:'Check the backend connection before starting a new investigation.'};
    default:
      return {reason:'The investigation stopped before completing.',
        nextStep:'Review the report limitations and Execution notices below before starting a new investigation.'};
  }
}
