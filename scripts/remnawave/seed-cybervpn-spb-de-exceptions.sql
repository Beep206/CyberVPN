-- Seed CyberVPN Premium SPB + DE Exceptions Remnawave metadata.
--
-- Usage:
--   psql "$REMNAWAVE_DATABASE_URL" -f scripts/remnawave/seed-cybervpn-spb-de-exceptions.sql
--
-- This seed intentionally does not create bridge credentials, public bridge
-- Hosts, or backend plan wiring. The Task2 operator creates/reuses the
-- dedicated bridge service user and Config Profiles from validated artifacts.

begin;

with template_upsert as (
    insert into subscription_templates (
        template_type,
        name,
        template_yaml,
        template_json,
        view_position
    )
    values (
        'MIHOMO',
        'CyberVPN Premium SPB DE Exceptions',
        $cybervpn_spb_de_exceptions_yaml$
remnawave:
  includeHiddenHosts: false

mixed-port: 7890
allow-lan: false
bind-address: 127.0.0.1
mode: rule
log-level: info
ipv6: false

proxy-groups:
  - name: SPB Default
    type: select
    remnawave:
      include-proxies: true

rules:
  - MATCH,SPB Default
$cybervpn_spb_de_exceptions_yaml$,
        null,
        242
    )
    on conflict (template_type, name) do update
    set template_yaml = excluded.template_yaml,
        template_json = null,
        view_position = excluded.view_position,
        updated_at = now()
    returning uuid
),
template_row as (
    select uuid from template_upsert
    union all
    select uuid
    from subscription_templates
    where template_type = 'MIHOMO'
      and name = 'CyberVPN Premium SPB DE Exceptions'
    limit 1
),
external_squad_upsert as (
    insert into external_squads (
        name,
        subscription_settings,
        host_overrides,
        response_headers,
        hwid_settings,
        custom_remarks,
        view_position
    )
    values (
        'CYBERVPN_SPB_DE_EXCEPTIONS',
        '{
          "profileTitle": "CyberVPN Premium SPB DE Exceptions",
          "supportLink": "https://cyber-vpn.org/support",
          "profileUpdateInterval": 24,
          "isProfileWebpageUrlEnabled": true,
          "happAnnounce": "CyberVPN Premium SPB + DE Exceptions: SPB default, Antifilter exceptions through DE. Torrent prohibited."
        }'::jsonb,
        '{}'::jsonb,
        '{
          "x-cybervpn-plan": "premium_spb_de_exceptions",
          "x-cybervpn-routing": "spb-default-de-exceptions",
          "x-cybervpn-policy-version": "task2-repo-foundation-v1",
          "x-cybervpn-unlimited": "true"
        }'::jsonb,
        '{}'::jsonb,
        '{"purpose":"Premium SPB default profile metadata; DE exceptions are enforced server-side on SPB"}'::jsonb,
        242
    )
    on conflict (name) do update
    set updated_at = now(),
        subscription_settings = excluded.subscription_settings,
        response_headers = excluded.response_headers,
        custom_remarks = excluded.custom_remarks,
        view_position = excluded.view_position
    returning uuid
),
external_squad_row as (
    select uuid from external_squad_upsert
    union all
    select uuid from external_squads
    where name = 'CYBERVPN_SPB_DE_EXCEPTIONS'
    limit 1
),
external_template_link as (
    insert into external_squads_templates (
        external_squad_uuid,
        template_uuid,
        template_type
    )
    select external_squad_row.uuid, template_row.uuid, 'MIHOMO'
    from external_squad_row, template_row
    on conflict (external_squad_uuid, template_type) do update
    set template_uuid = excluded.template_uuid
    returning external_squad_uuid
),
customer_squad_upsert as (
    insert into internal_squads (
        name,
        view_position
    )
    values (
        'CYBERVPN_SPB_DE_NODES',
        242
    )
    on conflict (name) do update
    set updated_at = now(),
        view_position = excluded.view_position
    returning uuid
),
bridge_squad_upsert as (
    insert into internal_squads (
        name,
        view_position
    )
    values (
        'CYBERVPN_SPB_DE_BRIDGE',
        243
    )
    on conflict (name) do update
    set updated_at = now(),
        view_position = excluded.view_position
    returning uuid
),
customer_squad_row as (
    select uuid from customer_squad_upsert
    union all
    select uuid from internal_squads
    where name = 'CYBERVPN_SPB_DE_NODES'
    limit 1
),
bridge_squad_row as (
    select uuid from bridge_squad_upsert
    union all
    select uuid from internal_squads
    where name = 'CYBERVPN_SPB_DE_BRIDGE'
    limit 1
),
bridge_inbound_customer_cleanup as (
    delete from internal_squad_inbounds
    using customer_squad_row, config_profile_inbounds
    where internal_squad_inbounds.internal_squad_uuid = customer_squad_row.uuid
      and internal_squad_inbounds.inbound_uuid = config_profile_inbounds.uuid
      and config_profile_inbounds.tag = 'DE_SPB_EXCEPTIONS_BRIDGE_9444'
    returning internal_squad_inbounds.inbound_uuid
)
select
    (select uuid from external_squad_row) as external_squad_uuid,
    (select uuid from customer_squad_row) as customer_internal_squad_uuid,
    (select uuid from bridge_squad_row) as bridge_internal_squad_uuid,
    (select count(*) from bridge_inbound_customer_cleanup) as removed_customer_bridge_inbounds,
    (select count(*) from external_template_link) as linked_templates;

