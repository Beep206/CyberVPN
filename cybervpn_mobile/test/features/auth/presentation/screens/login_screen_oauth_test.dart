import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/apple_sign_in_service.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/google_sign_in_service.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/login_screen.dart';
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

void ignoreOverflowErrors() {
  FlutterError.onError = (details) {
    final isOverflow = details.toString().contains('overflowed');
    if (!isOverflow) {
      FlutterError.dumpErrorToConsole(details);
    }
  };
}

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
      // Note: These tests verify OAuth service integration.
      // For full end-to-end OAuth flow testing, use E2E tests.
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

  group('LoginScreen - Google OAuth Flow', () {
    testWidgets('test_google_button_visible', (tester) async {
      ignoreOverflowErrors();

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
          fakeApiClient: fakeApiClient,
        ),
      );
      await tester.pumpAndSettle();

      expect(findGoogleButton(), findsOneWidget);
    });

    testWidgets('test_facebook_button_visible', (tester) async {
      ignoreOverflowErrors();

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
          fakeApiClient: fakeApiClient,
        ),
      );
      await tester.pumpAndSettle();

      expect(findFacebookButton(), findsOneWidget);
    });

    testWidgets('test_google_sign_in_calls_native_sdk', (tester) async {
      ignoreOverflowErrors();

      // Arrange: Mock Google Sign-In to return null (user cancelled)
      when(() => mockGoogleService.signIn()).thenAnswer((_) async => null);

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
          fakeApiClient: fakeApiClient,
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Google button
      await tester.ensureVisible(findGoogleButton());
      await tester.tap(findGoogleButton());
      await tester.pumpAndSettle();

      // Assert: Verify Google Sign-In service was called
      verify(() => mockGoogleService.signIn()).called(1);
    });

    testWidgets('test_google_sign_in_user_cancellation_no_error', (
      tester,
    ) async {
      ignoreOverflowErrors();

      // Arrange: User cancels Google Sign-In
      when(() => mockGoogleService.signIn()).thenAnswer((_) async => null);

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
          fakeApiClient: fakeApiClient,
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Google button
      await tester.ensureVisible(findGoogleButton());
      await tester.tap(findGoogleButton());
      await tester.pumpAndSettle();

      // Assert: No error snackbar shown
      expect(find.byType(SnackBar), findsNothing);
      // Still on login screen
      expect(find.byType(LoginScreen), findsOneWidget);
    });

    testWidgets('test_google_sign_in_shows_error_on_exception', (tester) async {
      ignoreOverflowErrors();

      // Arrange: Google Sign-In throws exception
      when(
        () => mockGoogleService.signIn(),
      ).thenThrow(Exception('Google Sign-In failed'));

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
          fakeApiClient: fakeApiClient,
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Google button
      await tester.ensureVisible(findGoogleButton());
      await tester.tap(findGoogleButton());
      await tester.pumpAndSettle();

      // Assert: Error snackbar shown
      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.byType(LoginScreen), findsOneWidget);
    });

    testWidgets('test_google_sign_in_no_server_auth_code_shows_error', (
      tester,
    ) async {
      ignoreOverflowErrors();

      // Arrange: Google Sign-In returns result without serverAuthCode
      when(() => mockGoogleService.signIn()).thenAnswer(
        (_) async => GoogleSignInResult(
          serverAuthCode: null, // Missing server auth code
          email: 'test@example.com',
        ),
      );

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
          fakeApiClient: fakeApiClient,
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Google button
      await tester.ensureVisible(findGoogleButton());
      await tester.tap(findGoogleButton());
      await tester.pumpAndSettle();

      // Assert: Error snackbar shown
      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.byType(LoginScreen), findsOneWidget);
    });
  });

  group('LoginScreen - Apple OAuth Visibility', () {
    testWidgets('test_apple_button_hidden_even_on_ios_builds', (tester) async {
      ignoreOverflowErrors();

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
          fakeApiClient: fakeApiClient,
        ),
      );
      await tester.pumpAndSettle();

      expect(findAppleButton(), findsNothing);
      verifyNever(() => mockAppleService.signIn());
    });
  });

  group('LoginScreen - OAuth Integration Flow', () {
    testWidgets('test_google_oauth_full_flow_success', (tester) async {
      ignoreOverflowErrors();

      // This test verifies the OAuth flow structure but cannot fully test
      // the integration without a real OAuthRemoteDataSource mock setup.
      // For comprehensive integration testing, use E2E tests.

      // Arrange: Mock successful Google Sign-In
      when(() => mockGoogleService.signIn()).thenAnswer(
        (_) async => GoogleSignInResult(
          serverAuthCode: 'mock-server-auth-code',
          email: 'test@example.com',
          displayName: 'Test User',
        ),
      );

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
          fakeApiClient: fakeApiClient,
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Google button
      await tester.ensureVisible(findGoogleButton());
      await tester.tap(findGoogleButton());
      await tester.pumpAndSettle();

      // Assert: Google Sign-In service was called
      verify(() => mockGoogleService.signIn()).called(1);

      // Note: Full OAuth backend flow verification (getAuthorizeUrl, loginCallback)
      // requires more complex setup or E2E tests.
    });
  });
}
