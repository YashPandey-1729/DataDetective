export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// Keep a lost connection from leaving uploads or investigations locked forever.
export async function api<T>(path: string, options: RequestInit = {}, timeoutMs = 30_000): Promise<T> {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  const externalSignal = options.signal;
  if (externalSignal?.aborted) controller.abort();
  else externalSignal?.addEventListener('abort', cancel, {once: true});
  let timedOut = false;
  const timer = setTimeout(() => {timedOut = true; controller.abort();}, timeoutMs);
  try {
    const response = await fetch('/api' + path, {...options, signal: controller.signal});
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const message = typeof body.detail === 'string' ? body.detail
        : Array.isArray(body.detail) ? body.detail.map((e: {msg?: string}) => e.msg || 'Invalid request').join('; ')
        : `Request failed (${response.status}). Check the backend connection and try again.`;
      throw new ApiError(message, response.status);
    }
    return await response.json();
  } catch (error) {
    if (timedOut) throw new ApiError('The backend did not respond in time. Check the connection and retry.');
    if (controller.signal.aborted) throw new DOMException('Request cancelled', 'AbortError');
    if (error instanceof ApiError) throw error;
    throw new ApiError('Cannot reach the backend. Check that FastAPI is running on port 8000.');
  } finally {
    clearTimeout(timer);
    externalSignal?.removeEventListener('abort', cancel);
  }
}
export async function upload<T>(path: string, file: File): Promise<T> {
  const body = new FormData(); body.append('file', file);
  return api<T>(path, {method: 'POST', body}, 60_000);
}
