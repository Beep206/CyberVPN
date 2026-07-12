-- Idempotently replace the legacy Smart RU onboarding code and add Task2.
-- Preconditions:
--   * Alembic head includes 20260711_plan_code_len.
--   * pricing catalog contains both target plan codes.
--   * the legacy invite still exists as the reviewed policy template.
-- Run against the CyberVPN backend database with psql -v ON_ERROR_STOP=1 and
-- provide legacy_invite_code, task1_invite_code and task2_invite_code through
-- the approved operator secret channel. The script never prints their values.

\if :{?legacy_invite_code}
\else
\echo 'missing required psql variable: legacy_invite_code'
\quit 3
\endif
\if :{?task1_invite_code}
\else
\echo 'missing required psql variable: task1_invite_code'
\quit 3
\endif
\if :{?task2_invite_code}
\else
\echo 'missing required psql variable: task2_invite_code'
\quit 3
\endif

begin;

select set_config('cybervpn.rollout.legacy_invite_code', :'legacy_invite_code', true) is not null
    as legacy_invite_configured;
select set_config('cybervpn.rollout.task1_invite_code', :'task1_invite_code', true) is not null
    as task1_invite_configured;
select set_config('cybervpn.rollout.task2_invite_code', :'task2_invite_code', true) is not null
    as task2_invite_configured;

select pg_advisory_xact_lock(hashtextextended('cybervpn:dual-product-invites:20260711', 0));

do $cybervpn_dual_product_invites$
declare
    v_template invite_codes%rowtype;
    v_plan subscription_plans%rowtype;
    v_existing invite_codes%rowtype;
    v_target record;
    v_new_id uuid;
    v_payload jsonb;
    v_legacy_code text := current_setting('cybervpn.rollout.legacy_invite_code');
    v_task1_code text := current_setting('cybervpn.rollout.task1_invite_code');
    v_task2_code text := current_setting('cybervpn.rollout.task2_invite_code');
begin
    select *
    into v_template
    from invite_codes
    where code = v_legacy_code
    for update;

    if not found then
        raise exception 'Legacy invite is missing; reviewed policy template unavailable';
    end if;

    if v_template.usage_mode <> 'multi_use'
       or v_template.grant_duration_mode <> 'lifetime'
       or v_template.grant_device_limit_override <> 5
       or v_template.per_user_redemption_cap <> 1 then
        raise exception 'Legacy invite no longer matches the reviewed rollout policy';
    end if;

    for v_target in
        select *
        from (values
            (v_task1_code, 'premium_smart_ru'::text),
            (v_task2_code, 'premium_spb_de_exceptions'::text)
        ) as targets(code, plan_code)
    loop
        select *
        into v_plan
        from subscription_plans
        where plan_code = v_target.plan_code
          and is_active = true
        order by updated_at desc, id
        limit 1;

        if not found then
            raise exception 'Active subscription plan % is missing', v_target.plan_code;
        end if;

        select *
        into v_existing
        from invite_codes
        where code = v_target.code
        for update;

        if found then
            if coalesce(v_existing.grant_plan_id, v_existing.plan_id) <> v_plan.id
               or v_existing.usage_mode <> 'multi_use'
               or v_existing.grant_duration_mode <> 'lifetime'
               or v_existing.grant_device_limit_override <> 5
               or v_existing.per_user_redemption_cap <> 1 then
                raise exception 'Existing invite for plan % conflicts with the reviewed rollout contract', v_target.plan_code;
            end if;

            update invite_codes
            set status = 'active',
                revoked_at = null,
                revoked_by_admin_id = null,
                revoked_reason = null,
                expires_at = null
            where id = v_existing.id;
            continue;
        end if;

        v_new_id := gen_random_uuid();
        v_payload := to_jsonb(v_template) || jsonb_build_object(
            'id', v_new_id,
            'code', v_target.code,
            'owner_user_id', null,
            'free_days', 0,
            'plan_id', v_plan.id,
            'batch_id', null,
            'campaign_id', null,
            'campaign_version_id', null,
            'root_invite_code_id', v_new_id,
            'parent_invite_code_id', null,
            'source_redemption_id', null,
            'generation_depth', 0,
            'source_growth_code_id', null,
            'source_benefit_id', null,
            'status', 'active',
            'usage_mode', 'multi_use',
            'max_redemptions', 100000,
            'redeemed_count', 0,
            'active_redemptions_count', 0,
            'reversed_redemptions_count', 0,
            'first_redeemed_at', null,
            'last_redeemed_at', null,
            'exhausted_at', null,
            'per_user_redemption_cap', 1,
            'code_hash', null,
            'code_prefix', null,
            'entitlement_mode', 'plan_snapshot',
            'entitlement_profile_key', v_target.plan_code || '_lifetime_multi_root_20260711_v1',
            'entitlement_snapshot', '{}'::jsonb,
            'grant_mode', 'plan_snapshot',
            'grant_plan_id', v_plan.id,
            'grant_duration_mode', 'lifetime',
            'grant_duration_days', null,
            'grant_device_limit_override', 5,
            'grant_snapshot', '{}'::jsonb,
            'child_grant_plan_id', v_plan.id,
            'child_grant_duration_mode', 'lifetime',
            'child_grant_duration_days', null,
            'child_grant_device_limit_override', 5,
            'child_invite_expiry_mode', 'none'
        ) || jsonb_build_object(
            'child_policy', coalesce(v_template.child_policy, '{}'::jsonb) || jsonb_build_object(
                'grant_plan_id', v_plan.id,
                'grant_plan_code', v_target.plan_code,
                'grant_snapshot', '{}'::jsonb,
                'grant_duration_mode', 'lifetime',
                'grant_duration_days', null,
                'grant_device_limit_override', 5
            ),
            'issue_policy', coalesce(v_template.issue_policy, '{}'::jsonb) || jsonb_build_object(
                'source', 'dual_product_rollout',
                'rollout', '20260711'
            ),
            'source', 'root_campaign',
            'source_payment_id', null,
            'is_used', false,
            'used_by_user_id', null,
            'used_at', null,
            'revoked_at', null,
            'revoked_by_admin_id', null,
            'revoked_reason', null,
            'expires_at', null,
            'created_at', now()
        );

        insert into invite_codes
        select (jsonb_populate_record(null::invite_codes, v_payload)).*;
    end loop;

    update invite_codes
    set status = 'revoked',
        revoked_at = coalesce(revoked_at, now()),
        revoked_reason = 'Superseded by the Task1 replacement invite in the 2026-07-11 dual-product rollout'
    where code = v_legacy_code;
