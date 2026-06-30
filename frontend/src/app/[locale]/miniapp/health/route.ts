import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

function firstNonEmpty(...values: Array<string | undefined>): string | null {
  for (const value of values) {
    const normalized = value?.trim();
    if (normalized) {
      return normalized;
    }
  }
  return null;
}

export async function GET(): Promise<NextResponse> {
  return NextResponse.json(
    {
      ok: true,
      surface: 'miniapp',
      route_group: 'miniapp',
      release: firstNonEmpty(
        process.env.NEXT_PUBLIC_SENTRY_RELEASE,
        process.env.SENTRY_RELEASE,
        process.env.CYBERVPN_IMAGE_TAG,
      ),
      git_sha: firstNonEmpty(
        process.env.NEXT_PUBLIC_GIT_SHA,
        process.env.GIT_SHA,
        process.env.CI_COMMIT_SHA,
      ),
      origin_marker: process.env.RUNTIME_ORIGIN_MARKER?.trim() || 'stage1-prod-a',
      generated_at: new Date().toISOString(),
    },
    {
      headers: {
        'Cache-Control': 'no-store, max-age=0',
      },
    },
  );
}
