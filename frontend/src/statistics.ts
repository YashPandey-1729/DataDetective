export interface StatisticalDefinition {
  operation: string; function?: string; description: string; required_arguments?: string[];
  assumptions?: string; note?: string;
  parameters_schema: {properties?: Record<string, {default?: unknown; type?: string; const?: unknown}>; required?: string[]};
}
export function resultSource(result: Record<string,unknown>): string {
  if (result.source_type === 'simulation') return 'Simulation · not observations';
  if ((result.source_type && result.source_type !== 'dataset') || ('before' in result && 'after' in result)) return 'Calculated from supplied values';
  return 'Computed from uploaded data';
}
export function parameterDefaults(definition: StatisticalDefinition, metrics: string[]): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [name,schema] of Object.entries(definition.parameters_schema.properties || {})) {
    if (schema.default !== undefined && schema.default !== null) result[name]=schema.default;
    if (schema.const !== undefined) result[name]=schema.const;
  }
  if (definition.function) result.function=definition.function;
  const required=definition.parameters_schema.required || [];
  if (required.includes('values') && metrics.length) result.values={column:metrics[0]};
  if (required.includes('columns')) result.columns=metrics.slice(0,2);
  if (required.includes('predictors')) result.predictors=metrics.slice(1,2);
  return result;
}
export function statisticalRequest(definition: StatisticalDefinition, fields: Record<string,string>, parameterText: string) {
  let parameters: unknown;
  try {parameters=JSON.parse(parameterText);} catch {throw new Error('Advanced options must contain valid JSON.');}
  if (!parameters || Array.isArray(parameters) || typeof parameters !== 'object') throw new Error('Advanced options must be a JSON object.');
  const request: Record<string, unknown> = {operation:definition.operation,parameters};
  for (const field of definition.required_arguments || []) {
    const value=fields[field];
    if (!value?.trim()) throw new Error(`Select or enter ${field.replaceAll('_',' ')}.`);
    if (field === 'before' || field === 'after') {
      const number=Number(value); if (!Number.isFinite(number)) throw new Error('Enter finite before and after values.');
      request[field]=number;
    } else request[field]=value;
  }
  return request;
}
