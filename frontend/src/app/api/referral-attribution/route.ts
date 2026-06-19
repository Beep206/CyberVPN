import { NextRequest, NextResponse } from 'next/server';
import {
  normalizeReferralCode,
  REFERRAL_ATTRIBUTION_COOKIE_NAME,
  REFERRAL_ATTRIBUTION_TTL_SECONDS,
} from '@/features/referral-attribution/constants';

const NO_STORE_HEADERS = {
  'Cache-Control': 'no-store, max-age=0',
};

function setAttributionCookie(response: NextResponse, referralCode: string): void {
  response.cookies.set({
    httpOnly: true,
    maxAge: REFERRAL_ATTRIBUTION_TTL_SECONDS,
    name: REFERRAL_ATTRIBUTION_COOKIE_NAME,
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    value: referralCode,
  });
}

export async function POST(request: NextRequest) {
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json(
      { code: 'REFERRAL_CODE_INVALID', message: 'Invalid JSON body' },
      { headers: NO_STORE_HEADERS, status: 422 },
    );
  }

  const rawCode = typeof payload === 'object' && payload !== null
    ? (payload as { referral_code?: unknown }).referral_code
    : undefined;
  const requestedCode = normalizeReferralCode(
    typeof rawCode === 'string' ? rawCode : undefined,
  );
  if (!requestedCode) {
    return NextResponse.json(
      { code: 'REFERRAL_CODE_INVALID', message: 'Referral code has an invalid format' },
      { headers: NO_STORE_HEADERS, status: 422 },
    );
  }

  const existingCode = normalizeReferralCode(
    request.cookies.get(REFERRAL_ATTRIBUTION_COOKIE_NAME)?.value,
  );
  const effectiveCode = existingCode ?? requestedCode;
  const response = NextResponse.json(
    { referral_code: effectiveCode },
    { headers: NO_STORE_HEADERS },
  );

  if (!existingCode) {
    setAttributionCookie(response, effectiveCode);
  }

  return response;
}

export function DELETE() {
  const response = new NextResponse(null, {
    headers: NO_STORE_HEADERS,
    status: 204,
  });
  response.cookies.set({
    httpOnly: true,
    maxAge: 0,
    name: REFERRAL_ATTRIBUTION_COOKIE_NAME,
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    value: '',
  });
  return response;
}
