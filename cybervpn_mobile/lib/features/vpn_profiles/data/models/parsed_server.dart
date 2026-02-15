import 'package:freezed_annotation/freezed_annotation.dart';

part 'parsed_server.freezed.dart';

/// A server entry parsed from a subscription response body.
///
/// Wraps the raw URI and extracted fields from the VPN URI parsers.
/// This is a data-layer model used by [SubscriptionFetcher] before
/// mapping to the domain [ProfileServer] entity.
@freezed
sealed class ParsedServer with _$ParsedServer {
  const factory ParsedServer({
    /// Display name extracted from the URI remark/fragment.
    required String name,

    /// The original raw URI line (e.g. `vless://...`, `vmess://...`).
    required String rawUri,

    /// Protocol identifier: `vless`, `vmess`, `trojan`, or `ss`.
    required String protocol,

    /// Server hostname or IP address.
    required String serverAddress,

    /// Server port number.
    required int port,

    /// Full parsed configuration data as JSON-encodable map.
    ///
    /// Contains transport settings, TLS settings, UUID, and any
    /// protocol-specific parameters extracted by the parser.
    required Map<String, dynamic> configData,
  }) = _ParsedServer;
}
