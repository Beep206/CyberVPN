import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/routing/deep_link_parser.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// Pending deep link state
// ---------------------------------------------------------------------------

/// Holds a pending [DeepLinkRoute] that should be executed after the user
/// authenticates.
///
/// When a deep link arrives while the user is unauthenticated, the route is
/// stored here. After login completes, the router consumes and clears it.
class PendingDeepLinkNotifier extends Notifier<DeepLinkRoute?> {
  @override
  DeepLinkRoute? build() => null;

  /// Store a deep link to execute after authentication.
  void setPending(DeepLinkRoute route) {
    state = route;
    AppLogger.info(
      'Stored pending deep link: $route',
      category: 'deep-link',
    );
  }

  /// Consume and return the pending deep link, clearing the state.
  DeepLinkRoute? consume() {
    final route = state;
    if (route != null) {
      state = null;
      AppLogger.info(
        'Consumed pending deep link: $route',
        category: 'deep-link',
      );
    }
    return route;
  }

  /// Clear the pending deep link without consuming it.
  void clear() {
    state = null;
  }
}

/// Provider for the pending deep link state.
final pendingDeepLinkProvider =
    NotifierProvider<PendingDeepLinkNotifier, DeepLinkRoute?>(() {
  return PendingDeepLinkNotifier();
});

// ---------------------------------------------------------------------------
// Route resolution
// ---------------------------------------------------------------------------

/// Resolves a [DeepLinkRoute] to a GoRouter path string.
///
/// Returns the internal app path that GoRouter should navigate to for the
/// given deep link route.
String resolveDeepLinkPath(DeepLinkRoute route) {
  return switch (route) {
    ConnectRoute(:final serverId) => '/servers/$serverId',
    ImportConfigRoute(:final configBase64) =>
      '/config-import?config=$configBase64',
    ReferralRoute(:final code) => '/referral?code=$code',
    SubscribeRoute(:final planId) => '/subscribe?plan=$planId',
    SettingsRoute() => '/settings',
    WidgetActionRoute() => '/connection',
    OAuthCallbackRoute(:final provider, :final code) =>
      '/profile/social-accounts?oauth_provider=$provider&oauth_code=$code',
  };
}

/// Attempts to parse the current URI as a deep link and return the resolved
/// internal path.
///
/// This is designed to be called from GoRouter's `redirect` callback.
/// Returns `null` if the URI is not a recognized deep link.
String? resolveDeepLinkFromUri(Uri uri) {
  // Only process URIs that look like deep links.
  final uriString = uri.toString();
  if (!DeepLinkParser.isDeepLink(uriString)) {
    return null;
  }

  final result = DeepLinkParser.parse(uriString);
  if (result.route != null) {
    final path = resolveDeepLinkPath(result.route!);
    AppLogger.info(
      'Resolved deep link $uriString -> $path',
      category: 'deep-link',
    );
    return path;
  }

  if (result.error != null) {
    AppLogger.warning(
      'Failed to parse deep link: ${result.error!.message}',
      category: 'deep-link',
    );
  }

  return null;
}
