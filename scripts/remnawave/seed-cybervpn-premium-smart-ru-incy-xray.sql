-- Run through run-premium-smart-ru-seeds.py on the PostgreSQL host/container.
-- The wrapper supplies a private random stage directory and trusted SHA-256
-- values directly through psql variables; this file intentionally has no /tmp
-- artifact fallback.

\set ON_ERROR_STOP on

begin;

create temporary table cybervpn_premium_smart_ru_artifact_contract (
    stage_dir text not null,
    stage_manifest_sha256 text not null,
    mihomo_sha256 text not null,
    incy_sha256 text not null,
    incy_canary_sha256 text not null,
    legacy_header_sha256 text not null,
    stage_manifest jsonb,
    incy_template jsonb,
    incy_canary_template jsonb,
    legacy_header jsonb
) on commit drop;

insert into cybervpn_premium_smart_ru_artifact_contract (
    stage_dir,
    stage_manifest_sha256,
    mihomo_sha256,
    incy_sha256,
    incy_canary_sha256,
    legacy_header_sha256
)
values (
    :'cybervpn_premium_smart_ru_stage_dir',
    :'cybervpn_premium_smart_ru_stage_manifest_sha256',
    :'cybervpn_premium_smart_ru_mihomo_sha256',
    :'cybervpn_premium_smart_ru_incy_sha256',
    :'cybervpn_premium_smart_ru_incy_canary_sha256',
    :'cybervpn_premium_smart_ru_legacy_header_sha256'
);

do $cybervpn_premium_smart_ru_incy_artifact_preflight$
declare
    v_contract cybervpn_premium_smart_ru_artifact_contract%rowtype;
    v_manifest_bytes bytea;
    v_incy_bytes bytea;
    v_incy_canary_bytes bytea;
    v_legacy_header_bytes bytea;
    v_manifest jsonb;
    v_incy jsonb;
    v_incy_canary jsonb;
    v_legacy_header jsonb;
    v_legacy_decoded jsonb;
    v_legacy_value text;
