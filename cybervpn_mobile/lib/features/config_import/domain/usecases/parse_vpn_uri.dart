import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/features/config_import/data/parsers/shadowsocks_parser.dart';
import 'package:cybervpn_mobile/features/config_import/data/parsers/trojan_parser.dart';
import 'package:cybervpn_mobile/features/config_import/data/parsers/vless_parser.dart';
import 'package:cybervpn_mobile/features/config_import/data/parsers/vmess_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';

/// Use case that dispatches a raw VPN URI string to the correct protocol
/// parser based on its URI scheme.
///
/// Supported schemes:
/// - `vless://` -> [VlessParser]
/// - `vmess://` -> [VmessParser]
/// - `trojan://` -> [TrojanParser]
/// - `ss://` -> [ShadowsocksParser]
///
/// Usage:
/// ```dart
/// final useCase = ParseVpnUri();
/// final result = useCase.call('vless://...');
/// switch (result) {
///   case ParseSuccess(:final config):
///     // use config
///   case ParseFailure(:final message):
///     // handle error
/// }
/// ```
@immutable
class ParseVpnUri {
  /// Creates a [ParseVpnUri] use case with optional custom parsers.
  ///
  /// If [parsers] is not provided, the default set of protocol parsers
  /// (VLESS, VMess, Trojan, Shadowsocks) is used.
  ParseVpnUri({List<VpnUriParser>? parsers})
      : _parsers = parsers ??
            <VpnUriParser>[
              VlessParser(),
              VmessParser(),
              TrojanParser(),
              ShadowsocksParser(),
            ];

  final List<VpnUriParser> _parsers;

  /// Supported URI scheme prefixes for quick reference.
  static const supportedSchemes = <String>[
    'vless://',
    'vmess://',
    'trojan://',
    'ss://',
  ];

  /// Parse a raw VPN URI string and return a [ParseResult].
  ///
  /// Detects the URI scheme and dispatches to the appropriate protocol
  /// parser. Returns [ParseFailure] for null, empty, or unknown schemes.
  ParseResult call(String? uri) {
    // Handle null or empty input
    if (uri == null || uri.trim().isEmpty) {
      return const ParseFailure('URI is null or empty');
    }

    final trimmed = uri.trim();

    // Find a parser that can handle this URI
    for (final parser in _parsers) {
      if (parser.canParse(trimmed)) {
        return parser.parse(trimmed);
      }
    }

    // No parser matched — extract the scheme for a descriptive error
    final scheme = _extractScheme(trimmed);
    if (scheme != null) {
      return ParseFailure(
        'Unsupported VPN URI scheme "$scheme". '
        'Supported schemes: ${supportedSchemes.join(", ")}',
      );
    }

    return ParseFailure(
      'Invalid VPN URI: no scheme detected. '
      'Expected one of: ${supportedSchemes.join(", ")}',
    );
  }

  /// Attempt to extract the scheme portion from a URI string.
  ///
  /// Returns the scheme (e.g. "http") or null if no `://` separator is found.
  String? _extractScheme(String uri) {
    final separatorIndex = uri.indexOf('://');
    if (separatorIndex > 0) {
      return uri.substring(0, separatorIndex).toLowerCase();
    }
    return null;
  }
}
