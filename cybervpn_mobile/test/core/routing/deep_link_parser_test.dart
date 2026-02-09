import 'dart:convert';

import 'package:cybervpn_mobile/core/routing/deep_link_parser.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('DeepLinkParser', () {
    // -----------------------------------------------------------------------
    // Connect route
    // -----------------------------------------------------------------------
    group('connect route', () {
      test('parses custom scheme with numeric server ID', () {
        final result = DeepLinkParser.parse('cybervpn://connect?server=123');
        expect(result.route, isA<ConnectRoute>());
        expect((result.route as ConnectRoute).serverId, '123');
        expect(result.error, isNull);
      });

      test('parses custom scheme with alphanumeric server ID', () {
        final result =
            DeepLinkParser.parse('cybervpn://connect?server=srv-abc-123');
        expect(result.route, isA<ConnectRoute>());
        expect((result.route as ConnectRoute).serverId, 'srv-abc-123');
        expect(result.error, isNull);
      });

      test('parses universal link with server ID', () {
        final result = DeepLinkParser.parse(
          'https://cybervpn.app/connect?server=456',
        );
        expect(result.route, isA<ConnectRoute>());
        expect((result.route as ConnectRoute).serverId, '456');
        expect(result.error, isNull);
      });

      test('returns error when server param is missing', () {
        final result = DeepLinkParser.parse('cybervpn://connect');
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('server'));
      });

      test('returns error for invalid server ID with special chars', () {
        final result =
            DeepLinkParser.parse('cybervpn://connect?server=ab@cd');
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('Invalid server ID'));
      });
    });

    // -----------------------------------------------------------------------
    // Import route
    // -----------------------------------------------------------------------
    group('import route', () {
      test('parses valid base64 config', () {
        final encoded = base64Encode(utf8.encode('vless://test-config'));
        final result =
            DeepLinkParser.parse('cybervpn://import?config=$encoded');
        expect(result.route, isA<ImportConfigRoute>());
        expect((result.route as ImportConfigRoute).configBase64, encoded);
        expect(result.error, isNull);
      });

      test('parses universal link with base64 config', () {
        final encoded = base64Encode(utf8.encode('ss://test'));
        final result = DeepLinkParser.parse(
          'https://cybervpn.app/import?config=$encoded',
        );
        expect(result.route, isA<ImportConfigRoute>());
        expect(result.error, isNull);
      });

      test('returns error when config param is missing', () {
        final result = DeepLinkParser.parse('cybervpn://import');
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('config'));
      });

      test('returns error for malformed base64', () {
        final result =
            DeepLinkParser.parse('cybervpn://import?config=!!!not-base64');
        expect(result.route, isNull);
        expect(result.error, isNotNull);
      });
    });

    // -----------------------------------------------------------------------
    // Referral route
    // -----------------------------------------------------------------------
    group('referral route', () {
      test('parses valid alphanumeric referral code', () {
        final result =
            DeepLinkParser.parse('cybervpn://referral?code=REF123');
        expect(result.route, isA<ReferralRoute>());
        expect((result.route as ReferralRoute).code, 'REF123');
        expect(result.error, isNull);
      });

      test('parses referral code with hyphens and underscores', () {
        final result =
            DeepLinkParser.parse('cybervpn://referral?code=ref-code_123');
        expect(result.route, isA<ReferralRoute>());
        expect((result.route as ReferralRoute).code, 'ref-code_123');
        expect(result.error, isNull);
      });

      test('parses universal link referral', () {
        final result = DeepLinkParser.parse(
          'https://cybervpn.app/referral?code=ABC',
        );
        expect(result.route, isA<ReferralRoute>());
        expect(result.error, isNull);
      });

      test('returns error when code param is missing', () {
        final result = DeepLinkParser.parse('cybervpn://referral');
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('code'));
      });

      test('returns error for invalid referral code', () {
        final result =
            DeepLinkParser.parse('cybervpn://referral?code=code@bad!');
        expect(result.route, isNull);
        expect(result.error, isNotNull);
      });
    });

    // -----------------------------------------------------------------------
    // Subscribe route
    // -----------------------------------------------------------------------
    group('subscribe route', () {
      test('parses valid plan ID', () {
        final result =
            DeepLinkParser.parse('cybervpn://subscribe?plan=premium-1');
        expect(result.route, isA<SubscribeRoute>());
        expect((result.route as SubscribeRoute).planId, 'premium-1');
        expect(result.error, isNull);
      });

      test('parses universal link subscribe', () {
        final result = DeepLinkParser.parse(
          'https://cybervpn.app/subscribe?plan=basic',
        );
        expect(result.route, isA<SubscribeRoute>());
        expect(result.error, isNull);
      });

      test('returns error when plan param is missing', () {
        final result = DeepLinkParser.parse('cybervpn://subscribe');
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('plan'));
      });
    });

    // -----------------------------------------------------------------------
    // Settings route
    // -----------------------------------------------------------------------
    group('settings route', () {
      test('parses custom scheme settings', () {
        final result = DeepLinkParser.parse('cybervpn://settings');
        expect(result.route, isA<SettingsRoute>());
        expect(result.error, isNull);
      });

      test('parses universal link settings', () {
        final result =
            DeepLinkParser.parse('https://cybervpn.app/settings');
        expect(result.route, isA<SettingsRoute>());
        expect(result.error, isNull);
      });
    });

    // -----------------------------------------------------------------------
    // OAuth callback route
    // -----------------------------------------------------------------------
    group('OAuth callback', () {
      test('parses custom scheme OAuth callback with provider and code', () {
        final result = DeepLinkParser.parse(
          'cybervpn://oauth/callback?provider=github&code=abc123',
        );
        expect(result.route, isA<OAuthCallbackRoute>());
        expect(result.error, isNull);
        final route = result.route as OAuthCallbackRoute;
        expect(route.provider, 'github');
        expect(route.code, 'abc123');
        expect(route.state, isNull);
      });

      test('parses OAuth callback with provider, code, and state', () {
        final result = DeepLinkParser.parse(
          'cybervpn://oauth/callback?provider=google&code=xyz&state=pkce_state',
        );
        expect(result.route, isA<OAuthCallbackRoute>());
        expect(result.error, isNull);
        final route = result.route as OAuthCallbackRoute;
        expect(route.provider, 'google');
        expect(route.code, 'xyz');
        expect(route.state, 'pkce_state');
      });

      test('parses universal link OAuth callback', () {
        final result = DeepLinkParser.parse(
          'https://cybervpn.app/oauth/callback?provider=discord&code=test',
        );
        expect(result.route, isA<OAuthCallbackRoute>());
        expect(result.error, isNull);
        final route = result.route as OAuthCallbackRoute;
        expect(route.provider, 'discord');
        expect(route.code, 'test');
      });

      test('returns error when provider is missing', () {
        final result = DeepLinkParser.parse(
          'cybervpn://oauth/callback?code=abc123',
        );
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('provider'));
      });

      test('returns error when code is missing', () {
        final result = DeepLinkParser.parse(
          'cybervpn://oauth/callback?provider=github',
        );
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('code'));
      });

      test('returns error for invalid provider format with numbers/uppercase',
          () {
        final result = DeepLinkParser.parse(
          'cybervpn://oauth/callback?provider=GitHub2&code=abc',
        );
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('Invalid provider format'));
      });
    });

    // -----------------------------------------------------------------------
    // Magic link verify route
    // -----------------------------------------------------------------------
    group('magic link verify', () {
      test('parses custom scheme magic link with token', () {
        final result = DeepLinkParser.parse(
          'cybervpn://magic-link/verify?token=abc123def',
        );
        expect(result.route, isA<MagicLinkVerifyRoute>());
        expect(result.error, isNull);
        final route = result.route as MagicLinkVerifyRoute;
        expect(route.token, 'abc123def');
      });

      test('parses universal link magic link with token', () {
        final result = DeepLinkParser.parse(
          'https://cybervpn.app/magic-link/verify?token=xyz789',
        );
        expect(result.route, isA<MagicLinkVerifyRoute>());
        expect(result.error, isNull);
        final route = result.route as MagicLinkVerifyRoute;
        expect(route.token, 'xyz789');
      });

      test('returns error when token is missing', () {
        final result = DeepLinkParser.parse(
          'cybervpn://magic-link/verify',
        );
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('token'));
      });
    });

    // -----------------------------------------------------------------------
    // Error cases
    // -----------------------------------------------------------------------
    group('error cases', () {
      test('returns error for empty string', () {
        final result = DeepLinkParser.parse('');
        expect(result.route, isNull);
        expect(result.error, isNotNull);
      });

      test('returns error for wrong host in universal link', () {
        final result = DeepLinkParser.parse(
          'https://example.com/connect',
        );
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('Unsupported host'));
      });

      test('returns error for unsupported scheme', () {
        final result = DeepLinkParser.parse('unknown://connect');
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('Unsupported scheme'));
      });

      test('returns error for unknown route', () {
        final result = DeepLinkParser.parse('cybervpn://nonexistent');
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('Unknown route'));
      });

      test('returns error for ftp scheme', () {
        final result = DeepLinkParser.parse('ftp://connect?server=1');
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('Unsupported scheme'));
      });

      test('returns error for wrong universal link host evil.com', () {
        final result = DeepLinkParser.parse(
          'https://evil.com/connect?server=1',
        );
        expect(result.route, isNull);
        expect(result.error, isNotNull);
        expect(result.error!.message, contains('Unsupported host'));
      });
    });

    // -----------------------------------------------------------------------
    // isDeepLink
    // -----------------------------------------------------------------------
    group('isDeepLink', () {
      test('returns true for custom scheme', () {
        expect(DeepLinkParser.isDeepLink('cybervpn://connect?server=1'), true);
      });

      test('returns true for universal link', () {
        expect(
          DeepLinkParser.isDeepLink('https://cybervpn.app/settings'),
          true,
        );
      });

      test('returns false for random URL', () {
        expect(DeepLinkParser.isDeepLink('https://google.com'), false);
      });

      test('returns false for empty string', () {
        expect(DeepLinkParser.isDeepLink(''), false);
      });
    });

    // -----------------------------------------------------------------------
    // Equality
    // -----------------------------------------------------------------------
    group('route equality', () {
      test('ConnectRoute equality', () {
        expect(
          const ConnectRoute(serverId: '1'),
          equals(const ConnectRoute(serverId: '1')),
        );
        expect(
          const ConnectRoute(serverId: '1'),
          isNot(equals(const ConnectRoute(serverId: '2'))),
        );
      });

      test('SettingsRoute equality', () {
        expect(const SettingsRoute(), equals(const SettingsRoute()));
      });
    });
  });
}
