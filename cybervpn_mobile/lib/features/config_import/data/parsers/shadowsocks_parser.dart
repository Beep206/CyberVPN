import 'dart:convert';

import 'package:cybervpn_mobile/features/config_import/domain/entities/parsed_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';

/// Parser for Shadowsocks (ss://) URIs.
///
/// Supports two formats:
///
/// **Standard format:**
/// `ss://BASE64(method:password)@host:port#remark`
///
/// The base64-encoded portion contains `method:password`. Host, port,
/// and optional remark (fragment) are in plain text.
///
/// **SIP002 format:**
/// `ss://BASE64(method:password)@host:port/?plugin=...#remark`
///
/// Similar to standard but includes query parameters for plugin
/// configuration (e.g., obfs-local, v2ray-plugin).
class ShadowsocksParser implements VpnUriParser {
  /// Supported Shadowsocks encryption methods.
  static const supportedMethods = <String>{
    // AEAD ciphers
    'aes-128-gcm',
    'aes-256-gcm',
    'chacha20-ietf-poly1305',
    // AEAD 2022 ciphers
    '2022-blake3-aes-128-gcm',
    '2022-blake3-aes-256-gcm',
    '2022-blake3-chacha20-poly1305',
    // Legacy stream ciphers (still seen in the wild)
    'aes-128-cfb',
    'aes-192-cfb',
    'aes-256-cfb',
    'aes-128-ctr',
    'aes-192-ctr',
    'aes-256-ctr',
    'camellia-128-cfb',
    'camellia-192-cfb',
    'camellia-256-cfb',
    'chacha20-ietf',
    'xchacha20-ietf-poly1305',
    'rc4-md5',
    'none',
    'plain',
  };

  @override
  String get protocolName => 'ss';

  @override
  bool canParse(String uri) {
    return uri.trimLeft().toLowerCase().startsWith('ss://');
  }

  @override
  ParseResult parse(String uri) {
    final trimmed = uri.trim();

    if (!canParse(trimmed)) {
      return const ParseFailure('Invalid Shadowsocks URI: scheme must be ss://');
    }

    try {
      return _parseUri(trimmed);
    } on FormatException catch (e) {
      return ParseFailure('Failed to decode base64 userinfo: ${e.message}');
    } catch (e) {
      return ParseFailure('Invalid Shadowsocks URI format: $e');
    }
  }

  ParseResult _parseUri(String uri) {
    // Remove scheme
    final withoutScheme = uri.substring(5); // length of 'ss://'

    // Extract fragment (remark) first — it comes after '#'
    String? remark;
    String body = withoutScheme;
    final fragmentIndex = body.lastIndexOf('#');
    if (fragmentIndex != -1) {
      remark = Uri.decodeComponent(body.substring(fragmentIndex + 1));
      body = body.substring(0, fragmentIndex);
    }

    // Determine format by checking for '@' in the remaining body.
    // SIP002: BASE64@host:port/?plugin=...
    // Standard (legacy): BASE64(method:password@host:port)
    //   — the entire portion is base64-encoded
    // Also standard with '@': BASE64(method:password)@host:port

    final atIndex = body.indexOf('@');

    String method;
    String password;
    String host;
    int port;
    Map<String, String>? queryParams;

    if (atIndex != -1) {
      // SIP002 or standard with separate base64 userinfo
      final userinfoPart = body.substring(0, atIndex);
      final hostPortQuery = body.substring(atIndex + 1);

      // Decode userinfo from base64
      final decoded = _decodeBase64(userinfoPart);
      final credentials = _parseCredentials(decoded);
      method = credentials.method;
      password = credentials.password;

      // Parse host:port and optional query
      final hostPortResult = _parseHostPortQuery(hostPortQuery);
      host = hostPortResult.host;
      port = hostPortResult.port;
      queryParams = hostPortResult.queryParams;
    } else {
      // Legacy format: entire body (minus fragment) is base64-encoded
      // containing method:password@host:port
      final decoded = _decodeBase64(body);
      final legacyResult = _parseLegacyFormat(decoded);
      method = legacyResult.method;
      password = legacyResult.password;
      host = legacyResult.host;
      port = legacyResult.port;
    }

    // Validate
    if (method.isEmpty) {
      return const ParseFailure(
        'Invalid Shadowsocks URI: encryption method is empty',
      );
    }

    if (password.isEmpty) {
      return const ParseFailure(
        'Invalid Shadowsocks URI: password is empty',
      );
    }

    if (host.isEmpty) {
      return const ParseFailure(
        'Invalid Shadowsocks URI: server address is empty',
      );
    }

    if (port < 1 || port > 65535) {
      return ParseFailure(
        'Invalid Shadowsocks URI: port $port out of range (1-65535)',
      );
    }

    if (!supportedMethods.contains(method.toLowerCase())) {
      return ParseFailure(
        'Unsupported encryption method: $method',
      );
    }

    // Build additional params for plugin info and query params
    Map<String, dynamic>? additionalParams;
    if (queryParams != null && queryParams.isNotEmpty) {
      additionalParams = <String, dynamic>{};
      if (queryParams.containsKey('plugin')) {
        additionalParams['plugin'] = queryParams['plugin'];
      }
      // Store all query params
      for (final entry in queryParams.entries) {
        if (entry.key != 'plugin') {
          additionalParams[entry.key] = entry.value;
        }
      }
    }

    return ParseSuccess(
      ParsedConfig(
        protocol: 'shadowsocks',
        serverAddress: host,
        port: port,
        uuid: method, // encryption method stored in uuid field
        password: password,
        remark: remark,
        additionalParams: additionalParams,
      ),
    );
  }

