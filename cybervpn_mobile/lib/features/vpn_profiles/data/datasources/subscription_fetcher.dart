import 'dart:convert';

import 'package:dio/dio.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/parsed_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/usecases/parse_vpn_uri.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/models/fetch_result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/models/parsed_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/subscription_info.dart';

/// Fetches a VPN subscription URL and parses the response into
/// structured subscription metadata and a list of VPN server configs.
///
/// Response headers provide subscription metadata:
/// - `profile-title` — display name for the subscription
/// - `subscription-userinfo` — traffic usage in format
///   `upload=X; download=Y; total=Z; expire=T`
/// - `profile-update-interval` — auto-update interval in hours
/// - `support-url` — provider support/help link
/// - `profile-web-page-url` — provider web page
///
/// Response body is typically Base64-encoded, with each decoded line
/// being a V2Ray URI (`vless://`, `vmess://`, `trojan://`, `ss://`).
///
/// Usage:
/// ```dart
/// final fetcher = SubscriptionFetcher(dio: dio);
/// final result = await fetcher.fetch('https://example.com/sub/token');
/// print('Servers: ${result.servers.length}');
/// print('Expires: ${result.info.expiresAt}');
/// ```
class SubscriptionFetcher {
  /// Creates a [SubscriptionFetcher].
  ///
  /// [dio] is the HTTP client used for the subscription request.
  /// [parseVpnUri] is an optional override for the VPN URI parser;
  /// defaults to [ParseVpnUri] with all built-in protocol parsers.
  SubscriptionFetcher({
    required Dio dio,
    ParseVpnUri? parseVpnUri,
  })  : _dio = dio,
        _parseVpnUri = parseVpnUri ?? ParseVpnUri();

  final Dio _dio;
  final ParseVpnUri _parseVpnUri;

  /// HTTP request timeout.
  static const Duration _timeout = Duration(seconds: 10);

  /// User-Agent header sent with subscription requests.
  static const String _userAgent = 'CyberVPN/1.0';

  /// Fetch and parse a subscription URL.
  ///
  /// Performs an HTTP GET, parses subscription metadata from response
  /// headers, decodes the body (Base64 → line-separated URIs), and
  /// parses each URI using the existing VPN URI parsers.
  ///
  /// Throws [SubscriptionFetcherException] on network or HTTP errors.
  Future<FetchResult> fetch(String url) async {
    final response = await _fetchRaw(url);
    final info = _parseHeaders(response.headers);
    final (servers, errors) = _parseBody(response.data ?? '');

    AppLogger.info(
      'Subscription fetched',
      category: 'subscription',
      data: {
        'url': _sanitizeUrl(url),
        'serverCount': servers.length,
        'errorCount': errors.length,
        'title': info.title,
      },
    );

    return FetchResult(
      info: info,
      servers: servers,
      parseErrors: errors,
    );
  }

  /// Perform the HTTP GET request.
  Future<Response<String>> _fetchRaw(String url) async {
    final uri = Uri.tryParse(url);
    if (uri == null || !uri.hasScheme || !uri.hasAuthority) {
      throw SubscriptionFetcherException(
        url: url,
        message: 'Invalid subscription URL format',
      );
    }

    try {
      return await _dio.get<String>(
        url,
        options: Options(
          responseType: ResponseType.plain,
          receiveTimeout: _timeout,
          sendTimeout: _timeout,
          headers: {
            'User-Agent': _userAgent,
            'Accept': '*/*',
          },
        ),
      );
    } on DioException catch (e) {
      final statusCode = e.response?.statusCode;
      final detail = statusCode != null ? 'HTTP $statusCode' : e.type.name;
      throw SubscriptionFetcherException(
        url: url,
        message: 'Failed to fetch subscription: $detail',
        cause: e,
      );
    }
  }

  /// Extract subscription metadata from response headers.
  SubscriptionInfo _parseHeaders(Headers headers) {
    final title = _headerValue(headers, 'profile-title');
    final userInfo = _headerValue(headers, 'subscription-userinfo');
    final updateInterval = _headerValue(headers, 'profile-update-interval');
    final supportUrl = _headerValue(headers, 'support-url');

    int uploadBytes = 0;
    int downloadBytes = 0;
    int totalBytes = 0;
    DateTime? expiresAt;

    if (userInfo != null) {
      final parsed = _parseUserInfo(userInfo);
      uploadBytes = parsed['upload'] ?? 0;
      downloadBytes = parsed['download'] ?? 0;
      totalBytes = parsed['total'] ?? 0;
      final expireTimestamp = parsed['expire'];
      if (expireTimestamp != null && expireTimestamp > 0) {
        expiresAt =
            DateTime.fromMillisecondsSinceEpoch(expireTimestamp * 1000);
      }
    }

    int updateIntervalMinutes = 60;
    if (updateInterval != null) {
      final hours = int.tryParse(updateInterval);
      if (hours != null && hours > 0) {
        updateIntervalMinutes = hours * 60;
      }
    }

    return SubscriptionInfo(
      title: title,
      uploadBytes: uploadBytes,
      downloadBytes: downloadBytes,
      totalBytes: totalBytes,
      expiresAt: expiresAt,
      updateIntervalMinutes: updateIntervalMinutes,
      supportUrl: supportUrl,
    );
  }

