import 'dart:convert';

import 'package:cybervpn_mobile/features/config_import/domain/entities/parsed_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';

/// Parser for VMess (vmess://) URIs.
///
/// VMess URIs encode configuration as a base64-encoded JSON object:
/// `vmess://BASE64_JSON`
///
/// The JSON body contains fields such as:
/// - `v` — version (typically "2")
/// - `ps` — remark / server name
/// - `add` — server address
/// - `port` — server port
/// - `id` — user UUID
/// - `aid` — alterId
/// - `net` — network/transport type (tcp, ws, h2, grpc, kcp, quic)
/// - `type` — header type (none, http, srtp, utp, wechat-video, dtls, wireguard)
/// - `host` — host header / SNI
/// - `path` — WebSocket or HTTP/2 path
/// - `tls` — TLS setting ("tls" or empty)
/// - `sni` — server name indication
class VmessParser implements VpnUriParser {
  /// Known alternative key names for standard VMess JSON fields.
  ///
  /// Some clients use non-standard keys; we normalise them here.
  static const _keyAliases = <String, List<String>>{
    'add': ['address', 'addr', 'server'],
    'port': ['server_port', 'serverPort'],
    'id': ['uuid'],
    'aid': ['alterId', 'alter_id'],
    'net': ['network', 'transport'],
    'ps': ['remark', 'name', 'remarks'],
    'host': ['requestHost', 'request_host'],
    'path': ['obfsParam', 'obfs_param'],
    'tls': ['security'],
    'sni': ['serverName', 'server_name'],
    'type': ['headerType', 'header_type'],
  };

  @override
  String get protocolName => 'vmess';

  @override
  bool canParse(String uri) {
    return uri.trimLeft().toLowerCase().startsWith('vmess://');
  }

  @override
  ParseResult parse(String uri) {
    final trimmed = uri.trim();

    if (!canParse(trimmed)) {
      return const ParseFailure(
        'Invalid VMess URI: scheme must be vmess://',
      );
    }

    try {
      return _parseUri(trimmed);
    } on FormatException catch (e) {
      return ParseFailure('Failed to decode VMess URI: ${e.message}');
    } catch (e) {
      return ParseFailure('Invalid VMess URI format: $e');
    }
  }

  ParseResult _parseUri(String uri) {
    // Remove scheme
    final payload = uri.substring(8); // length of 'vmess://'

    if (payload.isEmpty) {
      return const ParseFailure('Invalid VMess URI: empty payload');
    }

    // Decode base64
    final jsonString = _decodeBase64(payload);

    // Parse JSON
    final dynamic decoded;
    try {
      decoded = jsonDecode(jsonString);
    } on FormatException {
      return const ParseFailure('Invalid VMess URI: payload is not valid JSON');
    }

    if (decoded is! Map<String, dynamic>) {
      return const ParseFailure(
        'Invalid VMess URI: JSON payload must be an object',
      );
    }

    return _mapJsonToConfig(decoded);
  }

  /// Map the decoded VMess JSON to a [ParsedConfig].
  ParseResult _mapJsonToConfig(Map<String, dynamic> json) {
    // Extract fields with alias support
    final address = _getString(json, 'add');
    final portValue = _getPort(json);
    final uuid = _getString(json, 'id');
    final remark = _getString(json, 'ps');
    final alterId = _getInt(json, 'aid') ?? 0;
    final network = _getString(json, 'net') ?? 'tcp';
    final headerType = _getString(json, 'type') ?? 'none';
    final host = _getString(json, 'host') ?? '';
    final path = _getString(json, 'path') ?? '';
    final tls = _getString(json, 'tls') ?? '';
    final sni = _getString(json, 'sni') ?? '';
    final version = _getString(json, 'v') ?? '';

    // Validate required fields
    if (address == null || address.isEmpty) {
      return const ParseFailure(
        'Invalid VMess config: server address (add) is missing or empty',
      );
    }

    if (portValue == null) {
      return const ParseFailure(
        'Invalid VMess config: port is missing or invalid',
      );
    }

    if (portValue < 1 || portValue > 65535) {
      return ParseFailure(
        'Invalid VMess config: port $portValue out of range (1-65535)',
      );
    }

    if (uuid == null || uuid.isEmpty) {
      return const ParseFailure(
        'Invalid VMess config: user ID (id) is missing or empty',
      );
    }

    // Build transport settings
    final transportSettings = <String, dynamic>{
      'network': network,
      'headerType': headerType,
    };

    if (host.isNotEmpty) {
      transportSettings['host'] = host;
    }

    if (path.isNotEmpty) {
      transportSettings['path'] = path;
    }

    // Build TLS settings
    Map<String, dynamic>? tlsSettings;
    if (tls.isNotEmpty && tls.toLowerCase() == 'tls') {
      tlsSettings = <String, dynamic>{
        'security': 'tls',
      };
      if (sni.isNotEmpty) {
        tlsSettings['sni'] = sni;
      }
    }

    // Build additional params for VMess-specific fields
    final additionalParams = <String, dynamic>{
      'alterId': alterId,
    };

    if (version.isNotEmpty) {
      additionalParams['version'] = version;
    }

    return ParseSuccess(
      ParsedConfig(
        protocol: 'vmess',
        serverAddress: address,
        port: portValue,
        uuid: uuid,
        remark: remark,
        transportSettings: transportSettings,
        tlsSettings: tlsSettings,
        additionalParams: additionalParams,
      ),
    );
  }

  /// Decode a base64 or base64url string, handling missing padding.
  String _decodeBase64(String input) {
    // Replace URL-safe characters
    var normalized = input.replaceAll('-', '+').replaceAll('_', '/');

    // Remove any whitespace or newlines
    normalized = normalized.replaceAll(RegExp(r'\s'), '');

    // Add padding if needed
    final remainder = normalized.length % 4;
    if (remainder != 0) {
      normalized = normalized.padRight(
        normalized.length + (4 - remainder),
        '=',
      );
    }

    return utf8.decode(base64.decode(normalized));
  }

  /// Get a string value from the JSON map, checking aliases.
  String? _getString(Map<String, dynamic> json, String key) {
    // Check primary key
    final value = json[key];
    if (value != null) {
      return value.toString();
    }

    // Check aliases
    final aliases = _keyAliases[key];
    if (aliases != null) {
      for (final alias in aliases) {
        final aliasValue = json[alias];
        if (aliasValue != null) {
          return aliasValue.toString();
        }
      }
    }

    return null;
  }

  /// Get an integer value from the JSON map, checking aliases.
  ///
  /// Handles both integer and string representations of numbers.
  int? _getInt(Map<String, dynamic> json, String key) {
    final value = json[key] ?? _getAliasedValue(json, key);
    if (value == null) return null;

    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }

  /// Get the port value, handling both int and string types.
  int? _getPort(Map<String, dynamic> json) {
    return _getInt(json, 'port');
  }

  /// Look up a value by checking known aliases for the given key.
  dynamic _getAliasedValue(Map<String, dynamic> json, String key) {
    final aliases = _keyAliases[key];
    if (aliases == null) return null;

    for (final alias in aliases) {
      final value = json[alias];
      if (value != null) return value;
    }
    return null;
  }
}