  /// Decode a base64 or base64url string, handling missing padding.
  String _decodeBase64(String input) {
    // URL-decode first in case the base64 is percent-encoded
    var decoded = Uri.decodeComponent(input);

    // Replace URL-safe characters
    decoded = decoded.replaceAll('-', '+').replaceAll('_', '/');

    // Add padding if needed
    final remainder = decoded.length % 4;
    if (remainder != 0) {
      decoded = decoded.padRight(decoded.length + (4 - remainder), '=');
    }

    return utf8.decode(base64.decode(decoded));
  }

  /// Parse "method:password" from decoded base64 string.
  _Credentials _parseCredentials(String decoded) {
    final colonIndex = decoded.indexOf(':');
    if (colonIndex == -1) {
      throw FormatException(
        'Invalid userinfo format: expected method:password, got "$decoded"',
      );
    }
    return _Credentials(
      method: decoded.substring(0, colonIndex),
      password: decoded.substring(colonIndex + 1),
    );
  }

  /// Parse host:port and optional query parameters from the authority portion.
  _HostPortQuery _parseHostPortQuery(String input) {
    Map<String, String>? queryParams;

    var hostPort = input;

    // Extract query string if present
    final queryIndex = hostPort.indexOf('?');
    if (queryIndex != -1) {
      final queryString = hostPort.substring(queryIndex + 1);
      hostPort = hostPort.substring(0, queryIndex);
      queryParams = Uri.splitQueryString(queryString);
    }

    // Remove trailing slash
    if (hostPort.endsWith('/')) {
      hostPort = hostPort.substring(0, hostPort.length - 1);
    }

    // Parse host and port, handling IPv6 addresses in brackets
    String host;
    int port;

    if (hostPort.startsWith('[')) {
      // IPv6 address: [::1]:port
      final closeBracket = hostPort.indexOf(']');
      if (closeBracket == -1) {
        throw const FormatException('Invalid IPv6 address: missing closing bracket');
      }
      host = hostPort.substring(1, closeBracket);
      final portStr = hostPort.substring(closeBracket + 1);
      if (!portStr.startsWith(':') || portStr.length < 2) {
        throw FormatException('Invalid port after IPv6 address: "$portStr"');
      }
      port = int.parse(portStr.substring(1));
    } else {
      // IPv4 or hostname: host:port
      final lastColon = hostPort.lastIndexOf(':');
      if (lastColon == -1) {
        throw FormatException('Invalid host:port format: "$hostPort"');
      }
      host = hostPort.substring(0, lastColon);
      port = int.parse(hostPort.substring(lastColon + 1));
    }

    return _HostPortQuery(host: host, port: port, queryParams: queryParams);
  }

  /// Parse the legacy format where the entire string is
  /// "method:password@host:port".
  _LegacyParsed _parseLegacyFormat(String decoded) {
    final atIndex = decoded.lastIndexOf('@');
    if (atIndex == -1) {
      throw FormatException(
        'Invalid legacy Shadowsocks format: missing @ separator in "$decoded"',
      );
    }

    final credentials = _parseCredentials(decoded.substring(0, atIndex));
    final hostPortStr = decoded.substring(atIndex + 1);

    String host;
    int port;

    if (hostPortStr.startsWith('[')) {
      // IPv6
      final closeBracket = hostPortStr.indexOf(']');
      if (closeBracket == -1) {
        throw const FormatException('Invalid IPv6 address: missing closing bracket');
      }
      host = hostPortStr.substring(1, closeBracket);
      final portStr = hostPortStr.substring(closeBracket + 1);
      if (!portStr.startsWith(':') || portStr.length < 2) {
        throw FormatException('Invalid port after IPv6 address: "$portStr"');
      }
      port = int.parse(portStr.substring(1));
    } else {
      final lastColon = hostPortStr.lastIndexOf(':');
      if (lastColon == -1) {
        throw FormatException('Invalid host:port format: "$hostPortStr"');
      }
      host = hostPortStr.substring(0, lastColon);
      port = int.parse(hostPortStr.substring(lastColon + 1));
    }

    return _LegacyParsed(
      method: credentials.method,
      password: credentials.password,
      host: host,
      port: port,
    );
  }
}

/// Internal data class for parsed credentials.
class _Credentials {
  const _Credentials({required this.method, required this.password});

  final String method;
  final String password;
}

/// Internal data class for parsed host, port, and query parameters.
class _HostPortQuery {
  const _HostPortQuery({
    required this.host,
    required this.port,
    this.queryParams,
  });

  final String host;
  final int port;
  final Map<String, String>? queryParams;
}

/// Internal data class for legacy format parsed result.
class _LegacyParsed {
  const _LegacyParsed({
    required this.method,
    required this.password,
    required this.host,
    required this.port,
  });

  final String method;
  final String password;
  final String host;
  final int port;
}
