interface ProgressState {id: string; status: string}

export function mergeInvestigationUpdate<T extends ProgressState>(current: T | null, incoming: T): T | null {
  // A response from the old poll must not restore a reset or replaced investigation.
  if (!current || current.id !== incoming.id) return current;
  const active = (status: string) => status === 'queued' || status === 'running';
  // The cancel response may arrive before an older in-flight progress response.
  if (!active(current.status) && active(incoming.status)) return current;
  return incoming;
}
