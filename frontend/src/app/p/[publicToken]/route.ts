import { NextRequest, NextResponse } from 'next/server';
import { SITE_URL } from '@/shared/lib/seo-route-policy';

type CaptureResponse = {
  redirect_url: string;
};

const CAMPAIGN_KEYS = [
  'utm_source',
  'utm_medium',
  'utm_campaign',
  'utm_term',
  'utm_content',
  'gclid',
  'fbclid',
  'click_id',
  'sub_id',
] as const;

function resolveBackendApiBaseUrl(): string {
  const baseUrl = (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL)?.trim();
  if (!baseUrl) {
    throw new Error('API_URL or NEXT_PUBLIC_API_URL must be configured.');
  }
  return `${baseUrl.replace(/\/$/, '')}/api/v1`;
}

function collectCampaignParams(request: NextRequest): Record<string, string> {
  const params: Record<string, string> = {};
  for (const key of CAMPAIGN_KEYS) {
    const value = request.nextUrl.searchParams.get(key)?.trim();
    if (value) {
      params[key] = value.slice(0, 200);
    }
  }
  for (const [key, value] of request.nextUrl.searchParams.entries()) {
    if (key.startsWith('sub_') && value.trim()) {
      params[key] = value.trim().slice(0, 200);
    }
  }
  return params;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ publicToken: string }> },
) {
  const { publicToken } = await params;
  const response = await fetch(`${resolveBackendApiBaseUrl()}/partner-attribution/capture`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Forwarded-Host': request.headers.get('x-forwarded-host') ?? request.headers.get('host') ?? '',
    },
    body: JSON.stringify({
      public_token: publicToken,
      source_host: request.headers.get('x-forwarded-host') ?? request.headers.get('host'),
      source_path: `${request.nextUrl.pathname}${request.nextUrl.search}`,
      campaign_params: collectCampaignParams(request),
    }),
    cache: 'no-store',
  });

  if (!response.ok) {
    return NextResponse.redirect(new URL('/ru-RU/register', SITE_URL));
  }

  const payload = await response.json() as CaptureResponse;
  return NextResponse.redirect(payload.redirect_url);
}
