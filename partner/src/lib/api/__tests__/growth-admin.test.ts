import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { growthApi } from '../growth';

const MATCH_ANY_API_ORIGIN = {
  promoCodes: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/promo-codes(?:\?.*)?$/,
  promoCodeById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/promo-codes\/[^/]+$/,
  inviteCodes: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/invite-codes$/,
  partnerPromote: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/partners\/promote$/,
  referralOverview: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/referrals\/overview$/,
  referralUserDetail: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/referrals\/users\/[^/]+$/,
  partners: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/partners(?:\?.*)?$/,
  partnerDetail: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/partners\/[^/]+$/,
  partnerWorkspaces: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/partner-workspaces$/,
  partnerWorkspaceDetail: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/partner-workspaces\/[^/]+$/,
};

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('growthApi promo code operations', () => {
  it('lists admin promo codes with operational fields', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.promoCodes, () =>
        HttpResponse.json([
          {
            id: 'promo_001',
            code: 'SPRING25',
            discount_type: 'percent',
            discount_value: 25,
            currency: 'USD',
            max_uses: 100,
            current_uses: 10,
            is_single_use: false,
            is_active: true,
            expires_at: '2026-05-01T00:00:00Z',
            created_at: '2026-04-10T11:00:00Z',
          },
        ]),
      ),
    );

    const response = await growthApi.listPromos({ offset: 0, limit: 20 });

    expect(response.status).toBe(200);
    expect(response.data[0]?.code).toBe('SPRING25');
    expect(response.data[0]?.current_uses).toBe(10);
  });

  it('creates a promo code with advanced admin fields', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.promoCodes, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json(
          {
            id: 'promo_002',
            code: 'VIPFIXED',
            discount_type: 'fixed',
            discount_value: 15,
            currency: 'USD',
            max_uses: 50,
            current_uses: 0,
            is_single_use: true,
            is_active: true,
            expires_at: '2026-06-01T00:00:00Z',
            created_at: '2026-04-10T12:00:00Z',
          },
          { status: 201 },
        );
      }),
    );

    const response = await growthApi.createPromo({
      code: 'VIPFIXED',
      discount_type: 'fixed',
      discount_value: 15,
      max_uses: 50,
      is_single_use: true,
      plan_ids: ['plan_001'],
      min_amount: 25,
      expires_at: '2026-06-01T00:00:00Z',
      description: 'High-value segment',
      currency: 'USD',
    });

    expect(response.status).toBe(201);
    expect(response.data.code).toBe('VIPFIXED');
    expect(capturedBody).toMatchObject({
      code: 'VIPFIXED',
      discount_type: 'fixed',
      discount_value: 15,
      min_amount: 25,
      currency: 'USD',
    });
  });

  it('loads a single promo code detail', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.promoCodeById, ({ request }) => {
        const promoId = new URL(request.url).pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          id: promoId,
          code: 'FLASH50',
          discount_type: 'percent',
          discount_value: 50,
          currency: 'USD',
          max_uses: 10,
          current_uses: 3,
          is_single_use: false,
          is_active: true,
          expires_at: '2026-04-30T00:00:00Z',
          created_at: '2026-04-10T12:30:00Z',
        });
      }),
    );

    const response = await growthApi.getPromo('promo_003');

    expect(response.status).toBe(200);
    expect(response.data.id).toBe('promo_003');
    expect(response.data.code).toBe('FLASH50');
  });

  it('updates a promo code by id', async () => {
    let updatedId = '';
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.put(MATCH_ANY_API_ORIGIN.promoCodeById, async ({ request }) => {
        updatedId = new URL(request.url).pathname.split('/').at(-1) ?? '';
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          id: updatedId,
          code: 'SPRING25',
          discount_type: 'percent',
          discount_value: capturedBody.discount_value ?? 20,
          currency: 'USD',
          max_uses: capturedBody.max_uses ?? 100,
          current_uses: 15,
          is_single_use: false,
          is_active: capturedBody.is_active ?? true,
          expires_at: capturedBody.expires_at ?? null,
          created_at: '2026-04-10T12:40:00Z',
        });
      }),
    );

    const response = await growthApi.updatePromo('promo_004', {
      discount_value: 30,
      max_uses: 250,
      expires_at: '2026-07-01T00:00:00Z',
      description: 'Extended campaign',
      is_active: true,
    });

    expect(response.status).toBe(200);
    expect(updatedId).toBe('promo_004');
    expect(capturedBody).toMatchObject({
      discount_value: 30,
      max_uses: 250,
      is_active: true,
    });
  });

  it('deactivates a promo code by id', async () => {
    let deactivatedId = '';

    server.use(
      http.delete(MATCH_ANY_API_ORIGIN.promoCodeById, ({ request }) => {
        deactivatedId = new URL(request.url).pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          id: deactivatedId,
          code: 'LEGACY10',
          discount_type: 'percent',
          discount_value: 10,
          currency: 'USD',
          max_uses: null,
          current_uses: 99,
          is_single_use: false,
          is_active: false,
          expires_at: null,
          created_at: '2026-04-10T13:00:00Z',
        });
      }),
    );

    const response = await growthApi.deactivatePromo('promo_005');

    expect(response.status).toBe(200);
    expect(deactivatedId).toBe('promo_005');
    expect(response.data.is_active).toBe(false);
  });
});

