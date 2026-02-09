import 'dart:convert';

// ---------------------------------------------------------------------------
// Deep link route types (sealed class hierarchy)
// ---------------------------------------------------------------------------

/// Represents a parsed deep link route with validated parameters.
sealed class DeepLinkRoute {
  const DeepLinkRoute();
}

/// Navigate to a server and optionally auto-connect.
///
/// Triggered by:
/// - `cybervpn://connect?server={id}`
/// - `https://cybervpn.app/connect?server={id}`
class ConnectRoute extends DeepLinkRoute {
  final String serverId;
  const ConnectRoute({required this.serverId});

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ConnectRoute && other.serverId == serverId;

  @override
  int get hashCode => serverId.hashCode;

  @override
  String toString() => 'ConnectRoute(serverId: $serverId)';
}

/// Import a VPN configuration from a base64-encoded payload.
///
/// Triggered by:
/// - `cybervpn://import?config={base64}`
/// - `https://cybervpn.app/import?config={base64}`
class ImportConfigRoute extends DeepLinkRoute {
  final String configBase64;
  const ImportConfigRoute({required this.configBase64});

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ImportConfigRoute && other.configBase64 == configBase64;

  @override
  int get hashCode => configBase64.hashCode;

  @override
  String toString() => 'ImportConfigRoute(configBase64: $configBase64)';
}

/// Apply a referral code.
///
/// Triggered by:
/// - `cybervpn://referral?code={code}`
/// - `https://cybervpn.app/referral?code={code}`
class ReferralRoute extends DeepLinkRoute {
  final String code;
  const ReferralRoute({required this.code});

  @override
  bool operator ==(Object other) =>
      identical(this, other) || other is ReferralRoute && other.code == code;

  @override
  int get hashCode => code.hashCode;

  @override
  String toString() => 'ReferralRoute(code: $code)';
}

/// Navigate to a subscription plan.
///
/// Triggered by:
/// - `cybervpn://subscribe?plan={id}`
/// - `https://cybervpn.app/subscribe?plan={id}`
class SubscribeRoute extends DeepLinkRoute {
  final String planId;
  const SubscribeRoute({required this.planId});

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SubscribeRoute && other.planId == planId;

  @override
  int get hashCode => planId.hashCode;

  @override
  String toString() => 'SubscribeRoute(planId: $planId)';
}

/// Navigate to the settings screen.
///
/// Triggered by:
/// - `cybervpn://settings`
/// - `https://cybervpn.app/settings`
class SettingsRoute extends DeepLinkRoute {
  const SettingsRoute();

  @override
  bool operator ==(Object other) =>
      identical(this, other) || other is SettingsRoute;

  @override
  int get hashCode => runtimeType.hashCode;

  @override
  String toString() => 'SettingsRoute()';
}

/// Navigate to VPN connection screen from widget tap.
///
/// Triggered by:
/// - `cybervpn://widget-action`
///
/// This is a simple route used by iOS WidgetKit widgets to open
/// the main VPN connection screen when tapped.
class WidgetActionRoute extends DeepLinkRoute {
  const WidgetActionRoute();

  @override
  bool operator ==(Object other) =>
      identical(this, other) || other is WidgetActionRoute;

  @override
  int get hashCode => runtimeType.hashCode;

  @override
  String toString() => 'WidgetActionRoute()';
}

/// OAuth callback route for social account linking and OAuth login.
///
/// Triggered by:
/// - `cybervpn://oauth/callback?provider={provider}&code={code}`
/// - `cybervpn://oauth/callback?provider={provider}&code={code}&state={state}`
/// - `https://cybervpn.app/oauth/callback?provider={provider}&code={code}`
///
/// The optional [state] parameter is used for OAuth login flows (PKCE) to
/// distinguish them from account-linking flows.
class OAuthCallbackRoute extends DeepLinkRoute {
  final String provider;
  final String code;
  final String? state;
  const OAuthCallbackRoute({required this.provider, required this.code, this.state});

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is OAuthCallbackRoute &&
          other.provider == provider &&
          other.code == code &&
          other.state == state;

  @override
  int get hashCode => Object.hash(provider, code, state);

  @override
  String toString() => 'OAuthCallbackRoute(provider: $provider, code: $code, state: $state)';
}

/// Telegram OAuth callback route for authentication.
///
/// Triggered by:
/// - `cybervpn://telegram/callback?auth_data={base64}`
/// - `https://cybervpn.app/telegram/callback?auth_data={base64}`
///
/// The auth_data parameter contains base64-encoded JSON with Telegram user
/// info and HMAC-SHA256 signature for validation.
class TelegramAuthRoute extends DeepLinkRoute {
  /// Base64-encoded Telegram auth data with HMAC signature.
  final String authData;

  const TelegramAuthRoute({required this.authData});

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is TelegramAuthRoute && other.authData == authData;

  @override
  int get hashCode => authData.hashCode;

  @override
  String toString() => 'TelegramAuthRoute(authData: $authData)';
}

