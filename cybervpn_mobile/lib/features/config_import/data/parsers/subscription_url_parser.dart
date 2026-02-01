import 'dart:convert';

import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/parsed_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/usecases/parse_vpn_uri.dart';
import 'package:dio/dio.dart';

/// Result of parsing a subscription URL.
///
/// Contains both the successfully parsed configs and any errors
/// encountered during parsing individual lines.
class SubscriptionParseResult {
  const SubscriptionParseResult({
    required this.configs,
    required this.errors,
  });

  /// Successfully parsed VPN configurations.
  final List<ImportedConfig> configs;

  /// Errors encountered for individual lines that could not be parsed.
  ///
  /// Each entry contains the line number, the raw URI, and the error message.
  final List<SubscriptionParseError> errors;

  /// Whether all lines were parsed successfully (no errors).
  bool get isFullSuccess => errors.isEmpty && configs.isNotEmpty;

  /// Whether some lines parsed and some failed.
  bool get isPartialSuccess => configs.isNotEmpty && errors.isNotEmpty;

  /// Whether no lines could be parsed at all.
  bool get isFailure => configs.isEmpty;
}

/// Describes a single parse error from a subscription line.
class SubscriptionParseError {
  const SubscriptionParseError({
    required this.lineNumber,
    required this.rawUri,
    required this.message,
  });

  /// 1-based line number within the decoded subscription content.
  final int lineNumber;

  /// The raw URI string that failed to parse.
  final String rawUri;

  /// Human-readable error description.
  final String message;

  @override
  String toString() => 'Line $lineNumber: $message (URI: $rawUri)';
}

/// Fetches a subscription URL, decodes the base64 response, and parses
/// each line as a VPN URI into [ImportedConfig] objects.
///
/// Subscription URLs typically return a base64-encoded body where each
/// decoded line is a VPN URI (vless://, vmess://, trojan://, ss://).
///
/// Usage:
/// ```dart
/// final parser = SubscriptionUrlParser(dio: Dio());
/// final result = await parser.parse('https://example.com/sub');
/// for (final config in result.configs) {
///   // use config
/// }
/// for (final error in result.errors) {
///   // log error
/// }
/// ```
class SubscriptionUrlParser {
  /// Creates a [SubscriptionUrlParser].
  ///
  /// [dio] is the HTTP client used for fetching the subscription URL.
  /// [parseVpnUri] is the use case for parsing individual VPN URIs.
  /// If not provided, defaults are used.
  SubscriptionUrlParser({
    required Dio dio,
    ParseVpnUri? parseVpnUri,
  })  : _dio = dio,
        _parseVpnUri = parseVpnUri ?? ParseVpnUri();

  final Dio _dio;
  final ParseVpnUri _parseVpnUri;

  /// Default HTTP timeout for subscription URL requests.
  static const Duration defaultTimeout = Duration(seconds: 30);

  /// Fetch and parse a subscription URL.
  ///
  /// Performs an HTTP GET to [url], decodes the base64 response body,
  /// splits by newlines, and parses each line as a VPN URI.
  ///
  /// Returns a [SubscriptionParseResult] containing valid configs and
  /// any parse errors. Network and decoding errors throw exceptions.
  ///
  /// Throws [SubscriptionFetchException] on HTTP or network errors.
  /// Throws [SubscriptionDecodeException] if the response is not valid base64.
  Future<SubscriptionParseResult> parse(String url) async {
    final responseBody = await _fetchSubscriptionContent(url);
    final decodedContent = _decodeBase64Content(responseBody);
    return _parseDecodedContent(decodedContent, url);
  }

  /// Perform HTTP GET and return the raw response body string.
  ///
  /// Validates that the URL is well-formed and the response status is 2xx.
  Future<String> _fetchSubscriptionContent(String url) async {
    // Validate URL format
    final uri = Uri.tryParse(url);
    if (uri == null || !uri.hasScheme || !uri.hasAuthority) {
      throw SubscriptionFetchException(
        url: url,
        message: 'Invalid subscription URL format',
      );
    }

    try {
      final response = await _dio.get<String>(
        url,
        options: Options(
          responseType: ResponseType.plain,
          receiveTimeout: defaultTimeout,
          sendTimeout: defaultTimeout,
        ),
      );

      final body = response.data;
      if (body == null || body.trim().isEmpty) {
        throw SubscriptionFetchException(
          url: url,
          message: 'Empty response body from subscription URL',
        );
      }

      return body;
    } on DioException catch (e) {
      final statusCode = e.response?.statusCode;
      final statusMessage = statusCode != null
          ? 'HTTP $statusCode'
          : e.type.name;
      throw SubscriptionFetchException(
        url: url,
        message: 'Failed to fetch subscription: $statusMessage',
        cause: e,
      );
    }
  }

