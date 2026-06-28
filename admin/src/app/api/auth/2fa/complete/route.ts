import { NextRequest, NextResponse } from "next/server";
import { request as httpRequest } from "node:http";
import { request as httpsRequest } from "node:https";
import type { IncomingHttpHeaders } from "node:http";

import {
  parsePendingTwoFactorCookieValue,
  pendingTwoFactorCookieOptions,
  PENDING_2FA_COOKIE,
} from "@/features/auth/lib/pending-twofa";
import { getDefaultPostLoginPath } from "@/features/auth/lib/redirect-path";

function getBackendBaseUrl(): string {
  const baseUrl = process.env.API_INTERNAL_ORIGIN ?? process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) {
    throw new Error("API_INTERNAL_ORIGIN, API_URL or NEXT_PUBLIC_API_URL must be configured.");
  }

  return baseUrl.replace(/\/$/, "");
}

const ADMIN_CANONICAL_HOST = "admin.cyber-vpn.net";
const ADMIN_CANONICAL_PROTO = "https";
const MAX_BACKEND_RESPONSE_BYTES = 64 * 1024;
const BACKEND_REQUEST_TIMEOUT_MS = 10_000;
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

function isApprovedLocalStageAdminOrigin(request: NextRequest): boolean {
  return APPROVED_LOCAL_STAGE_ADMIN_ORIGINS.has(getRequestOrigin(request));
}

function shouldUseSecureCookie(request: NextRequest): boolean {
  return !isApprovedLocalStageAdminOrigin(request);
}

function normalizeSetCookieForRequest(
  headerValue: string,
  request: NextRequest,
): string {
  if (shouldUseSecureCookie(request)) {
    return headerValue;
  }

  return headerValue
    .split(";")
    .map((part) => part.trim())
    .filter((part) => part.toLowerCase() !== "secure")
    .join("; ");
}

function pendingCookieOptionsForRequest(request: NextRequest) {
  return {
    ...pendingTwoFactorCookieOptions,
    secure:
      shouldUseSecureCookie(request) && pendingTwoFactorCookieOptions.secure,
  };
}

function buildForwardHeaders(request: NextRequest, token: string): Headers {
  const headers = new Headers({
    accept: "application/json",
    authorization: `Bearer ${token}`,
    "content-type": "application/json",
  });

  const forwardedFor = request.headers.get("x-forwarded-for");
  const userAgent = request.headers.get("user-agent");
  const acceptLanguage = request.headers.get("accept-language");

  if (forwardedFor) {
    headers.set("x-forwarded-for", forwardedFor);
  }
  headers.set("x-forwarded-host", ADMIN_CANONICAL_HOST);
  headers.set("x-forwarded-proto", ADMIN_CANONICAL_PROTO);
  if (userAgent) {
    headers.set("user-agent", userAgent);
  }
  if (acceptLanguage) {
    headers.set("accept-language", acceptLanguage);
  }

  return headers;
}

interface BackendAuthResponse {
  ok: boolean;
  status: number;
  bodyText: string;
  headers: IncomingHttpHeaders;
  setCookieHeaders: string[];
}

function headersToBackendRecord(
  source: Headers,
  bodyText: string,
): Record<string, string> {
  const headers: Record<string, string> = {};
  source.forEach((value, key) => {
    headers[key] = value;
  });
  headers["content-length"] = String(Buffer.byteLength(bodyText));
  return headers;
}

function getBackendSetCookieHeaders(response: BackendAuthResponse): string[] {
  if (response.setCookieHeaders.length > 0) {
    return response.setCookieHeaders;
  }

  const setCookie = response.headers["set-cookie"];
  if (Array.isArray(setCookie)) {
    return setCookie;
  }
  return typeof setCookie === "string"
    ? splitCombinedSetCookieHeader(setCookie)
    : [];
}

function getFetchSetCookieHeaders(response: Response): string[] {
  const headers = response.headers as Headers & {
    getSetCookie?: () => string[];
  };

  if (typeof headers.getSetCookie === "function") {
    const setCookieHeaders = headers.getSetCookie();
    if (setCookieHeaders.length > 0) {
      return setCookieHeaders;
    }
  }

  const setCookie = response.headers.get("set-cookie");
  return setCookie ? splitCombinedSetCookieHeader(setCookie) : [];
}