end
$cybervpn_dual_product_invites$;

do $cybervpn_dual_product_invites_validation$
declare
    v_valid integer;
    v_legacy_code text := current_setting('cybervpn.rollout.legacy_invite_code');
    v_task1_code text := current_setting('cybervpn.rollout.task1_invite_code');
    v_task2_code text := current_setting('cybervpn.rollout.task2_invite_code');
begin
    select count(*)
    into v_valid
    from invite_codes i
    join subscription_plans p on p.id = coalesce(i.grant_plan_id, i.plan_id)
    where (i.code, p.plan_code) in (
        (v_task1_code, 'premium_smart_ru'),
        (v_task2_code, 'premium_spb_de_exceptions')
    )
      and i.status = 'active'
      and i.usage_mode = 'multi_use'
      and i.max_redemptions = 100000
      and i.per_user_redemption_cap = 1
      and i.grant_duration_mode = 'lifetime'
      and i.grant_duration_days is null
      and i.grant_device_limit_override = 5
      and i.expires_at is null
      and coalesce((i.redemption_policy->>'block_self_redemption')::boolean, false)
      and coalesce((i.redemption_policy->>'require_no_active_access')::boolean, false);

    if v_valid <> 2 then
        raise exception 'Dual-product invite validation expected 2 valid target codes, found %', v_valid;
    end if;

    if not exists (
        select 1 from invite_codes
        where code = v_legacy_code
          and status = 'revoked'
          and revoked_at is not null
    ) then
        raise exception 'Legacy invite was not revoked';
    end if;
end
$cybervpn_dual_product_invites_validation$;

commit;

select case
           when i.code = :'legacy_invite_code' then 'legacy'
           when i.code = :'task1_invite_code' then 'task1'
           when i.code = :'task2_invite_code' then 'task2'
       end as invite_role,
       i.status, p.plan_code, i.usage_mode, i.max_redemptions,
       i.per_user_redemption_cap, i.grant_duration_mode,
       i.grant_device_limit_override, i.redeemed_count
from invite_codes i
left join subscription_plans p on p.id = coalesce(i.grant_plan_id, i.plan_id)
where i.code in (:'legacy_invite_code', :'task1_invite_code', :'task2_invite_code')
order by invite_role;
