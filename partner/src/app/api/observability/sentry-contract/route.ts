import { timingSafeEqual } from 'node:crypto';

import { NextRequest, NextResponse } from 'next/server';

const SECRET_HEADER = 'x-observability-secret';

function isAuthorized(request: NextRequest): boolean {
  const configured = process.env.FRONTEND_OBSERVABILITY_INTERNAL_SECRET?.trim();
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

function resolveEnvironment(): string {
  return (
    process.env.APP_ENV ??
    process.env.NEXT_PUBLIC_APP_ENV ??
    process.env.NODE_ENV ??
    'development'
  );
}

function resolveRelease(): string {
  return process.env.SENTRY_RELEASE ?? process.env.NEXT_PUBLIC_SENTRY_RELEASE ?? '';
}

export async function GET(request: NextRequest) {
  if (!isAuthorized(request)) {
    return NextResponse.json({ detail: 'Forbidden' }, { status: 403 });
  }

  return NextResponse.json({
    runtimeSurface: 'partner',
    environment: resolveEnvironment(),
    release: resolveRelease(),
    dsnConfigured: Boolean(process.env.SENTRY_DSN?.trim()),
    publicDsnConfigured: Boolean(process.env.NEXT_PUBLIC_SENTRY_DSN?.trim()),
  });
}
