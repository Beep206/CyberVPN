import 'package:cybervpn_mobile/features/config_import/domain/entities/parsed_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';

/// Parser for Trojan (trojan://) URIs.
///
/// Format:
/// `trojan://password@host:port?params#remark`
///
/// **Password**: Extracted from userinfo (before `@`).
///
/// **Query parameters**:
/// - `sni` — Server Name Indication for TLS
/// - `fingerprint` — TLS fingerprint
/// - `type` — Transport type (tcp, ws, grpc, h2)
/// - `path` — Transport path (WebSocket/gRPC)
/// - `host` — Transport host header
/// - `security` — Security type (tls, xtls, reality)
/// - `alpn` — ALPN negotiation
/// - `allowInsecure` — Skip certificate verification
///
/// **Fragment**: Remark / display name.
class TrojanParser implements VpnUriParser {
  /// Allowed transport types.
  static const allowedTransportTypes = <String>{
    'tcp',
    'ws',
    'grpc',
    'h2',
    'http',
    'quic',
  };

  @override
  String get protocolName => 'trojan';

  @override
  bool canParse(String uri) {
    return uri.trimLeft().toLowerCase().startsWith('trojan://');
  }

  @override
  ParseResult parse(String uri) {
    final trimmed = uri.trim();

    if (!canParse(trimmed)) {
      return const ParseFailure(
        'Invalid Trojan URI: scheme must be trojan://',
      );
    }

    try {
      return _parseUri(trimmed);
    } catch (e) {
      return ParseFailure('Invalid Trojan URI format: $e');
    }
  }