describe('growthApi invite and partner operations', () => {
  it('creates a batch of invite codes for a target user', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.inviteCodes, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json(
          [
            {
              id: 'invite_001',
              code: 'INVITE-AAA',
              free_days: 14,
              is_used: false,
              expires_at: '2026-05-10T00:00:00Z',
              created_at: '2026-04-10T13:30:00Z',
            },
            {
              id: 'invite_002',
              code: 'INVITE-BBB',
              free_days: 14,
              is_used: false,
              expires_at: '2026-05-10T00:00:00Z',
              created_at: '2026-04-10T13:30:00Z',
            },
          ],
          { status: 201 },
        );
      }),
    );

    const response = await growthApi.createInviteCodes({
      user_id: 'c6ef42b0-1cc0-4ea2-a3dd-c4f689dc0d50',
      free_days: 14,
      count: 2,
      plan_id: 'plan_001',
    });

    expect(response.status).toBe(201);
    expect(response.data).toHaveLength(2);
    expect(capturedBody).toMatchObject({
      free_days: 14,
      count: 2,
      plan_id: 'plan_001',
    });
  });

  it('promotes a mobile user to partner status', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.partnerPromote, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          status: 'promoted',
          user_id: capturedBody.user_id,
        });
      }),
    );

    const response = await growthApi.promotePartner({
      user_id: 'd57c2fb8-25f0-4411-9c17-045a7ab7bb10',
    });

    expect(response.status).toBe(200);
    expect(response.data).toMatchObject({
      status: 'promoted',
      user_id: 'd57c2fb8-25f0-4411-9c17-045a7ab7bb10',
    });
    expect(capturedBody).toMatchObject({
      user_id: 'd57c2fb8-25f0-4411-9c17-045a7ab7bb10',
    });
  });

  it('creates a partner workspace from the admin growth surface', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.partnerWorkspaces, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json(
          {
            id: 'workspace_001',
            account_key: 'nebula-partners',
            display_name: 'Nebula Partners',
            status: 'active',
            legacy_owner_user_id: null,
            created_by_admin_user_id: 'admin_001',
            code_count: 0,
            active_code_count: 0,
            total_clients: 0,
            total_earned: 0,
            last_activity_at: null,
            current_role_key: null,
            current_permission_keys: [],
            members: [],
          },
          { status: 201 },
        );
      }),
    );

    const response = await growthApi.createPartnerWorkspace({
      display_name: 'Nebula Partners',
      owner_admin_user_id: '0d2f4a94-72a2-4b84-91f9-f7814d11b201',
    });

    expect(response.status).toBe(201);
    expect(response.data.account_key).toBe('nebula-partners');
    expect(capturedBody).toMatchObject({
      display_name: 'Nebula Partners',
      owner_admin_user_id: '0d2f4a94-72a2-4b84-91f9-f7814d11b201',
    });
  });

  it('loads a single partner workspace detail', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.partnerWorkspaceDetail, ({ request }) => {
        const workspaceId = new URL(request.url).pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          id: workspaceId,
          account_key: 'aurora-ops',
          display_name: 'Aurora Ops',
          status: 'active',
          legacy_owner_user_id: null,
          created_by_admin_user_id: 'admin_001',
          code_count: 4,
          active_code_count: 3,
          total_clients: 28,
          total_earned: 1240.5,
          last_activity_at: '2026-04-17T18:45:00Z',
          current_role_key: null,
          current_permission_keys: [],
          members: [
            {
              id: 'membership_001',
              admin_user_id: 'admin_partner_001',
              role_id: 'role_owner',
              role_key: 'owner',
              role_display_name: 'Owner',
              membership_status: 'active',
              permission_keys: ['workspace_read', 'membership_write'],
              invited_by_admin_user_id: 'admin_001',
              created_at: '2026-04-17T18:00:00Z',
              updated_at: '2026-04-17T18:00:00Z',
            },
          ],
        });
      }),
    );

    const response = await growthApi.getPartnerWorkspace('workspace_002');

    expect(response.status).toBe(200);
    expect(response.data.id).toBe('workspace_002');
    expect(response.data.members[0]?.role_key).toBe('owner');
    expect(response.data.total_clients).toBe(28);
  });

  it('loads referral overview metrics for admin analytics', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.referralOverview, () =>
        HttpResponse.json({
          total_commissions: 42,
          total_earned: 1350.5,
          unique_referrers: 12,
          unique_referred_users: 31,
          recent_commissions: [],
          top_referrers: [],
        }),
      ),
    );

    const response = await growthApi.getReferralOverview();

    expect(response.status).toBe(200);
    expect(response.data.total_commissions).toBe(42);
    expect(response.data.unique_referrers).toBe(12);
  });

  it('loads referral detail for a specific mobile user', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.referralUserDetail, ({ request }) => {
        const userId = new URL(request.url).pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          user: {
            id: userId,
            email: 'referrer@example.com',
            username: 'referrer',
            telegram_username: 'referrer_tg',
            referral_code: 'REF-001',
            is_partner: false,
          },
          referred_by_user_id: null,
          commission_count: 3,
          referred_users: 2,
          total_earned: 18.75,
          recent_commissions: [],
        });
      }),
    );

    const response = await growthApi.getReferralUserDetail('d57c2fb8-25f0-4411-9c17-045a7ab7bb10');

    expect(response.status).toBe(200);
    expect(response.data.user.email).toBe('referrer@example.com');
    expect(response.data.commission_count).toBe(3);
  });

  it('lists partners from the admin directory', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.partners, () =>
        HttpResponse.json({
          items: [
            {
              user: {
                id: '6bf366e0-5c78-4472-b0f2-3f1f577d1122',
                email: 'partner@example.com',
                username: 'partner',
                telegram_username: 'partner_tg',
                referral_code: 'PARTNER-01',
                is_partner: true,
              },
              promoted_at: '2026-04-10T13:00:00Z',
              code_count: 4,
              active_code_count: 3,
              total_clients: 7,
              total_earned: 250.25,
              last_activity_at: '2026-04-10T14:00:00Z',
            },
          ],
          total: 1,
          offset: 0,
          limit: 50,
        }),
      ),
    );

    const response = await growthApi.listPartners({ offset: 0, limit: 50 });

    expect(response.status).toBe(200);
    expect(response.data.total).toBe(1);
    expect(response.data.items[0]?.user.email).toBe('partner@example.com');
  });

  it('loads partner drill-down data with codes and recent earnings', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.partnerDetail, ({ request }) => {
        const userId = new URL(request.url).pathname.split('/').at(-1) ?? '';

        return HttpResponse.json({
          user: {
            id: userId,
            email: 'partner@example.com',
            username: 'partner',
            telegram_username: 'partner_tg',
            referral_code: 'PARTNER-01',
            is_partner: true,
          },
          promoted_at: '2026-04-10T13:00:00Z',
          code_count: 4,
          active_code_count: 3,
          total_clients: 7,
          total_earned: 250.25,
          last_activity_at: '2026-04-10T14:00:00Z',
          codes: [
            {
              id: '7c6bdb40-4b63-42dc-a59a-e8e8440abf2d',
              code: 'PARTNER-CODE',
              markup_pct: 15,
              is_active: true,
              created_at: '2026-04-10T13:00:00Z',
              updated_at: '2026-04-10T13:00:00Z',
            },
          ],
          recent_earnings: [],
        });
      }),
    );

    const response = await growthApi.getPartnerDetail('6bf366e0-5c78-4472-b0f2-3f1f577d1122');

    expect(response.status).toBe(200);
    expect(response.data.codes[0]?.code).toBe('PARTNER-CODE');
    expect(response.data.total_earned).toBe(250.25);
  });
});
