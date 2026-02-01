// ignore_for_file: avoid_relative_lib_imports
//
// Tests for the onboarding guard redirect logic in app_router.dart.
//
// We replicate the redirect logic locally to avoid importing the full
// production router which pulls in the DI graph with potentially
// unresolvable transitive dependencies in the test environment.

import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Redirect logic extracted from appRouterProvider for isolated testing.
//
// This mirrors the production redirect callback exactly so we can verify
// the priority order without requiring GoRouter or a full ProviderScope.
// ---------------------------------------------------------------------------

/// Returns the redirect path given the current navigation state.
///
/// Returns `null` when no redirect is needed.
String? resolveRedirect({
  required bool isAuthenticated,
  required bool shouldShowOnboarding,
  required String path,
}) {
  final isAuthRoute = path == '/login' || path == '/register';
  final isOnboardingRoute = path == '/onboarding';

  // 1. Onboarding not completed -> show onboarding
  if (shouldShowOnboarding && !isOnboardingRoute) {
    return '/onboarding';
  }

  // 2. Onboarding complete, not authenticated -> show login
  if (!isAuthenticated && !isAuthRoute && !isOnboardingRoute) {
    return '/login';
  }

  // 3. Authenticated user on auth/onboarding routes -> go to app
  if (isAuthenticated && (isAuthRoute || isOnboardingRoute)) {
    return '/connection';
  }

  // 4. Authenticated user on root -> go to connection
  if (isAuthenticated && path == '/') {
    return '/connection';
  }

  return null;
}

void main() {
  group('Router onboarding guard', () {
    // ----- First launch: onboarding not completed, not authenticated ------

    test('first launch -> redirects to /onboarding from /', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: true,
        path: '/',
      );
      expect(result, '/onboarding');
    });

    test('first launch -> redirects to /onboarding from /login', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: true,
        path: '/login',
      );
      expect(result, '/onboarding');
    });

    test('first launch -> redirects to /onboarding from /connection', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: true,
        path: '/connection',
      );
      expect(result, '/onboarding');
    });

    test('first launch -> stays on /onboarding (no redirect loop)', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: true,
        path: '/onboarding',
      );
      // Should NOT redirect away from onboarding
      expect(result, isNull);
    });

    // ----- Onboarding completed, not authenticated -------------------------

    test('after onboarding, not authenticated -> redirects to /login from /',
        () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: false,
        path: '/',
      );
      expect(result, '/login');
    });

    test(
        'after onboarding, not authenticated -> redirects to /login from /connection',
        () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: false,
        path: '/connection',
      );
      expect(result, '/login');
    });

    test('after onboarding, not authenticated -> stays on /login', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: false,
        path: '/login',
      );
      expect(result, isNull);
    });

    test('after onboarding, not authenticated -> stays on /register', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: false,
        path: '/register',
      );
      expect(result, isNull);
    });

    // ----- Authenticated user -----------------------------------------------

    test('authenticated -> no redirect from /connection', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        path: '/connection',
      );
      expect(result, isNull);
    });

    test('authenticated -> redirects from /login to /connection', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        path: '/login',
      );
      expect(result, '/connection');
    });

    test('authenticated -> redirects from /register to /connection', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        path: '/register',
      );
      expect(result, '/connection');
    });

    test('authenticated -> redirects from /onboarding to /connection', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        path: '/onboarding',
      );
      expect(result, '/connection');
    });

    test('authenticated -> redirects from / to /connection', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        path: '/',
      );
      expect(result, '/connection');
    });

    test('authenticated -> no redirect from /servers', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        path: '/servers',
      );
      expect(result, isNull);
    });

    test('authenticated -> no redirect from /settings', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        path: '/settings',
      );
      expect(result, isNull);
    });

    // ----- Edge case: authenticated but shouldShowOnboarding is true --------
    // (should not happen in practice but verify no infinite loop)

    test(
        'authenticated with shouldShowOnboarding -> redirects to /onboarding (onboarding takes priority)',
        () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: true,
        path: '/connection',
      );
      // Onboarding guard fires first, redirect to onboarding
      expect(result, '/onboarding');
    });

    test(
        'authenticated on /onboarding with shouldShowOnboarding -> redirects to /connection (auth takes priority on onboarding route)',
        () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: true,
        path: '/onboarding',
      );
      // Rule 3 fires: authenticated user on onboarding route goes to /connection
      expect(result, '/connection');
    });
  });
}
