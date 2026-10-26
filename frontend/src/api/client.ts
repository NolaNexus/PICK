const BASE_URL = '';

export type RequestConfig = {
  url: string;
  method: string;
  headers?: Record<string, string>;
  params?: Record<string, unknown>;
  body?: unknown;
  data?: unknown;
  signal?: AbortSignal;
};

export default async function request<T>(
  config: RequestConfig,
  _options?: unknown
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    const url = config.url.startsWith('http')
      ? config.url
      : `${BASE_URL}${config.url}`;

    const response = await fetch(url, {
      method: config.method,
      headers: {
        'Content-Type': 'application/json',
        ...config.headers,
      },
      body: config.body !== undefined ? JSON.stringify(config.body) : undefined,
      signal: config.signal ?? controller.signal,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Request failed with status ${response.status}`);
    }

    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      return (await response.json()) as T;
    }

    return (await response.text()) as unknown as T;
  } finally {
    clearTimeout(timeoutId);
  }
}
