import 'package:cybervpn_mobile/core/routing/deep_link_parser.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// Route intent query parameters
// ---------------------------------------------------------------------------

const postAuthRedirectQueryParam = 'next';
const oauthCodeQueryParam = 'oauth_code';
const oauthStateQueryParam = 'oauth_state';
const telegramAuthDataQueryParam = 'telegram_auth_data';
const telegramBotTokenQueryParam = 'telegram_bot_token';
const referralCodeQueryParam = 'referral_code';

String buildRouteLocation(
  String path, {
  Map<String, String?> queryParameters = const <String, String?>{},
}) {
  final filtered = <String, String>{
    for (final entry in queryParameters.entries)
      if (entry.value != null && entry.value!.isNotEmpty)
        entry.key: entry.value!,
  };

  return Uri(
    path: path,
    queryParameters: filtered.isEmpty ? null : filtered,
  ).toString();
}

String buildAuthRouteLocation({
  required String authPath,
  String? postAuthRedirect,
  String? oauthCode,
  String? oauthState,
  String? telegramAuthData,
  String? telegramBotToken,
  String? referralCode,
}) {
  return buildRouteLocation(
    authPath,
    queryParameters: <String, String?>{
      postAuthRedirectQueryParam: postAuthRedirect,
      oauthCodeQueryParam: oauthCode,
      oauthStateQueryParam: oauthState,
      telegramAuthDataQueryParam: telegramAuthData,
      telegramBotTokenQueryParam: telegramBotToken,
      referralCodeQueryParam: referralCode,
    },
  );
}

String buildQuickSetupLocation({String? postAuthRedirect}) {
  return buildRouteLocation(
    '/quick-setup',
    queryParameters: <String, String?>{
      postAuthRedirectQueryParam: postAuthRedirect,
    },
  );
}

String buildPermissionsLocation({String? postAuthRedirect}) {
  return buildRouteLocation(
    '/permissions',
    queryParameters: <String, String?>{
      postAuthRedirectQueryParam: postAuthRedirect,
    },
  );
}

String buildOnboardingLocation({String? postAuthRedirect}) {
  return buildRouteLocation(
    '/onboarding',
    queryParameters: <String, String?>{
      postAuthRedirectQueryParam: postAuthRedirect,
    },
  );
}

String? readPostAuthRedirect(Uri uri) {
  return uri.queryParameters[postAuthRedirectQueryParam];
}

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
    OAuthCallbackRoute(:final provider, :final code, :final state) =>
      state != null
          ? '/profile/social-accounts?oauth_provider=$provider&oauth_code=$code&oauth_state=$state'
          : '/profile/social-accounts?oauth_provider=$provider&oauth_code=$code',
    TelegramAuthRoute(:final authData) => '/telegram-auth?auth_data=$authData',
    TelegramBotLinkRoute(:final token) => '/auth/telegram-link?token=$token',
    MagicLinkVerifyRoute(:final token) => '/magic-link/verify?token=$token',
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
      'Resolved deep link route',
      category: 'deep-link',
      data: {
        'route_type': result.route.runtimeType.toString(),
        'target_path': path,
      },
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
