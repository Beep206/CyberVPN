-- Seed CyberVPN Premium Smart RU Remnawave Mihomo template, squads, and abuse plugin.
--
-- Usage: run run-premium-smart-ru-seeds.py on the PostgreSQL host/container.
-- The wrapper supplies a private random stage directory and trusted SHA-256
-- values directly through psql variables; this file intentionally has no /tmp
-- artifact fallback.
--
-- Configure backend with the returned external_squad_uuid:
--   REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID=<external_squad_uuid>
--
-- XRAY_BASE64 clients such as INCY require server-side Smart RU routing. After
-- this base seed, run apply-premium-smart-ru-server-routing.py with the
-- production source subscription URL supplied through its environment.

\set ON_ERROR_STOP on

do $premium_smart_ru_inbound_validation$
declare
    v_raw record;
    v_raw_count integer;
    v_raw_server_names_count integer;
    v_raw_short_ids_count integer;
    v_raw_reality_target text;
    v_raw_dest_override jsonb;
    v_xhttp record;
    v_xhttp_count integer;
    v_invalid_reality_min_client_ver_tags text[];
begin
    select array_agg(tag order by tag)
    into v_invalid_reality_min_client_ver_tags
    from config_profile_inbounds
    where tag in (
        'VLESS_REALITY_443',
        'VLESS_XHTTP_REALITY_8443',
        'DE_SMART_REALITY_443',
        'DE_SMART_XHTTP_REALITY_8443',
        'MSK_SMART_REALITY_443',
        'MSK_SMART_XHTTP_REALITY_8443'
    )
      and raw_inbound #>> '{streamSettings,realitySettings,minClientVer}'
            is distinct from '26.3.27';

    if coalesce(cardinality(v_invalid_reality_min_client_ver_tags), 0) > 0 then
        raise exception
            'CyberVPN Reality inbounds must use minClientVer=26.3.27; invalid tags=%',
            v_invalid_reality_min_client_ver_tags;
    end if;

    select count(*)
    into v_raw_count
    from config_profile_inbounds
    where tag = 'VLESS_REALITY_443';

    if v_raw_count <> 1 then
        raise exception 'VLESS_REALITY_443 inbound must exist exactly once, found %', v_raw_count;
    end if;

    select *
    into v_raw
    from config_profile_inbounds
    where tag = 'VLESS_REALITY_443';

    if lower(coalesce(v_raw.type, '')) <> 'vless' then
        raise exception 'VLESS_REALITY_443 must use type=vless';
    end if;

    if lower(coalesce(v_raw.network, '')) not in ('raw', 'tcp') then
        raise exception 'VLESS_REALITY_443 must use raw/tcp network';
    end if;

    if lower(coalesce(v_raw.security, '')) <> 'reality' then
        raise exception 'VLESS_REALITY_443 must use reality security';
    end if;

    if v_raw.port <> 443 then
        raise exception 'VLESS_REALITY_443 must use port 443';
    end if;

    if lower(coalesce(v_raw.raw_inbound #>> '{settings,decryption}', '')) <> 'none' then
        raise exception 'VLESS_REALITY_443 must use decryption=none';
    end if;

    if coalesce(v_raw.raw_inbound #>> '{settings,flow}', '') <> 'xtls-rprx-vision' then
        raise exception 'VLESS_REALITY_443 must use settings.flow=xtls-rprx-vision';
    end if;

    if lower(coalesce(v_raw.raw_inbound #>> '{streamSettings,network}', '')) not in ('raw', 'tcp') then
        raise exception 'VLESS_REALITY_443 streamSettings.network must be raw/tcp';
    end if;

    if lower(coalesce(v_raw.raw_inbound #>> '{streamSettings,security}', '')) <> 'reality' then
        raise exception 'VLESS_REALITY_443 streamSettings.security must be reality';
    end if;

    select
        case
            when jsonb_typeof(v_raw.raw_inbound #> '{streamSettings,realitySettings,serverNames}') = 'array'
            then jsonb_array_length(v_raw.raw_inbound #> '{streamSettings,realitySettings,serverNames}')
            else 0
        end,
        case
            when jsonb_typeof(v_raw.raw_inbound #> '{streamSettings,realitySettings,shortIds}') = 'array'
            then jsonb_array_length(v_raw.raw_inbound #> '{streamSettings,realitySettings,shortIds}')
            else 0
        end,
        coalesce(
            nullif(v_raw.raw_inbound #>> '{streamSettings,realitySettings,target}', ''),
            nullif(v_raw.raw_inbound #>> '{streamSettings,realitySettings,dest}', '')
        ),
        coalesce(v_raw.raw_inbound #> '{sniffing,destOverride}', '[]'::jsonb)
    into
        v_raw_server_names_count,
        v_raw_short_ids_count,
        v_raw_reality_target,
        v_raw_dest_override;

    if v_raw_server_names_count = 0 then
        raise exception 'VLESS_REALITY_443 serverNames is empty';
    end if;

    if v_raw_short_ids_count = 0 then
        raise exception 'VLESS_REALITY_443 shortIds is empty';
    end if;

    if length(coalesce(v_raw.raw_inbound #>> '{streamSettings,realitySettings,privateKey}', '')) = 0 then
        raise exception 'VLESS_REALITY_443 privateKey is empty';
    end if;

    if coalesce(v_raw_reality_target, '') = '' then
        raise exception 'VLESS_REALITY_443 Reality target is empty';
    end if;

    if right(btrim(v_raw_reality_target), 4) <> ':443' then
        raise exception 'VLESS_REALITY_443 Reality target must end with :443';
    end if;

    if lower(coalesce(v_raw.raw_inbound #>> '{sniffing,enabled}', 'false')) <> 'true' then
        raise exception 'VLESS_REALITY_443 sniffing must be enabled';
    end if;

    if jsonb_typeof(v_raw_dest_override) <> 'array'
       or not (v_raw_dest_override ?& array['http', 'tls', 'quic']) then
        raise exception 'VLESS_REALITY_443 sniffing.destOverride must contain http, tls, and quic';
    end if;

    select count(*)
    into v_xhttp_count
    from config_profile_inbounds
    where tag = 'VLESS_XHTTP_REALITY_8443';

    if v_xhttp_count <> 1 then
        raise exception 'VLESS_XHTTP_REALITY_8443 inbound must exist exactly once, found %', v_xhttp_count;
    end if;

    select *
    into v_xhttp
    from config_profile_inbounds
    where tag = 'VLESS_XHTTP_REALITY_8443';

    if lower(coalesce(v_xhttp.type, '')) <> 'vless' then
        raise exception 'VLESS_XHTTP_REALITY_8443 must use type=vless';
    end if;

    if lower(coalesce(v_xhttp.network, '')) <> 'xhttp' then
        raise exception 'VLESS_XHTTP_REALITY_8443 must use network=xhttp';
    end if;

    if lower(coalesce(v_xhttp.security, '')) <> 'reality' then
        raise exception 'VLESS_XHTTP_REALITY_8443 must use reality security';
    end if;

    if v_xhttp.port <> 8443 then
        raise exception 'VLESS_XHTTP_REALITY_8443 must use port 8443';
    end if;
end
$premium_smart_ru_inbound_validation$;

begin;

create temporary table cybervpn_premium_smart_ru_artifact_contract (
    stage_dir text not null,
    stage_manifest_sha256 text not null,
    mihomo_sha256 text not null,
    incy_sha256 text not null,
    legacy_header_sha256 text not null,
    stage_manifest jsonb,
    mihomo_template text,
    legacy_header jsonb
) on commit drop;

insert into cybervpn_premium_smart_ru_artifact_contract (
    stage_dir,
    stage_manifest_sha256,
    mihomo_sha256,
    incy_sha256,
    legacy_header_sha256
)
values (
    :'cybervpn_premium_smart_ru_stage_dir',
    :'cybervpn_premium_smart_ru_stage_manifest_sha256',
    :'cybervpn_premium_smart_ru_mihomo_sha256',
    :'cybervpn_premium_smart_ru_incy_sha256',
    :'cybervpn_premium_smart_ru_legacy_header_sha256'
);

do $cybervpn_premium_smart_ru_mihomo_preflight$
declare
    v_contract cybervpn_premium_smart_ru_artifact_contract%rowtype;
    v_manifest_bytes bytea;
    v_template_bytes bytea;
    v_legacy_header_bytes bytea;
    v_template text;
    v_manifest jsonb;
    v_legacy_header jsonb;
    v_legacy_decoded jsonb;
    v_legacy_value text;
    v_expected_bytes bigint;
begin
    select * into strict v_contract
    from cybervpn_premium_smart_ru_artifact_contract;

    if v_contract.stage_dir !~ '^/[A-Za-z0-9._/-]+$'
       or v_contract.stage_dir ~ '(^|/)\.\.(/|$)'
       or v_contract.stage_dir ~ '^/(tmp|var/tmp)(/|$)'
       or v_contract.stage_manifest_sha256 !~ '^[0-9a-f]{64}$'
       or v_contract.mihomo_sha256 !~ '^[0-9a-f]{64}$'
       or v_contract.incy_sha256 !~ '^[0-9a-f]{64}$'
       or v_contract.legacy_header_sha256 !~ '^[0-9a-f]{64}$' then
        raise exception 'CyberVPN Premium Smart RU trusted artifact variables are invalid';
    end if;

    v_manifest_bytes := pg_read_binary_file(v_contract.stage_dir || '/manifest.json');
    v_template_bytes := pg_read_binary_file(v_contract.stage_dir || '/mihomo.yaml');
    v_legacy_header_bytes := pg_read_binary_file(
        v_contract.stage_dir || '/legacy-routing-header.json'
    );

    if encode(sha256(v_manifest_bytes), 'hex') <> v_contract.stage_manifest_sha256 then
        raise exception 'CyberVPN Premium Smart RU stage manifest SHA-256 mismatch';
    end if;
    if encode(sha256(v_template_bytes), 'hex') <> v_contract.mihomo_sha256 then
        raise exception 'CyberVPN Premium Smart RU Mihomo SHA-256 mismatch';
    end if;
    if encode(sha256(v_legacy_header_bytes), 'hex') <> v_contract.legacy_header_sha256 then
        raise exception 'CyberVPN Premium Smart RU legacy header SHA-256 mismatch';
    end if;

    v_template := convert_from(v_template_bytes, 'UTF8');
    v_manifest := convert_from(v_manifest_bytes, 'UTF8')::jsonb;
    v_legacy_header := convert_from(v_legacy_header_bytes, 'UTF8')::jsonb;

    if v_manifest->>'schemaVersion' is distinct from '1'
       or v_manifest->>'product' is distinct from 'premium_smart_ru'
       or v_manifest#>>'{validation,mihomoProtocolOnlyTorrentPolicy}' is distinct from 'true'
       or v_manifest#>>'{artifacts,mihomo.yaml,sha256}' is distinct from v_contract.mihomo_sha256
       or v_manifest#>>'{artifacts,incy-xray.json,sha256}' is distinct from v_contract.incy_sha256
       or v_manifest#>>'{artifacts,legacy-routing-header.json,sha256}'
            is distinct from v_contract.legacy_header_sha256 then
        raise exception 'CyberVPN Premium Smart RU stage manifest contract is invalid';
    end if;

    v_expected_bytes := (v_manifest#>>'{artifacts,mihomo.yaml,bytes}')::bigint;
    if v_expected_bytes is null
       or octet_length(v_template_bytes) <> v_expected_bytes
       or octet_length(v_legacy_header_bytes) is distinct from
            (v_manifest#>>'{artifacts,legacy-routing-header.json,bytes}')::bigint then
        raise exception 'CyberVPN Premium Smart RU Mihomo artifact size mismatch';
    end if;

    if position('MATCH,🌍 World / EU' in v_template) = 0
       or position('name: 🇷🇺 RU Sites' in v_template) = 0
       or position('name: 🌍 World / EU' in v_template) = 0
       or position('DOMAIN-SUFFIX,rutracker.org' in v_template) = 0
       or position('RULE-SET,catalog-access-inline,🌍 World / EU' in v_template) = 0
       or position('RULE-SET,catalog-access-inline,🌍 World / EU' in v_template)
            > position(',⛔ BLOCK' in v_template)
       or position('name: Torrents' in v_template) <> 0
       or position('name: 🧲 Torrents' in v_template) <> 0
       or position('torrent-websites' in v_template) <> 0
       or position('torrent-trackers' in v_template) <> 0
       or position('torrent-clients' in v_template) <> 0
       or position('DOMAIN-SUFFIX,nnmclub.to,REJECT' in v_template) <> 0
       or position('DOMAIN-SUFFIX,rutracker.org,REJECT' in v_template) <> 0
       or position('DOMAIN-SUFFIX,rutor.info,REJECT' in v_template) <> 0
       or position('DOMAIN-SUFFIX,kinozal.tv,REJECT' in v_template) <> 0
       or position('MATCH,DIRECT' in v_template) <> 0 then
        raise exception 'CyberVPN Premium Smart RU Mihomo artifact contract is invalid';
    end if;

    v_legacy_value := v_legacy_header->>'value';
    if v_legacy_header->>'schemaVersion' is distinct from '1'
       or v_legacy_header->>'product' is distinct from 'premium_smart_ru'
       or v_legacy_header->>'consumer' is distinct from 'remnawave-legacy-routing-header'
       or v_legacy_header->>'encoding' is distinct from 'base64-json'
       or coalesce(v_legacy_value, '') !~ '^[A-Za-z0-9+/]+={0,2}$'
       or length(v_legacy_value) % 4 <> 0 then
        raise exception 'CyberVPN Premium Smart RU legacy routing artifact is invalid';
    end if;

    v_legacy_decoded := convert_from(decode(v_legacy_value, 'base64'), 'UTF8')::jsonb;
    if v_legacy_header->'decoded' is distinct from v_legacy_decoded
       or v_legacy_decoded->>'Name' is distinct from 'CyberVPN Premium Smart RU'
       or v_legacy_decoded->>'GlobalProxy' is distinct from 'true'
       or v_legacy_decoded->>'DomainStrategy' is distinct from 'AsIs'
       or v_legacy_decoded->>'FakeDNS' is distinct from 'false'
       or v_legacy_decoded->>'RemoteDNSType' is distinct from 'DoH'
       or v_legacy_decoded->>'RemoteDNSDomain' is distinct from 'https://cloudflare-dns.com/dns-query'
       or v_legacy_decoded->>'RemoteDNSIP' is distinct from '1.1.1.1'
       or jsonb_typeof(v_legacy_decoded->'BlockSites') is distinct from 'array'
       or (v_legacy_decoded->'BlockSites' ?| array[
            'domain:1337x.to',
            'domain:eztv.re',
            'domain:kinozal.tv',
            'domain:limetorrents.lol',
            'domain:nnmclub.to',
            'domain:rutracker.org',
            'domain:rutor.info',
            'domain:thepiratebay.org',
            'domain:torrentdownload.info',
            'domain:torrentgalaxy.to',
            'domain:yts.mx'
       ])
       or not (v_legacy_decoded->'BlockSites' ? 'geosite:category-ads-all')
       or jsonb_typeof(v_legacy_decoded->'DirectIp') is distinct from 'array'
       or not (v_legacy_decoded->'DirectIp' ? '10.0.0.0/8') then
        raise exception 'CyberVPN Premium Smart RU legacy routing semantics are invalid';
    end if;

    update cybervpn_premium_smart_ru_artifact_contract
    set stage_manifest = v_manifest,
        mihomo_template = v_template,
        legacy_header = v_legacy_header;
end
$cybervpn_premium_smart_ru_mihomo_preflight$;

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
        'CyberVPN Premium Smart RU',
        (select mihomo_template from cybervpn_premium_smart_ru_artifact_contract),
        null,
        202
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
      and name = 'CyberVPN Premium Smart RU'
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
        'CYBERVPN_PREMIUM_SMART_RU',
        '{
          "profileTitle": "CyberVPN Premium Smart RU",
          "supportLink": "https://cyber-vpn.org/support",
          "profileUpdateInterval": 24,
          "isProfileWebpageUrlEnabled": true,
          "happAnnounce": "CyberVPN Premium Smart RU: DE 25G + RU 25G smart routing. RU-сервисы работают без отключения VPN. BitTorrent-протокол запрещён; сайты-каталоги не блокируются."
        }'::jsonb,
        '{}'::jsonb,
        jsonb_build_object(
            'routing', (
                select legacy_header->>'value'
                from cybervpn_premium_smart_ru_artifact_contract
            ),
            'x-cybervpn-plan', 'premium_smart_ru',
            'x-cybervpn-routing', 'de-primary-ru-smart',
            'x-cybervpn-unlimited', 'true'
        ),
        '{}'::jsonb,
        '{"purpose":"Premium Smart RU MIHOMO template override for DE/NL/RU smart-routing users"}'::jsonb,
        202
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
    select uuid from external_squads where name = 'CYBERVPN_PREMIUM_SMART_RU'
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
internal_squad_upsert as (
    insert into internal_squads (
        name,
        view_position
    )
    values (
        'CYBERVPN_PREMIUM_SMART_RU_NODES',
        202
    )
    on conflict (name) do update
    set updated_at = now(),
        view_position = excluded.view_position
    returning uuid
),
internal_squad_row as (
    select uuid from internal_squad_upsert
    union all
    select uuid from internal_squads where name = 'CYBERVPN_PREMIUM_SMART_RU_NODES'
    limit 1
),
customer_squad_bridge_cleanup as (
    delete from internal_squad_inbounds
    using internal_squad_row, config_profile_inbounds
    where internal_squad_inbounds.internal_squad_uuid = internal_squad_row.uuid
      and internal_squad_inbounds.inbound_uuid = config_profile_inbounds.uuid
      and config_profile_inbounds.tag in (
          'MSK_SMART_RU_BRIDGE_9443',
          'MSK_SMART_RU_BRIDGE_V2_9443',
          'DE_SMART_GLOBAL_BRIDGE_9443'
      )
    returning internal_squad_inbounds.inbound_uuid
),
smart_inbound_rows as (
    select uuid, tag, profile_uuid as config_profile_uuid
    from config_profile_inbounds
    where tag in (
        'VLESS_REALITY_443',
        'VLESS_XHTTP_REALITY_8443',
        'DE_SMART_REALITY_443',
        'DE_SMART_XHTTP_REALITY_8443',
        'MSK_SMART_REALITY_443',
        'MSK_SMART_XHTTP_REALITY_8443'
    )
),
internal_squad_inbound_links as (
    insert into internal_squad_inbounds (
        internal_squad_uuid,
        inbound_uuid
    )
    select internal_squad_row.uuid, smart_inbound_rows.uuid
    from internal_squad_row, smart_inbound_rows
    on conflict do nothing
    returning inbound_uuid
),
smart_node_names(name) as (
    values
        ('🇩🇪 DE Frankfurt 01 25G'),
        ('🇳🇱 NL Amsterdam 01 10G'),
        ('🇷🇺 RU Moscow 01 25G'),
        ('🇷🇺 RU SPB 01 25G')
),
smart_node_rows as (
    select nodes.uuid, nodes.name
    from nodes
    join smart_node_names on smart_node_names.name = nodes.name
),
stale_frankfurt_base_node_inbound_links as (
    delete from config_profile_inbounds_to_nodes
    using config_profile_inbounds, nodes
    where config_profile_inbounds_to_nodes.config_profile_inbound_uuid = config_profile_inbounds.uuid
      and config_profile_inbounds_to_nodes.node_uuid = nodes.uuid
      and nodes.name = '🇩🇪 DE Frankfurt 01 25G'
      and config_profile_inbounds.tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
      and exists (
          select 1
          from smart_inbound_rows de_smart_inbound
          where de_smart_inbound.tag = 'DE_SMART_REALITY_443'
      )
    returning config_profile_inbounds_to_nodes.node_uuid
),
stale_frankfurt_base_node_inbound_cleanup as (
    select count(*) as removed_count
    from stale_frankfurt_base_node_inbound_links
),
stale_moscow_base_node_inbound_links as (
    delete from config_profile_inbounds_to_nodes
    using config_profile_inbounds, nodes
    where config_profile_inbounds_to_nodes.config_profile_inbound_uuid = config_profile_inbounds.uuid
      and config_profile_inbounds_to_nodes.node_uuid = nodes.uuid
      and nodes.name = '🇷🇺 RU Moscow 01 25G'
      and config_profile_inbounds.tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
      and exists (
          select 1
          from smart_inbound_rows moscow_smart_inbound
          where moscow_smart_inbound.tag = 'MSK_SMART_REALITY_443'
      )
    returning config_profile_inbounds_to_nodes.node_uuid
),
stale_moscow_base_node_inbound_cleanup as (
    select count(*) as removed_count
    from stale_moscow_base_node_inbound_links
),
smart_node_inbound_links as (
    insert into config_profile_inbounds_to_nodes (
        config_profile_inbound_uuid,
        node_uuid
    )
    select smart_inbound_rows.uuid, smart_node_rows.uuid
    from smart_inbound_rows,
         smart_node_rows,
         stale_frankfurt_base_node_inbound_cleanup,
         stale_moscow_base_node_inbound_cleanup
    where (
            smart_node_rows.name = '🇩🇪 DE Frankfurt 01 25G'
        and (
                (
                    exists (
                        select 1
                        from smart_inbound_rows de_smart_inbound
                        where de_smart_inbound.tag = 'DE_SMART_REALITY_443'
                    )
                and smart_inbound_rows.tag in ('DE_SMART_REALITY_443', 'DE_SMART_XHTTP_REALITY_8443')
                )
             or (
                    not exists (
                        select 1
                        from smart_inbound_rows de_smart_inbound
                        where de_smart_inbound.tag = 'DE_SMART_REALITY_443'
                    )
                and smart_inbound_rows.tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
                )
        )
    )
       or (
            smart_node_rows.name = '🇷🇺 RU Moscow 01 25G'
        and (
                (
                    exists (
                        select 1
                        from smart_inbound_rows moscow_smart_inbound
                        where moscow_smart_inbound.tag = 'MSK_SMART_REALITY_443'
                    )
                and smart_inbound_rows.tag in ('MSK_SMART_REALITY_443', 'MSK_SMART_XHTTP_REALITY_8443')
                )
             or (
                    not exists (
                        select 1
                        from smart_inbound_rows moscow_smart_inbound
                        where moscow_smart_inbound.tag = 'MSK_SMART_REALITY_443'
                    )
                and smart_inbound_rows.tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
                )
        )
    )
       or (
            smart_node_rows.name not in ('🇩🇪 DE Frankfurt 01 25G', '🇷🇺 RU Moscow 01 25G')
        and smart_inbound_rows.tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
    )
    on conflict do nothing
    returning node_uuid, config_profile_inbound_uuid
),
raw_smart_host_specs(node_name, remark, address, port, path, inbound_tag, server_description, host_tag, view_position) as (
    values
        (
            '🇩🇪 DE Frankfurt 01 25G',
            '🇩🇪 DE Frankfurt 01 25G Reality 443',
            'de-relay.cyber-vpn.org',
            2053,
            null::text,
            'VLESS_REALITY_443',
            'Premium Smart RU DE',
            'PREMIUM_SMART_RU_DE_REALITY_443',
            210
        ),
        (
            '🇩🇪 DE Frankfurt 01 25G',
            '🇩🇪 DE Frankfurt 01 25G XHTTP Reality 8443',
            'de-relay.cyber-vpn.org',
            2083,
            '/s1-xhttp-9fec0898',
            'VLESS_XHTTP_REALITY_8443',
            'Premium Smart RU DE',
            'PREMIUM_SMART_RU_DE_XHTTP_REALITY_8443',
            211
        ),
        (
            '🇳🇱 NL Amsterdam 01 10G',
            '🇳🇱 NL Amsterdam 01 10G Reality 443',
            'nl-4.cyber-vpn.org',
            443,
            null::text,
            'VLESS_REALITY_443',
            'Premium Smart RU NL',
            'PREMIUM_SMART_RU_NL_REALITY_443',
            212
        ),
        (
            '🇳🇱 NL Amsterdam 01 10G',
            '🇳🇱 NL Amsterdam 01 10G XHTTP Reality 8443',
            'nl-4.cyber-vpn.org',
            8443,
            '/s1-xhttp-9fec0898',
            'VLESS_XHTTP_REALITY_8443',
            'Premium Smart RU NL',
            'PREMIUM_SMART_RU_NL_XHTTP_REALITY_8443',
            213
        ),
        (
            '🇷🇺 RU Moscow 01 25G',
            '🇷🇺 RU Moscow 01 25G Reality 443',
            'msk-relay.cyber-vpn.org',
            2053,
            null::text,
            'VLESS_REALITY_443',
            'Premium Smart RU Moscow',
            'PREMIUM_SMART_RU_MSK_REALITY_443',
            214
        ),
        (
            '🇷🇺 RU Moscow 01 25G',
            '🇷🇺 RU Moscow 01 25G XHTTP Reality 8443',
            'msk-relay.cyber-vpn.org',
            2083,
            '/s1-xhttp-9fec0898',
            'VLESS_XHTTP_REALITY_8443',
            'Premium Smart RU Moscow',
            'PREMIUM_SMART_RU_MSK_XHTTP_REALITY_8443',
            215
        ),
        (
            '🇷🇺 RU SPB 01 25G',
            '🇷🇺 RU SPB 01 25G Reality 443',
            'ru-spb-3.cyber-vpn.org',
            443,
            null::text,
            'VLESS_REALITY_443',
            'Premium Smart RU SPB',
            'PREMIUM_SMART_RU_SPB_REALITY_443',
            216
        ),
        (
            '🇷🇺 RU SPB 01 25G',
            '🇷🇺 RU SPB 01 25G XHTTP Reality 8443',
            'ru-spb-3.cyber-vpn.org',
            8443,
            '/s1-xhttp-9fec0898',
            'VLESS_XHTTP_REALITY_8443',
            'Premium Smart RU SPB',
            'PREMIUM_SMART_RU_SPB_XHTTP_REALITY_8443',
            217
        )
),
smart_host_specs as (
    select
        raw_smart_host_specs.node_name,
        raw_smart_host_specs.remark,
        raw_smart_host_specs.address,
        raw_smart_host_specs.port,
        raw_smart_host_specs.path,
        case
            when raw_smart_host_specs.node_name = '🇩🇪 DE Frankfurt 01 25G'
             and raw_smart_host_specs.inbound_tag = 'VLESS_REALITY_443'
             and exists (
                 select 1 from smart_inbound_rows where tag = 'DE_SMART_REALITY_443'
             )
            then 'DE_SMART_REALITY_443'
            when raw_smart_host_specs.node_name = '🇩🇪 DE Frankfurt 01 25G'
             and raw_smart_host_specs.inbound_tag = 'VLESS_XHTTP_REALITY_8443'
             and exists (
                 select 1 from smart_inbound_rows where tag = 'DE_SMART_XHTTP_REALITY_8443'
             )
            then 'DE_SMART_XHTTP_REALITY_8443'
            when raw_smart_host_specs.node_name = '🇷🇺 RU Moscow 01 25G'
             and raw_smart_host_specs.inbound_tag = 'VLESS_REALITY_443'
             and exists (
                 select 1 from smart_inbound_rows where tag = 'MSK_SMART_REALITY_443'
             )
            then 'MSK_SMART_REALITY_443'
            when raw_smart_host_specs.node_name = '🇷🇺 RU Moscow 01 25G'
             and raw_smart_host_specs.inbound_tag = 'VLESS_XHTTP_REALITY_8443'
             and exists (
                 select 1 from smart_inbound_rows where tag = 'MSK_SMART_XHTTP_REALITY_8443'
             )
            then 'MSK_SMART_XHTTP_REALITY_8443'
            else raw_smart_host_specs.inbound_tag
        end as inbound_tag,
        raw_smart_host_specs.server_description,
        raw_smart_host_specs.host_tag,
        raw_smart_host_specs.view_position
    from raw_smart_host_specs
),
smart_host_update as (
    update hosts
    set view_position = smart_host_specs.view_position,
        address = smart_host_specs.address,
        port = smart_host_specs.port,
        path = smart_host_specs.path,
        sni = null,
        host = null,
        alpn = null,
        fingerprint = 'chrome',
        is_disabled = false,
        security_layer = 'DEFAULT',
        xhttp_extra_params = null,
        config_profile_inbound_uuid = smart_inbound_rows.uuid,
        config_profile_uuid = smart_inbound_rows.config_profile_uuid,
        server_description = smart_host_specs.server_description,
        mux_params = null,
        sockopt_params = null,
        is_hidden = false,
        override_sni_from_address = false,
        mihomo_x25519 = false,
        shuffle_host = false,
        keep_sni_blank = false,
        exclude_from_subscription_types = array[]::text[],
        tags = array[smart_host_specs.host_tag]::text[]
    from smart_host_specs
    join smart_inbound_rows
      on smart_inbound_rows.tag = smart_host_specs.inbound_tag
    where hosts.remark = smart_host_specs.remark
    returning hosts.uuid, hosts.remark, hosts.address, hosts.port
),
smart_host_insert as (
    insert into hosts (
        view_position,
        remark,
        address,
        port,
        path,
        sni,
        host,
        alpn,
        fingerprint,
        is_disabled,
        security_layer,
        xhttp_extra_params,
        config_profile_inbound_uuid,
        config_profile_uuid,
        server_description,
        mux_params,
        sockopt_params,
        is_hidden,
        override_sni_from_address,
        mihomo_x25519,
        shuffle_host,
        keep_sni_blank,
        exclude_from_subscription_types,
        tags
    )
    select
        smart_host_specs.view_position,
        smart_host_specs.remark,
        smart_host_specs.address,
        smart_host_specs.port,
        smart_host_specs.path,
        null,
        null,
        null,
        'chrome',
        false,
        'DEFAULT',
        null,
        smart_inbound_rows.uuid,
        smart_inbound_rows.config_profile_uuid,
        smart_host_specs.server_description,
        null,
        null,
        false,
        false,
        false,
        false,
        false,
        array[]::text[],
        array[smart_host_specs.host_tag]::text[]
    from smart_host_specs
    join smart_inbound_rows
      on smart_inbound_rows.tag = smart_host_specs.inbound_tag
    where not exists (
        select 1
        from hosts
        where hosts.remark = smart_host_specs.remark
          and hosts.address = smart_host_specs.address
          and hosts.port = smart_host_specs.port
    )
    returning uuid, remark, address, port
),
smart_host_rows as (
    select distinct on (smart_host_specs.node_name, smart_host_specs.inbound_tag)
        smart_hosts.uuid,
        smart_host_specs.node_name,
        smart_host_specs.inbound_tag
    from smart_host_specs
    join (
        select uuid, remark, address, port
        from smart_host_update
        union all
        select uuid, remark, address, port
        from smart_host_insert
        union all
        select hosts.uuid, hosts.remark, hosts.address, hosts.port
        from hosts
        join smart_host_specs existing_specs
          on existing_specs.remark = hosts.remark
         and existing_specs.address = hosts.address
         and existing_specs.port = hosts.port
        where not exists (
            select 1
            from smart_host_update
            where smart_host_update.remark = hosts.remark
              and smart_host_update.address = hosts.address
              and smart_host_update.port = hosts.port
        )
          and not exists (
              select 1
              from smart_host_insert
              where smart_host_insert.remark = hosts.remark
                and smart_host_insert.address = hosts.address
                and smart_host_insert.port = hosts.port
          )
    ) as smart_hosts
      on smart_hosts.remark = smart_host_specs.remark
     and smart_hosts.address = smart_host_specs.address
     and smart_hosts.port = smart_host_specs.port
    order by smart_host_specs.node_name, smart_host_specs.inbound_tag, smart_hosts.uuid
),
smart_host_node_links as (
    insert into hosts_to_nodes (
        host_uuid,
        node_uuid
    )
    select smart_host_rows.uuid, smart_node_rows.uuid
    from smart_host_rows
    join smart_node_rows
      on smart_node_rows.name = smart_host_rows.node_name
    on conflict do nothing
    returning host_uuid, node_uuid
),
premium_host_exclusions as (
    insert into internal_squad_host_exclusions (
        squad_uuid,
        host_uuid
    )
    select internal_squad_row.uuid, hosts.uuid
    from internal_squad_row
    join hosts
      on hosts.config_profile_inbound_uuid in (
          select smart_inbound_rows.uuid
          from smart_inbound_rows
      )
    where not exists (
        select 1
        from unnest(coalesce(hosts.tags, array[]::text[])) as host_tags(tag)
        where host_tags.tag like 'PREMIUM\_SMART\_RU\_%' escape '\'
    )
      and not exists (
          select 1
          from internal_squad_host_exclusions existing_exclusion
          where existing_exclusion.squad_uuid = internal_squad_row.uuid
            and existing_exclusion.host_uuid = hosts.uuid
      )
    returning host_uuid
),
plugin_update as (
    update node_plugin
    set plugin_config = '{
          "ingressFilter": {"enabled": false, "blockedIps": []},
          "egressFilter": {"enabled": true, "blockedIps": ["ext:tor-exit-nodes", "ext:tor-relays"], "blockedPorts": [25, 465, 587]},
          "torrentBlocker": {"enabled": true, "ignoreLists": {"ip": [], "userId": []}, "blockDuration": 86400},
          "connectionDrop": {"enabled": false, "whitelistIps": []},
          "sharedLists": [
            {"name": "ext:tor-exit-nodes", "type": "ipList", "items": []},
            {"name": "ext:tor-relays", "type": "ipList", "items": []}
          ]
        }'::jsonb,
        view_position = 202,
        updated_at = now()
    where name = 'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION'
    returning uuid
),
plugin_upsert as (
    insert into node_plugin (
        name,
        plugin_config,
        view_position
    )
    select
        'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION',
        '{
          "ingressFilter": {"enabled": false, "blockedIps": []},
          "egressFilter": {"enabled": true, "blockedIps": ["ext:tor-exit-nodes", "ext:tor-relays"], "blockedPorts": [25, 465, 587]},
          "torrentBlocker": {"enabled": true, "ignoreLists": {"ip": [], "userId": []}, "blockDuration": 86400},
          "connectionDrop": {"enabled": false, "whitelistIps": []},
          "sharedLists": [
            {"name": "ext:tor-exit-nodes", "type": "ipList", "items": []},
            {"name": "ext:tor-relays", "type": "ipList", "items": []}
          ]
        }'::jsonb,
        202

    where not exists (select 1 from plugin_update)
      and not exists (
          select 1
          from node_plugin
          where name = 'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION'
      )
    returning uuid
),
plugin_row as (
    select uuid from plugin_update
    union all
    select uuid from plugin_upsert
    union all
    select uuid
    from node_plugin
    where name = 'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION'
    limit 1
),
smart_node_plugin_assignment as (
    update nodes
    set active_plugin_uuid = plugin_row.uuid,
        updated_at = now()
    from plugin_row
    where nodes.name in (select name from smart_node_names)
      and (
          nodes.active_plugin_uuid is null
          or nodes.active_plugin_uuid = plugin_row.uuid
      )
    returning nodes.uuid
)
select
    (select count(*) from customer_squad_bridge_cleanup) as removed_customer_bridge_inbounds,
    (select count(*) from internal_squad_inbound_links) as linked_internal_squad_inbounds,
    (select count(*) from smart_node_inbound_links) as linked_node_inbounds,
    (select count(*) from smart_host_rows) as smart_host_count,
    (select count(*) from smart_host_node_links) as linked_smart_hosts,
    (select count(*) from smart_node_plugin_assignment) as plugin_assigned_nodes;

do $cybervpn_premium_smart_ru_validation$
declare
    v_external_squad_uuid uuid;
    v_internal_squad_uuid uuid;
    v_plugin_uuid uuid;
    v_template_uuid uuid;
    v_template_link_count integer;
    v_inbound_count integer;
    v_internal_squad_inbound_count integer;
    v_customer_bridge_inbound_count integer;
    v_smart_node_count integer;
    v_linked_node_inbounds integer;
    v_stale_frankfurt_base_link_count integer;
    v_stale_moscow_base_link_count integer;
    v_smart_host_count integer;
    v_visible_premium_host_count integer;
    v_smart_host_link_count integer;
    v_unexcluded_non_smart_host_count integer;
    v_conflicting_active_plugin_count integer;
    v_plugin_assigned_node_count integer;
    v_conflicting_node_names text;
begin
    select uuid
    into v_external_squad_uuid
    from external_squads
    where name = 'CYBERVPN_PREMIUM_SMART_RU';

    select uuid
    into v_internal_squad_uuid
    from internal_squads
    where name = 'CYBERVPN_PREMIUM_SMART_RU_NODES';

    select uuid
    into v_plugin_uuid
    from node_plugin
    where name = 'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION';

    select uuid
    into v_template_uuid
    from subscription_templates
    where template_type = 'MIHOMO'
      and name = 'CyberVPN Premium Smart RU';

    if v_external_squad_uuid is null then
        raise exception 'CYBERVPN_PREMIUM_SMART_RU external squad was not created';
    end if;
    if v_internal_squad_uuid is null then
        raise exception 'CYBERVPN_PREMIUM_SMART_RU_NODES internal squad was not created';
    end if;
    if v_plugin_uuid is null then
        raise exception 'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION plugin was not created';
    end if;
    if not exists (
        select 1
        from node_plugin
        where uuid = v_plugin_uuid
          and plugin_config#>>'{torrentBlocker,enabled}' = 'true'
          and plugin_config#>'{torrentBlocker,ignoreLists,ip}' = '[]'::jsonb
          and plugin_config#>'{torrentBlocker,ignoreLists,userId}' = '[]'::jsonb
          and plugin_config#>>'{torrentBlocker,blockDuration}' = '86400'
    ) then
        raise exception 'CYBERVPN_PREMIUM_SMART_RU torrentBlocker plugin config is invalid';
    end if;
    if v_template_uuid is null then
        raise exception 'CyberVPN Premium Smart RU MIHOMO template was not created';
    end if;

    select count(*)
    into v_template_link_count
    from external_squads_templates
    where external_squad_uuid = v_external_squad_uuid
      and template_uuid = v_template_uuid
      and template_type = 'MIHOMO';
    if v_template_link_count <> 1 then
        raise exception 'CyberVPN Premium Smart RU MIHOMO template link is missing or duplicated: %', v_template_link_count;
    end if;

    select count(*)
    into v_inbound_count
    from config_profile_inbounds
    where tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443');
    if v_inbound_count < 2 then
        raise exception 'Expected at least 2 Smart RU inbounds, found %', v_inbound_count;
    end if;

    select count(*)
    into v_internal_squad_inbound_count
    from internal_squad_inbounds
    where internal_squad_uuid = v_internal_squad_uuid;
    if v_internal_squad_inbound_count < 2 then
        raise exception 'Expected Smart RU internal squad to contain at least 2 inbounds, found %',
            v_internal_squad_inbound_count;
    end if;

    select count(*)
    into v_customer_bridge_inbound_count
    from internal_squad_inbounds
    join config_profile_inbounds
      on config_profile_inbounds.uuid = internal_squad_inbounds.inbound_uuid
    where internal_squad_inbounds.internal_squad_uuid = v_internal_squad_uuid
      and config_profile_inbounds.tag in (
          'MSK_SMART_RU_BRIDGE_9443',
          'MSK_SMART_RU_BRIDGE_V2_9443',
          'DE_SMART_GLOBAL_BRIDGE_9443'
      );
    if v_customer_bridge_inbound_count <> 0 then
        raise exception 'Premium Smart RU customer squad must not contain the Moscow bridge inbound';
    end if;

    select count(*)
    into v_smart_node_count
    from nodes
    where name in (
        '🇩🇪 DE Frankfurt 01 25G',
        '🇳🇱 NL Amsterdam 01 10G',
        '🇷🇺 RU Moscow 01 25G',
        '🇷🇺 RU SPB 01 25G'
    );
    if v_smart_node_count <> 4 then
        raise exception 'Expected 4 Premium Smart RU nodes by exact Remnawave name, found %', v_smart_node_count;
    end if;

    select count(*)
    into v_linked_node_inbounds
    from config_profile_inbounds_to_nodes
    join config_profile_inbounds
      on config_profile_inbounds.uuid = config_profile_inbounds_to_nodes.config_profile_inbound_uuid
    join nodes
      on nodes.uuid = config_profile_inbounds_to_nodes.node_uuid
    where (
            (
                nodes.name = '🇩🇪 DE Frankfurt 01 25G'
            and (
                    (
                        exists (
                            select 1
                            from config_profile_inbounds de_smart_inbound
                            where de_smart_inbound.tag = 'DE_SMART_REALITY_443'
                        )
                    and config_profile_inbounds.tag in (
                        'DE_SMART_REALITY_443',
                        'DE_SMART_XHTTP_REALITY_8443'
                    )
                    )
                 or (
                        not exists (
                            select 1
                            from config_profile_inbounds de_smart_inbound
                            where de_smart_inbound.tag = 'DE_SMART_REALITY_443'
                        )
                    and config_profile_inbounds.tag in (
                        'VLESS_REALITY_443',
                        'VLESS_XHTTP_REALITY_8443'
                    )
                    )
            )
            )
         or (
                nodes.name = '🇷🇺 RU Moscow 01 25G'
            and (
                    (
                        exists (
                            select 1
                            from config_profile_inbounds moscow_smart_inbound
                            where moscow_smart_inbound.tag = 'MSK_SMART_REALITY_443'
                        )
                    and config_profile_inbounds.tag in (
                        'MSK_SMART_REALITY_443',
                        'MSK_SMART_XHTTP_REALITY_8443'
                    )
                    )
                 or (
                        not exists (
                            select 1
                            from config_profile_inbounds moscow_smart_inbound
                            where moscow_smart_inbound.tag = 'MSK_SMART_REALITY_443'
                        )
                    and config_profile_inbounds.tag in (
                        'VLESS_REALITY_443',
                        'VLESS_XHTTP_REALITY_8443'
                    )
                    )
            )
            )
         or (
                nodes.name not in ('🇩🇪 DE Frankfurt 01 25G', '🇷🇺 RU Moscow 01 25G')
            and config_profile_inbounds.tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
            )
    )
      and nodes.name in (
          '🇩🇪 DE Frankfurt 01 25G',
          '🇳🇱 NL Amsterdam 01 10G',
          '🇷🇺 RU Moscow 01 25G',
          '🇷🇺 RU SPB 01 25G'
      );
    if v_linked_node_inbounds <> 8 then
        raise exception 'Expected exactly 8 Smart RU node inbound links, found %', v_linked_node_inbounds;
    end if;

    select count(*)
    into v_stale_frankfurt_base_link_count
    from config_profile_inbounds_to_nodes
    join config_profile_inbounds
      on config_profile_inbounds.uuid = config_profile_inbounds_to_nodes.config_profile_inbound_uuid
    join nodes
      on nodes.uuid = config_profile_inbounds_to_nodes.node_uuid
    where nodes.name = '🇩🇪 DE Frankfurt 01 25G'
      and config_profile_inbounds.tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
      and exists (
          select 1
          from config_profile_inbounds de_smart_inbound
          where de_smart_inbound.tag = 'DE_SMART_REALITY_443'
      );
    if v_stale_frankfurt_base_link_count <> 0 then
        raise exception 'Expected no stale Frankfurt base inbound links after DE Smart routing, found %',
            v_stale_frankfurt_base_link_count;
    end if;

    select count(*)
    into v_stale_moscow_base_link_count
    from config_profile_inbounds_to_nodes
    join config_profile_inbounds
      on config_profile_inbounds.uuid = config_profile_inbounds_to_nodes.config_profile_inbound_uuid
    join nodes
      on nodes.uuid = config_profile_inbounds_to_nodes.node_uuid
    where nodes.name = '🇷🇺 RU Moscow 01 25G'
      and config_profile_inbounds.tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
      and exists (
          select 1
          from config_profile_inbounds moscow_smart_inbound
          where moscow_smart_inbound.tag = 'MSK_SMART_REALITY_443'
      );
    if v_stale_moscow_base_link_count <> 0 then
        raise exception 'Expected no stale Moscow base inbound links after Moscow Smart routing, found %',
            v_stale_moscow_base_link_count;
    end if;

    select count(*)
    into v_smart_host_count
    from hosts
    join config_profile_inbounds
      on config_profile_inbounds.uuid = hosts.config_profile_inbound_uuid
    where hosts.remark in (
        '🇩🇪 DE Frankfurt 01 25G Reality 443',
        '🇩🇪 DE Frankfurt 01 25G XHTTP Reality 8443',
        '🇳🇱 NL Amsterdam 01 10G Reality 443',
        '🇳🇱 NL Amsterdam 01 10G XHTTP Reality 8443',
        '🇷🇺 RU Moscow 01 25G Reality 443',
        '🇷🇺 RU Moscow 01 25G XHTTP Reality 8443',
        '🇷🇺 RU SPB 01 25G Reality 443',
        '🇷🇺 RU SPB 01 25G XHTTP Reality 8443'
    )
      and hosts.address in (
          'de-relay.cyber-vpn.org',
          'nl-4.cyber-vpn.org',
          'msk-relay.cyber-vpn.org',
          'ru-spb-3.cyber-vpn.org'
      )
      and hosts.is_disabled = false
      and config_profile_inbounds.tag in (
          'VLESS_REALITY_443',
           'VLESS_XHTTP_REALITY_8443',
           'DE_SMART_REALITY_443',
           'DE_SMART_XHTTP_REALITY_8443',
           'MSK_SMART_REALITY_443',
           'MSK_SMART_XHTTP_REALITY_8443'
       );
    if v_smart_host_count <> 8 then
        raise exception 'Expected 8 Premium Smart RU Remnawave hosts, found %', v_smart_host_count;
    end if;

    select count(*)
    into v_visible_premium_host_count
    from hosts
    where hosts.remark in (
        '🇩🇪 DE Frankfurt 01 25G Reality 443',
        '🇩🇪 DE Frankfurt 01 25G XHTTP Reality 8443',
        '🇳🇱 NL Amsterdam 01 10G Reality 443',
        '🇳🇱 NL Amsterdam 01 10G XHTTP Reality 8443',
        '🇷🇺 RU Moscow 01 25G Reality 443',
        '🇷🇺 RU Moscow 01 25G XHTTP Reality 8443',
        '🇷🇺 RU SPB 01 25G Reality 443',
        '🇷🇺 RU SPB 01 25G XHTTP Reality 8443'
    )
      and hosts.is_disabled = false
      and exists (
          select 1
          from unnest(coalesce(hosts.tags, array[]::text[])) as host_tags(tag)
          where host_tags.tag like 'PREMIUM\_SMART\_RU\_%' escape '\'
      )
      and exists (
          select 1
          from internal_squad_inbounds
          where internal_squad_inbounds.internal_squad_uuid = v_internal_squad_uuid
            and internal_squad_inbounds.inbound_uuid = hosts.config_profile_inbound_uuid
      )
      and not exists (
          select 1
          from internal_squad_host_exclusions
          where internal_squad_host_exclusions.squad_uuid = v_internal_squad_uuid
            and internal_squad_host_exclusions.host_uuid = hosts.uuid
      );
    if v_visible_premium_host_count <> 8 then
        raise exception 'Expected exactly 8 visible Premium Smart RU tagged hosts, found %',
            v_visible_premium_host_count;
    end if;

    select count(*)
    into v_smart_host_link_count
    from hosts
    join hosts_to_nodes
      on hosts_to_nodes.host_uuid = hosts.uuid
    join nodes
      on nodes.uuid = hosts_to_nodes.node_uuid
    where (
            nodes.name = '🇩🇪 DE Frankfurt 01 25G'
        and hosts.remark in ('🇩🇪 DE Frankfurt 01 25G Reality 443', '🇩🇪 DE Frankfurt 01 25G XHTTP Reality 8443')
    )
       or (
            nodes.name = '🇳🇱 NL Amsterdam 01 10G'
        and hosts.remark in ('🇳🇱 NL Amsterdam 01 10G Reality 443', '🇳🇱 NL Amsterdam 01 10G XHTTP Reality 8443')
    )
       or (
            nodes.name = '🇷🇺 RU Moscow 01 25G'
        and hosts.remark in ('🇷🇺 RU Moscow 01 25G Reality 443', '🇷🇺 RU Moscow 01 25G XHTTP Reality 8443')
    )
       or (
            nodes.name = '🇷🇺 RU SPB 01 25G'
        and hosts.remark in ('🇷🇺 RU SPB 01 25G Reality 443', '🇷🇺 RU SPB 01 25G XHTTP Reality 8443')
    );
    if v_smart_host_link_count <> 8 then
        raise exception 'Expected 8 Premium Smart RU host-to-node links, found %', v_smart_host_link_count;
    end if;

    select count(*)
    into v_unexcluded_non_smart_host_count
    from hosts
    join config_profile_inbounds
      on config_profile_inbounds.uuid = hosts.config_profile_inbound_uuid
    where config_profile_inbounds.tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
      and not exists (
          select 1
          from unnest(coalesce(hosts.tags, array[]::text[])) as host_tags(tag)
          where host_tags.tag like 'PREMIUM\_SMART\_RU\_%' escape '\'
      )
      and not exists (
          select 1
          from internal_squad_host_exclusions
          where internal_squad_host_exclusions.squad_uuid = v_internal_squad_uuid
            and internal_squad_host_exclusions.host_uuid = hosts.uuid
      );
    if v_unexcluded_non_smart_host_count > 0 then
        raise exception 'Expected Premium Smart RU squad to exclude non-Smart-RU shared inbound hosts, found % unexcluded',
            v_unexcluded_non_smart_host_count;
    end if;

    select count(*), string_agg(name, ', ' order by name)
    into v_conflicting_active_plugin_count, v_conflicting_node_names
    from nodes
    where name in (
        '🇩🇪 DE Frankfurt 01 25G',
        '🇳🇱 NL Amsterdam 01 10G',
        '🇷🇺 RU Moscow 01 25G',
        '🇷🇺 RU SPB 01 25G'
    )
      and active_plugin_uuid is not null
      and active_plugin_uuid <> v_plugin_uuid;
    if v_conflicting_active_plugin_count > 0 then
        raise exception 'Refusing to overwrite existing active plugin on Premium Smart RU nodes: %',
            v_conflicting_node_names;
    end if;

    select count(distinct nodes.uuid)
    into v_plugin_assigned_node_count
    from nodes
    where nodes.name in (
        '🇩🇪 DE Frankfurt 01 25G',
        '🇳🇱 NL Amsterdam 01 10G',
        '🇷🇺 RU Moscow 01 25G',
        '🇷🇺 RU SPB 01 25G'
    )
      and nodes.active_plugin_uuid = v_plugin_uuid;
    if v_plugin_assigned_node_count <> 4 then
        raise exception 'Expected plugin_assigned_node_count=4, found %', v_plugin_assigned_node_count;
    end if;
end
$cybervpn_premium_smart_ru_validation$;

commit;

select
    external_squads.uuid as external_squad_uuid,
    external_squads.name as external_squad_name,
    subscription_templates.uuid as template_uuid,
    subscription_templates.name as template_name,
    internal_squads.uuid as internal_squad_uuid,
    internal_squads.name as internal_squad_name,
    node_plugin.uuid as node_plugin_uuid,
    node_plugin.name as node_plugin_name,
    external_squads_templates.template_type,
    (
        select count(*)
        from internal_squad_inbounds
        where internal_squad_inbounds.internal_squad_uuid = internal_squads.uuid
    ) as internal_squad_inbound_count,
    (
        select count(*)
        from config_profile_inbounds_to_nodes
        join config_profile_inbounds
          on config_profile_inbounds.uuid = config_profile_inbounds_to_nodes.config_profile_inbound_uuid
        join nodes
          on nodes.uuid = config_profile_inbounds_to_nodes.node_uuid
        where (
                (
                    nodes.name = '🇩🇪 DE Frankfurt 01 25G'
                and (
                        (
                            exists (
                                select 1
                                from config_profile_inbounds de_smart_inbound
                                where de_smart_inbound.tag = 'DE_SMART_REALITY_443'
                            )
                        and config_profile_inbounds.tag in (
                            'DE_SMART_REALITY_443',
                            'DE_SMART_XHTTP_REALITY_8443'
                        )
                        )
                     or (
                            not exists (
                                select 1
                                from config_profile_inbounds de_smart_inbound
                                where de_smart_inbound.tag = 'DE_SMART_REALITY_443'
                            )
                        and config_profile_inbounds.tag in (
                            'VLESS_REALITY_443',
                            'VLESS_XHTTP_REALITY_8443'
                        )
                        )
                )
                )
             or (
                    nodes.name = '🇷🇺 RU Moscow 01 25G'
                and (
                        (
                            exists (
                                select 1
                                from config_profile_inbounds moscow_smart_inbound
                                where moscow_smart_inbound.tag = 'MSK_SMART_REALITY_443'
                            )
                        and config_profile_inbounds.tag in (
                            'MSK_SMART_REALITY_443',
                            'MSK_SMART_XHTTP_REALITY_8443'
                        )
                        )
                     or (
                            not exists (
                                select 1
                                from config_profile_inbounds moscow_smart_inbound
                                where moscow_smart_inbound.tag = 'MSK_SMART_REALITY_443'
                            )
                        and config_profile_inbounds.tag in (
                            'VLESS_REALITY_443',
                            'VLESS_XHTTP_REALITY_8443'
                        )
                        )
                )
                )
             or (
                    nodes.name not in ('🇩🇪 DE Frankfurt 01 25G', '🇷🇺 RU Moscow 01 25G')
                and config_profile_inbounds.tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
                )
        )
          and nodes.name in (
              '🇩🇪 DE Frankfurt 01 25G',
              '🇳🇱 NL Amsterdam 01 10G',
              '🇷🇺 RU Moscow 01 25G',
              '🇷🇺 RU SPB 01 25G'
          )
    ) as linked_node_inbounds,
    (
        select count(*)
        from hosts
        join config_profile_inbounds
          on config_profile_inbounds.uuid = hosts.config_profile_inbound_uuid
        where hosts.remark in (
            '🇩🇪 DE Frankfurt 01 25G Reality 443',
            '🇩🇪 DE Frankfurt 01 25G XHTTP Reality 8443',
            '🇳🇱 NL Amsterdam 01 10G Reality 443',
            '🇳🇱 NL Amsterdam 01 10G XHTTP Reality 8443',
            '🇷🇺 RU Moscow 01 25G Reality 443',
            '🇷🇺 RU Moscow 01 25G XHTTP Reality 8443',
            '🇷🇺 RU SPB 01 25G Reality 443',
            '🇷🇺 RU SPB 01 25G XHTTP Reality 8443'
        )
          and config_profile_inbounds.tag in (
              'VLESS_REALITY_443',
              'VLESS_XHTTP_REALITY_8443',
              'DE_SMART_REALITY_443',
              'DE_SMART_XHTTP_REALITY_8443',
              'MSK_SMART_REALITY_443',
              'MSK_SMART_XHTTP_REALITY_8443'
          )
    ) as smart_host_count,
    (
        select count(*)
        from hosts
        join hosts_to_nodes
          on hosts_to_nodes.host_uuid = hosts.uuid
        join nodes
          on nodes.uuid = hosts_to_nodes.node_uuid
        where (
                nodes.name = '🇩🇪 DE Frankfurt 01 25G'
            and hosts.remark in ('🇩🇪 DE Frankfurt 01 25G Reality 443', '🇩🇪 DE Frankfurt 01 25G XHTTP Reality 8443')
        )
           or (
                nodes.name = '🇳🇱 NL Amsterdam 01 10G'
            and hosts.remark in ('🇳🇱 NL Amsterdam 01 10G Reality 443', '🇳🇱 NL Amsterdam 01 10G XHTTP Reality 8443')
        )
           or (
                nodes.name = '🇷🇺 RU Moscow 01 25G'
            and hosts.remark in ('🇷🇺 RU Moscow 01 25G Reality 443', '🇷🇺 RU Moscow 01 25G XHTTP Reality 8443')
        )
           or (
                nodes.name = '🇷🇺 RU SPB 01 25G'
            and hosts.remark in ('🇷🇺 RU SPB 01 25G Reality 443', '🇷🇺 RU SPB 01 25G XHTTP Reality 8443')
        )
    ) as smart_host_node_link_count,
    (
        select count(distinct nodes.uuid)
        from nodes
        where nodes.name in (
            '🇩🇪 DE Frankfurt 01 25G',
            '🇳🇱 NL Amsterdam 01 10G',
            '🇷🇺 RU Moscow 01 25G',
            '🇷🇺 RU SPB 01 25G'
        )
          and nodes.active_plugin_uuid = node_plugin.uuid
    ) as plugin_assigned_node_count
from external_squads
join external_squads_templates
  on external_squads_templates.external_squad_uuid = external_squads.uuid
join subscription_templates
  on subscription_templates.uuid = external_squads_templates.template_uuid
cross join internal_squads
cross join node_plugin
where external_squads.name = 'CYBERVPN_PREMIUM_SMART_RU'
  and external_squads_templates.template_type = 'MIHOMO'
  and subscription_templates.name = 'CyberVPN Premium Smart RU'
  and internal_squads.name = 'CYBERVPN_PREMIUM_SMART_RU_NODES'
  and node_plugin.name = 'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION';