  /// Parse the `subscription-userinfo` header.
  ///
  /// Format: `upload=123; download=456; total=789; expire=1234567890`
  /// Values are in bytes; expire is a Unix timestamp in seconds.
  Map<String, int> _parseUserInfo(String value) {
    final result = <String, int>{};
    final parts = value.split(';');
    for (final part in parts) {
      final trimmed = part.trim();
      final eqIndex = trimmed.indexOf('=');
      if (eqIndex == -1) continue;
      final key = trimmed.substring(0, eqIndex).trim().toLowerCase();
      final valStr = trimmed.substring(eqIndex + 1).trim();
      final parsed = int.tryParse(valStr);
      if (parsed != null) {
        result[key] = parsed;
      }
    }
    return result;
  }

  /// Get the first value of a response header (case-insensitive).
  String? _headerValue(Headers headers, String name) {
    final values = headers[name];
    if (values == null || values.isEmpty) return null;
    final value = values.first.trim();
    return value.isEmpty ? null : value;
  }

  /// Decode and parse the response body into a list of servers.
  ///
  /// Tries Base64 decoding first, falls back to plain text if the
  /// body already contains VPN URI schemes.
  (List<ParsedServer>, List<String>) _parseBody(String body) {
    final trimmed = body.trim();
    if (trimmed.isEmpty) return (const [], const []);

    final decoded = _decodeBody(trimmed);
    final lines = decoded.split(RegExp(r'\r?\n'));
    final servers = <ParsedServer>[];
    final errors = <String>[];

    for (var i = 0; i < lines.length; i++) {
      final line = lines[i].trim();
      if (line.isEmpty) continue;

      final result = _parseVpnUri.call(line);
      switch (result) {
        case ParseSuccess(:final config):
          servers.add(ParsedServer(
            name: config.remark ??
                '${config.protocol}:${config.serverAddress}',
            rawUri: line,
            protocol: config.protocol,
            serverAddress: config.serverAddress,
            port: config.port,
            configData: _buildConfigData(config),
          ));
        case ParseFailure(:final message):
          errors.add('Line ${i + 1}: $message');
          AppLogger.debug(
            'Failed to parse subscription line',
            category: 'subscription',
            data: {'line': i + 1, 'error': message},
          );
      }
    }

    return (servers, errors);
  }

  /// Try to Base64-decode the body; fall back to plain text.
  String _decodeBody(String body) {
    // If body already looks like VPN URIs, treat as plain text.
    if (_looksLikePlainVpnUris(body)) return body;

    try {
      var normalized = body.replaceAll('-', '+').replaceAll('_', '/');
      final remainder = normalized.length % 4;
      if (remainder != 0) {
        normalized =
            normalized.padRight(normalized.length + (4 - remainder), '=');
      }
      return utf8.decode(base64.decode(normalized));
    } on FormatException {
      // Not valid Base64 — treat as plain text.
      return body;
    }
  }

  /// Check if content starts with a known VPN URI scheme.
  bool _looksLikePlainVpnUris(String content) {
    final firstLine = content.split('\n').first.trim().toLowerCase();
    return ParseVpnUri.supportedSchemes.any(firstLine.startsWith);
  }

  /// Build a JSON-encodable config data map from a [ParsedConfig].
  Map<String, dynamic> _buildConfigData(ParsedConfig config) {
    return <String, dynamic>{
      'uuid': config.uuid,
      if (config.password != null) 'password': config.password,
      if (config.transportSettings != null)
        'transport': config.transportSettings,
      if (config.tlsSettings != null) 'tls': config.tlsSettings,
      if (config.additionalParams != null) 'params': config.additionalParams,
    };
  }

  /// Remove query params and fragment from URL for safe logging.
  String _sanitizeUrl(String url) {
    final uri = Uri.tryParse(url);
    if (uri == null) return '***';
    return '${uri.scheme}://${uri.host}${uri.path.isEmpty ? '' : '/***'}';
  }
}

/// Exception thrown when fetching or parsing a subscription URL fails.
class SubscriptionFetcherException implements Exception {
  const SubscriptionFetcherException({
    required this.url,
    required this.message,
    this.cause,
  });

  /// The subscription URL that was being fetched.
  final String url;

  /// Human-readable error description.
  final String message;

  /// The underlying exception, if any.
  final Object? cause;

  @override
  String toString() => 'SubscriptionFetcherException: $message (URL: $url)';
}
