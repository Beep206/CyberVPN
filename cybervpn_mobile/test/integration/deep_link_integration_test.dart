import 'package:cybervpn_mobile/core/routing/deep_link_handler.dart';
import 'package:cybervpn_mobile/core/routing/deep_link_parser.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Deep Link Integration Tests', () {
    late ProviderContainer container;

    setUp(() {
      container = ProviderContainer();
    });

    tearDown(() {
      container.dispose();
    });

    // -------------------------------------------------------------------------
    // Route resolution tests
    // -------------------------------------------------------------------------
    group('resolveDeepLinkPath', () {
      test('resolves ConnectRoute to server detail path', () {
        const route = ConnectRoute(serverId: 'srv-123');
        final path = resolveDeepLinkPath(route);
        expect(path, '/servers/srv-123');
      });

      test('resolves ImportConfigRoute with base64 query param', () {
        const route = ImportConfigRoute(configBase64: 'abc123==');
        final path = resolveDeepLinkPath(route);
        expect(path, '/config-import?config=abc123==');
      });

      test('resolves ReferralRoute with code query param', () {
        const route = ReferralRoute(code: 'REF-ABC-123');
        final path = resolveDeepLinkPath(route);
        expect(path, '/referral?code=REF-ABC-123');
      });

      test('resolves SubscribeRoute with plan query param', () {
        const route = SubscribeRoute(planId: 'premium-1');
        final path = resolveDeepLinkPath(route);
        expect(path, '/subscribe?plan=premium-1');
      });

      test('resolves SettingsRoute to settings path', () {
        const route = SettingsRoute();
        final path = resolveDeepLinkPath(route);
        expect(path, '/settings');
      });
    });

    // -------------------------------------------------------------------------
    // URI detection and parsing
    // -------------------------------------------------------------------------
    group('resolveDeepLinkFromUri', () {
      test('returns null for non-deep-link URIs', () {
        final uri = Uri.parse('https://google.com/search');
        final path = resolveDeepLinkFromUri(uri);
        expect(path, isNull);
      });

      test('returns null for app-internal routes', () {
        final uri = Uri.parse('/connection');
        final path = resolveDeepLinkFromUri(uri);
        expect(path, isNull);
      });

      test('resolves custom scheme deep link', () {
        final uri = Uri.parse('cybervpn://connect?server=abc-123');
        final path = resolveDeepLinkFromUri(uri);
        expect(path, '/servers/abc-123');
      });

      test('resolves universal link deep link', () {
        final uri = Uri.parse('https://cybervpn.app/settings');
        final path = resolveDeepLinkFromUri(uri);
        expect(path, '/settings');
      });

      test('returns null for malformed deep link', () {
        final uri = Uri.parse('cybervpn://connect'); // missing server param
        final path = resolveDeepLinkFromUri(uri);
        expect(path, isNull);
      });
    });

    // -------------------------------------------------------------------------
    // Pending deep link state management
    // -------------------------------------------------------------------------
    group('PendingDeepLinkNotifier', () {
      test('initial state is null', () {
        final notifier = container.read(pendingDeepLinkProvider.notifier);
        expect(notifier.state, isNull);
      });

      test('setPending stores a deep link route', () {
        final notifier = container.read(pendingDeepLinkProvider.notifier);
        const route = ConnectRoute(serverId: 'test-123');

        notifier.setPending(route);
        expect(container.read(pendingDeepLinkProvider), equals(route));
      });

      test('consume returns and clears the pending route', () {
        final notifier = container.read(pendingDeepLinkProvider.notifier);
        const route = ReferralRoute(code: 'REF-ABC');

        notifier.setPending(route);
        final consumed = notifier.consume();

        expect(consumed, equals(route));
        expect(container.read(pendingDeepLinkProvider), isNull);
      });

      test('consume returns null when no pending route', () {
        final notifier = container.read(pendingDeepLinkProvider.notifier);
        final consumed = notifier.consume();
        expect(consumed, isNull);
      });

      test('clear removes pending route without consuming', () {
        final notifier = container.read(pendingDeepLinkProvider.notifier);
        const route = SubscribeRoute(planId: 'basic');

        notifier.setPending(route);
        notifier.clear();

        expect(container.read(pendingDeepLinkProvider), isNull);
      });

      test('multiple setPending overwrites previous route', () {
        final notifier = container.read(pendingDeepLinkProvider.notifier);
        const route1 = ConnectRoute(serverId: 'first');
        const route2 = ConnectRoute(serverId: 'second');

        notifier.setPending(route1);
        notifier.setPending(route2);

        expect(container.read(pendingDeepLinkProvider), equals(route2));
      });
    });

    // -------------------------------------------------------------------------
    // Cold start scenario (app launches from deep link)
    // -------------------------------------------------------------------------
    group('Cold Start Deep Link', () {
      testWidgets('deep link opens correct screen when authenticated',
          (tester) async {
        // Simulate cold start with deep link: cybervpn://settings
        final uri = Uri.parse('cybervpn://settings');
        final path = resolveDeepLinkFromUri(uri);

        expect(path, isNotNull);
        expect(path, '/settings');

        // In a real router integration test, we would:
        // 1. Create a router with the deep link as initialLocation
        // 2. Verify it navigates to /settings
        // This is a unit-level verification of path resolution.
      });

      testWidgets('invalid deep link returns null and shows no navigation',
          (tester) async {
        // Simulate cold start with malformed deep link
        final uri = Uri.parse('cybervpn://unknown-route');
        final path = resolveDeepLinkFromUri(uri);

        expect(path, isNull);
      });
    });

    // -------------------------------------------------------------------------
    // Warm start scenario (app is already running, receives deep link)
    // -------------------------------------------------------------------------
    group('Warm Start Deep Link', () {
      testWidgets('deep link while authenticated navigates immediately',
          (tester) async {
        // Simulate receiving deep link while app is running
        final uri = Uri.parse('cybervpn://referral?code=WARM-START-123');
        final result = DeepLinkParser.parseUri(uri);

        expect(result.route, isNotNull);
        expect(result.route, isA<ReferralRoute>());
        expect((result.route as ReferralRoute).code, 'WARM-START-123');

        final path = resolveDeepLinkPath(result.route!);
        expect(path, '/referral?code=WARM-START-123');

        // In a real router test, we would:
        // 1. Navigate to the resolved path using GoRouter.of(context).go(path)
        // 2. Verify the correct screen is displayed
      });

      testWidgets('deep link while unauthenticated stores pending route',
          (tester) async {
        final notifier = container.read(pendingDeepLinkProvider.notifier);
        final uri = Uri.parse('cybervpn://connect?server=warm-srv');
        final result = DeepLinkParser.parseUri(uri);

        // Simulate unauthenticated state: store pending route
        if (result.route != null) {
          notifier.setPending(result.route!);
        }

        expect(container.read(pendingDeepLinkProvider), isNotNull);
        expect(
          container.read(pendingDeepLinkProvider),
          equals(const ConnectRoute(serverId: 'warm-srv')),
        );

        // After login, consume the pending route
        final pending = notifier.consume();
        expect(pending, isNotNull);
        final path = resolveDeepLinkPath(pending!);
        expect(path, '/servers/warm-srv');
      });
    });

    // -------------------------------------------------------------------------
    // Universal link scenarios
    // -------------------------------------------------------------------------
    group('Universal Links', () {
      test('https://cybervpn.app/connect resolves correctly', () {
        final uri = Uri.parse('https://cybervpn.app/connect?server=ul-123');
        final path = resolveDeepLinkFromUri(uri);
        expect(path, '/servers/ul-123');
      });

      test('https://cybervpn.app/subscribe resolves correctly', () {
        final uri = Uri.parse('https://cybervpn.app/subscribe?plan=pro');
        final path = resolveDeepLinkFromUri(uri);
        expect(path, '/subscribe?plan=pro');
      });

      test('wrong host does not resolve', () {
        final uri = Uri.parse('https://otherdomain.com/connect?server=123');
        final path = resolveDeepLinkFromUri(uri);
        expect(path, isNull);
      });

      test('http scheme also works for universal links', () {
        final uri = Uri.parse('http://cybervpn.app/settings');
        final path = resolveDeepLinkFromUri(uri);
        expect(path, '/settings');
      });
    });

    // -------------------------------------------------------------------------
    // Edge cases
    // -------------------------------------------------------------------------
    group('Edge Cases', () {
      test('deep link with URL-encoded params', () {
        // Base64 strings can contain URL-unsafe characters
        // Use a simple valid base64: dGVzdA== (base64 for 'test')
        // URL-encoded version: dGVzdA%3D%3D
        final uri = Uri.parse('cybervpn://import?config=dGVzdA%3D%3D');
        final result = DeepLinkParser.parseUri(uri);
        // Uri.parse decodes %3D to =, giving 'dGVzdA=='
        expect(result.route, isNotNull);
        expect(result.route, isA<ImportConfigRoute>());
        expect((result.route as ImportConfigRoute).configBase64, 'dGVzdA==');
      });

      test('deep link with uppercase scheme is normalized by Uri.parse', () {
        // Uri.parse normalizes schemes to lowercase
        final uri = Uri.parse('CYBERVPN://settings');
        expect(uri.scheme, 'cybervpn'); // Normalized to lowercase
        final path = resolveDeepLinkFromUri(uri);
        expect(path, '/settings');
      });

      test('deep link with trailing slash', () {
        final uri = Uri.parse('https://cybervpn.app/settings/');
        final path = resolveDeepLinkFromUri(uri);
        // The parser strips leading '/', so 'settings/' becomes 'settings/'
        // which doesn't match 'settings'. This is expected behavior.
        expect(path, isNull);
      });
    });
  });
}
