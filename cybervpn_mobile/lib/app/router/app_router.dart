import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:io' show Platform;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/routing/deep_link_handler.dart';
import 'package:cybervpn_mobile/core/routing/deep_link_parser.dart';
import 'package:cybervpn_mobile/core/security/screen_protection_observer.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/telegram_auth_provider.dart';
import 'package:cybervpn_mobile/features/quick_actions/domain/services/quick_actions_handler.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/forgot_password_screen.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/login_screen.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/register_screen.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/screens/import_list_screen.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/screens/qr_scanner_screen.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/screens/subscription_url_screen.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/screens/diagnostics_screen.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/screens/log_viewer_screen.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/screens/speed_test_screen.dart';
import 'package:cybervpn_mobile/features/navigation/presentation/screens/main_shell_screen.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/screens/notification_center_screen.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/providers/onboarding_provider.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/screens/onboarding_screen.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/screens/permission_request_screen.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/delete_account_screen.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/devices_screen.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/profile_dashboard_screen.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/social_accounts_screen.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/two_factor_screen.dart';
import 'package:cybervpn_mobile/features/quick_setup/presentation/providers/quick_setup_provider.dart';
import 'package:cybervpn_mobile/features/quick_setup/presentation/screens/quick_setup_screen.dart';
import 'package:cybervpn_mobile/features/referral/presentation/screens/referral_dashboard_screen.dart';
import 'package:cybervpn_mobile/features/servers/presentation/screens/server_detail_screen.dart';
import 'package:cybervpn_mobile/features/servers/presentation/screens/server_list_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/appearance_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/debug_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/language_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/notification_prefs_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/settings_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/trusted_wifi_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/vpn_settings_screen.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/screens/plans_screen.dart';
import 'package:cybervpn_mobile/features/splash/presentation/screens/splash_screen.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/screens/connection_screen.dart';
import 'package:cybervpn_mobile/shared/widgets/feature_error_boundary.dart';

// ---------------------------------------------------------------------------
// Placeholder screens removed - all real implementations are now in use
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Navigation keys for StatefulShellRoute branches
// ---------------------------------------------------------------------------

// Use the global rootNavigatorKey from quick_actions_handler for navigation
// This allows quick actions to navigate even when the app is in background
final _connectionNavigatorKey =
    GlobalKey<NavigatorState>(debugLabel: 'connection');
final _serversNavigatorKey =
    GlobalKey<NavigatorState>(debugLabel: 'servers');
final _profileNavigatorKey =
    GlobalKey<NavigatorState>(debugLabel: 'profile');
final _settingsNavigatorKey =
    GlobalKey<NavigatorState>(debugLabel: 'settings');

// ---------------------------------------------------------------------------
// Animation constants
// ---------------------------------------------------------------------------

const _transitionDuration = Duration(milliseconds: 300);
const _transitionCurve = Curves.easeInOutCubic;

// ---------------------------------------------------------------------------
// Transition builder for slide transitions
// ---------------------------------------------------------------------------

CustomTransitionPage<void> _buildSlideTransition({
  required GoRouterState state,
  required Widget child,
}) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    child: child,
    transitionDuration: _transitionDuration,
    reverseTransitionDuration: _transitionDuration,
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      // Respect accessibility settings - skip animation if disabled
      final disableAnimations = MediaQuery.of(context).disableAnimations;
      if (disableAnimations) {
        return child;
      }

      return SlideTransition(
        position: Tween<Offset>(
          begin: const Offset(1.0, 0.0),
          end: Offset.zero,
        ).animate(CurvedAnimation(
          parent: animation,
          curve: _transitionCurve,
        )),
        child: FadeTransition(
          opacity: CurvedAnimation(
            parent: animation,
            curve: const Interval(0.0, 0.5, curve: Curves.easeOut),
          ),
          child: RepaintBoundary(child: child),
        ),
      );
    },
  );
}

