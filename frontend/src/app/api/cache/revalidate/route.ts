import { timingSafeEqual } from 'node:crypto';

import { revalidateTag } from 'next/cache';
import { NextRequest, NextResponse } from 'next/server';

const SECRET_HEADER = 'x-cache-revalidate-secret';
const MAX_CONTENT_LENGTH_BYTES = 4096;
const MAX_TAGS_PER_REQUEST = 8;
const ALLOWED_TAGS = new Set([
  'public-pricing-catalog',
  'seo-compare',
  'seo-devices',
  'seo-guides',
  'seo-trust',
]);

type CacheRevalidationPayload = {
  tag?: unknown;
  tags?: unknown;
};

type PayloadReadResult =
  | { ok: true; payload: CacheRevalidationPayload }
  | { ok: false; response: NextResponse };

function jsonResponse(body: Record<string, unknown>, status: number): NextResponse {
  return NextResponse.json(body, {
    status,
    headers: {
      'Cache-Control': 'no-store',
    },
  });
}

function isAuthorized(request: NextRequest): boolean {
  const configured = process.env.NEXT_CACHE_REVALIDATE_SECRET?.trim();
  const provided = request.headers.get(SECRET_HEADER)?.trim();

  if (!configured || !provided) {
    return false;
  }

  const configuredBuffer = Buffer.from(configured);
  const providedBuffer = Buffer.from(provided);

  return (
    configuredBuffer.length === providedBuffer.length &&
    timingSafeEqual(configuredBuffer, providedBuffer)
  );
}

function readContentLength(request: NextRequest): number {
  const rawValue = request.headers.get('content-length');
  if (!rawValue) {
    return 0;
  }

  const parsed = Number(rawValue);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : MAX_CONTENT_LENGTH_BYTES + 1;
}

async function readBoundedJsonPayload(request: NextRequest): Promise<PayloadReadResult> {
  if (readContentLength(request) > MAX_CONTENT_LENGTH_BYTES) {
    return { ok: false, response: jsonResponse({ detail: 'Request body too large' }, 413) };
  }

  if (!request.body) {
    return { ok: false, response: jsonResponse({ detail: 'Invalid JSON body' }, 400) };
  }

  const decoder = new TextDecoder();
  const reader = request.body.getReader();
  let totalBytes = 0;
  let text = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!value) continue;

      totalBytes += value.byteLength;
      if (totalBytes > MAX_CONTENT_LENGTH_BYTES) {
        await reader.cancel().catch(() => undefined);
        return { ok: false, response: jsonResponse({ detail: 'Request body too large' }, 413) };
      }
      text += decoder.decode(value, { stream: true });
    }
  } finally {
    reader.releaseLock();
  }

  text += decoder.decode();

  try {
    return { ok: true, payload: JSON.parse(text) as CacheRevalidationPayload };
  } catch {
    return { ok: false, response: jsonResponse({ detail: 'Invalid JSON body' }, 400) };
  }
}

function normalizeRequestedTags(payload: CacheRevalidationPayload): string[] | null {
  const rawTags = Array.isArray(payload.tags)
    ? payload.tags
    : typeof payload.tag === 'string'
      ? [payload.tag]
      : null;

  if (!rawTags) {
    return null;
  }

  const tags = rawTags
    .map((tag) => (typeof tag === 'string' ? tag.trim() : ''))
    .filter(Boolean);

  return Array.from(new Set(tags));
}

export async function POST(request: NextRequest) {
  if (!isAuthorized(request)) {
    return jsonResponse({ detail: 'Forbidden' }, 403);
  }

  const payloadResult = await readBoundedJsonPayload(request);
  if (!payloadResult.ok) {
    return payloadResult.response;
  }

  const tags = normalizeRequestedTags(payloadResult.payload);
  if (!tags || tags.length === 0 || tags.length > MAX_TAGS_PER_REQUEST) {
    return jsonResponse({ detail: 'Invalid cache tags' }, 400);
  }

  const unsupportedTags = tags.filter((tag) => !ALLOWED_TAGS.has(tag));
  if (unsupportedTags.length > 0) {
    return jsonResponse({ detail: 'Unsupported cache tags', unsupportedTags }, 400);
  }

  for (const tag of tags) {
    revalidateTag(tag, 'max');
  }

  return jsonResponse({ revalidatedTags: tags }, 200);
}