do $cybervpn_spb_de_exceptions_validation$
declare
    v_external_squad_uuid uuid;
    v_customer_squad_uuid uuid;
    v_bridge_squad_uuid uuid;
    v_template_uuid uuid;
    v_template_link_count integer;
    v_template_direct_choice_count integer;
    v_customer_bridge_inbound_count integer;
begin
    select uuid
    into v_external_squad_uuid
    from external_squads
    where name = 'CYBERVPN_SPB_DE_EXCEPTIONS';

    select uuid
    into v_customer_squad_uuid
    from internal_squads
    where name = 'CYBERVPN_SPB_DE_NODES';

    select uuid
    into v_bridge_squad_uuid
    from internal_squads
    where name = 'CYBERVPN_SPB_DE_BRIDGE';

    select uuid
    into v_template_uuid
    from subscription_templates
    where template_type = 'MIHOMO'
      and name = 'CyberVPN Premium SPB DE Exceptions';

    if v_external_squad_uuid is null then
        raise exception 'CYBERVPN_SPB_DE_EXCEPTIONS external squad was not created';
    end if;
    if v_customer_squad_uuid is null then
        raise exception 'CYBERVPN_SPB_DE_NODES internal squad was not created';
    end if;
    if v_bridge_squad_uuid is null then
        raise exception 'CYBERVPN_SPB_DE_BRIDGE internal squad was not created';
    end if;
    if v_template_uuid is null then
        raise exception 'CyberVPN Premium SPB DE Exceptions MIHOMO template was not created';
    end if;

    select count(*)
    into v_template_link_count
    from external_squads_templates
    where external_squad_uuid = v_external_squad_uuid
      and template_uuid = v_template_uuid
      and template_type = 'MIHOMO';
    if v_template_link_count <> 1 then
        raise exception 'CyberVPN Premium SPB DE Exceptions template link count is %', v_template_link_count;
    end if;

    select count(*)
    into v_template_direct_choice_count
    from subscription_templates
    where uuid = v_template_uuid
      and template_yaml ~ '(?m)^\s*-\s*DIRECT\s*$';
    if v_template_direct_choice_count <> 0 then
        raise exception 'Task2 MIHOMO customer template must not expose DIRECT as a proxy choice';
    end if;

    select count(*)
    into v_customer_bridge_inbound_count
    from internal_squad_inbounds
    join config_profile_inbounds
      on config_profile_inbounds.uuid = internal_squad_inbounds.inbound_uuid
    where internal_squad_inbounds.internal_squad_uuid = v_customer_squad_uuid
      and config_profile_inbounds.tag = 'DE_SPB_EXCEPTIONS_BRIDGE_9444';
    if v_customer_bridge_inbound_count <> 0 then
        raise exception 'Task2 customer squad must not contain the DE bridge inbound';
    end if;
end
$cybervpn_spb_de_exceptions_validation$;

commit;

select
    external_squads.uuid as external_squad_uuid,
    external_squads.name as external_squad_name,
    customer_squads.uuid as customer_internal_squad_uuid,
    customer_squads.name as customer_internal_squad_name,
    bridge_squads.uuid as bridge_internal_squad_uuid,
    bridge_squads.name as bridge_internal_squad_name,
    subscription_templates.uuid as template_uuid,
    subscription_templates.name as template_name
from external_squads
join external_squads_templates
  on external_squads_templates.external_squad_uuid = external_squads.uuid
join subscription_templates
  on subscription_templates.uuid = external_squads_templates.template_uuid
cross join internal_squads as customer_squads
cross join internal_squads as bridge_squads
where external_squads.name = 'CYBERVPN_SPB_DE_EXCEPTIONS'
  and subscription_templates.name = 'CyberVPN Premium SPB DE Exceptions'
  and customer_squads.name = 'CYBERVPN_SPB_DE_NODES'
  and bridge_squads.name = 'CYBERVPN_SPB_DE_BRIDGE';