CustomTransitionPage<void> _buildFadeTransition({
  required GoRouterState state,
  required Widget child,
}) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    child: child,
    transitionDuration: _transitionDuration,
    reverseTransitionDuration: _transitionDuration,
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      // Respect accessibility settings - skip animation if disabled
      final disableAnimations = MediaQuery.of(context).disableAnimations;
      if (disableAnimations) {
        return child;
      }

      return FadeTransition(opacity: animation, child: child);
    },
  );
}

// ---------------------------------------------------------------------------
// Platform-adaptive transition builder
// ---------------------------------------------------------------------------

/// Builds a platform-adaptive page transition:
/// - **iOS**: Cupertino-style slide from right to left.
/// - **Android / other**: Material-style fade transition.
CustomTransitionPage<void> _buildAdaptiveTransition({
  required GoRouterState state,
  required Widget child,
}) {
  if (Platform.isIOS) {
    return _buildSlideTransition(state: state, child: child);
  }
  return _buildFadeTransition(state: state, child: child);
}

// ---------------------------------------------------------------------------
// Router refresh notifier
// ---------------------------------------------------------------------------

/// A [ChangeNotifier] that triggers GoRouter redirect re-evaluation without
/// recreating the entire router instance.
class _RouterRefreshNotifier extends ChangeNotifier {
  void notify() => notifyListeners();
}

// ---------------------------------------------------------------------------
// Router provider
// ---------------------------------------------------------------------------