async function fetchBackendJson(
  url: string,
  headers: Headers,
  bodyText: string,
): Promise<BackendAuthResponse> {
  const response = await fetch(url, {
    method: "POST",
    cache: "no-store",
    headers,
    body: bodyText,
  });

  return {
    ok: response.ok,
    status: response.status,
    bodyText: await response.text(),
    headers: Object.fromEntries(response.headers.entries()),
    setCookieHeaders: getFetchSetCookieHeaders(response),
  };
}

function postBackendJson(
  url: string,
  headers: Headers,
  bodyText: string,
): Promise<BackendAuthResponse> {
  const target = new URL(url);
  const transport = target.protocol === "https:" ? httpsRequest : httpRequest;

  return new Promise((resolve, reject) => {
    const request = transport(
      target,
      {
        method: "POST",
        headers: headersToBackendRecord(headers, bodyText),
      },
      (response) => {
        const chunks: Buffer[] = [];
        let totalBytes = 0;

        response.on("data", (chunk: Buffer | string) => {
          const buffer = Buffer.isBuffer(chunk)
            ? chunk
            : Buffer.from(chunk);
          totalBytes += buffer.byteLength;
          if (totalBytes > MAX_BACKEND_RESPONSE_BYTES) {
            request.destroy(new Error("Backend 2FA response is too large."));
            return;
          }
          chunks.push(buffer);
        });

        response.on("end", () => {
          const status = response.statusCode ?? 502;
          const setCookie = response.headers["set-cookie"];
          resolve({
            ok: status >= 200 && status < 300,
            status,
            bodyText: Buffer.concat(chunks).toString("utf8"),
            headers: response.headers,
            setCookieHeaders: Array.isArray(setCookie)
              ? setCookie
              : typeof setCookie === "string"
                ? splitCombinedSetCookieHeader(setCookie)
                : [],
          });
        });
      },
    );

    request.setTimeout(BACKEND_REQUEST_TIMEOUT_MS, () => {
      request.destroy(new Error("Backend 2FA request timed out."));
    });
    request.on("error", reject);
    request.write(bodyText);
    request.end();
  });
}

function splitCombinedSetCookieHeader(headerValue: string): string[] {
  const headers: string[] = [];
  let start = 0;
  let inExpiresAttribute = false;

  for (let index = 0; index < headerValue.length; index += 1) {
    const remaining = headerValue.slice(index).toLowerCase();
    if (remaining.startsWith("expires=")) {
      inExpiresAttribute = true;
    }

    const char = headerValue[index];
    if (char === ";") {
      inExpiresAttribute = false;
      continue;
    }

    if (char !== "," || inExpiresAttribute) {
      continue;
    }

    const nextPart = headerValue.slice(index + 1).trimStart();
    if (/^[^=;\s]+=/.test(nextPart)) {
      headers.push(headerValue.slice(start, index).trim());
      start = index + 1;
    }
  }

  const tail = headerValue.slice(start).trim();
  if (tail) {
    headers.push(tail);
  }

  return headers;
}

async function appendBackendAuthCookies(
  source: BackendAuthResponse,
  target: NextResponse,
  request: NextRequest,
): Promise<void> {
  const headerValues = getBackendSetCookieHeaders(source);
  if (headerValues.length > 0) {
    for (const headerValue of headerValues) {
      const normalizedHeaderValue = normalizeSetCookieForRequest(
        headerValue,
        request,
      );
      target.headers.append("Set-Cookie", normalizedHeaderValue);
      mirrorBackendCookieForNextResponse(
        normalizedHeaderValue,
        target,
        request,
      );
    }
  }

  // The backend response body is the authority for both tokens. Keep this
  // fallback even when Set-Cookie exists because some runtimes collapse multiple
  // backend Set-Cookie headers into one value before we can forward them.
  await appendJsonTokenFallbackCookies(source, target, request);
}

async function appendJsonTokenFallbackCookies(
  source: BackendAuthResponse,
  target: NextResponse,
  request: NextRequest,
): Promise<void> {
  let payload: { access_token?: string; refresh_token?: string };
  try {
    payload = JSON.parse(source.bodyText) as {
      access_token?: string;
      refresh_token?: string;
    };
  } catch {
    return;
  }

  const secure =
    process.env.NODE_ENV === "production" && shouldUseSecureCookie(request);
  for (const [name, value] of [
    ["access_token", payload.access_token],
    ["refresh_token", payload.refresh_token],
  ] as const) {
    if (!value) {
      continue;
    }
    target.cookies.set(name, value, {
      httpOnly: true,
      path: "/api",
      sameSite: "lax",
      secure,
    });
  }
}

