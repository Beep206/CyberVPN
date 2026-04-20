import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { integrationsApi } from '../integrations';

const MATCH_ANY_API_ORIGIN = {
  telegramUser: /https?:\/\/localhost(?::\d+)?\/api\/v1\/telegram\/user\/\d+$/,
  telegramConfig: /https?:\/\/localhost(?::\d+)?\/api\/v1\/telegram\/user\/\d+\/config$/,
  generateLoginLink: /https?:\/\/localhost(?::\d+)?\/api\/v1\/auth\/telegram\/generate-login-link$/,
  notifications: /https?:\/\/localhost(?::\d+)?\/api\/v1\/users\/me\/notifications$/,
  fcmToken: /https?:\/\/localhost(?::\d+)?\/api\/v1\/users\/me\/fcm-token$/,
  realtimeTicket: /https?:\/\/localhost(?::\d+)?\/api\/v1\/ws\/ticket$/,
  botUser: /https?:\/\/localhost(?::\d+)?\/api\/integrations\/telegram\/bot\/user\/\d+$/,
};

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('integrationsApi telegram operations', () => {
  it('loads a Telegram-linked user by telegram id', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.telegramUser, () =>
        HttpResponse.json({
          uuid: '550e8400-e29b-41d4-a716-446655440000',
          username: 'tg_user_01',
          status: 'active',
          data_usage: 1024,
          data_limit: 4096,
          expires_at: '2026-04-10T10:30:00Z',
          subscription_url: 'vless://example',
        }),
      ),
    );

    const response = await integrationsApi.getTelegramUser(123456789);

    expect(response.status).toBe(200);
    expect(response.data.username).toBe('tg_user_01');
    expect(response.data.status).toBe('active');
  });

  it('generates a telegram bot login link', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.generateLoginLink, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          token: 'login_token_001',
          url: 'https://t.me/ozoxy_bot?start=login_login_token_001',
          expires_at: '2026-04-10T11:00:00Z',
        });
      }),
    );

    const response = await integrationsApi.generateTelegramLoginLink({
      telegram_id: 987654321,
    });

    expect(response.status).toBe(200);
    expect(response.data.token).toBe('login_token_001');
    expect(capturedBody).toMatchObject({ telegram_id: 987654321 });
  });

  it('reads a bot-facing telegram user through the admin proxy', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.botUser, () =>
        HttpResponse.json({
          uuid: 'admin-user-01',
          telegram_id: 123456789,
          username: 'ozoxy_support',
          first_name: 'Ozoxy',
          language_code: 'en',
          status: 'active',
          is_admin: false,
          personal_discount: 0,
          next_purchase_discount: 0,
          referrer_id: null,
          points: 0,
          subscription: null,
          subscriptions: [],
          created_at: '2026-04-10T10:00:00Z',
          updated_at: '2026-04-10T10:00:00Z',
        }),
      ),
    );

    const response = await integrationsApi.getTelegramBotUser(123456789);

    expect(response.status).toBe(200);
    expect(response.data.telegram_id).toBe(123456789);
    expect(response.data.username).toBe('ozoxy_support');
  });
});

describe('integrationsApi push and realtime operations', () => {
  it('loads the current notification preferences', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.notifications, () =>
        HttpResponse.json({
          email_security: true,
          email_marketing: false,
          push_connection: true,
          push_payment: true,
          push_subscription: false,
        }),
      ),
    );

    const response = await integrationsApi.getNotificationPreferences();

    expect(response.status).toBe(200);
    expect(response.data.push_payment).toBe(true);
    expect(response.data.push_subscription).toBe(false);
  });

  it('registers an fcm token for the current device', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.fcmToken, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json(
          {
            token: 'fcm_token_001',
            device_id: 'device-01',
            platform: 'ios',
            created_at: '2026-04-10T10:10:00Z',
          },
          { status: 201 },
        );
      }),
    );

    const response = await integrationsApi.registerFcmToken({
      token: 'fcm_token_001',
      device_id: 'device-01',
      platform: 'ios',
    });

    expect(response.status).toBe(201);
    expect(response.data.platform).toBe('ios');
    expect(capturedBody).toMatchObject({
      token: 'fcm_token_001',
      device_id: 'device-01',
    });
  });

  it('creates a single-use realtime websocket ticket', async () => {
    server.use(
      http.post(MATCH_ANY_API_ORIGIN.realtimeTicket, () =>
        HttpResponse.json({
          ticket: 'ticket-001',
          expires_in: 30,
        }),
      ),
    );

    const response = await integrationsApi.createRealtimeTicket();

    expect(response.status).toBe(200);
    expect(response.data.ticket).toBe('ticket-001');
    expect(response.data.expires_in).toBe(30);
  });
});
