import 'dart:convert';
import 'package:yaml/yaml.dart';

import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/usecases/parse_vpn_uri.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/models/parsed_server.dart';

/// Supported subscription formats.
enum SubscriptionPayloadFormat {
  /// Base64 or plain text list of V2Ray URIs (vless://, vmess://, etc.)
  uriList,

  /// Clash Meta / Mihomo configuration with `proxies:` list
  clashYaml,

  /// Sing-box configuration with `outbounds:` list
  singboxJson,
}

/// Universal multi-format parser for VPN subscriptions.
///
/// Supports:
/// - Standard line-based Base64 / plain URI lists
/// - Clash Meta / Mihomo YAML subscriptions (`proxies:`)
/// - Sing-box JSON subscriptions (`outbounds:`)
class SubscriptionFormatParser {
  SubscriptionFormatParser({ParseVpnUri? parseVpnUri})
    : _parseVpnUri = parseVpnUri ?? ParseVpnUri();

  final ParseVpnUri _parseVpnUri;

  /// Parses the raw (or base64-decoded) subscription body into a list of [ParsedServer].
  (List<ParsedServer>, List<String>) parse(String decodedBody) {
    final trimmed = decodedBody.trim();
    if (trimmed.isEmpty) return (const [], const []);

    // 1. Try Sing-box JSON format first if starts with '{'
    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      final singboxResult = _tryParseSingbox(trimmed);
      if (singboxResult != null) {
        return singboxResult;
      }
    }

    // 2. Try Clash Meta YAML if it contains 'proxies:'
    if (trimmed.contains('proxies:')) {
      final clashResult = _tryParseClash(trimmed);
      if (clashResult != null) {
        return clashResult;
      }
    }