/// Creates the application [GoRouter] with onboarding, authentication, and
/// deep link redirect guards.
///
/// Uses [GoRouter.refreshListenable] to re-evaluate redirects when auth or
/// onboarding state changes, preserving the navigation stack instead of
/// recreating the entire router.
///
/// Redirect priority:
/// 1. If the incoming URI is a deep link (cybervpn:// or https://cybervpn.app)
///    -> parse it and redirect to the internal route. If unauthenticated, store
///    as pending and redirect to login.
/// 2. If onboarding has **not** been completed and the user is not already on
///    `/onboarding` -> redirect to `/onboarding`.
/// 3. If onboarding is complete but user is **not** authenticated and not on
///    an auth route -> redirect to `/login`.
/// 4. If authenticated and on an auth route or `/onboarding` -> redirect to
///    `/connection`. Also, consume any pending deep link.
/// 5. Otherwise -> no redirect.
final appRouterProvider = Provider<GoRouter>((ref) {
  // Notifier that fires when auth/onboarding state changes, triggering
  // GoRouter redirect re-evaluation without recreating the router.
  final refreshNotifier = _RouterRefreshNotifier();

  ref.listen(authProvider, (_, _) => refreshNotifier.notify());
  ref.listen(shouldShowOnboardingProvider, (_, _) => refreshNotifier.notify());
  ref.listen(shouldShowQuickSetupProvider, (_, _) => refreshNotifier.notify());

  // Initialize quick actions handler (keeps it alive)
  ref.watch(quickActionsHandlerProvider);

  // Dispose the notifier when this provider is disposed.
  ref.onDispose(refreshNotifier.dispose);

  return GoRouter(
    navigatorKey: rootNavigatorKey,
    initialLocation: '/splash',
    debugLogDiagnostics: false,
    refreshListenable: refreshNotifier,
    observers: [
      ScreenProtectionObserver(),
    ],
    redirect: (context, state) {
      try {
      // Read current state inside redirect (not captured in provider body)
      // so values are always fresh when redirect is re-evaluated.
      final authState = ref.read(authProvider);
      final isAuthenticated = ref.read(isAuthenticatedProvider);
      final isAuthLoading = authState.isLoading;
      final onboardingAsync = ref.read(shouldShowOnboardingProvider);
      final isOnboardingLoading = onboardingAsync.isLoading;
      final shouldShowOnboarding = onboardingAsync.value ?? false;
      final shouldShowQuickSetup = ref.read(shouldShowQuickSetupProvider);

      final uri = state.uri;
      final path = uri.path;
      final isAuthRoute = path == '/login' || path == '/register' || path == '/forgot-password';
      final isOnboardingRoute = path == '/onboarding';
      final isQuickSetupRoute = path == '/quick-setup';
      final isSplashRoute = path == '/splash';

      // -- Splash handling --------------------------------------------------
      // While auth or onboarding state is loading, keep the user on splash.
      // Once both resolve, redirect from splash into the normal guard chain.
      if (isSplashRoute && (isAuthLoading || isOnboardingLoading)) {
        return null; // stay on /splash
      }
      if (isSplashRoute && !isAuthLoading) {
        // Auth resolved. Redirect to root so the standard guards below
        // decide the correct destination (onboarding, login, or connection).
        return '/';
      }

      // -- Deep link handling -----------------------------------------------
      // Check if the incoming URI is an external deep link.
      if (DeepLinkParser.isDeepLink(uri.toString())) {
        final parseResult = DeepLinkParser.parseUri(uri);

        // Handle Telegram auth callback specially - trigger the provider
        // without navigating to a separate screen.
        if (parseResult.route case TelegramAuthRoute(:final authData)) {
          // Trigger Telegram auth callback asynchronously.
          // The auth state listener will handle navigation on success.
          unawaited(ref.read(telegramAuthProvider.notifier).handleCallback(authData));

          // Stay on current screen (login/register) - the listener will
          // navigate to /connection on success.
          return path.isEmpty || path == '/' ? '/login' : null;
        }

        final deepLinkPath =
            parseResult.route != null ? resolveDeepLinkPath(parseResult.route!) : null;
        if (deepLinkPath != null) {
          if (!isAuthenticated) {
            // Store the deep link for after login.
            ref
                .read<PendingDeepLinkNotifier>(pendingDeepLinkProvider.notifier)
                .setPending(parseResult.route!);
            return '/login';
          }
          return deepLinkPath;
        }
      }

      // -- Standard redirect guards -----------------------------------------

      // 1. Onboarding not completed -> show onboarding
      if (shouldShowOnboarding && !isOnboardingRoute) {
        return '/onboarding';
      }

      // 2. Onboarding complete, not authenticated -> show login
      //    (but allow deep link target paths through -- they get caught above)
      if (!isAuthenticated && !isAuthRoute && !isOnboardingRoute) {
        return '/login';
      }

      // 3. Authenticated user on auth/onboarding routes -> go to app
      //    Check for pending deep link first.
      if (isAuthenticated && (isAuthRoute || isOnboardingRoute)) {
        // Show quick setup if not completed.
        if (shouldShowQuickSetup && !isQuickSetupRoute) {
          return '/quick-setup';
        }
        final pendingRoute =
            ref.read<PendingDeepLinkNotifier>(pendingDeepLinkProvider.notifier).consume();
        if (pendingRoute != null) {
          return resolveDeepLinkPath(pendingRoute);
        }
        return '/connection';
      }

      // 4. Authenticated user on root -> go to quick setup or connection
      if (isAuthenticated && path == '/') {
        // Show quick setup if not completed.
        if (shouldShowQuickSetup && !isQuickSetupRoute) {
          return '/quick-setup';
        }
        final pendingRoute =
            ref.read<PendingDeepLinkNotifier>(pendingDeepLinkProvider.notifier).consume();
        if (pendingRoute != null) {
          return resolveDeepLinkPath(pendingRoute);
        }
        return '/connection';
      }

      return null;
      } catch (e, st) {
        AppLogger.error('Router redirect failed', error: e, stackTrace: st, category: 'router');
        return '/login';
      }
    },
    routes: [
      // -- Onboarding route (no bottom nav, before auth) --------------------
      GoRoute(
        path: '/onboarding',
        name: 'onboarding',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildFadeTransition(
          state: state,
          child: const OnboardingScreen(),
        ),
      ),

      // -- Permission request route (after onboarding, before auth) ---------
      GoRoute(
        path: '/permissions',
        name: 'permissions',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildFadeTransition(
          state: state,
          child: const PermissionRequestScreen(),
        ),
      ),

      // -- Auth routes (no bottom nav) --------------------------------------
      GoRoute(
        path: '/login',
        name: 'login',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildFadeTransition(
          state: state,
          child: const LoginScreen(),
        ),
      ),
      GoRoute(
        path: '/register',
        name: 'register',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: const RegisterScreen(),
        ),
      ),
      GoRoute(
        path: '/forgot-password',
        name: 'forgot-password',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: const ForgotPasswordScreen(),
        ),
      ),

      // -- Quick setup route (after first auth) -----------------------------
      GoRoute(
        path: '/quick-setup',
        name: 'quick-setup',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildFadeTransition(
          state: state,
          child: const QuickSetupScreen(),
        ),
      ),

      // -- Deep link target routes (outside shell, full screen) -------------
      GoRoute(
        path: '/config-import',
        name: 'config-import',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: const FeatureErrorBoundary(
            featureName: 'Config Import',
            child: ImportListScreen(),
          ),
        ),
        routes: [
          GoRoute(
            path: 'qr-scanner',
            name: 'config-import-qr-scanner',
            parentNavigatorKey: rootNavigatorKey,
            pageBuilder: (context, state) => _buildAdaptiveTransition(
              state: state,
              child: const FeatureErrorBoundary(
                featureName: 'QR Scanner',
                child: QrScannerScreen(),
              ),
            ),
          ),
          GoRoute(
            path: 'subscription-url',
            name: 'config-import-subscription-url',
            parentNavigatorKey: rootNavigatorKey,
            pageBuilder: (context, state) => _buildAdaptiveTransition(
              state: state,
              child: const FeatureErrorBoundary(
                featureName: 'Subscription URL',
                child: SubscriptionUrlScreen(),
              ),
            ),
          ),
          GoRoute(
            path: 'custom-servers',
            name: 'config-import-custom-servers',
            parentNavigatorKey: rootNavigatorKey,
            pageBuilder: (context, state) => _buildAdaptiveTransition(
              state: state,
              child: const FeatureErrorBoundary(
                featureName: 'Custom Servers',
                child: ImportListScreen(),
              ),
            ),
          ),
        ],
      ),
      GoRoute(
        path: '/referral',
        name: 'referral',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: const FeatureErrorBoundary(
            featureName: 'Referral',
            child: ReferralDashboardScreen(),
          ),
        ),
      ),
      GoRoute(
        path: '/subscribe',
        name: 'subscribe',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: const FeatureErrorBoundary(
            featureName: 'Subscription',
            child: PlansScreen(),
          ),
        ),
      ),

      // -- Notifications (full screen, outside shell) -----------------------
      GoRoute(
        path: '/notifications',
        name: 'notifications',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: const FeatureErrorBoundary(
            featureName: 'Notifications',
            child: NotificationCenterScreen(),
          ),
        ),
      ),

      // -- Diagnostics (full screen, outside shell) -------------------------
      GoRoute(
        path: '/diagnostics',
        name: 'diagnostics',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: const FeatureErrorBoundary(
            featureName: 'Diagnostics',
            child: DiagnosticsScreen(),
          ),
        ),
        routes: [
          GoRoute(
            path: 'speed-test',
            name: 'diagnostics-speed-test',
            parentNavigatorKey: rootNavigatorKey,
            pageBuilder: (context, state) => _buildAdaptiveTransition(
              state: state,
              child: const FeatureErrorBoundary(
                featureName: 'Speed Test',
                child: SpeedTestScreen(),
              ),
            ),
          ),
          GoRoute(
            path: 'connection-diagnostics',
            name: 'diagnostics-connection-diagnostics',
            parentNavigatorKey: rootNavigatorKey,
            pageBuilder: (context, state) => _buildAdaptiveTransition(
              state: state,
              child: const FeatureErrorBoundary(
                featureName: 'Connection Diagnostics',
                child: DiagnosticsScreen(),
              ),
            ),
          ),
          GoRoute(
            path: 'logs',
            name: 'diagnostics-logs',
            parentNavigatorKey: rootNavigatorKey,
            pageBuilder: (context, state) => _buildAdaptiveTransition(
              state: state,
              child: const FeatureErrorBoundary(
                featureName: 'Log Viewer',
                child: LogViewerScreen(),
              ),
            ),
          ),
        ],
      ),

      // -- Main shell with stateful bottom navigation -----------------------
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) {
          return MainShellScreen(navigationShell: navigationShell);
        },
        branches: [
          // Branch 0: Connection
          StatefulShellBranch(
            navigatorKey: _connectionNavigatorKey,
            routes: [
              GoRoute(
                path: '/connection',
                name: 'connection',
                builder: (context, state) => const FeatureErrorBoundary(
                  featureName: 'Connection',
                  child: ConnectionScreen(),
                ),
              ),
            ],
          ),

          // Branch 1: Servers
          StatefulShellBranch(
            navigatorKey: _serversNavigatorKey,
            routes: [
              GoRoute(
                path: '/servers',
                name: 'servers',
                builder: (context, state) => const FeatureErrorBoundary(
                  featureName: 'Servers',
                  child: ServerListScreen(),
                ),
                routes: [
                  GoRoute(
                    path: ':id',
                    name: 'server-detail',
                    builder: (context, state) => FeatureErrorBoundary(
                      featureName: 'Server Detail',
                      child: ServerDetailScreen(
                        serverId: state.pathParameters['id']!,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),

          // Branch 2: Profile
          StatefulShellBranch(
            navigatorKey: _profileNavigatorKey,
            routes: [
              GoRoute(
                path: '/profile',
                name: 'profile',
                builder: (context, state) =>
                    const FeatureErrorBoundary(
                      featureName: 'Profile',
                      child: ProfileDashboardScreen(),
                    ),
                routes: [
                  GoRoute(
                    path: '2fa',
                    name: 'profile-2fa',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'Two-Factor Auth',
                        child: TwoFactorScreen(),
                      ),
                    ),
                  ),
                  GoRoute(
                    path: 'social-accounts',
                    name: 'profile-social-accounts',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'Social Accounts',
                        child: SocialAccountsScreen(),
                      ),
                    ),
                  ),
                  GoRoute(
                    path: 'devices',
                    name: 'profile-devices',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'Devices',
                        child: DevicesScreen(),
                      ),
                    ),
                  ),
                  GoRoute(
                    path: 'delete-account',
                    name: 'profile-delete-account',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'Delete Account',
                        child: DeleteAccountScreen(),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),

          // Branch 3: Settings
          StatefulShellBranch(
            navigatorKey: _settingsNavigatorKey,
            routes: [
              GoRoute(
                path: '/settings',
                name: 'settings',
                builder: (context, state) => const FeatureErrorBoundary(
                  featureName: 'Settings',
                  child: SettingsScreen(),
                ),
                routes: [
                  GoRoute(
                    path: 'vpn',
                    name: 'settings-vpn',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'VPN Settings',
                        child: VpnSettingsScreen(),
                      ),
                    ),
                  ),
                  GoRoute(
                    path: 'trusted-wifi',
                    name: 'settings-trusted-wifi',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'Trusted WiFi',
                        child: TrustedWifiScreen(),
                      ),
                    ),
                  ),
                  GoRoute(
                    path: 'appearance',
                    name: 'settings-appearance',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'Appearance',
                        child: AppearanceScreen(),
                      ),
                    ),
                  ),
                  GoRoute(
                    path: 'language',
                    name: 'settings-language',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'Language',
                        child: LanguageScreen(),
                      ),
                    ),
                  ),
                  GoRoute(
                    path: 'notifications',
                    name: 'settings-notifications',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'Notification Preferences',
                        child: NotificationPrefsScreen(),
                      ),
                    ),
                  ),
                  GoRoute(
                    path: 'debug',
                    name: 'settings-debug',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'Debug',
                        child: DebugScreen(),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),

      // -- Splash route (shown during initial auth resolution) ---------------
      GoRoute(
        path: '/splash',
        name: 'splash',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildFadeTransition(
          state: state,
          child: const SplashScreen(),
        ),
      ),

      // -- Root redirect ----------------------------------------------------
      GoRoute(
        path: '/',
        redirect: (context, state) => '/connection',
      ),
    ],
  );
});

/// Convenience getter that reads the router from the provider.
///
/// Usage in `MaterialApp.router`:
/// ```dart
/// final router = ref.watch(appRouterProvider);
/// return MaterialApp.router(routerConfig: router, ...);
/// ```
