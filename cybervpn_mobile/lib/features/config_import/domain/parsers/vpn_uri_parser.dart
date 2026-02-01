import 'package:cybervpn_mobile/features/config_import/domain/entities/parsed_config.dart';

/// Result of a VPN URI parse attempt
sealed class ParseResult {
  const ParseResult();
}

/// Successful parse result containing the parsed configuration
class ParseSuccess extends ParseResult {
  const ParseSuccess(this.config);

  /// The successfully parsed VPN configuration
  final ParsedConfig config;
}

/// Failed parse result containing an error description
class ParseFailure extends ParseResult {
  const ParseFailure(this.message);

  /// Human-readable error description
  final String message;
}

/// Abstract interface for parsing VPN protocol URIs
///
/// Implementations handle specific protocols such as VLESS, VMess,
/// Trojan, and Shadowsocks. Each parser validates the URI scheme,
/// extracts server address, port, encryption settings, and
/// protocol-specific parameters.
abstract class VpnUriParser {
  /// Parse a VPN URI string and extract configuration details
  ///
  /// Returns a [ParseResult] indicating success or failure.
  /// Use pattern matching to handle the result:
  /// ```dart
  /// switch (parser.parse(uri)) {
  ///   case ParseSuccess(:final config):
  ///     // use config
  ///   case ParseFailure(:final message):
  ///     // handle error
  /// }
  /// ```
  ParseResult parse(String uri);

  /// Check if this parser can handle the given URI
  ///
  /// Returns true if the URI scheme matches this parser's protocol.
  /// This is a quick check that does not validate the full URI.
  bool canParse(String uri);

  /// Get the protocol name this parser handles (e.g., 'vless', 'vmess', 'trojan', 'ss')
  String get protocolName;
}