  ParseResult _parseUri(String uri) {
    // Extract fragment (remark) before parsing with Uri to avoid issues
    // with URL-encoded fragments.
    String? remark;
    var body = uri;
    final fragmentIndex = body.lastIndexOf('#');
    if (fragmentIndex != -1) {
      final rawFragment = body.substring(fragmentIndex + 1);
      if (rawFragment.isNotEmpty) {
        remark = Uri.decodeComponent(rawFragment);
      }
      body = body.substring(0, fragmentIndex);
    }

    // Remove scheme
    final withoutScheme = body.substring(9); // length of 'trojan://'

    if (withoutScheme.isEmpty) {
      return const ParseFailure(
        'Invalid Trojan URI: empty URI after scheme',
      );
    }

    // Split on '@' to separate password from host:port?params
    final atIndex = withoutScheme.indexOf('@');
    if (atIndex == -1) {
      return const ParseFailure(
        'Invalid Trojan URI: missing @ separator between password and host',
      );
    }

    // Extract and decode password
    final rawPassword = withoutScheme.substring(0, atIndex);
    final password = Uri.decodeComponent(rawPassword);

    if (password.isEmpty) {
      return const ParseFailure(
        'Invalid Trojan URI: password is empty',
      );
    }

    // Parse the host:port?params portion
    final hostPortQuery = withoutScheme.substring(atIndex + 1);

    if (hostPortQuery.isEmpty) {
      return const ParseFailure(
        'Invalid Trojan URI: missing host and port',
      );
    }

    // Extract query parameters
    Map<String, String> queryParams = {};
    var hostPortStr = hostPortQuery;
    final queryIndex = hostPortStr.indexOf('?');
    if (queryIndex != -1) {
      final queryString = hostPortStr.substring(queryIndex + 1);
      hostPortStr = hostPortStr.substring(0, queryIndex);
      queryParams = Uri.splitQueryString(queryString);
    }

    // Remove trailing slash
    if (hostPortStr.endsWith('/')) {
      hostPortStr = hostPortStr.substring(0, hostPortStr.length - 1);
    }

    // Parse host and port, handling IPv6 addresses in brackets
    String host;
    int port;

    if (hostPortStr.startsWith('[')) {
      // IPv6 address: [::1]:port
      final closeBracket = hostPortStr.indexOf(']');
      if (closeBracket == -1) {
        return const ParseFailure(
          'Invalid Trojan URI: IPv6 address missing closing bracket',
        );
      }
      host = hostPortStr.substring(1, closeBracket);
      final portStr = hostPortStr.substring(closeBracket + 1);
      if (!portStr.startsWith(':') || portStr.length < 2) {
        return ParseFailure(
          'Invalid Trojan URI: invalid port after IPv6 address "$portStr"',
        );
      }
      port = int.parse(portStr.substring(1));
    } else {
      // IPv4 or hostname: host:port
      final lastColon = hostPortStr.lastIndexOf(':');
      if (lastColon == -1) {
        return ParseFailure(
          'Invalid Trojan URI: missing port in "$hostPortStr"',
        );
      }
      host = hostPortStr.substring(0, lastColon);
      final portString = hostPortStr.substring(lastColon + 1);
      if (portString.isEmpty) {
        return const ParseFailure(
          'Invalid Trojan URI: port is empty',
        );
      }
      port = int.parse(portString);
    }

    // Validate host
    if (host.isEmpty) {
      return const ParseFailure(
        'Invalid Trojan URI: server address is empty',
      );
    }

    // Validate port
    if (port < 1 || port > 65535) {
      return ParseFailure(
        'Invalid Trojan URI: port $port out of range (1-65535)',
      );
    }

    // Extract known query parameters
    final sni = queryParams['sni'];
    final fingerprint = queryParams['fingerprint'];
    final transportType = queryParams['type'];
    final transportPath = queryParams['path'];
    final transportHost = queryParams['host'];
    final security = queryParams['security'];
    final alpn = queryParams['alpn'];
    final allowInsecure = queryParams['allowInsecure'];

    // Validate transport type if present
    if (transportType != null &&
        transportType.isNotEmpty &&
        !allowedTransportTypes.contains(transportType.toLowerCase())) {
      return ParseFailure(
        'Invalid Trojan URI: unsupported transport type "$transportType"',
      );
    }

    // Build TLS settings
    Map<String, dynamic>? tlsSettings;
    if (sni != null || fingerprint != null || security != null || alpn != null || allowInsecure != null) {
      tlsSettings = <String, dynamic>{};
      if (sni != null) tlsSettings['sni'] = sni;
      if (fingerprint != null) tlsSettings['fingerprint'] = fingerprint;
      if (security != null) tlsSettings['security'] = security;
      if (alpn != null) tlsSettings['alpn'] = alpn;
      if (allowInsecure != null) {
        tlsSettings['allowInsecure'] = allowInsecure == '1' || allowInsecure.toLowerCase() == 'true';
      }
    }

    // Build transport settings
    Map<String, dynamic>? transportSettings;
    if (transportType != null || transportPath != null || transportHost != null) {
      transportSettings = <String, dynamic>{};
      if (transportType != null) transportSettings['type'] = transportType;
      if (transportPath != null) transportSettings['path'] = transportPath;
      if (transportHost != null) transportSettings['host'] = transportHost;
    }

    // Build additional params for any remaining query params not already handled
    final handledKeys = <String>{
      'sni',
      'fingerprint',
      'type',
      'path',
      'host',
      'security',
      'alpn',
      'allowInsecure',
    };
    Map<String, dynamic>? additionalParams;
    for (final entry in queryParams.entries) {
      if (!handledKeys.contains(entry.key)) {
        additionalParams ??= <String, dynamic>{};
        additionalParams[entry.key] = entry.value;
      }
    }

    return ParseSuccess(
      ParsedConfig(
        protocol: 'trojan',
        serverAddress: host,
        port: port,
        uuid: password, // password stored in uuid field (like SS stores method)
        password: password,
        remark: remark,
        tlsSettings: tlsSettings,
        transportSettings: transportSettings,
        additionalParams: additionalParams,
      ),
    );
  }
}