    // 3. Fallback to standard line-separated URI list
    return _parseUriList(trimmed);
  }

  /// Parses a line-separated list of VPN URIs.
  (List<ParsedServer>, List<String>) _parseUriList(String content) {
    final lines = content.split(RegExp(r'\r?\n'));
    final servers = <ParsedServer>[];
    final errors = <String>[];

    for (var i = 0; i < lines.length; i++) {
      final line = lines[i].trim();
      if (line.isEmpty) continue;

      final result = _parseVpnUri.call(line);
      switch (result) {
        case ParseSuccess(:final config):
          servers.add(
            ParsedServer(
              name:
                  config.remark ?? '${config.protocol}:${config.serverAddress}',
              rawUri: line,
              protocol: config.protocol,
              serverAddress: config.serverAddress,
              port: config.port,
              configData: <String, dynamic>{
                'uuid': config.uuid,
                if (config.password != null) 'password': config.password,
                if (config.transportSettings != null)
                  'transport': config.transportSettings,
                if (config.tlsSettings != null) 'tls': config.tlsSettings,
                if (config.additionalParams != null)
                  'params': config.additionalParams,
              },
            ),
          );
        case ParseFailure(:final message):
          errors.add('Line ${i + 1}: $message');
      }
    }

    return (servers, errors);
  }

  /// Attempts to parse Sing-box JSON format.
  (List<ParsedServer>, List<String>)? _tryParseSingbox(String content) {
    try {
      final dynamic decoded = jsonDecode(content);
      if (decoded is! Map<String, dynamic>) return null;

      final dynamic outbounds = decoded['outbounds'];
      if (outbounds is! List) return null;

      final servers = <ParsedServer>[];
      final errors = <String>[];

      for (var i = 0; i < outbounds.length; i++) {
        final dynamic item = outbounds[i];
        if (item is! Map) continue;
        final map = item.cast<String, dynamic>();

        final type = (map['type'] as String? ?? '').toLowerCase();
        // Skip non-proxy outbound nodes
        if (_isNonProxyOutbound(type)) continue;

        final uri = _convertSingboxOutboundToUri(map);
        if (uri == null) {
          errors.add(
            'Sing-box outbound ${map['tag'] ?? i}: unsupported type "$type"',
          );
          continue;
        }

        final result = _parseVpnUri.call(uri);
        switch (result) {
          case ParseSuccess(:final config):
            servers.add(
              ParsedServer(
                name:
                    config.remark ??
                    map['tag'] as String? ??
                    '${config.protocol}:${config.serverAddress}',
                rawUri: uri,
                protocol: config.protocol,
                serverAddress: config.serverAddress,
                port: config.port,
                configData: <String, dynamic>{
                  'uuid': config.uuid,
                  if (config.password != null) 'password': config.password,
                  if (config.transportSettings != null)
                    'transport': config.transportSettings,
                  if (config.tlsSettings != null) 'tls': config.tlsSettings,
                  if (config.additionalParams != null)
                    'params': config.additionalParams,
                },
              ),
            );
          case ParseFailure(:final message):
            errors.add('Sing-box outbound ${map['tag'] ?? i}: $message');
        }
      }

      if (servers.isEmpty && errors.isEmpty) {
        return null;
      }
      return (servers, errors);
    } catch (_) {
      return null;
    }
  }

  /// Attempts to parse Clash Meta YAML format.
  (List<ParsedServer>, List<String>)? _tryParseClash(String content) {
    try {
      final dynamic doc = loadYaml(content);
      if (doc is! Map) return null;

      final dynamic proxies = doc['proxies'];
      if (proxies is! List) return null;

      final servers = <ParsedServer>[];
      final errors = <String>[];

      for (var i = 0; i < proxies.length; i++) {
        final dynamic item = proxies[i];
        if (item is! Map) continue;
        final map = <String, dynamic>{};
        for (final entry in item.entries) {
          map[entry.key.toString()] = entry.value;
        }

        final type = (map['type'] as String? ?? '').toLowerCase();
        final uri = _convertClashProxyToUri(map);
        if (uri == null) {
          errors.add(
            'Clash proxy ${map['name'] ?? i}: unsupported type "$type"',
          );
          continue;
        }

        final result = _parseVpnUri.call(uri);
        switch (result) {
          case ParseSuccess(:final config):
            servers.add(
              ParsedServer(
                name:
                    config.remark ??
                    map['name'] as String? ??
                    '${config.protocol}:${config.serverAddress}',
                rawUri: uri,
                protocol: config.protocol,
                serverAddress: config.serverAddress,
                port: config.port,
                configData: <String, dynamic>{
                  'uuid': config.uuid,
                  if (config.password != null) 'password': config.password,
                  if (config.transportSettings != null)
                    'transport': config.transportSettings,
                  if (config.tlsSettings != null) 'tls': config.tlsSettings,
                  if (config.additionalParams != null)
                    'params': config.additionalParams,
                },
              ),
            );
          case ParseFailure(:final message):
            errors.add('Clash proxy ${map['name'] ?? i}: $message');
        }
      }

      if (servers.isEmpty && errors.isEmpty) {
        return null;
      }
      return (servers, errors);
    } catch (_) {
      return null;
    }
  }

  bool _isNonProxyOutbound(String type) {
    return const {
      'direct',
      'block',
      'dns',
      'selector',
      'urltest',
      'fallback',
      'loadbalance',
    }.contains(type);
  }

  /// Converts a Clash Meta proxy configuration map to a standard URI.
  String? _convertClashProxyToUri(Map<String, dynamic> p) {
    final type = (p['type'] as String? ?? '').toLowerCase();
    final name = p['name'] as String? ?? 'Proxy';
    final server = p['server'] as String?;
    final port = p['port'] is int
        ? p['port'] as int
        : int.tryParse(p['port']?.toString() ?? '');

    if (server == null || port == null || port <= 0) return null;

    final encodedName = Uri.encodeComponent(name);

    switch (type) {
      case 'vless':
        final uuid = p['uuid'] as String? ?? '';
        final network = (p['network'] as String? ?? 'tcp').toLowerCase();
        final tls = p['tls'] == true;
        final realityOpts = p['reality-opts'] is Map
            ? (p['reality-opts'] as Map)
            : null;
        final security = realityOpts != null
            ? 'reality'
            : (tls ? 'tls' : 'none');
        final sni = p['servername'] ?? p['sni'] ?? '';
        final flow = p['flow'] as String?;

        final queryParams = <String, String>{
          'type': network,
          'security': security,
          if (sni.toString().isNotEmpty) 'sni': sni.toString(),
          if (flow != null && flow.isNotEmpty) 'flow': flow,
        };

        if (realityOpts != null) {
          final pbk = realityOpts['public-key']?.toString();
          final sid = realityOpts['short-id']?.toString();
          if (pbk != null) queryParams['pbk'] = pbk;
          if (sid != null) queryParams['sid'] = sid;
        }

        if (network == 'ws') {
          final wsOpts = p['ws-opts'] is Map ? (p['ws-opts'] as Map) : null;
          final path = wsOpts?['path']?.toString() ?? '/';
          final host =
              (wsOpts?['headers'] is Map
                      ? (wsOpts!['headers'] as Map)['Host']
                      : null)
                  ?.toString();
          queryParams['path'] = path;
          if (host != null && host.isNotEmpty) queryParams['host'] = host;
        } else if (network == 'grpc') {
          final grpcOpts = p['grpc-opts'] is Map
              ? (p['grpc-opts'] as Map)
              : null;
          final serviceName = grpcOpts?['grpc-service-name']?.toString() ?? '';
          if (serviceName.isNotEmpty) queryParams['serviceName'] = serviceName;
        }

        final query = queryParams.entries
            .map((e) => '${e.key}=${Uri.encodeComponent(e.value)}')
            .join('&');

        return 'vless://$uuid@$server:$port?$query#$encodedName';

      case 'trojan':
        final password = p['password'] as String? ?? '';
        final network = (p['network'] as String? ?? 'tcp').toLowerCase();
        final sni = p['sni'] ?? p['servername'] ?? '';

        final queryParams = <String, String>{
          'security': 'tls',
          'type': network,
          if (sni.toString().isNotEmpty) 'sni': sni.toString(),
        };

        final query = queryParams.entries
            .map((e) => '${e.key}=${Uri.encodeComponent(e.value)}')
            .join('&');

        return 'trojan://$password@$server:$port?$query#$encodedName';

      case 'ss':
      case 'shadowsocks':
        final cipher = p['cipher'] as String? ?? '';
        final password = p['password'] as String? ?? '';
        final userPass = base64.encode(utf8.encode('$cipher:$password'));
        return 'ss://$userPass@$server:$port#$encodedName';

      case 'vmess':
        final uuid = p['uuid'] as String? ?? '';
        final alterId = p['alterId'] is int ? p['alterId'] as int : 0;
        final cipher = p['cipher'] as String? ?? 'auto';
        final network = (p['network'] as String? ?? 'tcp').toLowerCase();
        final tls = p['tls'] == true ? 'tls' : 'none';
        final sni = p['servername'] ?? p['sni'] ?? '';
        final wsOpts = p['ws-opts'] is Map ? (p['ws-opts'] as Map) : null;
        final path = wsOpts?['path']?.toString() ?? '/';
        final host =
            (wsOpts?['headers'] is Map
                    ? (wsOpts!['headers'] as Map)['Host']
                    : null)
                ?.toString() ??
            '';

        final vmessJson = {
          'v': '2',
          'ps': name,
          'add': server,
          'port': port,
          'id': uuid,
          'aid': alterId,
          'scy': cipher,
          'net': network,
          'type': 'none',
          'host': host,
          'path': path,
          'tls': tls,
          'sni': sni.toString(),
        };

        final b64 = base64.encode(utf8.encode(jsonEncode(vmessJson)));
        return 'vmess://$b64';

      default:
        return null;
    }
  }

  /// Converts a Sing-box outbound configuration map to a standard URI.
  String? _convertSingboxOutboundToUri(Map<String, dynamic> o) {
    final type = (o['type'] as String? ?? '').toLowerCase();
    final name = o['tag'] as String? ?? 'Proxy';
    final server = o['server'] as String?;
    final port = o['server_port'] is int
        ? o['server_port'] as int
        : int.tryParse(o['server_port']?.toString() ?? '');

    if (server == null || port == null || port <= 0) return null;

    final encodedName = Uri.encodeComponent(name);

    switch (type) {
      case 'vless':
        final uuid = o['uuid'] as String? ?? '';
        final tlsMap = o['tls'] is Map ? (o['tls'] as Map) : null;
        final tlsEnabled = tlsMap?['enabled'] == true;
        final realityMap = tlsMap?['reality'] is Map
            ? (tlsMap!['reality'] as Map)
            : null;
        final realityEnabled = realityMap?['enabled'] == true;
        final security = realityEnabled
            ? 'reality'
            : (tlsEnabled ? 'tls' : 'none');
        final sni = tlsMap?['server_name']?.toString() ?? '';
        final flow = o['flow'] as String?;

        final transport = o['transport'] is Map
            ? (o['transport'] as Map)
            : null;
        final network = (transport?['type'] as String? ?? 'tcp').toLowerCase();

        final queryParams = <String, String>{
          'type': network,
          'security': security,
          if (sni.isNotEmpty) 'sni': sni,
          if (flow != null && flow.isNotEmpty) 'flow': flow,
        };

        if (realityEnabled && realityMap != null) {
          final pbk = realityMap['public_key']?.toString();
          final sid = realityMap['short_id']?.toString();
          if (pbk != null) queryParams['pbk'] = pbk;
          if (sid != null) queryParams['sid'] = sid;
        }

        if (network == 'ws') {
          final path = transport?['path']?.toString() ?? '/';
          final host =
              (transport?['headers'] is Map
                      ? (transport!['headers'] as Map)['Host']
                      : null)
                  ?.toString();
          queryParams['path'] = path;
          if (host != null && host.isNotEmpty) queryParams['host'] = host;
        } else if (network == 'grpc') {
          final serviceName = transport?['service_name']?.toString() ?? '';
          if (serviceName.isNotEmpty) queryParams['serviceName'] = serviceName;
        }

        final query = queryParams.entries
            .map((e) => '${e.key}=${Uri.encodeComponent(e.value)}')
            .join('&');

        return 'vless://$uuid@$server:$port?$query#$encodedName';

      case 'trojan':
        final password = o['password'] as String? ?? '';
        final tlsMap = o['tls'] is Map ? (o['tls'] as Map) : null;
        final sni = tlsMap?['server_name']?.toString() ?? '';
        final transport = o['transport'] is Map
            ? (o['transport'] as Map)
            : null;
        final network = (transport?['type'] as String? ?? 'tcp').toLowerCase();

        final queryParams = <String, String>{
          'security': 'tls',
          'type': network,
          if (sni.isNotEmpty) 'sni': sni,
        };

        final query = queryParams.entries
            .map((e) => '${e.key}=${Uri.encodeComponent(e.value)}')
            .join('&');

        return 'trojan://$password@$server:$port?$query#$encodedName';

      case 'shadowsocks':
        final method = o['method'] as String? ?? '';
        final password = o['password'] as String? ?? '';
        final userPass = base64.encode(utf8.encode('$method:$password'));
        return 'ss://$userPass@$server:$port#$encodedName';

      case 'vmess':
        final uuid = o['uuid'] as String? ?? '';
        final alterId = o['alter_id'] is int ? o['alter_id'] as int : 0;
        final cipher = o['security'] as String? ?? 'auto';
        final tlsMap = o['tls'] is Map ? (o['tls'] as Map) : null;
        final tls = tlsMap?['enabled'] == true ? 'tls' : 'none';
        final sni = tlsMap?['server_name']?.toString() ?? '';
        final transport = o['transport'] is Map
            ? (o['transport'] as Map)
            : null;
        final network = (transport?['type'] as String? ?? 'tcp').toLowerCase();
        final path = transport?['path']?.toString() ?? '/';
        final host =
            (transport?['headers'] is Map
                    ? (transport!['headers'] as Map)['Host']
                    : null)
                ?.toString() ??
            '';

        final vmessJson = {
          'v': '2',
          'ps': name,
          'add': server,
          'port': port,
          'id': uuid,
          'aid': alterId,
          'scy': cipher,
          'net': network,
          'type': 'none',
          'host': host,
          'path': path,
          'tls': tls,
          'sni': sni,
        };

        final b64 = base64.encode(utf8.encode(jsonEncode(vmessJson)));
        return 'vmess://$b64';

      default:
        return null;
    }
  }
}
