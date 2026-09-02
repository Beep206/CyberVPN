import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/apple_sign_in_service.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/google_sign_in_service.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/login_screen.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

import '../../../../helpers/fakes/fake_api_client.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockGoogleSignInService extends Mock implements GoogleSignInService {}

class MockAppleSignInService extends Mock implements AppleSignInService {}

class MockSecureStorageWrapper extends Mock implements SecureStorageWrapper {}

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

Widget buildTestableLoginScreen({
  required MockGoogleSignInService mockGoogleService,
  required MockAppleSignInService mockAppleService,
  required MockSecureStorageWrapper mockSecureStorage,
  required FakeApiClient fakeApiClient,
}) {
  final router = GoRouter(
    initialLocation: '/login',
    routes: [
      GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
      GoRoute(
        path: '/home',
        builder: (_, _) => const Scaffold(body: Text('Home Screen')),
      ),
      GoRoute(
        path: '/connection',
        builder: (_, _) => const Scaffold(body: Text('Connection Screen')),
      ),
    ],
  );

  return ProviderScope(
    overrides: [
      apiClientProvider.overrideWithValue(fakeApiClient),
      googleSignInServiceProvider.overrideWithValue(mockGoogleService),
      appleSignInServiceProvider.overrideWithValue(mockAppleService),
      secureStorageProvider.overrideWithValue(mockSecureStorage),
      // Keep every external boundary deterministic while proving that the
      // disabled provider policy cannot accidentally invoke it.
    ],
    child: MaterialApp.router(
      routerConfig: router,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
    ),
  );
}

// Finders
Finder findGoogleButton() =>
    find.widgetWithText(OutlinedButton, 'Continue with Google');
Finder findFacebookButton() =>
    find.widgetWithText(OutlinedButton, 'Continue with Facebook');
Finder findAppleButton() =>
    find.widgetWithText(OutlinedButton, 'Continue with Apple');

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockGoogleSignInService mockGoogleService;
  late MockAppleSignInService mockAppleService;
  late MockSecureStorageWrapper mockSecureStorage;
  late FakeApiClient fakeApiClient;

  setUp(() {
    mockGoogleService = MockGoogleSignInService();
    mockAppleService = MockAppleSignInService();
    mockSecureStorage = MockSecureStorageWrapper();
    fakeApiClient = FakeApiClient()
      ..setGetResponse('/api/v1/oauth/google/login', {
        'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'state': 'oauth-test-state',
      })
      ..setPostResponse('/api/v1/oauth/google/login/callback', {
        'access_token': 'oauth-access-token',
        'refresh_token': 'oauth-refresh-token',
        'token_type': 'Bearer',
        'expires_in': 3600,
        'user': {
          'id': 'user-001',
          'email': 'test@example.com',
          'username': 'testuser',
          'isEmailVerified': true,
          'isPremium': false,
        },
        'is_new_user': false,
        'requires_2fa': false,
      });

    // Default stub for secure storage
    when(
      () => mockSecureStorage.write(
        key: any(named: 'key'),
        value: any(named: 'value'),
      ),
    ).thenAnswer((_) async {});
  });

  group('LoginScreen - disabled OAuth entry points', () {
    testWidgets('does not render disabled provider buttons', (tester) async {
      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
          fakeApiClient: fakeApiClient,
        ),
      );
      await tester.pumpAndSettle();

      expect(findGoogleButton(), findsNothing);
      expect(findFacebookButton(), findsNothing);
      expect(findAppleButton(), findsNothing);
      verifyNever(() => mockGoogleService.signIn());
      verifyNever(() => mockAppleService.signIn());
    });

    test('provider policy keeps inactive mobile OAuth entries disabled', () {
      expect(OAuthProvider.google.isMobileAuthEntryEnabled, isFalse);
      expect(OAuthProvider.facebook.isMobileAuthEntryEnabled, isFalse);
      expect(OAuthProvider.apple.isMobileAuthEntryEnabled, isFalse);
    });
  });
}
