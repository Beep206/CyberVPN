import 'package:cybervpn_mobile/features/config_import/domain/entities/parsed_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';

/// Parser for VLESS (vless://) URIs.
///
/// Format:
/// `vless://UUID@host:port?params#remark`
///
/// The UUID is the user ID. Host and port define the server address.
/// Query parameters carry encryption, flow, security, transport, and
/// Reality/TLS settings. The fragment is the server remark/name.
class VlessParser implements VpnUriParser {
  /// UUID v4 regex pattern for validation.
  static final _uuidPattern = RegExp(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    caseSensitive: false,
  );

  /// Valid security types for VLESS connections.
  static const validSecurityTypes = <String>{
    'none',
    'tls',
    'reality',
    'xtls',
  };

  /// Valid transport types for VLESS connections.
  static const validTransportTypes = <String>{
    'tcp',
    'ws',
    'xhttp',
    'grpc',
    'http',
    'h2',
    'kcp',
    'quic',
    'splithttp',
  };

  @override
  String get protocolName => 'vless';

  @override
  bool canParse(String uri) {
    return uri.trimLeft().toLowerCase().startsWith('vless://');
  }

  @override
  ParseResult parse(String uri) {
    final trimmed = uri.trim();

    if (!canParse(trimmed)) {
      return const ParseFailure(
        'Invalid VLESS URI: scheme must be vless://',
      );
    }

    try {
      return _parseUri(trimmed);
    } catch (e) {
      return ParseFailure('Invalid VLESS URI format: $e');
    }
  }

  ParseResult _parseUri(String uri) {
    // Remove scheme
    final withoutScheme = uri.substring(8); // length of 'vless://'

    // Extract fragment (remark) first -- it comes after '#'
    String? remark;
    String body = withoutScheme;
    final fragmentIndex = body.lastIndexOf('#');
    if (fragmentIndex != -1) {
      final rawFragment = body.substring(fragmentIndex + 1);
      if (rawFragment.isNotEmpty) {
        remark = Uri.decodeComponent(rawFragment);
      }
      body = body.substring(0, fragmentIndex);
    }

    // Extract query parameters -- everything after '?'
    Map<String, String> queryParams = const {};
    final queryIndex = body.indexOf('?');
    if (queryIndex != -1) {
      final queryString = body.substring(queryIndex + 1);
      body = body.substring(0, queryIndex);
      if (queryString.isNotEmpty) {
        queryParams = Uri.splitQueryString(queryString);
      }
    }

    // Now body should be: UUID@host:port
    // Extract UUID (before '@')
    final atIndex = body.indexOf('@');
    if (atIndex == -1) {
      return const ParseFailure(
        'Invalid VLESS URI: missing @ separator in authority',
      );
    }

    final uuid = body.substring(0, atIndex);
    final hostPort = body.substring(atIndex + 1);

    // Validate UUID
    if (uuid.isEmpty) {
      return const ParseFailure('Invalid VLESS URI: UUID is empty');
    }

    if (!_uuidPattern.hasMatch(uuid)) {
      return ParseFailure(
        'Invalid VLESS URI: invalid UUID format "$uuid"',
      );
    }

    // Parse host and port, handling IPv6 addresses in brackets
    String host;
    int port;

    if (hostPort.startsWith('[')) {
      // IPv6 address: [::1]:port
      final closeBracket = hostPort.indexOf(']');
      if (closeBracket == -1) {
        return const ParseFailure(
          'Invalid VLESS URI: IPv6 address missing closing bracket',
        );
      }
      host = hostPort.substring(1, closeBracket);
      final portStr = hostPort.substring(closeBracket + 1);
      if (!portStr.startsWith(':') || portStr.length < 2) {
        return const ParseFailure(
          'Invalid VLESS URI: missing or invalid port after IPv6 address',
        );
      }
      final portParsed = int.tryParse(portStr.substring(1));
      if (portParsed == null) {
        return ParseFailure(
          'Invalid VLESS URI: port is not a number "${portStr.substring(1)}"',
        );
      }
      port = portParsed;
    } else {
      // IPv4 or hostname: host:port
      final lastColon = hostPort.lastIndexOf(':');
      if (lastColon == -1) {
        return ParseFailure(
          'Invalid VLESS URI: missing port in "$hostPort"',
        );
      }
      host = hostPort.substring(0, lastColon);
      final portParsed = int.tryParse(hostPort.substring(lastColon + 1));
      if (portParsed == null) {
        return ParseFailure(
          'Invalid VLESS URI: port is not a number '
          '"${hostPort.substring(lastColon + 1)}"',
        );
      }
      port = portParsed;
    }

    // Validate host
    if (host.isEmpty) {
      return const ParseFailure(
        'Invalid VLESS URI: server address is empty',
      );
    }

    // Validate port
    if (port < 1 || port > 65535) {
      return ParseFailure(
        'Invalid VLESS URI: port $port out of range (1-65535)',
      );
    }

    // Extract query parameters into structured maps
    final encryption = queryParams['encryption'] ?? 'none';
    final flow = queryParams['flow'];
    final security = queryParams['security'] ?? 'none';
    final sni = queryParams['sni'];
    final fingerprint = queryParams['fp'] ?? queryParams['fingerprint'];
    final publicKey = queryParams['pbk'] ?? queryParams['publicKey'];
    final shortId = queryParams['sid'] ?? queryParams['shortId'];
    final transportType = queryParams['type'] ?? 'tcp';
    final path = queryParams['path'];
    final hostHeader = queryParams['host'];

    // Validate security type if provided and non-empty
    if (security.isNotEmpty && !validSecurityTypes.contains(security)) {
      return ParseFailure(
        'Invalid VLESS URI: unsupported security type "$security"',
      );
    }

    // Build transport settings
    final transportSettings = <String, dynamic>{
      'type': transportType,
    };
    if (path != null) {
      transportSettings['path'] = path;
    }
    if (hostHeader != null) {
      transportSettings['host'] = hostHeader;
    }

    // Build TLS settings
    Map<String, dynamic>? tlsSettings;
    if (security != 'none') {
      tlsSettings = <String, dynamic>{
        'security': security,
      };
      if (sni != null) {
        tlsSettings['sni'] = sni;
      }
      if (fingerprint != null) {
        tlsSettings['fingerprint'] = fingerprint;
      }
      if (security == 'reality') {
        if (publicKey != null) {
          tlsSettings['publicKey'] = publicKey;
        }
        if (shortId != null) {
          tlsSettings['shortId'] = shortId;
        }
      }
    }

    // Build additional params for fields not covered by transport/tls
    final additionalParams = <String, dynamic>{
      'encryption': encryption,
    };
    if (flow != null) {
      additionalParams['flow'] = flow;
    }

    return ParseSuccess(
      ParsedConfig(
        protocol: 'vless',
        serverAddress: host,
        port: port,
        uuid: uuid,
        remark: remark,
        transportSettings: transportSettings,
        tlsSettings: tlsSettings,
        additionalParams: additionalParams,
      ),
    );
  }
}
