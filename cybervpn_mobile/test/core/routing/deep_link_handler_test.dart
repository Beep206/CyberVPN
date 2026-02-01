import 'package:cybervpn_mobile/core/routing/deep_link_handler.dart';
import 'package:cybervpn_mobile/core/routing/deep_link_parser.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('resolveDeepLinkPath', () {
    test('resolves ConnectRoute to /servers/{id}', () {
      const route = ConnectRoute(serverId: '42');
      expect(resolveDeepLinkPath(route), '/servers/42');
    });

    test('resolves ImportConfigRoute to /config-import with config param', () {
      const route = ImportConfigRoute(configBase64: 'dGVzdA==');
      expect(resolveDeepLinkPath(route), '/config-import?config=dGVzdA==');
    });

    test('resolves ReferralRoute to /referral with code param', () {
      const route = ReferralRoute(code: 'REF123');
      expect(resolveDeepLinkPath(route), '/referral?code=REF123');
    });

    test('resolves SubscribeRoute to /subscribe with plan param', () {
      const route = SubscribeRoute(planId: 'premium');
      expect(resolveDeepLinkPath(route), '/subscribe?plan=premium');
    });

    test('resolves SettingsRoute to /settings', () {
      const route = SettingsRoute();
      expect(resolveDeepLinkPath(route), '/settings');
    });
  });

  group('resolveDeepLinkFromUri', () {
    test('resolves custom scheme deep link', () {
      final uri = Uri.parse('cybervpn://connect?server=99');
      expect(resolveDeepLinkFromUri(uri), '/servers/99');
    });

    test('resolves universal link deep link', () {
      final uri = Uri.parse('https://cybervpn.app/settings');
      expect(resolveDeepLinkFromUri(uri), '/settings');
    });

    test('returns null for non-deep-link URI', () {
      final uri = Uri.parse('https://google.com');
      expect(resolveDeepLinkFromUri(uri), isNull);
    });

    test('returns null for internal app path', () {
      final uri = Uri.parse('/connection');
      expect(resolveDeepLinkFromUri(uri), isNull);
    });

    test('returns null for invalid deep link route', () {
      final uri = Uri.parse('cybervpn://unknown-route');
      expect(resolveDeepLinkFromUri(uri), isNull);
    });
  });
}
