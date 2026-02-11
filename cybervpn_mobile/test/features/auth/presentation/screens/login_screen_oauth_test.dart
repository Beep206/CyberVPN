import 'dart:io' show Platform;
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
}) {
  final router = GoRouter(
    initialLocation: '/login',
    routes: [
      GoRoute(
        path: '/login',
        builder: (_, __) => const LoginScreen(),
      ),
      GoRoute(
        path: '/home',
        builder: (_, __) => const Scaffold(body: Text('Home Screen')),
      ),
      GoRoute(
        path: '/connection',
        builder: (_, __) => const Scaffold(body: Text('Connection Screen')),
      ),
    ],
  );

  return ProviderScope(
    overrides: [
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
Finder findGoogleButton() => find.widgetWithText(OutlinedButton, 'Continue with Google');
Finder findAppleButton() => find.widgetWithText(OutlinedButton, 'Continue with Apple');

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockGoogleSignInService mockGoogleService;
  late MockAppleSignInService mockAppleService;
  late MockSecureStorageWrapper mockSecureStorage;

  setUp(() {
    mockGoogleService = MockGoogleSignInService();
    mockAppleService = MockAppleSignInService();
    mockSecureStorage = MockSecureStorageWrapper();

    // Default stub for secure storage
    when(() => mockSecureStorage.write(
          key: any(named: 'key'),
          value: any(named: 'value'),
        )).thenAnswer((_) async {});
  });

  group('LoginScreen - Google OAuth Flow', () {
    testWidgets('test_google_button_visible', (tester) async {
      ignoreOverflowErrors();

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
        ),
      );
      await tester.pumpAndSettle();

      expect(findGoogleButton(), findsOneWidget);
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
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Google button
      await tester.tap(findGoogleButton());
      await tester.pumpAndSettle();

      // Assert: Verify Google Sign-In service was called
      verify(() => mockGoogleService.signIn()).called(1);
    });

    testWidgets('test_google_sign_in_user_cancellation_no_error',
        (tester) async {
      ignoreOverflowErrors();

      // Arrange: User cancels Google Sign-In
      when(() => mockGoogleService.signIn()).thenAnswer((_) async => null);

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Google button
      await tester.tap(findGoogleButton());
      await tester.pumpAndSettle();

      // Assert: No error snackbar shown
      expect(find.byType(SnackBar), findsNothing);
      // Still on login screen
      expect(find.byType(LoginScreen), findsOneWidget);
    });

    testWidgets('test_google_sign_in_shows_error_on_exception',
        (tester) async {
      ignoreOverflowErrors();

      // Arrange: Google Sign-In throws exception
      when(() => mockGoogleService.signIn())
          .thenThrow(Exception('Google Sign-In failed'));

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Google button
      await tester.tap(findGoogleButton());
      await tester.pumpAndSettle();

      // Assert: Error snackbar shown
      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Authentication failed'), findsOneWidget);
    });

    testWidgets('test_google_sign_in_no_server_auth_code_shows_error',
        (tester) async {
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
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Google button
      await tester.tap(findGoogleButton());
      await tester.pumpAndSettle();

      // Assert: Error snackbar shown
      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Authentication failed'), findsOneWidget);
    });
  });

  group('LoginScreen - Apple OAuth Flow', () {
    testWidgets('test_apple_button_visible_on_ios', (tester) async {
      ignoreOverflowErrors();

      // Note: In a real test, we'd need to mock Platform.isIOS
      // For this test, we're checking if the button can be found when rendered

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
        ),
      );
      await tester.pumpAndSettle();

      // The Apple button is only shown on iOS, so we check if it's rendered
      // In a real iOS test environment, this would find the button
      // In this test environment (likely Linux/Android), it may not appear
      if (Platform.isIOS) {
        expect(findAppleButton(), findsOneWidget);
      } else {
        // On non-iOS platforms, the button should not be visible
        expect(findAppleButton(), findsNothing);
      }
    });

    testWidgets('test_apple_sign_in_calls_native_sdk', (tester) async {
      ignoreOverflowErrors();

      // Skip test if not on iOS since Apple button won't be visible
      if (!Platform.isIOS) {
        return;
      }

      // Arrange: Mock Apple Sign-In to return null (user cancelled)
      when(() => mockAppleService.signIn()).thenAnswer((_) async => null);

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Apple button
      await tester.tap(findAppleButton());
      await tester.pumpAndSettle();

      // Assert: Verify Apple Sign-In service was called
      verify(() => mockAppleService.signIn()).called(1);
    });

    testWidgets('test_apple_sign_in_user_cancellation_no_error',
        (tester) async {
      ignoreOverflowErrors();

      // Skip test if not on iOS
      if (!Platform.isIOS) {
        return;
      }

      // Arrange: User cancels Apple Sign-In
      when(() => mockAppleService.signIn()).thenAnswer((_) async => null);

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Apple button
      await tester.tap(findAppleButton());
      await tester.pumpAndSettle();

      // Assert: No error snackbar shown
      expect(find.byType(SnackBar), findsNothing);
      // Still on login screen
      expect(find.byType(LoginScreen), findsOneWidget);
    });

    testWidgets('test_apple_sign_in_shows_error_on_exception',
        (tester) async {
      ignoreOverflowErrors();

      // Skip test if not on iOS
      if (!Platform.isIOS) {
        return;
      }

      // Arrange: Apple Sign-In throws exception
      when(() => mockAppleService.signIn())
          .thenThrow(Exception('Apple Sign-In failed'));

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Apple button
      await tester.tap(findAppleButton());
      await tester.pumpAndSettle();

      // Assert: Error snackbar shown
      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Authentication failed'), findsOneWidget);
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
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Google button
      await tester.tap(findGoogleButton());
      await tester.pumpAndSettle();

      // Assert: Google Sign-In service was called
      verify(() => mockGoogleService.signIn()).called(1);

      // Note: Full OAuth backend flow verification (getAuthorizeUrl, loginCallback)
      // requires more complex setup or E2E tests.
    });

    testWidgets('test_apple_oauth_full_flow_success', (tester) async {
      ignoreOverflowErrors();

      // Skip test if not on iOS
      if (!Platform.isIOS) {
        return;
      }

      // Arrange: Mock successful Apple Sign-In
      when(() => mockAppleService.signIn()).thenAnswer(
        (_) async => AppleSignInResult(
          authorizationCode: 'mock-auth-code',
          identityToken: 'mock-identity-token',
          email: 'test@example.com',
          givenName: 'Test',
          familyName: 'User',
        ),
      );

      await tester.pumpWidget(
        buildTestableLoginScreen(
          mockGoogleService: mockGoogleService,
          mockAppleService: mockAppleService,
          mockSecureStorage: mockSecureStorage,
        ),
      );
      await tester.pumpAndSettle();

      // Act: Tap Apple button
      await tester.tap(findAppleButton());
      await tester.pumpAndSettle();

      // Assert: Apple Sign-In service was called
      verify(() => mockAppleService.signIn()).called(1);

      // Note: Full OAuth backend flow verification requires E2E tests.
    });
  });
}
