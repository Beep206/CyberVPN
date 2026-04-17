import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_v2ray_plus/flutter_v2ray.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/services/vpn_runtime_capabilities.dart';

typedef DohLookup =
    Future<List<InternetAddress>> Function({
      required Uri dohUrl,
      required String host,
      required InternetAddressType type,
      String? dnsIp,
    });
typedef HostLookup =
    Future<List<InternetAddress>> Function(
      String host, {
      InternetAddressType type,
    });
typedef TcpProbe =
    Future<Duration?> Function(String address, int port, {Duration timeout});

class VpnServerAddressResolveResult {
  const VpnServerAddressResolveResult({
    required this.config,
    this.selectedAddress,
    this.candidateAddresses = const <String>[],
    this.appliedSettings = const <String>[],
    this.skippedSettings = const <String, String>{},
  });

  final VpnConfigEntity config;
  final String? selectedAddress;
  final List<String> candidateAddresses;
  final List<String> appliedSettings;
  final Map<String, String> skippedSettings;
}

class VpnServerAddressResolver {
  VpnServerAddressResolver({
    HostLookup? hostLookup,
    DohLookup? dohLookup,
    TcpProbe? tcpProbe,
  }) : _hostLookup = hostLookup ?? _defaultHostLookup,
       _dohLookup = dohLookup ?? _defaultDohLookup,
       _tcpProbe = tcpProbe ?? _defaultTcpProbe;

  static const _defaultProbeTimeout = Duration(milliseconds: 1200);

  final HostLookup _hostLookup;
  final DohLookup _dohLookup;
  final TcpProbe _tcpProbe;

  Future<VpnServerAddressResolveResult> resolve({
    required VpnConfigEntity sourceConfig,
    required VpnSettings vpnSettings,
    required VpnRuntimeCapabilities capabilities,
  }) async {
    if (!vpnSettings.serverAddressResolveEnabled) {
      return VpnServerAddressResolveResult(config: sourceConfig);
    }

    if (!capabilities.supportsServerAddressResolve) {
      return VpnServerAddressResolveResult(
        config: sourceConfig,
        skippedSettings: const {
          'serverResolve':
              'Server address resolve is unsupported on this platform',
        },
      );
    }

    final host = sourceConfig.serverAddress.trim();
    if (host.isEmpty) {
      return VpnServerAddressResolveResult(
        config: sourceConfig,
        skippedSettings: const {
          'serverResolve': 'Server address resolve requires a non-empty host',
        },
      );
    }

    if (InternetAddress.tryParse(host) != null) {
      return VpnServerAddressResolveResult(
        config: sourceConfig,
        skippedSettings: const {
          'serverResolve':
              'Server address resolve skipped because the server address is already numeric',
        },
      );
    }

    final lookupType = switch (vpnSettings.preferredIpType) {
      PreferredIpType.auto => InternetAddressType.any,
      PreferredIpType.ipv4 => InternetAddressType.IPv4,
      PreferredIpType.ipv6 => InternetAddressType.IPv6,
    };

    final applied = <String>[];
    final skipped = <String, String>{};
    final candidates = <InternetAddress>[];
    final dohValue = vpnSettings.serverAddressResolveDohUrl?.trim();
    final dnsIpValue = vpnSettings.serverAddressResolveDnsIp?.trim();

    if (dohValue != null && dohValue.isNotEmpty) {
      final dohUri = Uri.tryParse(dohValue);
      if (dohUri == null || !dohUri.hasScheme || !dohUri.hasAuthority) {
        skipped['serverResolve'] =
            'Server resolve DoH URL must be a valid absolute URL';
      } else {
        try {
          candidates.addAll(
            await _dohLookup(
              dohUrl: dohUri,
              host: host,
              type: lookupType,
              dnsIp: dnsIpValue?.isEmpty == true ? null : dnsIpValue,
            ),
          );
          if (candidates.isNotEmpty) {
            applied.add('server-resolve:doh');
          }
        } catch (error) {
          skipped['serverResolve'] = 'DoH lookup failed: $error';
        }
      }
    }

    if (candidates.isEmpty) {
      try {
        candidates.addAll(await _hostLookup(host, type: lookupType));
        if (candidates.isNotEmpty) {
          applied.add('server-resolve:system');
        }
      } catch (error) {
        skipped['serverResolve'] = 'System DNS lookup failed: $error';
      }
    }

    final uniqueCandidates = _dedupeAddresses(candidates);
    if (uniqueCandidates.isEmpty) {
      return VpnServerAddressResolveResult(
        config: sourceConfig,
        appliedSettings: applied,
        skippedSettings: skipped.isNotEmpty
            ? skipped
            : const {
                'serverResolve':
                    'No IP addresses were resolved for the configured host',
              },
      );
    }

    final selected = await _selectBestAddress(
      uniqueCandidates,
      sourceConfig.port,
      skipped,
    );

    if (selected == null) {
      return VpnServerAddressResolveResult(
        config: sourceConfig,
        appliedSettings: applied,
        skippedSettings: skipped,
      );
    }

    if (selected == host) {
      return VpnServerAddressResolveResult(
        config: sourceConfig,
        selectedAddress: selected,
        candidateAddresses: uniqueCandidates
            .map((candidate) => candidate.address)
            .toList(growable: false),
        appliedSettings: applied,
        skippedSettings: skipped,
      );
    }

    return VpnServerAddressResolveResult(
      config: _patchResolvedAddress(
        sourceConfig,
        originalHost: host,
        ip: selected,
      ),
      selectedAddress: selected,
      candidateAddresses: uniqueCandidates
          .map((candidate) => candidate.address)
          .toList(growable: false),
      appliedSettings: [...applied, 'server-resolve:selected'],
      skippedSettings: skipped,
    );
  }