function mirrorBackendCookieForNextResponse(
  headerValue: string,
  target: NextResponse,
  request: NextRequest,
): void {
  const [nameValue, ...attributes] = headerValue
    .split(";")
    .map((part) => part.trim());
  const separatorIndex = nameValue.indexOf("=");
  if (separatorIndex <= 0) {
    return;
  }

  const name = nameValue.slice(0, separatorIndex);
  const value = nameValue.slice(separatorIndex + 1);
  const pathAttribute = attributes.find((attribute) =>
    attribute.toLowerCase().startsWith("path="),
  );
  const sameSiteAttribute = attributes.find((attribute) =>
    attribute.toLowerCase().startsWith("samesite="),
  );
  const sameSite = sameSiteAttribute?.split("=")[1]?.toLowerCase();

  target.cookies.set(name, value, {
    httpOnly: attributes.some(
      (attribute) => attribute.toLowerCase() === "httponly",
    ),
    path: pathAttribute?.slice("path=".length) || "/",
    sameSite:
      sameSite === "strict" || sameSite === "lax" || sameSite === "none"
        ? sameSite
        : undefined,
    secure:
      attributes.some((attribute) => attribute.toLowerCase() === "secure") &&
      shouldUseSecureCookie(request),
  });
}

function deletePendingTwoFactorCookie(
  response: NextResponse,
  request: NextRequest,
): void {
  response.cookies.set(PENDING_2FA_COOKIE, "", {
    ...pendingCookieOptionsForRequest(request),
    maxAge: 0,
  });
}

async function readErrorPayload(
  response: BackendAuthResponse,
): Promise<{ detail: string }> {
  try {
    const payload = JSON.parse(response.bodyText) as { detail?: string };
    return {
      detail: payload.detail || "Two-factor verification failed.",
    };
  } catch {
    return {
      detail: "Two-factor verification failed.",
    };
  }
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const transaction = parsePendingTwoFactorCookieValue(
    request.cookies.get(PENDING_2FA_COOKIE)?.value,
  );
  if (!transaction) {
    const response = NextResponse.json(
      { detail: "Two-factor login session expired. Start sign-in again." },
      { status: 401 },
    );
    deletePendingTwoFactorCookie(response, request);
    return response;
  }

  let body: { code?: string };
  try {
    body = (await request.json()) as { code?: string };
  } catch {
    return NextResponse.json(
      { detail: "Invalid request body." },
      { status: 400 },
    );
  }

  const code = typeof body.code === "string" ? body.code.trim() : "";
  if (!/^\d{6}$/.test(code)) {
    return NextResponse.json(
      { detail: "Enter a valid 6-digit code." },
      { status: 400 },
    );
  }

  let backendResponse: BackendAuthResponse;
  try {
    const backendBody = JSON.stringify({ code });
    const backendUrl = `${getBackendBaseUrl()}/api/v1/2fa/complete`;
    const backendHeaders = buildForwardHeaders(request, transaction.token);
    backendResponse = process.env.NODE_ENV === "production"
      ? await postBackendJson(backendUrl, backendHeaders, backendBody)
      : await fetchBackendJson(backendUrl, backendHeaders, backendBody);
  } catch {
    return NextResponse.json(
      { detail: "Authentication service is unavailable." },
      { status: 503 },
    );
  }

  if (!backendResponse.ok) {
    const errorPayload = await readErrorPayload(backendResponse);
    const response = NextResponse.json(errorPayload, {
      status: backendResponse.status,
    });
    if (backendResponse.status === 401) {
      deletePendingTwoFactorCookie(response, request);
    }
    return response;
  }

  const redirectTo = new URL(transaction.returnTo, request.url);
  const defaultReturnTo = getDefaultPostLoginPath(transaction.locale);
  if (transaction.isNewUser && transaction.returnTo === defaultReturnTo) {
    redirectTo.searchParams.set("welcome", "true");
  }

  const response = NextResponse.json({
    redirect_to: redirectTo.pathname + redirectTo.search,
  });
  deletePendingTwoFactorCookie(response, request);
  await appendBackendAuthCookies(backendResponse, response, request);
  return response;
}
