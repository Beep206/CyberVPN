import { NextResponse, type NextRequest } from 'next/server';
import { getSeoDashboardSummary } from '@/shared/lib/analytics-reporting';
import { hasAllowedAnalyticsOrigin } from '../allowed-origin';

export async function GET(request: NextRequest) {
  if (!hasAllowedAnalyticsOrigin(request)) {
    return NextResponse.json({ error: 'forbidden' }, { status: 403 });
  }

  return NextResponse.json(getSeoDashboardSummary(), {
    headers: {
      'Cache-Control': 'no-store',
    },
  });
}
