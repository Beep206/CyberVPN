-- Seed the Stage 1 Remnawave Mihomo template override for hidden RU plans.
--
-- Usage:
--   psql "$REMNAWAVE_DATABASE_URL" -f scripts/remnawave/seed-stage1-ru-bundle.sql
--
-- The external squad UUID returned by the final SELECT must be configured as:
--   REMNAWAVE_RU_BUNDLE_EXTERNAL_SQUAD_UUID=<external_squad_uuid>

begin;

with default_mihomo as (
    select template_yaml
    from subscription_templates
    where template_type = 'MIHOMO'
      and name = 'Default'
    limit 1
),
template_upsert as (
    insert into subscription_templates (
        template_type,
        name,
        template_yaml,
        template_json,
        view_position
    )
    select
        'MIHOMO',
        'Mihomo (RU bundle)',
        '# CyberVPN S1 Mihomo RU bundle' || chr(10)
            || replace(template_yaml, '→ Remnawave', 'CyberVPN RU'),
        null,
        101
    from default_mihomo
    on conflict (template_type, name) do update
    set template_yaml = excluded.template_yaml,
        updated_at = now()
    returning uuid
),
template_row as (
    select uuid from template_upsert
    union all
    select uuid
    from subscription_templates
    where template_type = 'MIHOMO'
      and name = 'Mihomo (RU bundle)'
    limit 1
),
squad_upsert as (
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
        'S1_RU_BUNDLE',
        '{}'::jsonb,
        '{}'::jsonb,
        '{}'::jsonb,
        '{}'::jsonb,
        '{"purpose":"Stage 1 hidden RU plans; Mihomo template override only"}'::jsonb,
        101
    )
    on conflict (name) do update
    set updated_at = now(),
        custom_remarks = excluded.custom_remarks
    returning uuid
),
squad_row as (
    select uuid from squad_upsert
    union all
    select uuid from external_squads where name = 'S1_RU_BUNDLE'
    limit 1
)
insert into external_squads_templates (
    external_squad_uuid,
    template_uuid,
    template_type
)
select squad_row.uuid, template_row.uuid, 'MIHOMO'
from squad_row, template_row
on conflict (external_squad_uuid, template_type) do update
set template_uuid = excluded.template_uuid;

commit;

select
    external_squads.uuid as external_squad_uuid,
    external_squads.name as external_squad_name,
    subscription_templates.name as template_name,
    external_squads_templates.template_type
from external_squads
join external_squads_templates
  on external_squads_templates.external_squad_uuid = external_squads.uuid
join subscription_templates
  on subscription_templates.uuid = external_squads_templates.template_uuid
where external_squads.name = 'S1_RU_BUNDLE'
  and external_squads_templates.template_type = 'MIHOMO';