  Future<String?> _selectBestAddress(
    List<InternetAddress> candidates,
    int port,
    Map<String, String> skipped,
  ) async {
    if (candidates.isEmpty) {
      skipped['serverResolve'] =
          'No candidate addresses were available for probing';
      return null;
    }

    if (candidates.length == 1) {
      return candidates.first.address;
    }

    final probeResults = await Future.wait(
      candidates.map((candidate) async {
        final latency = await _tcpProbe(
          candidate.address,
          port,
          timeout: _defaultProbeTimeout,
        );
        return (candidate: candidate, latency: latency);
      }),
    );

    final successful =
        probeResults.where((result) => result.latency != null).toList()
          ..sort((left, right) => left.latency!.compareTo(right.latency!));

    if (successful.isNotEmpty) {
      return successful.first.candidate.address;
    }

    skipped['serverResolve:probe'] =
        'Pre-connect probes failed for all resolved addresses; using the first candidate';
    return candidates.first.address;
  }

  VpnConfigEntity _patchResolvedAddress(
    VpnConfigEntity sourceConfig, {
    required String originalHost,
    required String ip,
  }) {
    final patchedConfigData = _patchConfigData(
      sourceConfig.configData,
      originalHost: originalHost,
      ip: ip,
    );

    return sourceConfig.copyWith(
      serverAddress: ip,
      configData: patchedConfigData,
    );
  }

  String _patchConfigData(
    String configData, {
    required String originalHost,
    required String ip,
  }) {
    final trimmed = configData.trim();
    if (trimmed.isEmpty) {
      return trimmed;
    }

    final decodedJson = _tryDecodeJson(trimmed);
    if (decodedJson != null) {
      return jsonEncode(
        _patchJsonConfig(decodedJson, originalHost: originalHost, ip: ip),
      );
    }

    try {
      final fullConfig =
          jsonDecode(FlutterV2ray.parseFromURL(trimmed).getFullConfiguration())
              as Map<String, dynamic>;
      return jsonEncode(
        _patchJsonConfig(fullConfig, originalHost: originalHost, ip: ip),
      );
    } catch (_) {
      return trimmed;
    }
  }

