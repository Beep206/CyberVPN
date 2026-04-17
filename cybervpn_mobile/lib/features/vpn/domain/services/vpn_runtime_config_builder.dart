import 'dart:convert';

import 'package:flutter_v2ray_plus/flutter_v2ray.dart';

import 'package:cybervpn_mobile/core/constants/vpn_constants.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/excluded_route_entry.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/routing_profile.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/services/vpn_runtime_capabilities.dart';

const _fragmentDialerTag = 'fragment';
const _proxyOutboundTag = 'proxy';
const _directOutboundTag = 'direct';
const _blockOutboundTag = 'blackhole';

/// Runtime-ready VPN config plus metadata about applied or skipped settings.
class VpnRuntimeBuildResult {
  const VpnRuntimeBuildResult({
    required this.config,
    this.appliedSettings = const <String>[],
    this.skippedSettings = const <String, String>{},
  });

  final VpnConfigEntity config;
  final List<String> appliedSettings;
  final Map<String, String> skippedSettings;
}

class _DnsPlan {
  const _DnsPlan({
    this.servers,
    this.preserveJsonDns = false,
    this.appliedLabel,
  });

  final List<String>? servers;
  final bool preserveJsonDns;
  final String? appliedLabel;
}

/// Builds runtime Xray JSON from stored settings and connection metadata.
class VpnRuntimeConfigBuilder {
  const VpnRuntimeConfigBuilder();

  VpnRuntimeBuildResult build({
    required VpnConfigEntity sourceConfig,
    required VpnSettings vpnSettings,
    required VpnRuntimeCapabilities capabilities,
    required List<String> blockedApps,
  }) {
    final applied = <String>[];
    final skipped = <String, String>{};

    final configData = sourceConfig.configData.trim();
    final decodedJson = _tryDecodeJson(configData);
    final dnsPlan = _resolveDnsPlan(
      vpnSettings,
      capabilities,
      skipped,
      decodedJson: decodedJson,
    );
    final proxyOnly = _resolveProxyOnly(vpnSettings, capabilities, skipped);
    if (proxyOnly) {
      applied.add('proxy-only');
    }

    final mtu = _resolveMtu(vpnSettings, capabilities, skipped);
    final bypassSubnets = _resolveBypassSubnets(
      vpnSettings,
      capabilities,
      skipped,
    );

    if (configData.isEmpty) {
      skipped['configData'] = 'Missing source config data';
      return VpnRuntimeBuildResult(
        config: sourceConfig.copyWith(
          blockedApps: blockedApps,
          bypassSubnets: bypassSubnets,
          dnsServers: dnsPlan.servers,
          mtu: mtu,
          proxyOnly: proxyOnly,
        ),
        appliedSettings: applied,
        skippedSettings: skipped,
      );
    }

    final shouldBuildJson =
        _requiresJsonMutation(vpnSettings, dnsPlan: dnsPlan) ||
        decodedJson != null;

    if (!shouldBuildJson) {
      return VpnRuntimeBuildResult(
        config: sourceConfig.copyWith(
          blockedApps: blockedApps,
          bypassSubnets: bypassSubnets,
          dnsServers: dnsPlan.servers,
          mtu: mtu,
          proxyOnly: proxyOnly,
        ),
        appliedSettings: applied,
        skippedSettings: skipped,
      );
    }

    final jsonConfig = _resolveBaseJson(
      sourceConfig: sourceConfig,
      configData: configData,
      decodedJson: decodedJson,
    );

    _applyDns(jsonConfig, dnsPlan, applied);
    _applyLogSettings(jsonConfig, vpnSettings, applied);
    _applyRouting(jsonConfig, vpnSettings, capabilities, applied, skipped);
    _applyMux(jsonConfig, vpnSettings, capabilities, applied, skipped);
    _applyPreferredIpType(
      jsonConfig,
      vpnSettings,
      capabilities,
      applied,
      skipped,
    );
    _applyFragmentation(
      jsonConfig,
      vpnSettings,
      capabilities,
      applied,
      skipped,
    );
    _applySniffing(jsonConfig, vpnSettings, capabilities, applied, skipped);

    return VpnRuntimeBuildResult(
      config: sourceConfig.copyWith(
        configData: jsonEncode(jsonConfig),
        blockedApps: blockedApps,
        bypassSubnets: bypassSubnets,
        dnsServers: dnsPlan.servers,
        mtu: mtu,
        proxyOnly: proxyOnly,
      ),
      appliedSettings: applied,
      skippedSettings: skipped,
    );
  }

