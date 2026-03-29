import 'package:flutter/material.dart';
import 'dart:io' show Platform;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/routing/deep_link_handler.dart';
import 'package:cybervpn_mobile/core/routing/deep_link_parser.dart';
import 'package:cybervpn_mobile/core/security/screen_protection_observer.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/quick_actions/domain/services/quick_actions_handler.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/forgot_password_screen.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/reset_password_screen.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/login_screen.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/magic_link_screen.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/register_screen.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/otp_verification_screen.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/screens/import_list_screen.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/screens/qr_scanner_screen.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/screens/diagnostics_screen.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/screens/log_viewer_screen.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/screens/speed_test_screen.dart';
import 'package:cybervpn_mobile/features/navigation/presentation/screens/main_shell_screen.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/screens/notification_center_screen.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/presentation/screens/profile_list_screen.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/presentation/screens/profile_detail_screen.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/presentation/screens/add_profile_screen.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/presentation/screens/add_by_url_screen.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/providers/onboarding_provider.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/screens/onboarding_screen.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/screens/permission_request_screen.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/change_password_screen.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/delete_account_screen.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/devices_screen.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/profile_dashboard_screen.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/social_accounts_screen.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/two_factor_screen.dart';
import 'package:cybervpn_mobile/features/security/presentation/screens/antiphishing_screen.dart';
import 'package:cybervpn_mobile/features/quick_setup/presentation/providers/quick_setup_provider.dart';
import 'package:cybervpn_mobile/features/quick_setup/presentation/screens/quick_setup_screen.dart';
import 'package:cybervpn_mobile/features/referral/presentation/screens/referral_dashboard_screen.dart';
import 'package:cybervpn_mobile/features/partner/presentation/screens/partner_dashboard_screen.dart';
import 'package:cybervpn_mobile/features/wallet/presentation/screens/wallet_screen.dart';
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
import 'package:cybervpn_mobile/features/subscription/presentation/screens/payment_history_screen.dart';
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
final _connectionNavigatorKey = GlobalKey<NavigatorState>(
  debugLabel: 'connection',
);
final _serversNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'servers');
final _profilesNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'profiles');
final _profileNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'profile');
final _settingsNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'settings');

({String code, String state})? _extractOAuthLoginCallback(Uri uri) {
  if (!DeepLinkParser.isDeepLink(uri.toString())) {
    return null;
  }

  final routePath = uri.scheme == DeepLinkParser.customScheme
      ? uri.host + uri.path
      : uri.path.startsWith('/')
      ? uri.path.substring(1)
      : uri.path;

  if (routePath != 'oauth/callback') {
    return null;
  }

  final code = uri.queryParameters['code'];
  final state = uri.queryParameters['state'];
  if (code == null || code.isEmpty || state == null || state.isEmpty) {
    return null;
  }

  return (code: code, state: state);
}

String _authRouteWithOAuthCallback({
  required String currentPath,
  required String code,
  required String state,
}) {
  final authPath = currentPath == '/register' ? '/register' : '/login';
  return buildAuthRouteLocation(
    authPath: authPath,
    oauthCode: code,
    oauthState: state,
  );
}

// ---------------------------------------------------------------------------
// Animation constants
// ---------------------------------------------------------------------------

