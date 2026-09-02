-- Safe Remnawave inbound diagnostics for CyberVPN Premium Smart RU.
--
-- Prints only non-secret contract fields, counts, and booleans.
-- Does not print Reality private keys, server names/SNI, short IDs, public keys,
-- subscription links, or raw inbound JSON.

select
    cpi.tag,
    cpi.type,
    cpi.network,
    cpi.security,
    cpi.port,
    count(*) over (partition by cpi.tag) as tag_row_count,

    cpi.raw_inbound #>> '{settings,decryption}' as decryption,
    (cpi.raw_inbound #>> '{settings,flow}') = 'xtls-rprx-vision'
        as settings_flow_is_xtls_rprx_vision,
    cpi.raw_inbound #>> '{streamSettings,network}' as stream_network,
    cpi.raw_inbound #>> '{streamSettings,security}' as stream_security,
    (cpi.raw_inbound #>> '{streamSettings,realitySettings,minClientVer}') = '26.3.27'
        as reality_min_client_ver_is_26_3_27,

    case
        when jsonb_typeof(
            cpi.raw_inbound #> '{streamSettings,realitySettings,serverNames}'
        ) = 'array'
        then jsonb_array_length(
            cpi.raw_inbound #> '{streamSettings,realitySettings,serverNames}'
        )
        else 0
    end as server_names_count,

    case
        when jsonb_typeof(
            cpi.raw_inbound #> '{streamSettings,realitySettings,shortIds}'
        ) = 'array'
        then jsonb_array_length(
            cpi.raw_inbound #> '{streamSettings,realitySettings,shortIds}'
        )
        else 0
    end as short_ids_count,

    length(
        coalesce(
            cpi.raw_inbound #>> '{streamSettings,realitySettings,privateKey}',
            ''
        )
    ) > 0 as reality_private_key_present,

    coalesce(
        nullif(cpi.raw_inbound #>> '{streamSettings,realitySettings,target}', ''),
        nullif(cpi.raw_inbound #>> '{streamSettings,realitySettings,dest}', '')
    ) is not null as reality_target_present,

    right(
        btrim(
            coalesce(
                nullif(cpi.raw_inbound #>> '{streamSettings,realitySettings,target}', ''),
                nullif(cpi.raw_inbound #>> '{streamSettings,realitySettings,dest}', ''),
                ''
            )
        ),
        4
    ) = ':443' as reality_target_ends_443,

    lower(coalesce(cpi.raw_inbound #>> '{sniffing,enabled}', 'false')) = 'true'
        as sniffing_enabled,

    coalesce(cpi.raw_inbound #> '{sniffing,destOverride}', '[]'::jsonb) ? 'http'
        as dest_override_has_http,
    coalesce(cpi.raw_inbound #> '{sniffing,destOverride}', '[]'::jsonb) ? 'tls'
        as dest_override_has_tls,
    coalesce(cpi.raw_inbound #> '{sniffing,destOverride}', '[]'::jsonb) ? 'quic'
        as dest_override_has_quic
from config_profile_inbounds cpi
where cpi.tag in (
    'VLESS_REALITY_443',
    'VLESS_XHTTP_REALITY_8443',
    'DE_SMART_REALITY_443',
    'DE_SMART_XHTTP_REALITY_8443',
    'MSK_SMART_REALITY_443',
    'MSK_SMART_XHTTP_REALITY_8443'
)
order by cpi.tag;
