import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { governanceApi } from '../governance';

const MATCH_ANY_API_ORIGIN = {
  auditLog: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/audit-log(?:\?.*)?$/,
  webhookLog: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/webhook-log(?:\?.*)?$/,
  adminInvites: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/invites$/,
  adminInviteByToken: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/invites\/[^/]+$/,
  settings: /https?:\/\/localhost(?::\d+)?\/api\/v1\/settings\/$/,
  settingById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/settings\/\d+$/,
};

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('governanceApi audit and webhook operations', () => {
  it('loads audit log entries with privileged metadata', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.auditLog, () =>
        HttpResponse.json([
          {
            id: 'audit_001',
            admin_id: 'admin_001',
            action: 'update_setting',
            entity_type: 'setting',
            entity_id: '42',
            old_value: { enabled: false },
            new_value: { enabled: true },
            ip_address: '203.0.113.10',
            user_agent: 'Mozilla/5.0',
            created_at: '2026-04-10T10:30:00Z',
          },
        ]),
      ),
    );

    const response = await governanceApi.getAuditLogs({ page: 1, page_size: 10 });

    expect(response.status).toBe(200);
    expect(response.data[0]?.action).toBe('update_setting');
    expect(response.data[0]?.entity_type).toBe('setting');
  });

  it('loads webhook log entries with provider payloads', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.webhookLog, () =>
        HttpResponse.json([
          {
            id: 'webhook_001',
            source: 'cryptobot',
            event_type: 'invoice_paid',
            payload: { invoice_id: 'inv_123' },
            is_valid: true,
            error_message: null,
            processed_at: '2026-04-10T10:35:00Z',
            created_at: '2026-04-10T10:34:00Z',
          },
        ]),
      ),
    );

    const response = await governanceApi.getWebhookLogs({ page: 1, page_size: 10 });

    expect(response.status).toBe(200);
    expect(response.data[0]?.source).toBe('cryptobot');
    expect(response.data[0]?.payload).toMatchObject({ invoice_id: 'inv_123' });
  });
});

describe('governanceApi admin invite operations', () => {
  it('lists active admin invite tokens', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.adminInvites, () =>
        HttpResponse.json({
          invites: [
            {
              token: 'invite-token-001',
              role: 'operator',
              email_hint: 'ops@ozoxy.ru',
              created_by: 'admin_001',
              created_at: '2026-04-10T09:00:00Z',
              ttl_seconds: 3600,
            },
          ],
          total: 1,
        }),
      ),
    );

    const response = await governanceApi.listAdminInvites();

    expect(response.status).toBe(200);
    expect(response.data.total).toBe(1);
    expect(response.data.invites[0]?.role).toBe('operator');
  });

  it('creates an admin invite with role and email restriction', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.adminInvites, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json(
          {
            token: 'invite-token-002',
            role: 'support',
            email_hint: 'support@ozoxy.ru',
            expires_in_hours: 24,
          },
          { status: 201 },
        );
      }),
    );

    const response = await governanceApi.createAdminInvite({
      role: 'support',
      email_hint: 'support@ozoxy.ru',
    });

    expect(response.status).toBe(201);
    expect(response.data.token).toBe('invite-token-002');
    expect(capturedBody).toMatchObject({
      role: 'support',
      email_hint: 'support@ozoxy.ru',
    });
  });

  it('revokes an admin invite by token', async () => {
    let revokedToken = '';

    server.use(
      http.delete(MATCH_ANY_API_ORIGIN.adminInviteByToken, ({ request }) => {
        revokedToken = new URL(request.url).pathname.split('/').at(-1) ?? '';
        return new HttpResponse(null, { status: 204 });
      }),
    );

    const response = await governanceApi.revokeAdminInvite('invite-token-003');

    expect(response.status).toBe(204);
    expect(revokedToken).toBe('invite-token-003');
  });
});

describe('governanceApi policy settings operations', () => {
  it('loads visible settings from the settings endpoint', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.settings, () =>
        HttpResponse.json([
          {
            id: 7,
            key: 'registration_mode',
            value: { enabled: true },
            description: 'Registration gate',
            isPublic: false,
          },
        ]),
      ),
    );

    const response = await governanceApi.getSettings();

    expect(response.status).toBe(200);
    expect(response.data[0]?.key).toBe('registration_mode');
    expect(response.data[0]?.isPublic).toBe(false);
  });

  it('creates a setting with JSON payload', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.settings, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          id: 8,
          key: 'invite_policy',
          value: { ttl_hours: 24 },
          description: 'Invite ttl policy',
          isPublic: false,
        });
      }),
    );

    const response = await governanceApi.createSetting({
      key: 'invite_policy',
      value: { ttl_hours: 24 },
      description: 'Invite ttl policy',
      is_public: false,
    });

    expect(response.status).toBe(200);
    expect(response.data.key).toBe('invite_policy');
    expect(capturedBody).toMatchObject({
      key: 'invite_policy',
      description: 'Invite ttl policy',
      is_public: false,
    });
  });

  it('updates a setting by numeric id', async () => {
    let updatedId = '';

    server.use(
      http.put(MATCH_ANY_API_ORIGIN.settingById, async ({ request }) => {
        updatedId = new URL(request.url).pathname.split('/').at(-1) ?? '';
        const body = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          id: Number(updatedId),
          key: 'registration_mode',
          value: body.value ?? { enabled: false },
          description: body.description ?? 'Updated policy',
          isPublic: body.is_public ?? true,
        });
      }),
    );

    const response = await governanceApi.updateSetting(7, {
      value: { enabled: false },
      description: 'Updated policy',
      is_public: true,
    });

    expect(response.status).toBe(200);
    expect(updatedId).toBe('7');
    expect(response.data.isPublic).toBe(true);
  });
});
