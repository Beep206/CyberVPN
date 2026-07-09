import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

const nextCacheMock = vi.hoisted(() => ({
  revalidateTag: vi.fn(),
}));

vi.mock('next/cache', () => ({
  revalidateTag: nextCacheMock.revalidateTag,
}));

import { POST } from './route';

function createRequest(body: unknown, secret?: string): NextRequest {
  return new NextRequest('http://localhost:3001/api/cache/revalidate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(secret ? { 'x-cache-revalidate-secret': secret } : {}),
    },
    body: JSON.stringify(body),
  });
}

function createOversizedStreamRequest(secret: string): NextRequest {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode('{"tags":["seo-trust"],"padding":"'));
      controller.enqueue(new Uint8Array(4097));
      controller.enqueue(new TextEncoder().encode('"}'));
      controller.close();
    },
  });

  return new NextRequest('http://localhost:3001/api/cache/revalidate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-cache-revalidate-secret': secret,
    },
    body,
    duplex: 'half',
  } as unknown as ConstructorParameters<typeof NextRequest>[1]);
}

describe('POST /api/cache/revalidate', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    nextCacheMock.revalidateTag.mockReset();
  });

  it('rejects requests without the dedicated cache secret', async () => {
    vi.stubEnv('NEXT_CACHE_REVALIDATE_SECRET', 'expected-cache-secret');

    const response = await POST(createRequest({ tag: 'seo-trust' }));

    expect(response.status).toBe(403);
    expect(nextCacheMock.revalidateTag).not.toHaveBeenCalled();
    await expect(response.json()).resolves.toEqual({ detail: 'Forbidden' });
  });

  it('rejects tags outside the admin public SEO allowlist', async () => {
    vi.stubEnv('NEXT_CACHE_REVALIDATE_SECRET', 'expected-cache-secret');

    const response = await POST(createRequest(
      { tags: ['seo-trust', 'admin-session'] },
      'expected-cache-secret',
    ));

    expect(response.status).toBe(400);
    expect(nextCacheMock.revalidateTag).not.toHaveBeenCalled();
    await expect(response.json()).resolves.toEqual({
      detail: 'Unsupported cache tags',
      unsupportedTags: ['admin-session'],
    });
  });

  it('revalidates only allowed public admin tags with the current Next profile argument', async () => {
    vi.stubEnv('NEXT_CACHE_REVALIDATE_SECRET', 'expected-cache-secret');

    const response = await POST(createRequest(
      { tags: ['seo-guides', 'seo-trust', 'seo-guides'] },
      'expected-cache-secret',
    ));

    expect(response.status).toBe(200);
    expect(nextCacheMock.revalidateTag).toHaveBeenCalledTimes(2);
    expect(nextCacheMock.revalidateTag).toHaveBeenNthCalledWith(1, 'seo-guides', 'max');
    expect(nextCacheMock.revalidateTag).toHaveBeenNthCalledWith(2, 'seo-trust', 'max');
    await expect(response.json()).resolves.toEqual({
      revalidatedTags: ['seo-guides', 'seo-trust'],
    });
  });

  it('rejects oversized chunked requests without relying on content-length', async () => {
    vi.stubEnv('NEXT_CACHE_REVALIDATE_SECRET', 'expected-cache-secret');

    const response = await POST(createOversizedStreamRequest('expected-cache-secret'));

    expect(response.status).toBe(413);
    expect(nextCacheMock.revalidateTag).not.toHaveBeenCalled();
    await expect(response.json()).resolves.toEqual({ detail: 'Request body too large' });
  });
});