/// Magic link verification route.
///
/// Triggered by:
/// - `cybervpn://magic-link/verify?token={token}`
/// - `https://cybervpn.app/magic-link/verify?token={token}`
class MagicLinkVerifyRoute extends DeepLinkRoute {
  final String token;
  const MagicLinkVerifyRoute({required this.token});

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is MagicLinkVerifyRoute && other.token == token;

  @override
  int get hashCode => token.hashCode;

  @override
  String toString() => 'MagicLinkVerifyRoute(token: $token)';
}

// ---------------------------------------------------------------------------
// Parse error
// ---------------------------------------------------------------------------

/// Returned when a deep link cannot be parsed or validated.
class DeepLinkParseError {
  final String message;
  final Uri? uri;
  const DeepLinkParseError({required this.message, this.uri});

  @override
  String toString() => 'DeepLinkParseError($message, uri: $uri)';
}

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

/// Parses incoming deep link URIs into typed [DeepLinkRoute] instances.
///
/// Supports two URI formats:
/// - Custom scheme: `cybervpn://connect?server=123`
/// - Universal link: `https://cybervpn.app/connect?server=123`
class DeepLinkParser {
  /// The custom URL scheme for the app.
  static const String customScheme = 'cybervpn';

  /// The host for universal links.
  static const String universalLinkHost = 'cybervpn.app';

  /// Accepted schemes for deep links.
  static const Set<String> _validSchemes = {customScheme, 'https', 'http'};

