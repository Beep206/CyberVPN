import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/security/widgets/root_detection_dialog.dart';
import 'package:cybervpn_mobile/core/security/widgets/root_warning_banner.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

/// Main shell screen that wraps the bottom navigation for the app.
///
/// Uses [StatefulNavigationShell] from GoRouter to preserve state across
/// tabs. Each tab corresponds to a branch in the [StatefulShellRoute].
class MainShellScreen extends ConsumerStatefulWidget {
  /// The navigation shell provided by [StatefulShellRoute.indexedStack].
  final StatefulNavigationShell navigationShell;

  const MainShellScreen({
    super.key,
    required this.navigationShell,
  });

  @override
  ConsumerState<MainShellScreen> createState() => _MainShellScreenState();
}

class _MainShellScreenState extends ConsumerState<MainShellScreen> {
  /// Track whether auto-connect notification was shown.
  bool _autoConnectNotificationShown = false;

  @override
  void initState() {
    super.initState();
    // Check device integrity on app startup (after user logs in/completes onboarding)
    unawaited(_checkDeviceIntegrity());
  }

  /// Checks if the device is rooted/jailbroken and shows warning if needed.
  ///
  /// This check runs asynchronously without blocking app startup. If the device
  /// is rooted/jailbroken AND the user hasn't dismissed the warning before,
  /// a non-blocking informational dialog is shown.
  Future<void> _checkDeviceIntegrity() async {
    try {
      final integrityChecker = ref.read(deviceIntegrityCheckerProvider);

      // Check if device is rooted/jailbroken
      final isRooted = await integrityChecker.isDeviceRooted();

      if (!isRooted) {
        AppLogger.info('Device integrity check passed', category: 'security');
        return;
      }

      // Check if user has already dismissed the warning
      final hasDismissed = await integrityChecker.hasUserDismissedWarning();

      if (hasDismissed) {
        AppLogger.info(
          'Device is rooted/jailbroken but user has dismissed warning',
          category: 'security',
        );
        return;
      }

      // Show the warning dialog
      if (mounted) {
        // Delay slightly to ensure the UI is fully rendered
        await Future<void>.delayed(const Duration(milliseconds: 500));

        if (mounted) {
          await RootDetectionDialog.show(
            context: context,
            integrityChecker: integrityChecker,
          );
        }
      }
    } catch (e, stackTrace) {
      AppLogger.error(
        'Failed to perform device integrity check',
        error: e,
        stackTrace: stackTrace,
        category: 'security',
      );
      // Fail silently - don't block app usage
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    // Listen to VPN connection state for auto-connect notifications.
    ref.listen<AsyncValue<VpnConnectionState>>(
      vpnConnectionProvider,
      (previous, next) {
        final prevState = previous?.value;
        final nextState = next.value;

        // Show notification when transitioning from disconnected to connecting
        // during app startup (auto-connect scenario).
        if (!_autoConnectNotificationShown &&
            prevState is VpnDisconnected &&
            nextState is VpnConnecting) {
          _autoConnectNotificationShown = true;
          _showAutoConnectNotification(context, nextState.server?.name);
        }

        // Show error notification if auto-connect fails.
        if (nextState is VpnError && !_autoConnectNotificationShown) {
          _autoConnectNotificationShown = true;
          _showAutoConnectError(context, nextState.message);
        }

        // Show success notification when auto-connect succeeds.
        if (prevState is VpnConnecting && nextState is VpnConnected) {
          _showAutoConnectSuccess(context, nextState.server.name);
        }
      },
    );

    final l10n = AppLocalizations.of(context);

    /// Tablet / landscape breakpoint (Material 3 compact → medium).
    const tabletBreakpoint = 600.0;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth >= tabletBreakpoint;

        if (isWide) {
          return Scaffold(
            body: Column(
              children: [
                const RootWarningBanner(),
                Expanded(
                  child: Row(
                    children: [
                      NavigationRail(
                        selectedIndex: widget.navigationShell.currentIndex,
                        onDestinationSelected: _onTabSelected,
                        labelType: NavigationRailLabelType.all,
                        indicatorColor: theme.colorScheme.primary
                            .withValues(alpha: 0.15),
                        destinations: [
                          NavigationRailDestination(
                            icon: const Icon(Icons.power_settings_new),
                            selectedIcon: Icon(
                              Icons.power_settings_new,
                              color: theme.colorScheme.primary,
                            ),
                            label: Text(l10n.navConnection),
                          ),
                          NavigationRailDestination(
                            icon: const Icon(Icons.public),
                            selectedIcon: Icon(
                              Icons.public,
                              color: theme.colorScheme.primary,
                            ),
                            label: Text(l10n.servers),
                          ),
                          NavigationRailDestination(
                            icon: const Icon(Icons.person),
                            selectedIcon: Icon(
                              Icons.person,
                              color: theme.colorScheme.primary,
                            ),
                            label: Text(l10n.profile),
                          ),
                          NavigationRailDestination(
                            icon: const Icon(Icons.settings),
                            selectedIcon: Icon(
                              Icons.settings,
                              color: theme.colorScheme.primary,
                            ),
                            label: Text(l10n.settings),
                          ),
                        ],
                      ),
                      const VerticalDivider(thickness: 1, width: 1),
                      Expanded(child: widget.navigationShell),
                    ],
                  ),
                ),
              ],
            ),
          );
        }

        return Scaffold(
          body: Column(
            children: [
              const RootWarningBanner(),
              Expanded(child: widget.navigationShell),
            ],
          ),
          bottomNavigationBar: NavigationBar(
            selectedIndex: widget.navigationShell.currentIndex,
            onDestinationSelected: _onTabSelected,
            indicatorColor:
                theme.colorScheme.primary.withValues(alpha: 0.15),
            destinations: [
              NavigationDestination(
                icon: Icon(
                  Icons.power_settings_new,
                  color: _iconColor(context, 0),
                ),
                selectedIcon: Icon(
                  Icons.power_settings_new,
                  color: theme.colorScheme.primary,
                ),
                label: l10n.navConnection,
              ),
              NavigationDestination(
                icon: Icon(
                  Icons.public,
                  color: _iconColor(context, 1),
                ),
                selectedIcon: Icon(
                  Icons.public,
                  color: theme.colorScheme.primary,
                ),
                label: l10n.servers,
              ),
              NavigationDestination(
                icon: Icon(
                  Icons.person,
                  color: _iconColor(context, 2),
                ),
                selectedIcon: Icon(
                  Icons.person,
                  color: theme.colorScheme.primary,
                ),
                label: l10n.profile,
              ),
              NavigationDestination(
                icon: Icon(
                  Icons.settings,
                  color: _iconColor(context, 3),
                ),
                selectedIcon: Icon(
                  Icons.settings,
                  color: theme.colorScheme.primary,
                ),
                label: l10n.settings,
              ),
            ],
          ),
        );
      },
    );
  }

  /// Navigate to the selected tab branch, preserving state.
  void _onTabSelected(int index) {
    widget.navigationShell.goBranch(
      index,
      // Navigate to the initial location of the branch when tapping
      // the already-active tab item.
      initialLocation: index == widget.navigationShell.currentIndex,
    );
  }

  /// Returns the default icon color for unselected tabs.
  Color _iconColor(BuildContext context, int index) {
    if (index == widget.navigationShell.currentIndex) {
      return Theme.of(context).colorScheme.primary;
    }
    return Theme.of(context).colorScheme.onSurfaceVariant;
  }

  /// Shows a non-blocking SnackBar when auto-connect is triggered.
  void _showAutoConnectNotification(BuildContext context, String? serverName) {
    if (!mounted) return;

    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    messenger.clearSnackBars();
    messenger.showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                serverName != null
                    ? l10n.autoConnectingToServer(serverName)
                    : l10n.autoConnectingToVpn,
                style: const TextStyle(fontSize: 14),
              ),
            ),
          ],
        ),
        backgroundColor: Theme.of(context).colorScheme.primary,
        duration: const Duration(seconds: 3),
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  /// Shows an error SnackBar when auto-connect fails.
  void _showAutoConnectError(BuildContext context, String message) {
    if (!mounted) return;

    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    messenger.clearSnackBars();
    messenger.showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.white, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                l10n.autoConnectFailed(message),
                style: const TextStyle(fontSize: 14),
              ),
            ),
          ],
        ),
        backgroundColor: Theme.of(context).colorScheme.error,
        duration: const Duration(seconds: 5),
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.all(16),
        action: SnackBarAction(
          label: l10n.dismiss,
          textColor: Colors.white,
          onPressed: messenger.hideCurrentSnackBar,
        ),
      ),
    );
  }

  /// Shows a success SnackBar when auto-connect succeeds.
  void _showAutoConnectSuccess(BuildContext context, String serverName) {
    if (!mounted) return;

    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    messenger.clearSnackBars();
    messenger.showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle_outline, color: Colors.white, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                l10n.autoConnectSuccess(serverName),
                style: const TextStyle(fontSize: 14),
              ),
            ),
          ],
        ),
        backgroundColor: Theme.of(context).colorScheme.tertiary,
        duration: const Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.all(16),
      ),
    );
  }
}
