import { NextRequest, NextResponse } from "next/server";

import {
  createPendingTwoFactorCookieValue,
  pendingTwoFactorCookieOptions,
  PENDING_2FA_COOKIE,
} from "@/features/auth/lib/pending-twofa";

interface PendingTwoFactorBody {
  token?: string;
  locale?: string | null;
  return_to?: string | null;
  is_new_user?: boolean;
}

const APPROVED_LOCAL_STAGE_ADMIN_ORIGINS = new Set([
  "http://127.0.0.1:13001",
  "http://localhost:13001",
  "http://127.0.0.1:3000",
  "http://localhost:3000",
]);

function getRequestOrigin(request: NextRequest): string {
  try {
    return new URL(request.url).origin;
  } catch {
    return request.nextUrl.origin;
  }
}

function pendingCookieOptionsForRequest(request: NextRequest) {
  return {
    ...pendingTwoFactorCookieOptions,
    secure: APPROVED_LOCAL_STAGE_ADMIN_ORIGINS.has(getRequestOrigin(request))
      ? false
      : pendingTwoFactorCookieOptions.secure,
  };
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  let body: PendingTwoFactorBody;
  try {
    body = (await request.json()) as PendingTwoFactorBody;
  } catch {
    return NextResponse.json(
      { detail: "Invalid request body." },
      { status: 400 },
    );
  }

  const token = typeof body.token === "string" ? body.token.trim() : "";
  if (!token) {
    return NextResponse.json(
      { detail: "Missing pending 2FA token." },
      { status: 400 },
    );
  }

  const transaction = createPendingTwoFactorCookieValue(
    token,
    body.locale,
    body.return_to ?? null,
    body.is_new_user ?? false,
  );

  const response = new NextResponse(null, { status: 204 });
  response.cookies.set(
    PENDING_2FA_COOKIE,
    transaction.cookieValue,
    pendingCookieOptionsForRequest(request),
  );
  return response;
}