  /// Decode a base64 or base64url encoded string.
  ///
  /// Handles missing padding and URL-safe base64 characters.
  /// Falls back to treating the input as plain text if it appears to
  /// already contain VPN URIs (non-base64 subscription providers).
  String _decodeBase64Content(String content) {
    final trimmed = content.trim();

    // If the content already looks like VPN URIs (starts with a known scheme),
    // treat it as plain text — some providers do not base64-encode.
    if (_looksLikePlainVpnUris(trimmed)) {
      return trimmed;
    }

    try {
      // Normalize base64url to standard base64
      var normalized = trimmed.replaceAll('-', '+').replaceAll('_', '/');

      // Add padding if needed
      final remainder = normalized.length % 4;
      if (remainder != 0) {
        normalized =
            normalized.padRight(normalized.length + (4 - remainder), '=');
      }

      return utf8.decode(base64.decode(normalized));
    } on FormatException catch (e) {
      throw SubscriptionDecodeException(
        message: 'Response is not valid base64: ${e.message}',
        cause: e,
      );
    }
  }

  /// Check if the content starts with a known VPN URI scheme,
  /// indicating it is already plain text and not base64-encoded.
  bool _looksLikePlainVpnUris(String content) {
    final firstLine = content.split('\n').first.trim().toLowerCase();
    return ParseVpnUri.supportedSchemes.any(firstLine.startsWith);
  }

  /// Split decoded content by newlines and parse each line as a VPN URI.
  ///
  /// Empty lines and whitespace-only lines are skipped.
  /// Successfully parsed configs are collected into the result list.
  /// Failed parses are collected into the errors list with line context.
  SubscriptionParseResult _parseDecodedContent(
    String decodedContent,
    String subscriptionUrl,
  ) {
    final lines = decodedContent.split(RegExp(r'\r?\n'));
    final configs = <ImportedConfig>[];
    final errors = <SubscriptionParseError>[];

    for (var i = 0; i < lines.length; i++) {
      final line = lines[i].trim();
      if (line.isEmpty) continue;

      final lineNumber = i + 1;
      final result = _parseVpnUri.call(line);

      switch (result) {
        case ParseSuccess(:final config):
          configs.add(
            _toImportedConfig(
              config: config,
              rawUri: line,
              subscriptionUrl: subscriptionUrl,
            ),
          );
        case ParseFailure(:final message):
          errors.add(
            SubscriptionParseError(
              lineNumber: lineNumber,
              rawUri: line,
              message: message,
            ),
          );
      }
    }

    return SubscriptionParseResult(configs: configs, errors: errors);
  }

  /// Convert a [ParsedConfig] into an [ImportedConfig] with subscription
  /// metadata.
  ImportedConfig _toImportedConfig({
    required ParsedConfig config,
    required String rawUri,
    required String subscriptionUrl,
  }) {
    return ImportedConfig(
      id: _generateId(rawUri),
      name: config.remark ?? '${config.protocol}:${config.serverAddress}',
      rawUri: rawUri,
      protocol: config.protocol,
      serverAddress: config.serverAddress,
      port: config.port,
      source: ImportSource.subscriptionUrl,
      subscriptionUrl: subscriptionUrl,
      importedAt: DateTime.now(),
    );
  }

  /// Generate a deterministic ID from the raw URI for deduplication.
  String _generateId(String rawUri) {
    // Use a simple hash-based approach for ID generation.
    // This ensures the same URI always produces the same ID.
    final bytes = utf8.encode(rawUri);
    var hash = 0xcbf29ce484222325;
    for (final byte in bytes) {
      hash ^= byte;
      hash = (hash * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF;
    }
    return hash.toRadixString(16).padLeft(16, '0');
  }
}

/// Exception thrown when fetching the subscription URL fails.
class SubscriptionFetchException implements Exception {
  const SubscriptionFetchException({
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
  String toString() => 'SubscriptionFetchException: $message (URL: $url)';
}

/// Exception thrown when decoding the subscription response fails.
class SubscriptionDecodeException implements Exception {
  const SubscriptionDecodeException({
    required this.message,
    this.cause,
  });

  /// Human-readable error description.
  final String message;

  /// The underlying exception, if any.
  final Object? cause;

  @override
  String toString() => 'SubscriptionDecodeException: $message';
}
