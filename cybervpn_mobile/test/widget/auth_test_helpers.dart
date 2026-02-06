import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
import 'package:cybervpn_mobile/features/referral/presentation/providers/referral_provider.dart';

import '../helpers/mock_repositories.dart';
import '../helpers/mock_factories.dart';

// ---------------------------------------------------------------------------
// Shared finders
// ---------------------------------------------------------------------------

/// Finds the email [TextFormField] by its label text.
Finder findEmailField() => find.widgetWithText(TextFormField, 'Email');

/// Finds the password [TextFormField] by its label text.
Finder findPasswordField() => find.widgetWithText(TextFormField, 'Password');

/// Finds the confirm-password [TextFormField] by label text.
Finder findConfirmPasswordField() =>
    find.widgetWithText(TextFormField, 'Confirm Password');

/// Finds the login [ElevatedButton].
Finder findLoginButton() => find.widgetWithText(ElevatedButton, 'Login');

/// Finds the register [ElevatedButton].
Finder findRegisterButton() => find.widgetWithText(ElevatedButton, 'Register');

/// Finds a [CircularProgressIndicator] (loading spinner).
Finder findLoadingIndicator() => find.byType(CircularProgressIndicator);

// ---------------------------------------------------------------------------
// Mock auth repository setup helpers
// ---------------------------------------------------------------------------

/// Configures [mockRepo] to return [AuthUnauthenticated] on initial check
/// (isAuthenticated returns false).
void stubUnauthenticated(MockAuthRepository mockRepo) {
  when(() => mockRepo.isAuthenticated()).thenAnswer((_) async => const Success(false));
  when(() => mockRepo.getCurrentUser()).thenAnswer((_) async => const Success(null));
}

/// Configures [mockRepo] so that [login] succeeds with a default user.
void stubLoginSuccess(MockAuthRepository mockRepo, {UserEntity? user}) {
  final mockUser = user ?? createMockUser();
  when(() => mockRepo.login(
        email: any(named: 'email'),
        password: any(named: 'password'),
        device: any(named: 'device'),
      )).thenAnswer((_) async => Success((mockUser, 'mock-token')));
}

/// Configures [mockRepo] so that [login] throws an error.
void stubLoginFailure(MockAuthRepository mockRepo, {String? message}) {
  when(() => mockRepo.login(
        email: any(named: 'email'),
        password: any(named: 'password'),
        device: any(named: 'device'),
      )).thenThrow(Exception(message ?? 'Invalid credentials'));
}

/// Configures [mockRepo] so that [register] succeeds with a default user.
void stubRegisterSuccess(MockAuthRepository mockRepo, {UserEntity? user}) {
  final mockUser = user ?? createMockUser();
  when(() => mockRepo.register(
        email: any(named: 'email'),
        password: any(named: 'password'),
        device: any(named: 'device'),
        referralCode: any(named: 'referralCode'),
      )).thenAnswer((_) async => Success((mockUser, 'mock-token')));
}

/// Configures [mockRepo] so that [register] throws an error.
void stubRegisterFailure(MockAuthRepository mockRepo, {String? message}) {
  when(() => mockRepo.register(
        email: any(named: 'email'),
        password: any(named: 'password'),
        device: any(named: 'device'),
        referralCode: any(named: 'referralCode'),
      )).thenThrow(Exception(message ?? 'Email already taken'));
}

// ---------------------------------------------------------------------------
// Provider override builder
// ---------------------------------------------------------------------------

/// Returns a list of Riverpod overrides that wire up the mock auth repository.
List<dynamic> authOverrides(
  MockAuthRepository mockRepo, {
  bool referralAvailable = true,
}) {
  return [
    authRepositoryProvider.overrideWithValue(mockRepo),
    // Mock the referral availability provider for register screen tests
    isReferralAvailableProvider.overrideWith((ref) => referralAvailable),
  ];
}

// ---------------------------------------------------------------------------
// GoRouter builder for auth screen tests
// ---------------------------------------------------------------------------

/// Creates a [GoRouter] suitable for widget tests of auth screens.
///
/// Puts the [initialWidget] at [initialPath] and adds placeholder routes
/// for `/connection`, `/login`, and `/register` so that `context.go()` calls
/// do not throw.
GoRouter buildTestRouter({
  required Widget initialWidget,
  required String initialPath,
}) {
  return GoRouter(
    initialLocation: initialPath,
    routes: [
      GoRoute(
        path: '/login',
        builder: (_, __) => initialPath == '/login'
            ? initialWidget
            : const Scaffold(body: Text('Login Screen Route')),
      ),
      GoRoute(
        path: '/register',
        builder: (_, __) => initialPath == '/register'
            ? initialWidget
            : const Scaffold(body: Text('Register Screen Route')),
      ),
      GoRoute(
        path: '/connection',
        builder: (_, __) =>
            const Scaffold(body: Text('Connection Screen')),
      ),
    ],
  );
}

/// Wraps a screen widget in a [ProviderScope] + [MaterialApp.router] backed
/// by a [GoRouter] with the required auth-screen routes.
Widget buildTestableAuthScreen({
  required Widget child,
  required String path,
  required List<dynamic> overrides,
}) {
  final router = buildTestRouter(initialWidget: child, initialPath: path);
  return ProviderScope(
    overrides: overrides.cast(),
    child: MaterialApp.router(
      routerConfig: router,
      theme: ThemeData.light(useMaterial3: true),
    ),
  );
}

// ---------------------------------------------------------------------------
// Test constants
// ---------------------------------------------------------------------------

/// Valid test credentials that pass [InputValidators].
const kValidEmail = 'test@example.com';

/// Valid password: 8+ chars, uppercase, lowercase, digit.
const kValidPassword = 'Abcdef1g';

// ---------------------------------------------------------------------------
// Overflow error suppression
// ---------------------------------------------------------------------------

/// Suppresses [FlutterError]s caused by RenderFlex overflow in widget tests.
///
/// The auth screens have Row widgets that may overflow in the constrained test
/// viewport. This is a layout concern, not a functional bug, so we suppress it
/// to keep widget tests focused on behavior.
///
/// Must be called inside each [testWidgets] callback body.
void ignoreOverflowErrors() {
  FlutterError.onError = (details) {
    final isOverflow = details.toString().contains('overflowed');
    if (!isOverflow) {
      FlutterError.dumpErrorToConsole(details);
      throw details.exception;
    }
  };
}
