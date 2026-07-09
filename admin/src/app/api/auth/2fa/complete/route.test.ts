import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { POST } from "./route";
import {
  createPendingTwoFactorCookieValue,
  PENDING_2FA_COOKIE,
} from "@/features/auth/lib/pending-twofa";

function readSetCookieHeaders(response: Response): string[] {
  const headers = response.headers as Headers & {
    getSetCookie?: () => string[];
  };

  if (typeof headers.getSetCookie === "function") {
    return headers.getSetCookie();
  }

  const setCookie = response.headers.get("set-cookie");
  return setCookie ? [setCookie] : [];
}

describe("POST /api/auth/2fa/complete", () => {

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("completes pending 2FA, forwards backend cookies, and returns redirect target", async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "access_token_value",
          refresh_token: "refresh_token_value",
          token_type: "bearer",
          expires_in: 3600,
        }),
        {
          status: 200,
          headers: {
            "content-type": "application/json",
            "set-cookie": "access_token=abc; Path=/; HttpOnly",
          },
        },
      ),
    ));

    const pending = createPendingTwoFactorCookieValue(
      "pending_2fa_token",
      "ru-RU",
      "/ru-RU/dashboard",
      true,
    );
    const request = new NextRequest(
      "https://admin.cyber-vpn.net/api/auth/2fa/complete",
      {
        method: "POST",
        body: JSON.stringify({ code: "123456" }),
        headers: {
          "content-type": "application/json",
          authorization: "Bearer browser-supplied",
          "x-backend-internal-secret": "leaked-backend-secret",
          "x-forwarded-for": "203.0.113.10",
          "x-forwarded-host": "api.cyber-vpn.net",
          "x-forwarded-proto": "https",
          "x-payment-settlement-worker-secret": "leaked-payment-secret",
          "x-telegram-bot-secret": "leaked-telegram-secret",
          "x-auth-realm": "customer",
        },
      },
    );
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/2fa/complete",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ code: "123456" }),
        cache: "no-store",
        headers: expect.any(Headers),
      }),
    );
    const forwardedHeaders = (global.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0]?.[1]?.headers as Headers;
    expect(forwardedHeaders.get("x-forwarded-host")).toBe(
      "admin.cyber-vpn.net",
    );
    expect(forwardedHeaders.get("x-forwarded-proto")).toBe("https");
    expect(forwardedHeaders.get("x-forwarded-for")).toBeNull();
    expect(forwardedHeaders.get("x-auth-realm")).toBeNull();
    expect(forwardedHeaders.get("authorization")).toBe("Bearer pending_2fa_token");
    expect(forwardedHeaders.get("x-backend-internal-secret")).toBeNull();
    expect(forwardedHeaders.get("x-payment-settlement-worker-secret")).toBeNull();
    expect(forwardedHeaders.get("x-telegram-bot-secret")).toBeNull();
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      redirect_to: "/ru-RU/dashboard?welcome=true",
    });
    const setCookieHeaders = readSetCookieHeaders(response).join("\n");
    expect(setCookieHeaders).toContain("access_token=");
    expect(setCookieHeaders).toContain("refresh_token=");
    expect(setCookieHeaders).toContain("Path=/");
  });

  it("splits collapsed backend auth cookies and mirrors JSON token fallback cookies", async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "json_access_token_value",
          refresh_token: "json_refresh_token_value",
          token_type: "bearer",
          expires_in: 3600,
        }),
        {
          status: 200,
          headers: {
            "content-type": "application/json",
            "set-cookie":
              "access_token=backend_access; Path=/api/a,b=c; HttpOnly; Secure; SameSite=Lax, refresh_token=backend_refresh; Path=/api; HttpOnly; Secure; SameSite=Lax",
          },
        },
      ),
    ));

    const pending = createPendingTwoFactorCookieValue(
      "pending_2fa_token",
      "ru-RU",
      "/ru-RU/dashboard",
      false,
    );
    const request = new NextRequest(
      "https://admin.cyber-vpn.net/api/auth/2fa/complete",
      {
        method: "POST",
        body: JSON.stringify({ code: "123456" }),
        headers: {
          "content-type": "application/json",
        },
      },
    );
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);
    const setCookieHeaders = readSetCookieHeaders(response).join("\n");

    expect(response.status).toBe(200);
    expect(setCookieHeaders).toContain("access_token=json_access_token_value");
    expect(setCookieHeaders).toContain(
      "refresh_token=json_refresh_token_value",
    );
    const authCookieHeaders = readSetCookieHeaders(response).filter(
      (header) =>
        header.startsWith("access_token=") ||
        header.startsWith("refresh_token="),
    );
    expect(authCookieHeaders).toHaveLength(2);
    expect(authCookieHeaders).toEqual([
      expect.stringContaining("Path=/api"),
      expect.stringContaining("Path=/api"),
    ]);
    expect(authCookieHeaders.join("\n")).not.toContain("Path=/;");
  });

  it("forwards collapsed backend auth cookies with comma attributes when no JSON fallback is present", async () => {
    const combinedSetCookie =
      "access_token=backend_access; Path=/api/a,b=c; HttpOnly; Secure; SameSite=Lax, refresh_token=backend_refresh; Path=/api; HttpOnly; Secure; SameSite=Lax";
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        entries: () => [["content-type", "application/json"]][Symbol.iterator](),
        get: (name: string) =>
          name.toLowerCase() === "set-cookie"
            ? combinedSetCookie
            : null,
        getSetCookie: () => [combinedSetCookie],
      },
      text: async () => JSON.stringify({ redirect_to: "/ru-RU/dashboard" }),
    } as unknown as Response));

    const pending = createPendingTwoFactorCookieValue(
      "pending_2fa_token",
      "ru-RU",
      "/ru-RU/dashboard",
      false,
    );
    const request = new NextRequest(
      "https://admin.cyber-vpn.net/api/auth/2fa/complete",
      {
        method: "POST",
        body: JSON.stringify({ code: "123456" }),
        headers: {
          "content-type": "application/json",
        },
      },
    );
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);
    const setCookieHeaders = readSetCookieHeaders(response);
    const authCookieHeaders = setCookieHeaders.filter(
      (header) =>
        header.startsWith("access_token=") ||
        header.startsWith("refresh_token="),
    );
    const accessCookie = authCookieHeaders.find((header) => header.startsWith("access_token="));

    expect(response.status).toBe(200);
    expect(authCookieHeaders).toHaveLength(2);
    expect(accessCookie).toContain("access_token=backend_access");
    expect(accessCookie).toContain("Path=/api/a,b=c");
    expect(accessCookie).not.toContain("refresh_token=backend_refresh");
  });

  it("strips Secure from backend auth cookies for approved local-stage admin origin", async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "json_access_token_value",
          refresh_token: "json_refresh_token_value",
          token_type: "bearer",
          expires_in: 3600,
        }),
        {
          status: 200,
          headers: {
            "content-type": "application/json",
            "set-cookie":
              "access_token=backend_access; Path=/api; HttpOnly; Secure; SameSite=Lax, refresh_token=backend_refresh; Path=/api; HttpOnly; Secure; SameSite=Lax",
          },
        },
      ),
    ));

    const pending = createPendingTwoFactorCookieValue(
      "pending_2fa_token",
      "en-EN",
      "/en-EN/dashboard",
      false,
    );
    const request = new NextRequest(
      "http://127.0.0.1:13001/api/auth/2fa/complete",
      {
        method: "POST",
        body: JSON.stringify({ code: "123456" }),
        headers: {
          "content-type": "application/json",
          "x-auth-realm": "admin",
        },
      },
    );
    request.cookies.set(PENDING_2FA_COOKIE, pending.cookieValue);

    const response = await POST(request);
    const setCookieHeaders = readSetCookieHeaders(response).join("\n");

    const forwardedHeaders = (global.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0]?.[1]?.headers as Headers;

    expect(response.status).toBe(200);
    expect(forwardedHeaders.get("x-forwarded-host")).toBe(
      "admin.cyber-vpn.net",
    );
    expect(forwardedHeaders.get("x-forwarded-proto")).toBe("https");
    expect(forwardedHeaders.get("x-auth-realm")).toBeNull();
    expect(setCookieHeaders).toContain("access_token=");
    expect(setCookieHeaders).toContain("refresh_token=");
    expect(setCookieHeaders).not.toContain("Secure");
  });

  it("rejects requests without a valid pending 2FA cookie", async () => {
    const request = new NextRequest(
      "http://localhost:3000/api/auth/2fa/complete",
      {
        method: "POST",
        body: JSON.stringify({ code: "123456" }),
        headers: {
          "content-type": "application/json",
        },
      },
    );

    const response = await POST(request);

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({
      detail: "Two-factor login session expired. Start sign-in again.",
    });
  });
});
