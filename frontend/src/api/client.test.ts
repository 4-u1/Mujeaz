import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from './client';

afterEach(() => vi.unstubAllGlobals());

function stubFetch(status: number, body: unknown) {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('api client', () => {
  it('surfaces the server error envelope message', async () => {
    stubFetch(409, { error: { code: 'http_409', message: 'DRAFT → SUBMITTED is not an allowed transition' } });
    await expect(api.transition('x', 'SUBMITTED')).rejects.toMatchObject({
      status: 409,
      message: 'DRAFT → SUBMITTED is not an allowed transition',
    });
  });

  it('throws ApiError for non-JSON failures', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('bad gateway', { status: 502 })));
    await expect(api.metrics()).rejects.toBeInstanceOf(ApiError);
  });

  it('sends JSON bodies with POST', async () => {
    const f = stubFetch(200, { mode: 'fallback' });
    await api.analyzeOrder({ clinicalNoteText: 'MRI lumbar' });
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/ai/analyze-order');
    expect(init.method).toBe('POST');
    expect(JSON.parse(String(init.body))).toEqual({ clinicalNoteText: 'MRI lumbar' });
  });
});
