// ignore_for_file: avoid_relative_lib_imports
//
// Tests for the redirect logic in app_router.dart.
//
// We replicate the redirect logic locally to avoid importing the full
// production router which pulls in the DI graph with potentially
// unresolvable transitive dependencies in the test environment.

import 'package:flutter/foundation.dart';
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
  required bool isAuthLoading,
  required String path,
  bool shouldShowQuickSetup = false,
}) {
  final isAuthRoute = path == '/login' || path == '/register';
  final isOnboardingRoute = path == '/onboarding';
  final isQuickSetupRoute = path == '/quick-setup';
  final isSplashRoute = path == '/splash';

  // -- Splash handling
  if (isSplashRoute && isAuthLoading) return null; // stay on /splash
  if (isSplashRoute && !isAuthLoading) return '/';

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
    if (shouldShowQuickSetup && !isQuickSetupRoute) return '/quick-setup';
    return '/connection';
  }

  // 4. Authenticated user on root -> go to connection
  if (isAuthenticated && path == '/') {
    if (shouldShowQuickSetup && !isQuickSetupRoute) return '/quick-setup';
    return '/connection';
  }

  return null;
}

/// Mirrors [_RouterRefreshNotifier] from production to verify the pattern.
class TestRouterRefreshNotifier extends ChangeNotifier {
  void notify() => notifyListeners();
}

void main() {
  group('Router onboarding guard', () {
    // ----- First launch: onboarding not completed, not authenticated ------

    test('first launch -> redirects to /onboarding from /', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: true,
        isAuthLoading: false,
        path: '/',
      );
      expect(result, '/onboarding');
    });

    test('first launch -> redirects to /onboarding from /login', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: true,
        isAuthLoading: false,
        path: '/login',
      );
      expect(result, '/onboarding');
    });

    test('first launch -> redirects to /onboarding from /connection', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: true,
        isAuthLoading: false,
        path: '/connection',
      );
      expect(result, '/onboarding');
    });

    test('first launch -> stays on /onboarding (no redirect loop)', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: true,
        isAuthLoading: false,
        path: '/onboarding',
      );
      expect(result, isNull);
    });

    // ----- Onboarding completed, not authenticated -------------------------

    test('after onboarding, not authenticated -> redirects to /login from /',
        () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: false,
        isAuthLoading: false,
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
        isAuthLoading: false,
        path: '/connection',
      );
      expect(result, '/login');
    });

    test('after onboarding, not authenticated -> stays on /login', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/login',
      );
      expect(result, isNull);
    });

    test('after onboarding, not authenticated -> stays on /register', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/register',
      );
      expect(result, isNull);
    });

    // ----- Authenticated user -----------------------------------------------

    test('authenticated -> no redirect from /connection', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/connection',
      );
      expect(result, isNull);
    });

    test('authenticated -> redirects from /login to /connection', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/login',
      );
      expect(result, '/connection');
    });

    test('authenticated -> redirects from /register to /connection', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/register',
      );
      expect(result, '/connection');
    });

    test('authenticated -> redirects from /onboarding to /connection', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/onboarding',
      );
      expect(result, '/connection');
    });

    test('authenticated -> redirects from / to /connection', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/',
      );
      expect(result, '/connection');
    });

    test('authenticated -> no redirect from /servers', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/servers',
      );
      expect(result, isNull);
    });

    test('authenticated -> no redirect from /settings', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/settings',
      );
      expect(result, isNull);
    });

    // ----- Edge case: authenticated but shouldShowOnboarding is true --------

    test(
        'authenticated with shouldShowOnboarding -> redirects to /onboarding',
        () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: true,
        isAuthLoading: false,
        path: '/connection',
      );
      expect(result, '/onboarding');
    });

    test(
        'authenticated on /onboarding with shouldShowOnboarding -> redirects to /connection',
        () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: true,
        isAuthLoading: false,
        path: '/onboarding',
      );
      expect(result, '/connection');
    });
  });

  group('Splash screen handling', () {
    test('stays on /splash while auth is loading', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: false,
        isAuthLoading: true,
        path: '/splash',
      );
      expect(result, isNull);
    });

    test('redirects from /splash to / when auth resolves', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/splash',
      );
      expect(result, '/');
    });

    test('redirects from /splash to / when authenticated', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/splash',
      );
      expect(result, '/');
    });
  });

  group('Quick setup flow', () {
    test('authenticated on /login with quickSetup -> redirects to /quick-setup',
        () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        shouldShowQuickSetup: true,
        path: '/login',
      );
      expect(result, '/quick-setup');
    });

    test('authenticated on / with quickSetup -> redirects to /quick-setup',
        () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        shouldShowQuickSetup: true,
        path: '/',
      );
      expect(result, '/quick-setup');
    });

    test('authenticated on /connection with quickSetup -> no redirect', () {
      // Quick setup only triggers from auth/onboarding/root routes
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        shouldShowQuickSetup: true,
        path: '/connection',
      );
      expect(result, isNull);
    });

    test('not authenticated with quickSetup -> still goes to /login', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        shouldShowQuickSetup: true,
        path: '/connection',
      );
      expect(result, '/login');
    });
  });

  group('Navigation stack preservation (refreshListenable)', () {
    test('refreshNotifier fires listeners when notify() called', () {
      final notifier = TestRouterRefreshNotifier();
      var notifyCount = 0;
      notifier.addListener(() => notifyCount++);

      notifier.notify();
      expect(notifyCount, 1);

      notifier.notify();
      expect(notifyCount, 2);

      notifier.dispose();
    });

    test('authenticated user on /servers stays after auth state change', () {
      // Simulates: user is on /servers, auth state refreshes (token refresh).
      // Redirect should return null, preserving the navigation stack.
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/servers',
      );
      expect(result, isNull);
    });

    test('authenticated user on /settings stays after auth state change', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/settings',
      );
      expect(result, isNull);
    });

    test('authenticated user on /profile stays after auth state change', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/profile',
      );
      expect(result, isNull);
    });

    test('logout redirects from /servers to /login', () {
      final result = resolveRedirect(
        isAuthenticated: false,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/servers',
      );
      expect(result, '/login');
    });

    test('re-login from /login redirects to /connection', () {
      final result = resolveRedirect(
        isAuthenticated: true,
        shouldShowOnboarding: false,
        isAuthLoading: false,
        path: '/login',
      );
      expect(result, '/connection');
    });
  });
}