const _transitionDuration = AnimDurations.normal;
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
        ).animate(CurvedAnimation(parent: animation, curve: _transitionCurve)),
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
  ref.listen(quickSetupProvider, (_, _) => refreshNotifier.notify());

  // Dispose the notifier when this provider is disposed.
  ref.onDispose(refreshNotifier.dispose);

  return GoRouter(
    navigatorKey: rootNavigatorKey,
    initialLocation: '/splash',
    debugLogDiagnostics: false,
    refreshListenable: refreshNotifier,
    observers: [ScreenProtectionObserver()],
    redirect: (context, state) {
      try {
        // Read current state inside redirect (not captured in provider body)
        // so values are always fresh when redirect is re-evaluated.
        final authState = ref.read(authProvider);
        final isAuthenticated = ref.read(isAuthenticatedProvider);
        final isAuthLoading = authState.isLoading;
        final shouldShowOnboarding = ref.read(shouldShowOnboardingProvider);
        final shouldShowQuickSetup = ref.read(shouldShowQuickSetupProvider);

        final uri = state.uri;
        final path = uri.path;
        final postAuthRedirect = readPostAuthRedirect(uri);
        final isAuthRoute =
            path == '/login' ||
            path == '/register' ||
            path == '/forgot-password' ||
            path == '/reset-password' ||
            path == '/magic-link' ||
            path == '/otp-verification';
        final isOnboardingRoute = path == '/onboarding';
        final isQuickSetupRoute = path == '/quick-setup';
        final isSplashRoute = path == '/splash';

        // -- Splash handling --------------------------------------------------
        // Keep the user on splash only while auth restoration is still loading.
        // Auth restoration has its own timeout, so we don't block on any other
        // startup work here.
        if (isSplashRoute && isAuthLoading) {
          return null; // stay on /splash
        }
        if (isSplashRoute) {
          // Auth resolved. Redirect to root so the standard guards below
          // decide the correct destination (onboarding, login, or connection).
          return '/';
        }

        // -- Deep link handling -----------------------------------------------
        // Check if the incoming URI is an external deep link.
        if (DeepLinkParser.isDeepLink(uri.toString())) {
          final oauthLoginCallback = _extractOAuthLoginCallback(uri);
          if (!isAuthenticated && oauthLoginCallback != null) {
            return _authRouteWithOAuthCallback(
              currentPath: path,
              code: oauthLoginCallback.code,
              state: oauthLoginCallback.state,
            );
          }

          final parseResult = DeepLinkParser.parseUri(uri);

          if (parseResult.route case TelegramAuthRoute(:final authData)) {
            return buildAuthRouteLocation(
              authPath: path == '/register' ? '/register' : '/login',
              telegramAuthData: authData,
            );
          }

          if (parseResult.route case TelegramBotLinkRoute(:final token)) {
            return buildAuthRouteLocation(
              authPath: path == '/register' ? '/register' : '/login',
              telegramBotToken: token,
            );
          }

          if (parseResult.route case ReferralRoute(:final code)) {
            if (!isAuthenticated) {
              return buildAuthRouteLocation(
                authPath: '/register',
                referralCode: code,
              );
            }

            return resolveDeepLinkPath(parseResult.route!);
          }

          final deepLinkPath = parseResult.route != null
              ? resolveDeepLinkPath(parseResult.route!)
              : null;
          if (deepLinkPath != null) {
            if (!isAuthenticated) {
              return buildAuthRouteLocation(
                authPath: '/login',
                postAuthRedirect: deepLinkPath,
              );
            }
            return deepLinkPath;
          }
        }

        // -- Standard redirect guards -----------------------------------------

        // 1. Onboarding not completed -> show onboarding
        if (shouldShowOnboarding && !isOnboardingRoute) {
          return buildOnboardingLocation(postAuthRedirect: postAuthRedirect);
        }

        // 2. Onboarding complete, not authenticated -> show login
        //    (but allow deep link target paths through -- they get caught above)
        if (!isAuthenticated && !isAuthRoute && !isOnboardingRoute) {
          return buildAuthRouteLocation(
            authPath: '/login',
            postAuthRedirect: postAuthRedirect,
          );
        }

        // 3. Authenticated user on auth/onboarding routes -> go to app
        if (isAuthenticated && (isAuthRoute || isOnboardingRoute)) {
          // Show quick setup if not completed.
          if (shouldShowQuickSetup && !isQuickSetupRoute) {
            return buildQuickSetupLocation(postAuthRedirect: postAuthRedirect);
          }
          if (postAuthRedirect != null && postAuthRedirect.isNotEmpty) {
            return postAuthRedirect;
          }
          return '/connection';
        }

        // 4. Authenticated user on root -> go to quick setup or connection
        if (isAuthenticated && path == '/') {
          // Show quick setup if not completed.
          if (shouldShowQuickSetup && !isQuickSetupRoute) {
            return buildQuickSetupLocation(postAuthRedirect: postAuthRedirect);
          }
          if (postAuthRedirect != null && postAuthRedirect.isNotEmpty) {
            return postAuthRedirect;
          }
          return '/connection';
        }

        return null;
      } catch (e, st) {
        AppLogger.error(
          'Router redirect failed',
          error: e,
          stackTrace: st,
          category: 'router',
        );
        // Preserve current location on transient errors instead of forcing logout.
        return null;
      }
    },
    routes: [
      // -- Onboarding route (no bottom nav, before auth) --------------------
      GoRoute(
        path: '/onboarding',
        name: 'onboarding',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) =>
            _buildFadeTransition(state: state, child: const OnboardingScreen()),
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
        pageBuilder: (context, state) =>
            _buildFadeTransition(state: state, child: const LoginScreen()),
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
        path: '/otp-verification',
        name: 'otp-verification',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: OtpVerificationScreen(
            email: state.uri.queryParameters['email'] ?? '',
          ),
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
      GoRoute(
        path: '/reset-password',
        name: 'reset-password',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: ResetPasswordScreen(email: state.uri.queryParameters['email']),
        ),
      ),
      GoRoute(
        path: '/magic-link',
        name: 'magic-link',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: const MagicLinkScreen(),
        ),
      ),

      // -- Quick setup route (after first auth) -----------------------------
      GoRoute(
        path: '/quick-setup',
        name: 'quick-setup',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) =>
            _buildFadeTransition(state: state, child: const QuickSetupScreen()),
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
          // Subscription URL import redirects to the new AddByUrlScreen
          // in the multi-profile system. Preserves the route name for deep
          // links and backward compatibility.
          GoRoute(
            path: 'subscription-url',
            name: 'config-import-subscription-url',
            parentNavigatorKey: rootNavigatorKey,
            redirect: (_, _) => '/profiles/add/url',
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
        path: '/partner',
        name: 'partner',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: const FeatureErrorBoundary(
            featureName: 'Partner',
            child: PartnerDashboardScreen(),
          ),
        ),
      ),
      GoRoute(
        path: '/wallet',
        name: 'wallet',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: const FeatureErrorBoundary(
            featureName: 'Wallet',
            child: WalletScreen(),
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
      GoRoute(
        path: '/payment-history',
        name: 'payment-history',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: const FeatureErrorBoundary(
            featureName: 'Payment History',
            child: PaymentHistoryScreen(),
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

      // -- Server detail (root navigator, full-screen modal) ----------------
      // Moved out of the Servers branch so tapping the Servers tab always
      // returns to the server list, not to a lingering detail page.
      GoRoute(
        path: '/servers/:id',
        name: 'server-detail',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: FeatureErrorBoundary(
            featureName: 'Server Detail',
            child: ServerDetailScreen(serverId: state.pathParameters['id']!),
          ),
        ),
      ),

      // -- Profile detail (root navigator, full-screen modal) ---------------
      // Outside the Profiles branch so tapping the Profiles tab always
      // returns to the profile list, not to a lingering detail page.
      GoRoute(
        path: '/profiles/:id',
        name: 'profile-detail',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => _buildAdaptiveTransition(
          state: state,
          child: FeatureErrorBoundary(
            featureName: 'Profile Detail',
            child: ProfileDetailScreen(profileId: state.pathParameters['id']!),
          ),
        ),
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
              ),
            ],
          ),

          // Branch 2: Profiles
          StatefulShellBranch(
            navigatorKey: _profilesNavigatorKey,
            routes: [
              GoRoute(
                path: '/profiles',
                name: 'profiles',
                builder: (context, state) => const FeatureErrorBoundary(
                  featureName: 'Profiles',
                  child: ProfileListScreen(),
                ),
                routes: [
                  GoRoute(
                    path: 'add',
                    name: 'profiles-add',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'Add Profile',
                        child: AddProfileScreen(),
                      ),
                    ),
                    routes: [
                      GoRoute(
                        path: 'url',
                        name: 'profiles-add-url',
                        parentNavigatorKey: rootNavigatorKey,
                        pageBuilder: (context, state) =>
                            _buildAdaptiveTransition(
                              state: state,
                              child: const FeatureErrorBoundary(
                                featureName: 'Add Profile URL',
                                child: AddByUrlScreen(),
                              ),
                            ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),

          // Profile detail pushed to root navigator (full screen, like server detail)
          // is registered as a top-level route below the shell.

          // Branch 3: Account (user profile)
          StatefulShellBranch(
            navigatorKey: _profileNavigatorKey,
            routes: [
              GoRoute(
                path: '/profile',
                name: 'profile',
                builder: (context, state) => const FeatureErrorBoundary(
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
                    path: 'change-password',
                    name: 'profile-change-password',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'Change Password',
                        child: ChangePasswordScreen(),
                      ),
                    ),
                  ),
                  GoRoute(
                    path: 'antiphishing',
                    name: 'profile-antiphishing',
                    parentNavigatorKey: rootNavigatorKey,
                    pageBuilder: (context, state) => _buildAdaptiveTransition(
                      state: state,
                      child: const FeatureErrorBoundary(
                        featureName: 'Antiphishing Code',
                        child: AntiphishingScreen(),
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

          // Branch 4: Settings
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
        pageBuilder: (context, state) =>
            _buildFadeTransition(state: state, child: const SplashScreen()),
      ),

      // -- Root redirect ----------------------------------------------------
      GoRoute(path: '/', redirect: (context, state) => '/connection'),
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