  /// Attempts to parse a URI string into a [DeepLinkRoute].
  ///
  /// Returns either a [DeepLinkRoute] on success or a [DeepLinkParseError]
  /// if the URI is invalid, unsupported, or missing required parameters.
  static ({DeepLinkRoute? route, DeepLinkParseError? error}) parse(
    String uriString,
  ) {
    final Uri uri;
    try {
      uri = Uri.parse(uriString);
    } catch (e) {
      return (
        route: null,
        error: const DeepLinkParseError(
          message: 'Invalid URI format',
        ),
      );
    }

    if (!_validSchemes.contains(uri.scheme)) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Unsupported scheme: ${uri.scheme}',
          uri: uri,
        ),
      );
    }

    // For universal links, verify the host matches.
    if ((uri.scheme == 'https' || uri.scheme == 'http') &&
        uri.host != universalLinkHost) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Unsupported host: ${uri.host}',
          uri: uri,
        ),
      );
    }

    // Determine the route path segment.
    // For custom scheme: cybervpn://connect -> host = 'connect', path = ''
    //                    cybervpn://telegram/callback -> host = 'telegram', path = '/callback'
    // For universal links: https://cybervpn.app/connect -> path = '/connect'
    final String routePath;
    if (uri.scheme == customScheme) {
      // In custom scheme URIs, combine host and path for routes with subpaths.
      // Example: cybervpn://telegram/callback -> "telegram" + "/callback" = "telegram/callback"
      routePath = uri.host + uri.path;
    } else {
      // Universal link: strip leading '/' from path.
      routePath = uri.path.startsWith('/')
          ? uri.path.substring(1)
          : uri.path;
    }

    return _parseRoute(routePath, uri.queryParameters, uri);
  }

  /// Attempts to parse a [Uri] object into a [DeepLinkRoute].
  static ({DeepLinkRoute? route, DeepLinkParseError? error}) parseUri(
    Uri uri,
  ) {
    return parse(uri.toString());
  }

  /// Returns `true` if the given URI string looks like a CyberVPN deep link.
  static bool isDeepLink(String uriString) {
    try {
      final uri = Uri.parse(uriString);
      if (uri.scheme == customScheme) return true;
      if ((uri.scheme == 'https' || uri.scheme == 'http') &&
          uri.host == universalLinkHost) {
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  // -----------------------------------------------------------------------
  // Private helpers
  // -----------------------------------------------------------------------

  static ({DeepLinkRoute? route, DeepLinkParseError? error}) _parseRoute(
    String routePath,
    Map<String, String> queryParams,
    Uri uri,
  ) {
    switch (routePath) {
      case 'connect':
        return _parseConnect(queryParams, uri);
      case 'import':
        return _parseImport(queryParams, uri);
      case 'referral':
        return _parseReferral(queryParams, uri);
      case 'subscribe':
        return _parseSubscribe(queryParams, uri);
      case 'settings':
        return (route: const SettingsRoute(), error: null);
      case 'widget-action':
        return (route: const WidgetActionRoute(), error: null);
      case 'oauth/callback':
        return _parseOAuthCallback(queryParams, uri);
      case 'telegram/callback':
        return _parseTelegramCallback(queryParams, uri);
      case 'magic-link/verify':
        return _parseMagicLinkVerify(queryParams, uri);
      default:
        return (
          route: null,
          error: DeepLinkParseError(
            message: 'Unknown route: $routePath',
            uri: uri,
          ),
        );
    }
  }

  static ({DeepLinkRoute? route, DeepLinkParseError? error}) _parseConnect(
    Map<String, String> queryParams,
    Uri uri,
  ) {
    final serverId = queryParams['server'];
    if (serverId == null || serverId.isEmpty) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Missing required parameter: server',
          uri: uri,
        ),
      );
    }
    // Validate that serverId looks like a valid identifier (alphanumeric + hyphens).
    if (!RegExp(r'^[a-zA-Z0-9\-_]+$').hasMatch(serverId)) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Invalid server ID format: $serverId',
          uri: uri,
        ),
      );
    }
    return (route: ConnectRoute(serverId: serverId), error: null);
  }

  static ({DeepLinkRoute? route, DeepLinkParseError? error}) _parseImport(
    Map<String, String> queryParams,
    Uri uri,
  ) {
    final config = queryParams['config'];
    if (config == null || config.isEmpty) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Missing required parameter: config',
          uri: uri,
        ),
      );
    }
    // Validate base64 format (standard or URL-safe base64).
    if (!RegExp(r'^[A-Za-z0-9+/\-_]+=*$').hasMatch(config)) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Invalid base64 config format',
          uri: uri,
        ),
      );
    }
    // Verify it actually decodes.
    try {
      base64Decode(config.replaceAll('-', '+').replaceAll('_', '/'));
    } catch (e) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Config is not valid base64',
          uri: uri,
        ),
      );
    }
    return (route: ImportConfigRoute(configBase64: config), error: null);
  }

  static ({DeepLinkRoute? route, DeepLinkParseError? error}) _parseReferral(
    Map<String, String> queryParams,
    Uri uri,
  ) {
    final code = queryParams['code'];
    if (code == null || code.isEmpty) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Missing required parameter: code',
          uri: uri,
        ),
      );
    }
    // Validate referral code: alphanumeric, hyphens, underscores.
    if (!RegExp(r'^[a-zA-Z0-9\-_]+$').hasMatch(code)) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Invalid referral code format: $code',
          uri: uri,
        ),
      );
    }
    return (route: ReferralRoute(code: code), error: null);
  }

  static ({DeepLinkRoute? route, DeepLinkParseError? error}) _parseSubscribe(
    Map<String, String> queryParams,
    Uri uri,
  ) {
    final planId = queryParams['plan'];
    if (planId == null || planId.isEmpty) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Missing required parameter: plan',
          uri: uri,
        ),
      );
    }
    // Validate plan ID: alphanumeric, hyphens, underscores.
    if (!RegExp(r'^[a-zA-Z0-9\-_]+$').hasMatch(planId)) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Invalid plan ID format: $planId',
          uri: uri,
        ),
      );
    }
    return (route: SubscribeRoute(planId: planId), error: null);
  }

  static ({DeepLinkRoute? route, DeepLinkParseError? error}) _parseOAuthCallback(
    Map<String, String> queryParams,
    Uri uri,
  ) {
    final provider = queryParams['provider'];
    if (provider == null || provider.isEmpty) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Missing required parameter: provider',
          uri: uri,
        ),
      );
    }
    final code = queryParams['code'];
    if (code == null || code.isEmpty) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Missing required parameter: code',
          uri: uri,
        ),
      );
    }
    // Validate provider name: lowercase alphanumeric.
    if (!RegExp(r'^[a-z]+$').hasMatch(provider)) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Invalid provider format: $provider',
          uri: uri,
        ),
      );
    }
    // state is optional since some flows (account linking) don't use it.
    final state = queryParams['state'];
    return (route: OAuthCallbackRoute(provider: provider, code: code, state: state), error: null);
  }

  static ({DeepLinkRoute? route, DeepLinkParseError? error}) _parseTelegramCallback(
    Map<String, String> queryParams,
    Uri uri,
  ) {
    final authData = queryParams['auth_data'];
    if (authData == null || authData.isEmpty) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Missing required parameter: auth_data',
          uri: uri,
        ),
      );
    }
    // Validate base64 format (standard or URL-safe base64).
    if (!RegExp(r'^[A-Za-z0-9+/\-_]+=*$').hasMatch(authData)) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Invalid base64 auth_data format',
          uri: uri,
        ),
      );
    }
    // Verify it actually decodes.
    try {
      base64Decode(authData.replaceAll('-', '+').replaceAll('_', '/'));
    } catch (e) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'auth_data is not valid base64',
          uri: uri,
        ),
      );
    }
    return (route: TelegramAuthRoute(authData: authData), error: null);
  }

  static ({DeepLinkRoute? route, DeepLinkParseError? error}) _parseMagicLinkVerify(
    Map<String, String> queryParams,
    Uri uri,
  ) {
    final token = queryParams['token'];
    if (token == null || token.isEmpty) {
      return (
        route: null,
        error: DeepLinkParseError(
          message: 'Missing required parameter: token',
          uri: uri,
        ),
      );
    }
    return (route: MagicLinkVerifyRoute(token: token), error: null);
  }
}