  Map<String, dynamic> _patchJsonConfig(
    Map<String, dynamic> source, {
    required String originalHost,
    required String ip,
  }) {
    final root = _deepCopyMap(source);
    final outbounds = root['outbounds'];
    if (outbounds is! List) {
      return root;
    }

    for (final outbound in outbounds.whereType<Map<String, dynamic>>()) {
      final settings = outbound['settings'];
      if (settings is! Map<String, dynamic>) {
        continue;
      }

      final vnext = settings['vnext'];
      if (vnext is List) {
        for (final server in vnext.whereType<Map<String, dynamic>>()) {
          if (server['address'] == originalHost) {
            server['address'] = ip;
          }
        }
      }

      final servers = settings['servers'];
      if (servers is List) {
        for (final server in servers.whereType<Map<String, dynamic>>()) {
          if (server['address'] == originalHost) {
            server['address'] = ip;
          }
        }
      }

      if (settings['address'] == originalHost) {
        settings['address'] = ip;
      }
    }

    return root;
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

  Map<String, dynamic> _deepCopyMap(Map<String, dynamic> source) {
    return jsonDecode(jsonEncode(source)) as Map<String, dynamic>;
  }

  List<InternetAddress> _dedupeAddresses(List<InternetAddress> candidates) {
    final seen = <String>{};
    final result = <InternetAddress>[];
    for (final candidate in candidates) {
      if (seen.add(candidate.address)) {
        result.add(candidate);
      }
    }
    return result;
  }

  static Future<List<InternetAddress>> _defaultHostLookup(
    String host, {
    InternetAddressType type = InternetAddressType.any,
  }) {
    return InternetAddress.lookup(host, type: type);
  }

  static Future<Duration?> _defaultTcpProbe(
    String address,
    int port, {
    Duration timeout = _defaultProbeTimeout,
  }) async {
    final stopwatch = Stopwatch()..start();
    Socket? socket;

    try {
      socket = await Socket.connect(address, port, timeout: timeout);
      stopwatch.stop();
      return stopwatch.elapsed;
    } catch (_) {
      return null;
    } finally {
      await socket?.close();
    }
  }

  static Future<List<InternetAddress>> _defaultDohLookup({
    required Uri dohUrl,
    required String host,
    required InternetAddressType type,
    String? dnsIp,
  }) async {
    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 3)
      ..idleTimeout = const Duration(seconds: 1)
      ..findProxy = (_) => 'DIRECT';

    final trimmedDnsIp = dnsIp?.trim();
    if (trimmedDnsIp != null && trimmedDnsIp.isNotEmpty) {
      final targetPort = dohUrl.hasPort
          ? dohUrl.port
          : (dohUrl.scheme == 'https' ? 443 : 80);
      client.connectionFactory = (uri, proxyHost, proxyPort) {
        return Future.value(
          ConnectionTask.fromSocket(
            Socket.connect(
              trimmedDnsIp,
              targetPort,
              timeout: client.connectionTimeout,
            ),
            () {},
          ),
        );
      };
    }

    try {
      final recordTypes = switch (type) {
        InternetAddressType.IPv4 => const ['A'],
        InternetAddressType.IPv6 => const ['AAAA'],
        _ => const ['A', 'AAAA'],
      };

      final responses = await Future.wait(
        recordTypes.map(
          (recordType) => _fetchDohRecords(
            client,
            dohUrl: dohUrl,
            host: host,
            recordType: recordType,
          ),
        ),
      );

      final addresses = <InternetAddress>[
        for (final response in responses) ...response,
      ];
      return addresses;
    } finally {
      client.close(force: true);
    }
  }

  static Future<List<InternetAddress>> _fetchDohRecords(
    HttpClient client, {
    required Uri dohUrl,
    required String host,
    required String recordType,
  }) async {
    final uri = dohUrl.replace(
      queryParameters: {
        ...dohUrl.queryParameters,
        'name': host,
        'type': recordType,
      },
    );

    final request = await client.getUrl(uri);
    request.headers.set(HttpHeaders.acceptHeader, 'application/dns-json');
    final response = await request.close();
    final body = await response.transform(utf8.decoder).join();

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw HttpException(
        'DoH request failed with status ${response.statusCode}',
        uri: uri,
      );
    }

    final decoded = jsonDecode(body);
    if (decoded is! Map<String, dynamic>) {
      return const <InternetAddress>[];
    }

    final answers = decoded['Answer'];
    if (answers is! List) {
      return const <InternetAddress>[];
    }

    final addresses = <InternetAddress>[];
    for (final answer in answers.whereType<Map<String, dynamic>>()) {
      final data = answer['data'];
      if (data is! String) continue;
      final parsed = InternetAddress.tryParse(data.trim());
      if (parsed != null) {
        addresses.add(parsed);
      }
    }

    return addresses;
  }
}
