import 'package:freezed_annotation/freezed_annotation.dart';

import 'package:cybervpn_mobile/features/vpn_profiles/data/models/parsed_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/subscription_info.dart';

part 'fetch_result.freezed.dart';

/// Result of fetching and parsing a VPN subscription URL.
///
/// Contains the subscription metadata (traffic usage, expiry, etc.)
/// parsed from response headers, and the list of VPN servers parsed
/// from the response body.
@freezed
sealed class FetchResult with _$FetchResult {
  const factory FetchResult({
    /// Subscription metadata parsed from response headers.
    required SubscriptionInfo info,

    /// VPN servers parsed from the response body.
    required List<ParsedServer> servers,

    /// Lines from the response body that failed to parse.
    ///
    /// Each entry is a human-readable error string including the
    /// line number and reason for failure.
    @Default([]) List<String> parseErrors,
  }) = _FetchResult;
}