  Map<String, dynamic> _resolveBaseJson({
    required VpnConfigEntity sourceConfig,
    required String configData,
    Map<String, dynamic>? decodedJson,
  }) {
    final map = decodedJson;
    if (map != null && map['outbounds'] is List && map['inbounds'] is List) {
      return _deepCopyMap(map);
    }

    if (map != null) {
      return _buildConfigFromProfileMetadata(sourceConfig, map);
    }

    final parsed = FlutterV2ray.parseFromURL(configData);
    return _deepCopyMap(
      jsonDecode(parsed.getFullConfiguration()) as Map<String, dynamic>,
    );
  }

  Map<String, dynamic>? _tryDecodeJson(String raw) {
    try {
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  Map<String, dynamic> _buildConfigFromProfileMetadata(
    VpnConfigEntity sourceConfig,
    Map<String, dynamic> partial,
  ) {
    final transport =
        (partial['transport'] as Map?)?.cast<String, dynamic>() ??
        const <String, dynamic>{};
    final tls =
        (partial['tls'] as Map?)?.cast<String, dynamic>() ??
        const <String, dynamic>{};
    final params =
        (partial['params'] as Map?)?.cast<String, dynamic>() ??
        const <String, dynamic>{};

    final outbound = switch (sourceConfig.protocol) {
      VpnProtocol.vless => _buildVlessOutbound(
        sourceConfig,
        partial,
        transport,
        tls,
        params,
      ),
      VpnProtocol.vmess => _buildVmessOutbound(
        sourceConfig,
        partial,
        transport,
        tls,
        params,
      ),
      VpnProtocol.trojan => _buildTrojanOutbound(
        sourceConfig,
        partial,
        transport,
        tls,
      ),
      VpnProtocol.shadowsocks => _buildShadowsocksOutbound(
        sourceConfig,
        partial,
      ),
    };

    return {
      'log': {'access': '', 'error': '', 'loglevel': 'error', 'dnsLog': false},
      'inbounds': [
        {
          'tag': 'in_proxy',
          'port': 10807,
          'protocol': 'socks',
          'listen': '127.0.0.1',
          'settings': {'auth': 'noauth', 'udp': true, 'userLevel': 8},
          'sniffing': {'enabled': false},
        },
      ],
      'outbounds': [
        outbound,
        _buildDirectOutbound(),
        _buildBlackholeOutbound(),
      ],
      'dns': {'servers': VpnConstants.defaultDnsServers},
      'routing': {
        'domainStrategy': 'AsIs',
        'rules': <Map<String, dynamic>>[],
        'balancers': <Map<String, dynamic>>[],
      },
    };
  }

  Map<String, dynamic> _buildVlessOutbound(
    VpnConfigEntity sourceConfig,
    Map<String, dynamic> partial,
    Map<String, dynamic> transport,
    Map<String, dynamic> tls,
    Map<String, dynamic> params,
  ) {
    final userId = partial['uuid'] as String? ?? '';
    final encryption = params['encryption'] as String? ?? 'none';
    final flow = params['flow'] as String? ?? '';

    return {
      'tag': _proxyOutboundTag,
      'protocol': 'vless',
      'settings': {
        'vnext': [
          {
            'address': sourceConfig.serverAddress,
            'port': sourceConfig.port,
            'users': [
              {
                'id': userId,
                'security': 'auto',
                'level': 8,
                'encryption': encryption,
                'flow': flow,
              },
            ],
          },
        ],
      },
      'streamSettings': _buildStreamSettings(
        sourceConfig.serverAddress,
        transport,
        tls,
      ),
      'mux': {'enabled': false, 'concurrency': 8},
    };
  }

  Map<String, dynamic> _buildVmessOutbound(
    VpnConfigEntity sourceConfig,
    Map<String, dynamic> partial,
    Map<String, dynamic> transport,
    Map<String, dynamic> tls,
    Map<String, dynamic> params,
  ) {
    final userId = partial['uuid'] as String? ?? '';
    final alterId = params['alterId'] as int? ?? 0;
    final security = params['security'] as String? ?? 'auto';

    return {
      'tag': _proxyOutboundTag,
      'protocol': 'vmess',
      'settings': {
        'vnext': [
          {
            'address': sourceConfig.serverAddress,
            'port': sourceConfig.port,
            'users': [
              {
                'id': userId,
                'alterId': alterId,
                'security': security,
                'level': 8,
              },
            ],
          },
        ],
      },
      'streamSettings': _buildStreamSettings(
        sourceConfig.serverAddress,
        transport,
        tls,
      ),
      'mux': {'enabled': false, 'concurrency': 8},
    };
  }

  Map<String, dynamic> _buildTrojanOutbound(
    VpnConfigEntity sourceConfig,
    Map<String, dynamic> partial,
    Map<String, dynamic> transport,
    Map<String, dynamic> tls,
  ) {
    final password =
        partial['password'] as String? ?? partial['uuid'] as String? ?? '';

    return {
      'tag': _proxyOutboundTag,
      'protocol': 'trojan',
      'settings': {
        'servers': [
          {
            'address': sourceConfig.serverAddress,
            'port': sourceConfig.port,
            'password': password,
            'level': 8,
          },
        ],
      },
      'streamSettings': _buildStreamSettings(
        sourceConfig.serverAddress,
        transport,
        tls,
      ),
      'mux': {'enabled': false, 'concurrency': 8},
    };
  }

  Map<String, dynamic> _buildShadowsocksOutbound(
    VpnConfigEntity sourceConfig,
    Map<String, dynamic> partial,
  ) {
    final method = partial['uuid'] as String? ?? 'aes-256-gcm';
    final password = partial['password'] as String? ?? '';

    return {
      'tag': _proxyOutboundTag,
      'protocol': 'shadowsocks',
      'settings': {
        'servers': [
          {
            'address': sourceConfig.serverAddress,
            'port': sourceConfig.port,
            'method': method,
            'password': password,
            'level': 8,
          },
        ],
      },
      'mux': {'enabled': false, 'concurrency': 8},
    };
  }

  Map<String, dynamic> _buildStreamSettings(
    String address,
    Map<String, dynamic> transport,
    Map<String, dynamic> tls,
  ) {
    final network =
        (transport['type'] as String? ??
                transport['network'] as String? ??
                'tcp')
            .toLowerCase();
    final security = (tls['security'] as String? ?? 'none').toLowerCase();
    final stream = <String, dynamic>{
      'network': network == 'tcp' ? 'raw' : network,
      'security': security == 'none' ? 'none' : security,
    };

    if (network == 'ws') {
      stream['wsSettings'] = {
        'path': transport['path'] ?? '/',
        'headers': {if (transport['host'] != null) 'Host': transport['host']},
      };
    } else if (network == 'grpc') {
      stream['grpcSettings'] = {
        'serviceName': transport['serviceName'] ?? '',
        'multiMode': transport['mode'] == 'multi',
      };
    } else if (network == 'http' || network == 'h2') {
      stream['httpSettings'] = {
        'path': transport['path'] ?? '/',
        'host': [if (transport['host'] != null) transport['host']],
      };
    } else if (network == 'quic') {
      stream['quicSettings'] = {
        'security': transport['quicSecurity'] ?? 'none',
        'key': transport['key'] ?? '',
        'header': {'type': transport['headerType'] ?? 'none'},
      };
    } else if (network == 'kcp') {
      stream['kcpSettings'] = {
        'header': {'type': transport['headerType'] ?? 'none'},
        if (transport['seed'] != null) 'seed': transport['seed'],
      };
    }

    if (security == 'tls') {
      stream['tlsSettings'] = {
        'serverName': tls['sni'] ?? address,
        if (tls['alpn'] is String)
          'alpn': (tls['alpn'] as String)
              .split(',')
              .map((value) => value.trim())
              .where((value) => value.isNotEmpty)
              .toList(),
        if (tls['fingerprint'] != null) 'fingerprint': tls['fingerprint'],
        if (tls['allowInsecure'] == true) 'allowInsecure': true,
      };
    } else if (security == 'reality') {
      stream['realitySettings'] = {
        'serverName': tls['sni'] ?? address,
        if (tls['fingerprint'] != null) 'fingerprint': tls['fingerprint'],
        if (tls['publicKey'] != null) 'publicKey': tls['publicKey'],
        if (tls['shortId'] != null) 'shortId': tls['shortId'],
      };
    }

    return stream;
  }

  Map<String, dynamic> _buildDirectOutbound() {
    return {
      'tag': _directOutboundTag,
      'protocol': 'freedom',
      'settings': {'domainStrategy': 'AsIs'},
    };
  }

  Map<String, dynamic> _buildBlackholeOutbound() {
    return {
      'tag': _blockOutboundTag,
      'protocol': 'blackhole',
      'settings': <String, dynamic>{},
    };
  }

  _DnsPlan _resolveDnsPlan(
    VpnSettings vpnSettings,
    VpnRuntimeCapabilities capabilities,
    Map<String, String> skipped, {
    required Map<String, dynamic>? decodedJson,
  }) {
    if (vpnSettings.useDnsFromJson) {
      final jsonServers = _readJsonDnsServers(decodedJson);
      if (jsonServers != null) {
        return const _DnsPlan(
          servers: null,
          preserveJsonDns: true,
          appliedLabel: 'dns:json',
        );
      }

      skipped['dnsFromJson'] =
          'DNS from JSON requested but the source config has no DNS servers';
    }

    if (vpnSettings.useLocalDns) {
      if (!capabilities.supportsLocalDns) {
        skipped['localDns'] =
            'Local DNS is not supported by the current mobile runtime bridge';
      } else {
        return const _DnsPlan(
          servers: ['127.0.0.1'],
          preserveJsonDns: false,
          appliedLabel: 'dns:local',
        );
      }
    }

    if (!capabilities.supportsDnsOverride) {
      skipped['dns'] = 'DNS overrides are unsupported on this platform';
      return const _DnsPlan();
    }

    return switch (vpnSettings.dnsProvider) {
      DnsProvider.system => const _DnsPlan(
        servers: null,
        preserveJsonDns: false,
        appliedLabel: 'dns:system',
      ),
      DnsProvider.cloudflare => const _DnsPlan(
        servers: [
          VpnConstants.cloudflareIPv4Primary,
          VpnConstants.cloudflareIPv4Secondary,
        ],
        preserveJsonDns: false,
        appliedLabel: 'dns:override',
      ),
      DnsProvider.google => const _DnsPlan(
        servers: [
          VpnConstants.googleIPv4Primary,
          VpnConstants.googleIPv4Secondary,
        ],
        preserveJsonDns: false,
        appliedLabel: 'dns:override',
      ),
      DnsProvider.quad9 => const _DnsPlan(
        servers: [
          VpnConstants.quad9IPv4Primary,
          VpnConstants.quad9IPv4Secondary,
        ],
        preserveJsonDns: false,
        appliedLabel: 'dns:override',
      ),
      DnsProvider.custom => () {
        final customDns = vpnSettings.customDns?.trim();
        if (customDns == null || customDns.isEmpty) {
          skipped['dns'] = 'Custom DNS selected without a server address';
          return const _DnsPlan(
            servers: null,
            preserveJsonDns: false,
            appliedLabel: 'dns:system',
          );
        }
        return _DnsPlan(
          servers: [customDns],
          preserveJsonDns: false,
          appliedLabel: 'dns:override',
        );
      }(),
    };
  }

  bool _requiresJsonMutation(
    VpnSettings vpnSettings, {
    required _DnsPlan dnsPlan,
  }) {
    return dnsPlan.servers != null ||
        vpnSettings.logLevel != LogLevel.error ||
        vpnSettings.routingEnabled ||
        vpnSettings.muxEnabled ||
        vpnSettings.fragmentationEnabled ||
        vpnSettings.preferredIpType != PreferredIpType.auto ||
        vpnSettings.sniffingEnabled;
  }

  int? _resolveMtu(
    VpnSettings vpnSettings,
    VpnRuntimeCapabilities capabilities,
    Map<String, String> skipped,
  ) {
    if (vpnSettings.mtuMode != MtuMode.manual) {
      return null;
    }

    if (!capabilities.supportsManualMtu) {
      skipped['mtu'] = 'Manual MTU is unsupported on this platform';
      return null;
    }

    if (vpnSettings.mtuValue <= 0) {
      skipped['mtu'] = 'Manual MTU must be a positive integer';
      return null;
    }

    return vpnSettings.mtuValue;
  }

  List<String> _resolveBypassSubnets(
    VpnSettings vpnSettings,
    VpnRuntimeCapabilities capabilities,
    Map<String, String> skipped,
  ) {
    final entries = vpnSettings.excludedRouteEntries.isNotEmpty
        ? vpnSettings.excludedRouteEntries
        : vpnSettings.bypassSubnets
              .where((subnet) => subnet.trim().isNotEmpty)
              .map(ExcludedRouteEntry.parse)
              .toList(growable: false);

    if (entries.isEmpty) {
      return const <String>[];
    }

    if (!capabilities.supportsExcludedRoutes) {
      skipped['excludedRoutes'] =
          'Excluded routes are unsupported on this platform';
      return const <String>[];
    }

    final normalized = <String>[];
    for (final entry in entries) {
      final raw = entry.normalizedValue;
      final isCidr = entry.isCidr;
      final isIpv6 = entry.isIpv6;
      if (raw.isEmpty) {
        continue;
      }
      final cidr = isCidr ? raw : '$raw/${isIpv6 ? 128 : 32}';
      if (!normalized.contains(cidr)) {
        normalized.add(cidr);
      }
    }

    return normalized;
  }

  void _applyDns(
    Map<String, dynamic> jsonConfig,
    _DnsPlan dnsPlan,
    List<String> applied,
  ) {
    final dnsConfig = _ensureMap(jsonConfig, 'dns');
    if (dnsPlan.preserveJsonDns && _readJsonDnsServers(jsonConfig) != null) {
      applied.add(dnsPlan.appliedLabel ?? 'dns:json');
      return;
    }

    dnsConfig['servers'] = dnsPlan.servers ?? VpnConstants.defaultDnsServers;
    applied.add(dnsPlan.appliedLabel ?? 'dns:system');
  }

  void _applyLogSettings(
    Map<String, dynamic> jsonConfig,
    VpnSettings vpnSettings,
    List<String> applied,
  ) {
    final logConfig = _ensureMap(jsonConfig, 'log');
    final runtimeLevel = switch (vpnSettings.logLevel) {
      LogLevel.auto => 'warning',
      LogLevel.debug => 'debug',
      LogLevel.info => 'info',
      LogLevel.warning => 'warning',
      LogLevel.error => 'error',
      LogLevel.none => 'none',
    };

    logConfig['loglevel'] = runtimeLevel;
    logConfig['dnsLog'] = runtimeLevel == 'debug';
    applied.add('log-level:$runtimeLevel');
  }

  void _applyRouting(
    Map<String, dynamic> jsonConfig,
    VpnSettings vpnSettings,
    VpnRuntimeCapabilities capabilities,
    List<String> applied,
    Map<String, String> skipped,
  ) {
    final routingConfig = _ensureMap(jsonConfig, 'routing');
    final rules = <Map<String, dynamic>>[];

    if (!vpnSettings.routingEnabled) {
      routingConfig['rules'] = rules;
      routingConfig['domainStrategy'] = 'AsIs';
      return;
    }

    if (!capabilities.supportsRoutingRules) {
      skipped['routing'] = 'Routing rules are unsupported on this platform';
      return;
    }

    final profile = vpnSettings.activeRoutingProfile;
    if (profile == null || !profile.enabled) {
      skipped['routing'] = 'Routing is enabled without an active profile';
      return;
    }

    var requiresIpResolution = false;

    for (final rule in profile.rules.where((rule) => rule.enabled)) {
      final translated = _translateRoutingRule(rule, skipped);
      if (translated == null) {
        continue;
      }

      if (translated.containsKey('ip')) {
        requiresIpResolution = true;
      }

      rules.add(translated);
    }

    routingConfig['rules'] = rules;
    routingConfig['balancers'] = <Map<String, dynamic>>[];
    routingConfig['domainStrategy'] = requiresIpResolution
        ? 'IPIfNonMatch'
        : 'AsIs';

    if (rules.isNotEmpty) {
      applied.add('routing:${profile.id}');
    }
  }

  Map<String, dynamic>? _translateRoutingRule(
    RoutingRule rule,
    Map<String, String> skipped,
  ) {
    final outboundTag = switch (rule.action) {
      RoutingRuleAction.proxy => _proxyOutboundTag,
      RoutingRuleAction.direct => _directOutboundTag,
      RoutingRuleAction.block => _blockOutboundTag,
    };

    final translated = <String, dynamic>{
      'outboundTag': outboundTag,
      'ruleTag': rule.note?.trim().isNotEmpty == true
          ? rule.note!.trim()
          : rule.id,
    };

    switch (rule.matchType) {
      case RoutingRuleMatchType.domain:
        translated['domain'] = ['full:${rule.value}'];
      case RoutingRuleMatchType.domainSuffix:
        translated['domain'] = ['domain:${rule.value}'];
      case RoutingRuleMatchType.domainKeyword:
        translated['domain'] = ['keyword:${rule.value}'];
      case RoutingRuleMatchType.ipCidr:
        translated['ip'] = [rule.value];
      case RoutingRuleMatchType.geoSite:
        translated['domain'] = ['geosite:${rule.value}'];
      case RoutingRuleMatchType.geoIp:
        translated['ip'] = ['geoip:${rule.value}'];
      case RoutingRuleMatchType.processName:
        skipped['routing:${rule.id}'] =
            'processName rules are unsupported on mobile Xray runtimes';
        return null;
      case RoutingRuleMatchType.packageName:
        skipped['routing:${rule.id}'] =
            'packageName rules are unsupported by Xray routing rules';
        return null;
    }

    return translated;
  }

  void _applyMux(
    Map<String, dynamic> jsonConfig,
    VpnSettings vpnSettings,
    VpnRuntimeCapabilities capabilities,
    List<String> applied,
    Map<String, String> skipped,
  ) {
    if (!vpnSettings.muxEnabled) {
      return;
    }

    if (!capabilities.supportsMux) {
      skipped['mux'] = 'Mux is unsupported on this platform';
      return;
    }

    final proxyOutbound = _ensurePrimaryProxyOutbound(jsonConfig);
    proxyOutbound['mux'] = {'enabled': true, 'concurrency': 8};
    applied.add('mux');
  }

  void _applyPreferredIpType(
    Map<String, dynamic> jsonConfig,
    VpnSettings vpnSettings,
    VpnRuntimeCapabilities capabilities,
    List<String> applied,
    Map<String, String> skipped,
  ) {
    if (vpnSettings.preferredIpType == PreferredIpType.auto) {
      return;
    }

    if (!capabilities.supportsPreferredIpType) {
      skipped['preferredIpType'] =
          'Preferred IP type is unsupported on this platform';
      return;
    }

    final strategy = switch (vpnSettings.preferredIpType) {
      PreferredIpType.auto => 'AsIs',
      PreferredIpType.ipv4 => 'UseIPv4',
      PreferredIpType.ipv6 => 'UseIPv6',
    };

    final dnsStrategy = switch (vpnSettings.preferredIpType) {
      PreferredIpType.auto => 'UseSystem',
      PreferredIpType.ipv4 => 'UseIPv4',
      PreferredIpType.ipv6 => 'UseIPv6',
    };

    final proxyOutbound = _ensurePrimaryProxyOutbound(jsonConfig);
    proxyOutbound['targetStrategy'] = strategy;

    final streamSettings = _ensureMap(proxyOutbound, 'streamSettings');
    final sockopt = _ensureMap(streamSettings, 'sockopt');
    sockopt['domainStrategy'] = strategy;

    final directOutbound = _ensureTaggedOutbound(
      jsonConfig,
      tag: _directOutboundTag,
      fallback: _buildDirectOutbound(),
    );
    final directSettings = _ensureMap(directOutbound, 'settings');
    directSettings['domainStrategy'] = strategy;

    final dnsConfig = _ensureMap(jsonConfig, 'dns');
    dnsConfig['queryStrategy'] = dnsStrategy;

    applied.add('preferred-ip:${vpnSettings.preferredIpType.name}');
  }

  void _applyFragmentation(
    Map<String, dynamic> jsonConfig,
    VpnSettings vpnSettings,
    VpnRuntimeCapabilities capabilities,
    List<String> applied,
    Map<String, String> skipped,
  ) {
    if (!vpnSettings.fragmentationEnabled) {
      _removeOutbound(jsonConfig, _fragmentDialerTag);

      final proxyOutbound = _ensurePrimaryProxyOutbound(jsonConfig);
      final streamSettings = proxyOutbound['streamSettings'];
      if (streamSettings is Map<String, dynamic>) {
        final sockopt = streamSettings['sockopt'];
        if (sockopt is Map<String, dynamic> &&
            sockopt['dialerProxy'] == _fragmentDialerTag) {
          sockopt.remove('dialerProxy');
          if (sockopt.isEmpty) {
            streamSettings.remove('sockopt');
          }
        }
      }
      return;
    }

    if (!capabilities.supportsFragmentation) {
      skipped['fragmentation'] =
          'Fragmentation is unsupported on this platform';
      return;
    }

    final proxyOutbound = _ensurePrimaryProxyOutbound(jsonConfig);
    final streamSettings = _ensureMap(proxyOutbound, 'streamSettings');
    final sockopt = _ensureMap(streamSettings, 'sockopt');
    sockopt['dialerProxy'] = _fragmentDialerTag;

    final fragmentOutbound = <String, dynamic>{
      'tag': _fragmentDialerTag,
      'protocol': 'freedom',
      'settings': {
        'domainStrategy': 'AsIs',
        'fragment': {
          'packets': 'tlshello',
          'length': '100-200',
          'interval': '10-20',
        },
      },
    };

    _upsertOutbound(jsonConfig, fragmentOutbound);
    applied.add('fragmentation');
  }

  void _applySniffing(
    Map<String, dynamic> jsonConfig,
    VpnSettings vpnSettings,
    VpnRuntimeCapabilities capabilities,
    List<String> applied,
    Map<String, String> skipped,
  ) {
    final inbounds = jsonConfig['inbounds'];
    if (inbounds is! List) {
      if (vpnSettings.sniffingEnabled) {
        skipped['sniffing'] = 'Config has no inbounds to apply sniffing to';
      }
      return;
    }

    if (!vpnSettings.sniffingEnabled) {
      for (final inbound in inbounds.whereType<Map<String, dynamic>>()) {
        if (inbound['tag'] == 'api') {
          continue;
        }
        inbound['sniffing'] = {
          'enabled': false,
          'destOverride': ['http', 'tls', 'quic'],
          'metadataOnly': false,
        };
      }
      return;
    }

    if (!capabilities.supportsSniffing) {
      skipped['sniffing'] = 'Packet analysis is unsupported on this platform';
      return;
    }

    for (final inbound in inbounds.whereType<Map<String, dynamic>>()) {
      if (inbound['tag'] == 'api') {
        continue;
      }

      inbound['sniffing'] = {
        'enabled': true,
        'destOverride': ['http', 'tls', 'quic'],
        'metadataOnly': false,
      };
    }

    applied.add('sniffing');
  }

  bool _resolveProxyOnly(
    VpnSettings vpnSettings,
    VpnRuntimeCapabilities capabilities,
    Map<String, String> skipped,
  ) {
    if (vpnSettings.vpnRunMode != VpnRunMode.proxyOnly) {
      return false;
    }

    if (!capabilities.supportsProxyOnlyMode) {
      skipped['proxyOnly'] = 'Proxy-only mode is unsupported on this platform';
      return false;
    }

    return true;
  }

  List<String>? _readJsonDnsServers(Map<String, dynamic>? jsonConfig) {
    final dns = jsonConfig?['dns'];
    if (dns is! Map<String, dynamic>) {
      return null;
    }

    final servers = dns['servers'];
    if (servers is! List) {
      return null;
    }

    final result = servers
        .whereType<String>()
        .map((value) => value.trim())
        .where((value) => value.isNotEmpty)
        .toList();

    return result.isEmpty ? null : result;
  }

  Map<String, dynamic> _ensurePrimaryProxyOutbound(Map<String, dynamic> json) {
    return _ensureTaggedOutbound(
      json,
      tag: _proxyOutboundTag,
      fallback: _buildDirectOutbound()
        ..['tag'] = _proxyOutboundTag
        ..['protocol'] = 'freedom',
    );
  }

  Map<String, dynamic> _ensureTaggedOutbound(
    Map<String, dynamic> jsonConfig, {
    required String tag,
    required Map<String, dynamic> fallback,
  }) {
    final outbounds = _ensureOutbounds(jsonConfig);
    for (final outbound in outbounds) {
      if (outbound['tag'] == tag) {
        return outbound;
      }
    }
    final inserted = _deepCopyMap(fallback);
    outbounds.add(inserted);
    return inserted;
  }

  void _upsertOutbound(
    Map<String, dynamic> jsonConfig,
    Map<String, dynamic> outbound,
  ) {
    final outbounds = _ensureOutbounds(jsonConfig);
    for (var i = 0; i < outbounds.length; i++) {
      if (outbounds[i]['tag'] == outbound['tag']) {
        outbounds[i] = outbound;
        return;
      }
    }
    outbounds.add(outbound);
  }

  void _removeOutbound(Map<String, dynamic> jsonConfig, String tag) {
    final outbounds = _ensureOutbounds(jsonConfig);
    outbounds.removeWhere((outbound) => outbound['tag'] == tag);
  }

  List<Map<String, dynamic>> _ensureOutbounds(Map<String, dynamic> jsonConfig) {
    final existing = jsonConfig['outbounds'];
    if (existing is List<Map<String, dynamic>>) {
      return existing;
    }
    if (existing is List) {
      final casted = existing
          .whereType<Map<Object?, Object?>>()
          .map(Map<String, dynamic>.from)
          .toList();
      jsonConfig['outbounds'] = casted;
      return casted;
    }

    final created = <Map<String, dynamic>>[];
    jsonConfig['outbounds'] = created;
    return created;
  }

  Map<String, dynamic> _ensureMap(Map<String, dynamic> parent, String key) {
    final current = parent[key];
    if (current is Map<String, dynamic>) {
      return current;
    }
    if (current is Map) {
      final casted = Map<String, dynamic>.from(current);
      parent[key] = casted;
      return casted;
    }
    final created = <String, dynamic>{};
    parent[key] = created;
    return created;
  }

  Map<String, dynamic> _deepCopyMap(Map<String, dynamic> input) {
    return Map<String, dynamic>.from(
      jsonDecode(jsonEncode(input)) as Map<String, dynamic>,
    );
  }
}
