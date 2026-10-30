import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, readSse } from './client';

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

describe('analysis stream', () => {
  const sse = (chunks: string[]) =>
    new ReadableStream<Uint8Array>({
      start(c) {
        const enc = new TextEncoder();
        chunks.forEach((s) => c.enqueue(enc.encode(s)));
        c.close();
      },
    });

  it('parses events split across chunks', async () => {
    const events: unknown[] = [];
    for await (const e of readSse(sse(['event: step\ndata: {"agent":"A1",', '"status":"RUNNING"}\n\nevent: done\ndata: {"status":"RISK_DETECTED"}\n\n'])))
      events.push(e);
    expect(events).toEqual([
      { event: 'step', data: { agent: 'A1', status: 'RUNNING' } },
      { event: 'done', data: { status: 'RISK_DETECTED' } },
    ]);
  });

  it('reports progress and returns the final result', async () => {
    const body = 'event: start\ndata: {"case_id":"c"}\n\nevent: step\ndata: {"agent":"A1","status":"COMPLETED"}\n\nevent: done\ndata: {"status":"DECISION_READY","readiness":100}\n\n';
    const f = vi.fn(async () => new Response(sse([body]), { status: 200, headers: { 'Content-Type': 'text/event-stream' } }));
    vi.stubGlobal('fetch', f);
    const seen: string[] = [];
    const result = await api.analyzeCase('c', (e) => seen.push(e.event), 'baseline');
    expect(seen).toEqual(['start', 'step', 'done']);
    expect(result).toMatchObject({ status: 'DECISION_READY', readiness: 100 });
    expect((f.mock.calls[0] as unknown as [string])[0]).toBe('/api/cases/c/analyze?stream=true&mode=baseline');
  });

  it('turns a streamed error into ApiError', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(sse(['event: error\ndata: {"status":409,"message":"no"}\n\n']), { status: 200 })));
    await expect(api.analyzeCase('c', () => undefined)).rejects.toMatchObject({ status: 409, message: 'no' });
  });

  it('surfaces HTTP errors before the stream starts', async () => {
    stubFetch(403, { error: { message: 'Missing permission: case:analyze' } });
    await expect(api.analyzeCase('c', () => undefined)).rejects.toMatchObject({ status: 403 });
  });
});
