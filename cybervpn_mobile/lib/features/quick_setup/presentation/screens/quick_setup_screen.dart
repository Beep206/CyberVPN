import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/quick_setup/presentation/providers/quick_setup_provider.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

/// Quick setup screen shown after first login/registration.
///
/// Auto-selects the best server and offers one-tap connection within
/// 60 seconds. Shows celebration animation on success and navigates to
/// the main connection screen.
class QuickSetupScreen extends ConsumerStatefulWidget {
  const QuickSetupScreen({super.key});

  @override
  ConsumerState<QuickSetupScreen> createState() => _QuickSetupScreenState();
}

class _QuickSetupScreenState extends ConsumerState<QuickSetupScreen>
    with SingleTickerProviderStateMixin {
  Timer? _timeoutTimer;
  Timer? _connectionTimeoutTimer;
  bool _isConnecting = false;
  bool _showCelebration = false;
  late final AnimationController _celebrationController;

  @override
  void initState() {
    super.initState();
    _celebrationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    // Start 60-second timeout timer.
    _startTimeout();
  }

  @override
  void dispose() {
    _timeoutTimer?.cancel();
    _connectionTimeoutTimer?.cancel();
    _celebrationController.dispose();
    super.dispose();
  }

  void _startTimeout() {
    _timeoutTimer = Timer(const Duration(seconds: 60), () {
      if (mounted && !_isConnecting && !_showCelebration) {
        AppLogger.info('Quick setup timeout - showing gentle prompt');
        _handleTimeout();
      }
    });
  }

  void _handleTimeout() {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Take your time - you can connect anytime from the main screen'),
          backgroundColor: Theme.of(context).colorScheme.surfaceContainerHigh,
          behavior: SnackBarBehavior.floating,
          duration: const Duration(seconds: 3),
        ),
      );

      // Mark as abandoned and navigate
      Future.delayed(const Duration(seconds: 1), () {
        if (mounted) {
          _abandonSetup();
        }
      });
    }
  }

  void _abandonSetup() {
    _timeoutTimer?.cancel();
    _connectionTimeoutTimer?.cancel();
    ref.read(quickSetupProvider.notifier).abandon();
    if (mounted) {
      context.go('/connection');
    }
  }

  Future<void> _handleConnect() async {
    if (_isConnecting) return;

    final recommendedServer = ref.read(recommendedServerProvider);
    if (recommendedServer == null) {
      _handleConnectionError('No available servers found. Please try again later.');
      return;
    }

    setState(() => _isConnecting = true);
    ref.read(quickSetupProvider.notifier).setConnecting(true);

    // Start 30-second connection timeout
    _connectionTimeoutTimer = Timer(const Duration(seconds: 30), () {
      if (_isConnecting && mounted) {
        AppLogger.warning('Quick setup connection timeout after 30 seconds');
        _handleConnectionError('Connection timeout. Please try selecting a different server.');
      }
    });

    try {
      AppLogger.info('Quick setup: connecting to ${recommendedServer.name}');
      await ref.read(vpnConnectionProvider.notifier).connect(recommendedServer);

      // Check if connection was successful.
      final vpnState = ref.read(vpnConnectionProvider).value;
      if (vpnState is VpnConnected) {
        _connectionTimeoutTimer?.cancel();
        _showSuccess();
      } else if (vpnState is VpnError) {
        _connectionTimeoutTimer?.cancel();
        _handleConnectionError(vpnState.message);
      }
    } catch (e) {
      _connectionTimeoutTimer?.cancel();
      _handleConnectionError(e.toString());
    }
  }

  void _handleConnectionError(String error) {
    setState(() => _isConnecting = false);
    ref.read(quickSetupProvider.notifier).setConnecting(false);
    ref.read(quickSetupProvider.notifier).setError(error);

    AppLogger.error('Quick setup connection failed', error: error);

    if (mounted) {
      // Show error snackbar with action to navigate to server list
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Connection failed: $error'),
          backgroundColor: Theme.of(context).colorScheme.error,
          behavior: SnackBarBehavior.floating,
          duration: const Duration(seconds: 5),
          action: SnackBarAction(
            label: 'Choose Server',
            textColor: Colors.white,
            onPressed: _navigateToServerList,
          ),
        ),
      );

      // Auto-navigate to server list after 3 seconds
      Future.delayed(const Duration(seconds: 3), () {
        if (mounted) {
          _navigateToServerList();
        }
      });
    }
  }

  void _navigateToServerList() {
    _timeoutTimer?.cancel();
    _connectionTimeoutTimer?.cancel();
    ref.read(quickSetupProvider.notifier).complete();
    if (mounted) {
      context.go('/servers');
    }
  }

  void _showSuccess() {
    setState(() {
      _isConnecting = false;
      _showCelebration = true;
    });

    _celebrationController.forward();

    // Wait for animation to complete, then navigate.
    Future.delayed(const Duration(milliseconds: 2000), () {
      if (mounted) {
        _completeSetup();
      }
    });
  }

  void _completeSetup() {
    _timeoutTimer?.cancel();
    ref.read(quickSetupProvider.notifier).complete();
    if (mounted) {
      context.go('/connection');
    }
  }

  void _handleSkip() {
    AppLogger.info('Quick setup skipped by user');
    _abandonSetup();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final recommendedServer = ref.watch(recommendedServerProvider);

    // Listen to VPN connection state changes.
    ref.listen<AsyncValue<VpnConnectionState>>(vpnConnectionProvider,
        (previous, next) {
      final state = next.value;
      if (state is VpnConnected && !_showCelebration) {
        _showSuccess();
      } else if (state is VpnError) {
        _handleConnectionError(state.message);
      }
    });

    return PopScope(
      canPop: !_isConnecting && !_showCelebration,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          // User tried to navigate away - mark as abandoned.
          AppLogger.info('Quick setup cancelled by user navigation');
          _abandonSetup();
        }
      },
      child: Scaffold(
        body: SafeArea(
          child: _showCelebration
              ? _buildCelebration(theme)
              : _buildSetupContent(theme, recommendedServer),
        ),
      ),
    );
  }

  Widget _buildSetupContent(ThemeData theme, ServerEntity? server) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          const Spacer(),

          // -- Icon --
          Icon(
            Icons.rocket_launch_outlined,
            size: 80,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(height: Spacing.xl),

          // -- Title --
          Text(
            'Ready to protect you',
            style: theme.textTheme.headlineMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: theme.colorScheme.onSurface,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: Spacing.md),

          // -- Subtitle --
          Text(
            'We\'ve selected the best server for you',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: Spacing.xl * 1.5),

          // -- Server card --
          if (server != null) ...[
            _buildServerCard(theme, server),
            const SizedBox(height: Spacing.xl * 1.5),
          ] else ...[
            const CircularProgressIndicator(),
            const SizedBox(height: Spacing.lg),
            Text(
              'Finding the best server...',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: Spacing.xl * 1.5),
          ],

          // -- Connect button --
          SizedBox(
            width: double.infinity,
            height: 56,
            child: ElevatedButton(
              onPressed: (_isConnecting || server == null)
                  ? null
                  : _handleConnect,
              style: ElevatedButton.styleFrom(
                backgroundColor: theme.colorScheme.primary,
                foregroundColor: theme.colorScheme.onPrimary,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(Radii.lg),
                ),
              ),
              child: _isConnecting
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        color: Colors.white,
                      ),
                    )
                  : Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.shield, size: 24),
                        const SizedBox(width: Spacing.sm),
                        Text(
                          'Connect Now',
                          style: theme.textTheme.titleMedium?.copyWith(
                            color: theme.colorScheme.onPrimary,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
            ),
          ),

          const Spacer(),

          // -- Skip button --
          TextButton(
            onPressed: _isConnecting ? null : _handleSkip,
            child: Text(
              'Skip for now',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildServerCard(ThemeData theme, ServerEntity server) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(Spacing.lg),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(Radii.md),
        border: Border.all(
          color: theme.colorScheme.outline.withValues(alpha: 0.2),
        ),
      ),
      child: Column(
        children: [
          // Country flag emoji (simple fallback using first letter).
          Text(
            _getCountryFlag(server.countryCode),
            style: const TextStyle(fontSize: 48),
          ),
          const SizedBox(height: Spacing.sm),

          // Server name.
          Text(
            server.name,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: Spacing.xs),

          // Location.
          Text(
            '${server.city}, ${server.countryName}',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),

          // Ping indicator.
          if (server.ping != null) ...[
            const SizedBox(height: Spacing.sm),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.speed,
                  size: 16,
                  color: _getPingColor(server.ping!, theme),
                ),
                const SizedBox(width: Spacing.xs),
                Text(
                  '${server.ping} ms',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: _getPingColor(server.ping!, theme),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCelebration(ThemeData theme) {
    return FadeTransition(
      opacity: _celebrationController,
      child: ScaleTransition(
        scale: Tween<double>(begin: 0.8, end: 1.0).animate(
          CurvedAnimation(
            parent: _celebrationController,
            curve: Curves.elasticOut,
          ),
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.check_circle_outline,
                size: 120,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: Spacing.xl),
              Text(
                'You\'re protected!',
                style: theme.textTheme.headlineLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.primary,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: Spacing.md),
              Text(
                'Your connection is now secure',
                style: theme.textTheme.bodyLarge?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _getCountryFlag(String countryCode) {
    // Simple flag emoji mapper for common countries.
    // In production, use a proper country-code-to-flag library.
    final flagMap = {
      'US': '🇺🇸',
      'GB': '🇬🇧',
      'DE': '🇩🇪',
      'FR': '🇫🇷',
      'JP': '🇯🇵',
      'CA': '🇨🇦',
      'AU': '🇦🇺',
      'NL': '🇳🇱',
      'SG': '🇸🇬',
      'SE': '🇸🇪',
    };
    return flagMap[countryCode.toUpperCase()] ?? '🌐';
  }

  Color _getPingColor(int ping, ThemeData theme) {
    if (ping < 50) {
      return Colors.green;
    } else if (ping < 150) {
      return Colors.orange;
    } else {
      return Colors.red;
    }
  }
}