begin
    select * into strict v_contract
    from cybervpn_premium_smart_ru_artifact_contract;

    if v_contract.stage_dir !~ '^/[A-Za-z0-9._/-]+$'
       or v_contract.stage_dir ~ '(^|/)\.\.(/|$)'
       or v_contract.stage_dir ~ '^/(tmp|var/tmp)(/|$)'
       or v_contract.stage_manifest_sha256 !~ '^[0-9a-f]{64}$'
       or v_contract.mihomo_sha256 !~ '^[0-9a-f]{64}$'
       or v_contract.incy_sha256 !~ '^[0-9a-f]{64}$'
       or v_contract.incy_canary_sha256 !~ '^[0-9a-f]{64}$'
       or v_contract.legacy_header_sha256 !~ '^[0-9a-f]{64}$' then
        raise exception 'CyberVPN Premium Smart RU trusted artifact variables are invalid';
    end if;

    v_manifest_bytes := pg_read_binary_file(v_contract.stage_dir || '/manifest.json');
    v_incy_bytes := pg_read_binary_file(v_contract.stage_dir || '/incy-xray.json');
    v_incy_canary_bytes := pg_read_binary_file(
        v_contract.stage_dir || '/incy-xray-failover-canary.json'
    );
    v_legacy_header_bytes := pg_read_binary_file(
        v_contract.stage_dir || '/legacy-routing-header.json'
    );

    if encode(sha256(v_manifest_bytes), 'hex') <> v_contract.stage_manifest_sha256 then
        raise exception 'CyberVPN Premium Smart RU stage manifest SHA-256 mismatch';
    end if;
    if encode(sha256(v_incy_bytes), 'hex') <> v_contract.incy_sha256 then
        raise exception 'CyberVPN Premium Smart RU INCY SHA-256 mismatch';
    end if;
    if encode(sha256(v_incy_canary_bytes), 'hex') <> v_contract.incy_canary_sha256 then
        raise exception 'CyberVPN Premium Smart RU INCY canary SHA-256 mismatch';
    end if;
    if encode(sha256(v_legacy_header_bytes), 'hex') <> v_contract.legacy_header_sha256 then
        raise exception 'CyberVPN Premium Smart RU legacy header SHA-256 mismatch';
    end if;

    v_manifest := convert_from(v_manifest_bytes, 'UTF8')::jsonb;
    v_incy := convert_from(v_incy_bytes, 'UTF8')::jsonb;
    v_incy_canary := convert_from(v_incy_canary_bytes, 'UTF8')::jsonb;
    v_legacy_header := convert_from(v_legacy_header_bytes, 'UTF8')::jsonb;

    if v_manifest->>'schemaVersion' is distinct from '1'
       or v_manifest->>'product' is distinct from 'premium_smart_ru'
       or v_manifest#>>'{validation,mihomoProtocolOnlyTorrentPolicy}' is distinct from 'true'
       or v_manifest#>>'{artifacts,mihomo.yaml,sha256}' is distinct from v_contract.mihomo_sha256
       or v_manifest#>>'{artifacts,incy-xray.json,sha256}' is distinct from v_contract.incy_sha256
       or v_manifest#>>'{artifacts,incy-xray-failover-canary.json,sha256}'
            is distinct from v_contract.incy_canary_sha256
       or v_manifest#>>'{artifacts,legacy-routing-header.json,sha256}'
            is distinct from v_contract.legacy_header_sha256
       or octet_length(v_incy_bytes) is distinct from
            (v_manifest#>>'{artifacts,incy-xray.json,bytes}')::bigint
       or octet_length(v_incy_canary_bytes) is distinct from
            (v_manifest#>>'{artifacts,incy-xray-failover-canary.json,bytes}')::bigint
       or octet_length(v_legacy_header_bytes) is distinct from
            (v_manifest#>>'{artifacts,legacy-routing-header.json,bytes}')::bigint then
        raise exception 'CyberVPN Premium Smart RU stage manifest contract is invalid';
    end if;

    if jsonb_typeof(v_incy) is distinct from 'object'
       or v_incy#>>'{remnawave,routePolicy,schemaVersion}' is distinct from '1'
       or v_incy#>>'{remnawave,routePolicy,product}' is distinct from 'premium_smart_ru'
       or v_incy#>>'{remnawave,routePolicy,rendererMode}'
            is distinct from 'automatic-failover'
       or jsonb_typeof(v_incy#>'{remnawave,injectHosts}') is distinct from 'array'
       or jsonb_array_length(v_incy#>'{remnawave,injectHosts}') <> 4
       or jsonb_typeof(v_incy->'inbounds') is distinct from 'array'
       or jsonb_array_length(v_incy->'inbounds') <> 2
       or jsonb_typeof(v_incy#>'{routing,rules}') is distinct from 'array'
       or jsonb_array_length(v_incy#>'{routing,rules}') = 0
       or jsonb_typeof(v_incy#>'{routing,balancers}') is distinct from 'array'
       or jsonb_array_length(v_incy#>'{routing,balancers}') <> 4
       or v_incy#>'{routing,balancers}' is distinct from '[
            {"tag":"eu-primary","selector":["eu-de-2"],"strategy":{"type":"leastPing"},"fallbackTag":"eu-fallback-loop"},
            {"tag":"eu-fallback","selector":["eu-nl-2"],"strategy":{"type":"leastPing"},"fallbackTag":"block"},
            {"tag":"ru-primary","selector":["ru-msk-2"],"strategy":{"type":"leastPing"},"fallbackTag":"ru-fallback-loop"},
            {"tag":"ru-fallback","selector":["ru-spb-2"],"strategy":{"type":"leastPing"},"fallbackTag":"block"}
       ]'::jsonb
       or v_incy->'observatory' is distinct from '{
            "subjectSelector":["eu-de-2","eu-nl-2","ru-msk-2","ru-spb-2"],
            "probeUrl":"https://www.ozon.ru/",
            "probeInterval":"10s",
            "enableConcurrency":true
       }'::jsonb
       or v_incy->'burstObservatory' is not null
       or v_incy#>'{routing,rules,0}' is distinct from '{
            "type":"field",
            "ruleTag":"route_eu_failover_loop",
            "inboundTag":["eu-fallback-in"],
            "network":"tcp,udp",
            "balancerTag":"eu-fallback"
       }'::jsonb
       or v_incy#>'{routing,rules,1}' is distinct from '{
            "type":"field",
            "ruleTag":"route_ru_failover_loop",
            "inboundTag":["ru-fallback-in"],
            "network":"tcp,udp",
            "balancerTag":"ru-fallback"
       }'::jsonb
       or exists (
            select 1
            from jsonb_array_elements(v_incy#>'{routing,balancers}') as balancer
            where balancer->>'fallbackTag' = 'direct'
       )
       or not exists (
            select 1
            from jsonb_array_elements(v_incy#>'{routing,rules}') as rule
            where rule->>'ruleTag' = 'route_final_eu'
              and rule->>'balancerTag' = 'eu-primary'
       )
       or not exists (
            select 1
            from jsonb_array_elements(v_incy#>'{routing,rules}') as rule
            where rule->>'ruleTag' = 'route_ru_services'
              and rule->>'balancerTag' = 'ru-primary'
       )
       or exists (
            select 1
            from jsonb_array_elements(v_incy#>'{routing,rules}') as rule
            where rule->>'ruleTag' in (
                    'block_bittorrent_protocol',
                    'block_torrent_processes',
                    'block_torrent_sources'
                  )
               or exists (
                    select 1
                    from jsonb_array_elements_text(
                        case jsonb_typeof(rule->'protocol')
                            when 'array' then rule->'protocol'
                            when 'string' then jsonb_build_array(rule->'protocol')
                            else '[]'::jsonb
                        end
                    ) as protocol_value(value)
                    where lower(btrim(protocol_value.value)) = 'bittorrent'
               )
               or exists (
                    select 1
                    from jsonb_array_elements_text(
                        case jsonb_typeof(rule->'process')
                            when 'array' then rule->'process'
                            when 'string' then jsonb_build_array(rule->'process')
                            else '[]'::jsonb
                        end
                    ) as process_value(value)
                    where lower(btrim(process_value.value)) like '%torrent%'
               )
               or (
                    (
                        lower(coalesce(rule->>'outboundTag', '')) in (
                            'block',
                            'rw_tb_outbound_block'
                        )
                        or exists (
                            select 1
                            from jsonb_array_elements(v_incy->'outbounds') as outbound
                            where lower(coalesce(outbound->>'tag', '')) =
                                  lower(coalesce(rule->>'outboundTag', ''))
                              and lower(coalesce(outbound->>'protocol', '')) = 'blackhole'
                        )
                    )
                    and exists (
                        select 1
                        from jsonb_array_elements_text(
                            case jsonb_typeof(rule->'domain')
                                when 'array' then rule->'domain'
                                when 'string' then jsonb_build_array(rule->'domain')
                                else '[]'::jsonb
                            end
                        ) as domain_value(value)
                        where (
                                lower(btrim(domain_value.value)) like 'keyword:%'
                                and exists (
                                    select 1
                                    from unnest(array[
                                        '1337x.to',
                                        'eztv.re',
                                        'kinozal.tv',
                                        'limetorrents.lol',
                                        'nnmclub.to',
                                        'rutracker.org',
                                        'rutor.info',
                                        'thepiratebay.org',
                                        'torrentdownload.info',
                                        'torrentgalaxy.to',
                                        'yts.mx'
                                    ]) as catalog_domain(value)
                                    where position(
                                        btrim(substring(lower(btrim(domain_value.value)) from 9))
                                        in catalog_domain.value
                                    ) > 0
                                )
                              )
                           or (
                                lower(btrim(domain_value.value)) like 'regexp:%'
                                and exists (
                                    select 1
                                    from unnest(array[
                                        '1337x.to',
                                        'eztv.re',
                                        'kinozal.tv',
                                        'limetorrents.lol',
                                        'nnmclub.to',
                                        'rutracker.org',
                                        'rutor.info',
                                        'thepiratebay.org',
                                        'torrentdownload.info',
                                        'torrentgalaxy.to',
                                        'yts.mx'
                                    ]) as catalog_domain(value)
                                    where catalog_domain.value ~* btrim(
                                            substring(domain_value.value from 8)
                                        )
                                       or ('www.' || catalog_domain.value) ~* btrim(
                                            substring(domain_value.value from 8)
                                        )
                                )
                              )
                           or regexp_replace(
                                lower(btrim(domain_value.value)),
                                '^(domain|full):',
                                ''
                              ) = any(array[
                                '1337x.to',
                                'eztv.re',
                                'kinozal.tv',
                                'limetorrents.lol',
                                'nnmclub.to',
                                'rutracker.org',
                                'rutor.info',
                                'thepiratebay.org',
                                'torrentdownload.info',
                                'torrentgalaxy.to',
                                'yts.mx'
                              ])
                    )
               )
       )
       or not exists (
            select 1
            from jsonb_array_elements(v_incy#>'{routing,rules}')
                with ordinality as catalog_rule(rule, position)
            where catalog_rule.rule->>'ruleTag' = 'route_catalog_exceptions'
              and catalog_rule.rule->>'balancerTag' = 'eu-primary'
              and (
                    select count(distinct regexp_replace(
                        lower(btrim(domain_value.value)),
                        '^(domain|full):',
                        ''
                    ))
                    from jsonb_array_elements_text(
                        case jsonb_typeof(catalog_rule.rule->'domain')
                            when 'array' then catalog_rule.rule->'domain'
                            when 'string' then jsonb_build_array(catalog_rule.rule->'domain')
                            else '[]'::jsonb
                        end
                    ) as domain_value(value)
                    where regexp_replace(
                        lower(btrim(domain_value.value)),
                        '^(domain|full):',
                        ''
                    ) = any(array[
                        '1337x.to',
                        'eztv.re',
                        'kinozal.tv',
                        'limetorrents.lol',
                        'nnmclub.to',
                        'rutracker.org',
                        'rutor.info',
                        'thepiratebay.org',
                        'torrentdownload.info',
                        'torrentgalaxy.to',
                        'yts.mx'
                    ])
              ) = 11
              and not exists (
                    select 1
                    from jsonb_array_elements(v_incy#>'{routing,rules}')
                        with ordinality as block_rule(rule, position)
                    where block_rule.rule->>'ruleTag' = any(array[
                        'block_ads_trackers',
                        'block_tor_best_effort',
                        'block_quic_doq',
                        'block_smtp_abuse'
                    ])
                      and block_rule.position < catalog_rule.position
              )
       )
       or exists (
            select 1
            from jsonb_array_elements(v_incy#>'{routing,rules}') as rule
            cross join lateral jsonb_array_elements_text(
                case jsonb_typeof(rule->'domain')
                    when 'array' then rule->'domain'
                    when 'string' then jsonb_build_array(rule->'domain')
                    else '[]'::jsonb
                end
            ) as domain_value(value)
            where rule->>'ruleTag' = 'route_eu_exceptions'
              and regexp_replace(
                    lower(btrim(domain_value.value)),
                    '^(domain|full):',
                    ''
                  ) = any(array[
                    '1337x.to',
                    'eztv.re',
                    'kinozal.tv',
                    'limetorrents.lol',
                    'nnmclub.to',
                    'rutracker.org',
                    'rutor.info',
                    'thepiratebay.org',
                    'torrentdownload.info',
                    'torrentgalaxy.to',
                    'yts.mx'
                  ])
       )
       or not exists (
            select 1
            from jsonb_array_elements(v_incy#>'{routing,rules}') as rule
            where rule->>'ruleTag' = 'block_smtp_abuse'
              and rule->>'network' = 'tcp'
              and rule->>'port' = '25,465,587'
              and rule->>'outboundTag' = 'block'
       ) then
        raise exception 'CyberVPN Premium Smart RU INCY artifact semantics are invalid';
    end if;

    if jsonb_typeof(v_incy_canary) is distinct from 'object'
       or v_incy_canary#>>'{remnawave,routePolicy,schemaVersion}' is distinct from '1'
       or v_incy_canary#>>'{remnawave,routePolicy,product}' is distinct from 'premium_smart_ru'
       or v_incy_canary#>>'{remnawave,routePolicy,rendererMode}'
            is distinct from 'automatic-failover-canary'
       or jsonb_typeof(v_incy_canary#>'{remnawave,injectHosts}') is distinct from 'array'
       or jsonb_array_length(v_incy_canary#>'{remnawave,injectHosts}') <> 4
       or jsonb_typeof(v_incy_canary#>'{routing,balancers}') is distinct from 'array'
       or jsonb_array_length(v_incy_canary#>'{routing,balancers}') <> 4
       or v_incy_canary#>'{routing,balancers}' is distinct from '[
            {"tag":"eu-primary","selector":["eu-de-2"],"strategy":{"type":"leastPing"},"fallbackTag":"eu-fallback-loop"},
            {"tag":"eu-fallback","selector":["eu-nl-2"],"strategy":{"type":"leastPing"},"fallbackTag":"block"},
            {"tag":"ru-primary","selector":["ru-msk-2"],"strategy":{"type":"leastPing"},"fallbackTag":"ru-fallback-loop"},
            {"tag":"ru-fallback","selector":["ru-spb-2"],"strategy":{"type":"leastPing"},"fallbackTag":"block"}
       ]'::jsonb
       or jsonb_typeof(v_incy_canary->'observatory') is distinct from 'object'
       or v_incy_canary->'observatory' is distinct from '{
            "subjectSelector":["eu-de-2","eu-nl-2","ru-msk-2","ru-spb-2"],
            "probeUrl":"https://www.ozon.ru/",
            "probeInterval":"10s",
            "enableConcurrency":true
       }'::jsonb
       or v_incy_canary->'burstObservatory' is not null
       or v_incy_canary#>'{routing,rules,0}' is distinct from '{
            "type":"field",
            "ruleTag":"route_eu_failover_loop",
            "inboundTag":["eu-fallback-in"],
            "network":"tcp,udp",
            "balancerTag":"eu-fallback"
       }'::jsonb
       or v_incy_canary#>'{routing,rules,1}' is distinct from '{
            "type":"field",
            "ruleTag":"route_ru_failover_loop",
            "inboundTag":["ru-fallback-in"],
            "network":"tcp,udp",
            "balancerTag":"ru-fallback"
       }'::jsonb
       or exists (
            select 1
            from jsonb_array_elements(v_incy_canary#>'{routing,balancers}') as balancer
            where balancer->>'fallbackTag' = 'direct'
       )
       or not exists (
            select 1
            from jsonb_array_elements(v_incy_canary#>'{routing,rules}') as rule
            where rule->>'ruleTag' = 'route_final_eu'
              and rule->>'balancerTag' = 'eu-primary'
       )
       or not exists (
            select 1
            from jsonb_array_elements(v_incy_canary#>'{routing,rules}') as rule
            where rule->>'ruleTag' = 'route_ru_services'
              and rule->>'balancerTag' = 'ru-primary'
       )
       or not exists (
            select 1
            from jsonb_array_elements(v_incy_canary#>'{routing,rules}') as rule
            where rule->>'ruleTag' = 'route_eu_failover_loop'
              and rule->>'balancerTag' = 'eu-fallback'
       )
       or not exists (
            select 1
            from jsonb_array_elements(v_incy_canary#>'{routing,rules}') as rule
            where rule->>'ruleTag' = 'route_ru_failover_loop'
              and rule->>'balancerTag' = 'ru-fallback'
       )
       or exists (
            select 1
            from jsonb_array_elements(v_incy_canary#>'{routing,rules}') as rule
            where rule->>'ruleTag' in (
                    'block_bittorrent_protocol',
                    'block_torrent_processes',
                    'block_torrent_sources'
                  )
               or exists (
                    select 1
                    from jsonb_array_elements_text(
                        case jsonb_typeof(rule->'protocol')
                            when 'array' then rule->'protocol'
                            when 'string' then jsonb_build_array(rule->'protocol')
                            else '[]'::jsonb
                        end
                    ) as protocol_value(value)
                    where lower(btrim(protocol_value.value)) = 'bittorrent'
               )
               or exists (
                    select 1
                    from jsonb_array_elements_text(
                        case jsonb_typeof(rule->'process')
                            when 'array' then rule->'process'
                            when 'string' then jsonb_build_array(rule->'process')
                            else '[]'::jsonb
                        end
                    ) as process_value(value)
                    where lower(btrim(process_value.value)) like '%torrent%'
               )
               or (
                    (
                        lower(coalesce(rule->>'outboundTag', '')) in (
                            'block',
                            'rw_tb_outbound_block'
                        )
                        or exists (
                            select 1
                            from jsonb_array_elements(v_incy_canary->'outbounds') as outbound
                            where lower(coalesce(outbound->>'tag', '')) =
                                  lower(coalesce(rule->>'outboundTag', ''))
                              and lower(coalesce(outbound->>'protocol', '')) = 'blackhole'
                        )
                    )
                    and exists (
                        select 1
                        from jsonb_array_elements_text(
                            case jsonb_typeof(rule->'domain')
                                when 'array' then rule->'domain'
                                when 'string' then jsonb_build_array(rule->'domain')
                                else '[]'::jsonb
                            end
                        ) as domain_value(value)
                        where (
                                lower(btrim(domain_value.value)) like 'keyword:%'
                                and exists (
                                    select 1
                                    from unnest(array[
                                        '1337x.to',
                                        'eztv.re',
                                        'kinozal.tv',
                                        'limetorrents.lol',
                                        'nnmclub.to',
                                        'rutracker.org',
                                        'rutor.info',
                                        'thepiratebay.org',
                                        'torrentdownload.info',
                                        'torrentgalaxy.to',
                                        'yts.mx'
                                    ]) as catalog_domain(value)
                                    where position(
                                        btrim(substring(lower(btrim(domain_value.value)) from 9))
                                        in catalog_domain.value
                                    ) > 0
                                )
                              )
                           or (
                                lower(btrim(domain_value.value)) like 'regexp:%'
                                and exists (
                                    select 1
                                    from unnest(array[
                                        '1337x.to',
                                        'eztv.re',
                                        'kinozal.tv',
                                        'limetorrents.lol',
                                        'nnmclub.to',
                                        'rutracker.org',
                                        'rutor.info',
                                        'thepiratebay.org',
                                        'torrentdownload.info',
                                        'torrentgalaxy.to',
                                        'yts.mx'
                                    ]) as catalog_domain(value)
                                    where catalog_domain.value ~* btrim(
                                            substring(domain_value.value from 8)
                                        )
                                       or ('www.' || catalog_domain.value) ~* btrim(
                                            substring(domain_value.value from 8)
                                        )
                                )
                              )
                           or regexp_replace(
                                lower(btrim(domain_value.value)),
                                '^(domain|full):',
                                ''
                              ) = any(array[
                                '1337x.to',
                                'eztv.re',
                                'kinozal.tv',
                                'limetorrents.lol',
                                'nnmclub.to',
                                'rutracker.org',
                                'rutor.info',
                                'thepiratebay.org',
                                'torrentdownload.info',
                                'torrentgalaxy.to',
                                'yts.mx'
                              ])
                    )
               )
       )
       or not exists (
            select 1
            from jsonb_array_elements(v_incy_canary#>'{routing,rules}')
                with ordinality as catalog_rule(rule, position)
            where catalog_rule.rule->>'ruleTag' = 'route_catalog_exceptions'
              and catalog_rule.rule->>'balancerTag' = 'eu-primary'
              and (
                    select count(distinct regexp_replace(
                        lower(btrim(domain_value.value)),
                        '^(domain|full):',
                        ''
                    ))
                    from jsonb_array_elements_text(
                        case jsonb_typeof(catalog_rule.rule->'domain')
                            when 'array' then catalog_rule.rule->'domain'
                            when 'string' then jsonb_build_array(catalog_rule.rule->'domain')
                            else '[]'::jsonb
                        end
                    ) as domain_value(value)
                    where regexp_replace(
                        lower(btrim(domain_value.value)),
                        '^(domain|full):',
                        ''
                    ) = any(array[
                        '1337x.to',
                        'eztv.re',
                        'kinozal.tv',
                        'limetorrents.lol',
                        'nnmclub.to',
                        'rutracker.org',
                        'rutor.info',
                        'thepiratebay.org',
                        'torrentdownload.info',
                        'torrentgalaxy.to',
                        'yts.mx'
                    ])
              ) = 11
              and not exists (
                    select 1
                    from jsonb_array_elements(v_incy_canary#>'{routing,rules}')
                        with ordinality as block_rule(rule, position)
                    where block_rule.rule->>'ruleTag' = any(array[
                        'block_ads_trackers',
                        'block_tor_best_effort',
                        'block_quic_doq',
                        'block_smtp_abuse'
                    ])
                      and block_rule.position < catalog_rule.position
              )
       )
       or exists (
            select 1
            from jsonb_array_elements(v_incy_canary#>'{routing,rules}') as rule
            cross join lateral jsonb_array_elements_text(
                case jsonb_typeof(rule->'domain')
                    when 'array' then rule->'domain'
                    when 'string' then jsonb_build_array(rule->'domain')
                    else '[]'::jsonb
                end
            ) as domain_value(value)
            where rule->>'ruleTag' = 'route_eu_exceptions'
              and regexp_replace(
                    lower(btrim(domain_value.value)),
                    '^(domain|full):',
                    ''
                  ) = any(array[
                    '1337x.to',
                    'eztv.re',
                    'kinozal.tv',
                    'limetorrents.lol',
                    'nnmclub.to',
                    'rutracker.org',
                    'rutor.info',
                    'thepiratebay.org',
                    'torrentdownload.info',
                    'torrentgalaxy.to',
                    'yts.mx'
                  ])
       )
       or not exists (
            select 1
            from jsonb_array_elements(v_incy_canary#>'{routing,rules}') as rule
            where rule->>'ruleTag' = 'block_smtp_abuse'
              and rule->>'network' = 'tcp'
              and rule->>'port' = '25,465,587'
              and rule->>'outboundTag' = 'block'
       ) then
        raise exception 'CyberVPN Premium Smart RU INCY canary semantics are invalid';
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
       or (v_legacy_decoded->'BlockSites' ? 'domain:rutracker.org')
       or not (v_legacy_decoded->'BlockSites' ? 'geosite:category-ads-all')
       or jsonb_typeof(v_legacy_decoded->'DirectIp') is distinct from 'array'
       or not (v_legacy_decoded->'DirectIp' ? '10.0.0.0/8') then
        raise exception 'CyberVPN Premium Smart RU legacy routing semantics are invalid';
    end if;

    update cybervpn_premium_smart_ru_artifact_contract
    set stage_manifest = v_manifest,
        incy_template = v_incy,
        incy_canary_template = v_incy_canary,
        legacy_header = v_legacy_header;
end
$cybervpn_premium_smart_ru_incy_artifact_preflight$;

insert into subscription_templates (
    uuid,
    template_type,
    template_yaml,
    template_json,
    created_at,
    updated_at,
    name,
    view_position
)
values (
    gen_random_uuid(),
    'XRAY_JSON',
    null,
    (select incy_template from cybervpn_premium_smart_ru_artifact_contract),
    now(),
    now(),
    'CyberVPN Premium Smart RU INCY',
    220
)
on conflict (template_type, name) do update
set template_json = excluded.template_json,
    template_yaml = null,
    updated_at = now(),
    view_position = excluded.view_position;

insert into subscription_templates (
    uuid,
    template_type,
    template_yaml,
    template_json,
    created_at,
    updated_at,
    name,
    view_position
)
values (
    gen_random_uuid(),
    'XRAY_JSON',
    null,
    (select incy_canary_template from cybervpn_premium_smart_ru_artifact_contract),
    now(),
    now(),
    'CyberVPN Premium Smart RU INCY Failover Canary',
    221
)
on conflict (template_type, name) do update
set template_json = excluded.template_json,
    template_yaml = null,
    updated_at = now(),
    view_position = excluded.view_position;

create temporary table incy_host_specs (
    source_tag text not null,
    target_tag text unique not null,
    target_remark text unique not null,
    target_address text,
    target_view_position integer not null,
    target_hidden boolean not null,
    use_xray_template boolean not null
) on commit drop;

insert into incy_host_specs values
    -- DE/NL and Moscow/SPB intentionally share literal relay bootstrap IPs.
    -- Distinct source inbounds, Reality SNI/path and vless_route_id select the
    -- terminal region; generated-subscription runtime evidence must verify it.
    ('PREMIUM_SMART_RU_DE_REALITY_443', 'PREMIUM_SMART_RU_INCY_DE_RAW', 'CyberVPN INCY DE RAW', '138.16.140.44', 320, true, false),
    ('PREMIUM_SMART_RU_DE_XHTTP_REALITY_8443', 'PREMIUM_SMART_RU_INCY_DE_XHTTP', 'CyberVPN INCY DE XHTTP', '138.16.140.44', 321, true, false),
    ('PREMIUM_SMART_RU_NL_REALITY_443', 'PREMIUM_SMART_RU_INCY_NL_RAW', 'CyberVPN INCY NL RAW', '138.16.140.44', 322, true, false),
    ('PREMIUM_SMART_RU_NL_XHTTP_REALITY_8443', 'PREMIUM_SMART_RU_INCY_NL_XHTTP', 'CyberVPN INCY NL XHTTP', '138.16.140.44', 323, true, false),
    ('PREMIUM_SMART_RU_MSK_REALITY_443', 'PREMIUM_SMART_RU_INCY_MSK_RAW', 'CyberVPN INCY Moscow RAW', '193.233.91.99', 324, true, false),
    ('PREMIUM_SMART_RU_MSK_XHTTP_REALITY_8443', 'PREMIUM_SMART_RU_INCY_MSK_XHTTP', 'CyberVPN INCY Moscow XHTTP', '193.233.91.99', 325, true, false),
    ('PREMIUM_SMART_RU_SPB_REALITY_443', 'PREMIUM_SMART_RU_INCY_SPB_RAW', 'CyberVPN INCY SPB RAW', '193.233.91.99', 326, true, false),
    ('PREMIUM_SMART_RU_SPB_XHTTP_REALITY_8443', 'PREMIUM_SMART_RU_INCY_SPB_XHTTP', 'CyberVPN INCY SPB XHTTP', '193.233.91.99', 327, true, false),
    ('PREMIUM_SMART_RU_DE_REALITY_443', 'PREMIUM_SMART_RU_INCY_VIRTUAL', 'CyberVPN Premium Smart RU', null, 319, false, true);

do $cybervpn_incy_preflight$
declare
    v_invalid_source_count integer;
begin
    select count(*)
    into v_invalid_source_count
    from (
        select specs.source_tag
        from (
            select distinct source_tag
            from incy_host_specs
        ) specs
        left join hosts source_host
          on source_host.tags @> array[specs.source_tag]::text[]
         and source_host.is_disabled = false
        group by specs.source_tag
        having count(source_host.uuid) <> 1
    ) invalid_sources;

    if v_invalid_source_count <> 0 then
        raise exception 'Missing or ambiguous enabled Premium Smart RU source host(s) for % INCY injection spec(s)',
            v_invalid_source_count;
    end if;
end
$cybervpn_incy_preflight$;

update hosts target_host
set view_position = specs.target_view_position,
    remark = specs.target_remark,
    address = coalesce(specs.target_address, source_host.address),
    port = source_host.port,
    path = source_host.path,
    sni = source_host.sni,
    host = source_host.host,
    alpn = source_host.alpn,
    fingerprint = source_host.fingerprint,
    is_disabled = false,
    security_layer = source_host.security_layer,
    xhttp_extra_params = source_host.xhttp_extra_params,
    config_profile_inbound_uuid = source_host.config_profile_inbound_uuid,
    config_profile_uuid = source_host.config_profile_uuid,
    server_description = 'CyberVPN Smart RU INCY',
    mux_params = source_host.mux_params,
    sockopt_params = source_host.sockopt_params,
    is_hidden = specs.target_hidden,
    override_sni_from_address = source_host.override_sni_from_address,
    vless_route_id = source_host.vless_route_id,
    mihomo_x25519 = source_host.mihomo_x25519,
    shuffle_host = source_host.shuffle_host,
    xray_json_template_uuid = case
        when specs.use_xray_template then (
            select uuid
            from subscription_templates
            where template_type = 'XRAY_JSON'
              and name = 'CyberVPN Premium Smart RU INCY'
        )
        else null
    end,
    keep_sni_blank = source_host.keep_sni_blank,
    exclude_from_subscription_types = array['MIHOMO', 'CLASH', 'STASH', 'SINGBOX', 'XRAY_BASE64']::text[],
    final_mask = source_host.final_mask,
    pinned_peer_cert_sha256 = source_host.pinned_peer_cert_sha256,
    verify_peer_cert_by_name = source_host.verify_peer_cert_by_name,
    mihomo_ip_version = source_host.mihomo_ip_version,
    tags = array[specs.target_tag]::text[]
from incy_host_specs specs
join hosts source_host
  on source_host.tags @> array[specs.source_tag]::text[]
 and source_host.is_disabled = false
where target_host.tags @> array[specs.target_tag]::text[];

insert into hosts (
    uuid,
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
    vless_route_id,
    mihomo_x25519,
    shuffle_host,
    xray_json_template_uuid,
    keep_sni_blank,
    exclude_from_subscription_types,
    final_mask,
    pinned_peer_cert_sha256,
    verify_peer_cert_by_name,
    mihomo_ip_version,
    tags
)
select
    gen_random_uuid(),
    specs.target_view_position,
    specs.target_remark,
    coalesce(specs.target_address, source_host.address),
    source_host.port,
    source_host.path,
    source_host.sni,
    source_host.host,
    source_host.alpn,
    source_host.fingerprint,
    false,
    source_host.security_layer,
    source_host.xhttp_extra_params,
    source_host.config_profile_inbound_uuid,
    source_host.config_profile_uuid,
    'CyberVPN Smart RU INCY',
    source_host.mux_params,
    source_host.sockopt_params,
    specs.target_hidden,
    source_host.override_sni_from_address,
    source_host.vless_route_id,
    source_host.mihomo_x25519,
    source_host.shuffle_host,
    case
        when specs.use_xray_template then (
            select uuid
            from subscription_templates
            where template_type = 'XRAY_JSON'
              and name = 'CyberVPN Premium Smart RU INCY'
        )
        else null
    end,
    source_host.keep_sni_blank,
    array['MIHOMO', 'CLASH', 'STASH', 'SINGBOX', 'XRAY_BASE64']::text[],
    source_host.final_mask,
    source_host.pinned_peer_cert_sha256,
    source_host.verify_peer_cert_by_name,
    source_host.mihomo_ip_version,
    array[specs.target_tag]::text[]
from incy_host_specs specs
join hosts source_host
  on source_host.tags @> array[specs.source_tag]::text[]
 and source_host.is_disabled = false
where not exists (
    select 1
    from hosts existing_target
    where existing_target.tags @> array[specs.target_tag]::text[]
);

delete from hosts_to_nodes target_link
using hosts target_host, incy_host_specs specs
where target_link.host_uuid = target_host.uuid
  and target_host.tags @> array[specs.target_tag]::text[];

insert into hosts_to_nodes (host_uuid, node_uuid)
select distinct target_host.uuid, source_link.node_uuid
from incy_host_specs specs
join hosts source_host
  on source_host.tags @> array[specs.source_tag]::text[]
 and source_host.is_disabled = false
join hosts_to_nodes source_link
  on source_link.host_uuid = source_host.uuid
join hosts target_host
  on target_host.tags @> array[specs.target_tag]::text[]
on conflict do nothing;

update hosts source_host
set exclude_from_subscription_types = array(
    select distinct exclusion
    from unnest(
        coalesce(source_host.exclude_from_subscription_types, array[]::text[])
        || array['XRAY_JSON']::text[]
    ) exclusion
    order by exclusion
)
where exists (
    select 1
    from incy_host_specs specs
    where source_host.tags @> array[specs.source_tag]::text[]
      and source_host.is_disabled = false
);

with new_rules as (
    select jsonb_build_array(
        jsonb_build_object(
            'name', 'Mihomo Premium Smart RU',
            'description', 'Serve the hardened Smart RU Mihomo template only for an authoritative product identity',
            'enabled', true,
            'operator', 'AND',
            'conditions', jsonb_build_array(
                jsonb_build_object(
                    'caseSensitive', false,
                    'headerName', 'x-cybervpn-product',
                    'operator', 'EQUALS',
                    'value', 'premium_smart_ru'
                ),
                jsonb_build_object(
                    'caseSensitive', false,
                    'headerName', 'x-cybervpn-client-family',
                    'operator', 'EQUALS',
                    'value', 'mihomo'
                )
            ),
            'responseType', 'MIHOMO',
            'responseModifications', jsonb_build_object(
                'subscriptionTemplate', 'CyberVPN Premium Smart RU'
            )
        ),
        jsonb_build_object(
            'name', 'HAPP Premium Smart RU Failover Canary',
            'description', 'Serve the isolated Smart RU automatic failover canary to an opted-in HAPP identity',
            'enabled', true,
            'operator', 'AND',
            'conditions', jsonb_build_array(
                jsonb_build_object(
                    'caseSensitive', false,
                    'headerName', 'x-cybervpn-product',
                    'operator', 'EQUALS',
                    'value', 'premium_smart_ru'
                ),
                jsonb_build_object(
                    'caseSensitive', false,
                    'headerName', 'x-cybervpn-client-family',
                    'operator', 'EQUALS',
                    'value', 'happ'
                ),
                jsonb_build_object(
                    'caseSensitive', true,
                    'headerName', 'x-cybervpn-xray-failover-canary',
                    'operator', 'EQUALS',
                    'value', '1'
                )
            ),
            'responseType', 'XRAY_JSON',
            'responseModifications', jsonb_build_object(
                'subscriptionTemplate', 'CyberVPN Premium Smart RU INCY Failover Canary',
                'ignoreHostXrayJsonTemplate', true,
                'applyHeadersToEnd', true,
                'headers', jsonb_build_array(
                    jsonb_build_object(
                        'key', 'X-CyberVPN-Profile',
                        'value', 'premium_smart_ru_xray_failover_canary'
                    )
                )
            )
        ),
        jsonb_build_object(
            'name', 'INCY Premium Smart RU Failover Canary',
            'description', 'Serve the isolated Smart RU automatic failover canary to an opted-in INCY identity',
            'enabled', true,
            'operator', 'AND',
            'conditions', jsonb_build_array(
                jsonb_build_object(
                    'caseSensitive', false,
                    'headerName', 'x-cybervpn-product',
                    'operator', 'EQUALS',
                    'value', 'premium_smart_ru'
                ),
                jsonb_build_object(
                    'caseSensitive', false,
                    'headerName', 'x-cybervpn-client-family',
                    'operator', 'EQUALS',
                    'value', 'incy'
                ),
                jsonb_build_object(
                    'caseSensitive', true,
                    'headerName', 'x-cybervpn-xray-failover-canary',
                    'operator', 'EQUALS',
                    'value', '1'
                )
            ),
            'responseType', 'XRAY_JSON',
            'responseModifications', jsonb_build_object(
                'subscriptionTemplate', 'CyberVPN Premium Smart RU INCY Failover Canary',
                'ignoreHostXrayJsonTemplate', true,
                'applyHeadersToEnd', true,
                'headers', jsonb_build_array(
                    jsonb_build_object(
                        'key', 'X-CyberVPN-Profile',
                        'value', 'premium_smart_ru_xray_failover_canary'
                    )
                )
            )
        ),
        jsonb_build_object(
            'name', 'HAPP Premium Smart RU',
            'description', 'Serve one client-side Smart RU Xray config to HAPP for an authoritative product identity',
            'enabled', true,
            'operator', 'AND',
            'conditions', jsonb_build_array(
                jsonb_build_object(
                    'caseSensitive', false,
                    'headerName', 'x-cybervpn-product',
                    'operator', 'EQUALS',
                    'value', 'premium_smart_ru'
                ),
                jsonb_build_object(
                    'caseSensitive', false,
                    'headerName', 'x-cybervpn-client-family',
                    'operator', 'EQUALS',
                    'value', 'happ'
                )
            ),
            'responseType', 'XRAY_JSON',
            'responseModifications', jsonb_build_object(
                'subscriptionTemplate', 'CyberVPN Premium Smart RU INCY',
                'ignoreHostXrayJsonTemplate', true,
                'applyHeadersToEnd', true,
                'headers', jsonb_build_array(
                    jsonb_build_object(
                        'key', 'X-CyberVPN-Profile',
                        'value', 'premium_smart_ru_xray'
                    )
                )
            )
        ),
        jsonb_build_object(
            'name', 'INCY Premium Smart RU',
            'description', 'Serve one client-side Smart RU Xray config to INCY for an authoritative product identity',
            'enabled', true,
            'operator', 'AND',
            'conditions', jsonb_build_array(
                jsonb_build_object(
                    'caseSensitive', false,
                    'headerName', 'x-cybervpn-product',
                    'operator', 'EQUALS',
                    'value', 'premium_smart_ru'
                ),
                jsonb_build_object(
                    'caseSensitive', false,
                    'headerName', 'x-cybervpn-client-family',
                    'operator', 'EQUALS',
                    'value', 'incy'
                )
            ),
            'responseType', 'XRAY_JSON',
            'responseModifications', jsonb_build_object(
                'subscriptionTemplate', 'CyberVPN Premium Smart RU INCY',
                'ignoreHostXrayJsonTemplate', true,
                'applyHeadersToEnd', true,
                'headers', jsonb_build_array(
                    jsonb_build_object(
                        'key', 'X-CyberVPN-Profile',
                        'value', 'premium_smart_ru_xray'
                    )
                )
            )
        )
    ) as rules
),
rules_without_target as (
    select subscription_settings.uuid,
           subscription_settings.response_rules,
           coalesce(
               jsonb_agg(rule_element.value order by rule_element.ordinality)
                   filter (
                       where rule_element.value->>'name' not in (
                            'Mihomo Premium Smart RU',
                            'HAPP Premium Smart RU Failover Canary',
                            'INCY Premium Smart RU Failover Canary',
                            'HAPP Premium Smart RU',
                           'INCY Premium Smart RU'
                       )
                   ),
               '[]'::jsonb
           ) as rules
    from subscription_settings
    left join lateral jsonb_array_elements(
        coalesce(subscription_settings.response_rules->'rules', '[]'::jsonb)
    ) with ordinality as rule_element(value, ordinality) on true
    group by subscription_settings.uuid, subscription_settings.response_rules
),
rebuilt_rules as (
    select rules_without_target.uuid,
           rules_without_target.response_rules,
           coalesce(
               (
                   select jsonb_agg(value order by ordinality)
                   from jsonb_array_elements(rules_without_target.rules) with ordinality items(value, ordinality)
                   where value->>'responseType' = 'BROWSER'
               ),
               '[]'::jsonb
           )
           || new_rules.rules
           || coalesce(
               (
                   select jsonb_agg(value order by ordinality)
                   from jsonb_array_elements(rules_without_target.rules) with ordinality items(value, ordinality)
                   where value->>'responseType' not in ('BROWSER', 'XRAY_BASE64')
               ),
               '[]'::jsonb
           )
           || coalesce(
               (
                   select jsonb_agg(value order by ordinality)
                   from jsonb_array_elements(rules_without_target.rules) with ordinality items(value, ordinality)
                   where value->>'responseType' = 'XRAY_BASE64'
               ),
               '[]'::jsonb
           ) as rules
    from rules_without_target, new_rules
)
update subscription_settings
set response_rules = jsonb_set(
        coalesce(rebuilt_rules.response_rules, '{"version":"1","rules":[]}'::jsonb),
        '{rules}',
        rebuilt_rules.rules,
        true
    ),
    updated_at = now()
from rebuilt_rules
where subscription_settings.uuid = rebuilt_rules.uuid;

do $cybervpn_incy_external_squad_update$
declare
    v_updated_external_squad_count integer;
begin
    update external_squads
    set response_headers = jsonb_set(
            coalesce(response_headers, '{}'::jsonb),
            '{routing}',
            to_jsonb(
                (
                    select legacy_header->>'value'
                    from cybervpn_premium_smart_ru_artifact_contract
                )
            ),
            true
        ),
        updated_at = now()
    where name = 'CYBERVPN_PREMIUM_SMART_RU';

    get diagnostics v_updated_external_squad_count = row_count;
    if v_updated_external_squad_count <> 1 then
        raise exception 'Expected exactly one CYBERVPN_PREMIUM_SMART_RU external squad update, got %',
            v_updated_external_squad_count;
    end if;
end
$cybervpn_incy_external_squad_update$;

do $cybervpn_incy_validation$
declare
    v_template_count integer;
    v_injected_host_count integer;
    v_virtual_host_count integer;
    v_visible_xray_host_count integer;
    v_wrong_bootstrap_count integer;
    v_invalid_target_count integer;
    v_mihomo_rule_position integer;
    v_happ_canary_rule_position integer;
    v_incy_canary_rule_position integer;
    v_happ_rule_position integer;
    v_incy_rule_position integer;
    v_fallback_rule_position integer;
begin
    select count(*) into v_template_count
    from subscription_templates
    where template_type = 'XRAY_JSON'
      and name in (
          'CyberVPN Premium Smart RU INCY',
          'CyberVPN Premium Smart RU INCY Failover Canary'
      );

    select count(*) into v_injected_host_count
    from hosts
    where is_hidden = true
      and exists (
          select 1 from unnest(coalesce(tags, array[]::text[])) tag
          where tag like 'PREMIUM\_SMART\_RU\_INCY\_%' escape '\'
            and tag <> 'PREMIUM_SMART_RU_INCY_VIRTUAL'
      );

    select count(*) into v_virtual_host_count
    from hosts
    where is_hidden = false
      and tags @> array['PREMIUM_SMART_RU_INCY_VIRTUAL']::text[]
      and xray_json_template_uuid = (
          select uuid from subscription_templates
          where template_type = 'XRAY_JSON'
            and name = 'CyberVPN Premium Smart RU INCY'
      );

    select count(*) into v_wrong_bootstrap_count
    from incy_host_specs specs
    join hosts target_host
      on target_host.tags @> array[specs.target_tag]::text[]
    where specs.target_address is not null
      and target_host.address is distinct from specs.target_address;

    select count(*) into v_invalid_target_count
    from (
        select specs.target_tag
        from incy_host_specs specs
        left join hosts target_host
          on target_host.tags @> array[specs.target_tag]::text[]
         and target_host.is_disabled = false
        group by specs.target_tag
        having count(target_host.uuid) <> 1
    ) invalid_targets;

    select count(*) into v_visible_xray_host_count
    from hosts
    where is_disabled = false
      and is_hidden = false
      and not ('XRAY_JSON' = any(coalesce(exclude_from_subscription_types, array[]::text[])))
      and config_profile_inbound_uuid in (
          select inbound_uuid
          from internal_squad_inbounds
          join internal_squads on internal_squads.uuid = internal_squad_inbounds.internal_squad_uuid
          where internal_squads.name = 'CYBERVPN_PREMIUM_SMART_RU_NODES'
      )
      and not exists (
          select 1
          from internal_squad_host_exclusions
          join internal_squads
            on internal_squads.uuid = internal_squad_host_exclusions.squad_uuid
          where internal_squads.name = 'CYBERVPN_PREMIUM_SMART_RU_NODES'
            and internal_squad_host_exclusions.host_uuid = hosts.uuid
      );

    select min(ordinality) filter (where value->>'name' = 'Mihomo Premium Smart RU'),
           min(ordinality) filter (where value->>'name' = 'HAPP Premium Smart RU Failover Canary'),
           min(ordinality) filter (where value->>'name' = 'INCY Premium Smart RU Failover Canary'),
           min(ordinality) filter (where value->>'name' = 'HAPP Premium Smart RU'),
           min(ordinality) filter (where value->>'name' = 'INCY Premium Smart RU'),
           min(ordinality) filter (where value->>'responseType' = 'XRAY_BASE64')
    into v_mihomo_rule_position,
         v_happ_canary_rule_position,
         v_incy_canary_rule_position,
         v_happ_rule_position,
         v_incy_rule_position,
         v_fallback_rule_position
    from subscription_settings,
         jsonb_array_elements(response_rules->'rules') with ordinality rules(value, ordinality);

    if v_template_count <> 2
       or v_injected_host_count <> 8
       or v_virtual_host_count <> 1
       or v_visible_xray_host_count <> 1
       or v_wrong_bootstrap_count <> 0
       or v_invalid_target_count <> 0
       or v_mihomo_rule_position is null
       or v_happ_canary_rule_position is null
       or v_incy_canary_rule_position is null
       or v_happ_rule_position is null
       or v_incy_rule_position is null
       or v_fallback_rule_position is null
       or v_mihomo_rule_position >= v_happ_canary_rule_position
       or v_happ_canary_rule_position >= v_incy_canary_rule_position
       or v_incy_canary_rule_position >= v_happ_rule_position
       or v_happ_rule_position >= v_incy_rule_position
       or v_incy_rule_position >= v_fallback_rule_position then
        raise exception 'Smart RU delivery validation failed: template %, injected %, virtual %, visible %, wrong bootstrap %, invalid targets %, Mihomo %, HAPP canary %, INCY canary %, HAPP %, INCY %, fallback %',
            v_template_count,
            v_injected_host_count,
            v_virtual_host_count,
            v_visible_xray_host_count,
            v_wrong_bootstrap_count,
            v_invalid_target_count,
            v_mihomo_rule_position,
            v_happ_canary_rule_position,
            v_incy_canary_rule_position,
            v_happ_rule_position,
            v_incy_rule_position,
            v_fallback_rule_position;
    end if;
end
$cybervpn_incy_validation$;

commit;

select
    (select count(*) from subscription_templates where template_type = 'XRAY_JSON' and name in ('CyberVPN Premium Smart RU INCY', 'CyberVPN Premium Smart RU INCY Failover Canary')) as template_count,
    (select count(*) from hosts where is_hidden = true and exists (
        select 1 from unnest(coalesce(tags, array[]::text[])) tag
        where tag like 'PREMIUM\_SMART\_RU\_INCY\_%' escape '\'
    )) as injected_host_count,
    (select count(*) from hosts where tags @> array['PREMIUM_SMART_RU_INCY_VIRTUAL']::text[]) as virtual_host_count;
