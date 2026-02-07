import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

/// A large circular button (120dp diameter) that toggles VPN connection.
///
/// Visual states:
/// - **Disconnected**: Gray background, "Connect" label.
/// - **Connecting**: Pulsing blue animation, "Connecting..." label.
/// - **Connected**: Green with outer glow, "Connected" label.
/// - **Disconnecting**: Fading orange, "Disconnecting..." label.
/// - **Reconnecting**: Pulsing orange, "Reconnecting..." label.
/// - **Error**: Red background, "Retry" label.
///
/// Wrapped in [RepaintBoundary] to isolate expensive animations.
class ConnectButton extends ConsumerStatefulWidget {
  const ConnectButton({super.key});

  @override
  ConsumerState<ConnectButton> createState() => _ConnectButtonState();
}

class _ConnectButtonState extends ConsumerState<ConnectButton>
    with TickerProviderStateMixin {
  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;

  /// Controller for the connected-state glow blurRadius animation (18-30).
  late final AnimationController _glowController;
  late final Animation<double> _glowAnimation;

  VpnConnectionState? _previousState;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.15).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    );
    _glowAnimation = Tween<double>(begin: 18.0, end: 30.0).animate(
      CurvedAnimation(parent: _glowController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _glowController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(vpnConnectionProvider);
    final vpnState = asyncState.value ?? const VpnDisconnected();

    // Trigger haptic feedback on state changes.
    _triggerHapticOnStateChange(vpnState);

    // Drive pulse animation based on state.
    _syncAnimation(vpnState);

    final config = _resolveConfig(
      vpnState,
      AppLocalizations.of(context),
      Theme.of(context).colorScheme,
    );

    return RepaintBoundary(
      child: ListenableBuilder(
        listenable: Listenable.merge([_pulseAnimation, _glowAnimation]),
        builder: (context, child) {
          final scale =
              (vpnState is VpnConnecting || vpnState is VpnReconnecting)
                  ? _pulseAnimation.value
                  : 1.0;

          final opacity = vpnState is VpnDisconnecting ? 0.6 : 1.0;

          return Transform.scale(
            scale: scale,
            child: AnimatedOpacity(
              opacity: opacity,
              duration: const Duration(milliseconds: 300),
              child: _buildButton(context, vpnState, config),
            ),
          );
        },
      ),
    );
  }

  Widget _buildButton(
    BuildContext context,
    VpnConnectionState vpnState,
    _ButtonConfig config,
  ) {
    final l10n = AppLocalizations.of(context);
    final semanticLabel = _getSemanticLabel(vpnState, l10n);
    final semanticHint = _getSemanticHint(vpnState, l10n);
    final isEnabled = _isButtonEnabled(vpnState);

    return Semantics(
      label: semanticLabel,
      hint: semanticHint,
      button: true,
      enabled: isEnabled,
      child: GestureDetector(
        onTap: () => _onTap(vpnState),
        child: Container(
          width: 120,
          height: 120,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: config.color,
            boxShadow: [
              if (vpnState is VpnConnected)
                BoxShadow(
                  color: config.color.withValues(alpha: 0.5),
                  blurRadius: _glowController.isAnimating
                      ? _glowAnimation.value
                      : 24,
                  spreadRadius: 6,
                ),
              BoxShadow(
                color: config.color.withValues(alpha: 0.3),
                blurRadius: 12,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(config.icon, color: Colors.white, size: 32),
              const SizedBox(height: 6),
              Text(
                config.label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _getSemanticLabel(VpnConnectionState vpnState, AppLocalizations l10n) {
    return switch (vpnState) {
      VpnDisconnected() => l10n.a11yConnectToVpn,
      VpnConnecting() => l10n.a11yConnectingToVpn,
      VpnConnected() => l10n.a11yDisconnectFromVpn,
      VpnDisconnecting() => l10n.a11yDisconnectingFromVpn,
      VpnReconnecting() => l10n.a11yReconnectingToVpn,
      VpnError() => l10n.a11yRetryVpnConnection,
    };
  }

  String _getSemanticHint(VpnConnectionState vpnState, AppLocalizations l10n) {
    return switch (vpnState) {
      VpnDisconnected() => l10n.a11yTapToConnect,
      VpnConnected() => l10n.a11yTapToDisconnect,
      VpnError() => l10n.a11yTapToRetry,
      VpnConnecting() || VpnDisconnecting() || VpnReconnecting() =>
        l10n.a11yPleaseWaitConnectionInProgress,
    };
  }

  bool _isButtonEnabled(VpnConnectionState vpnState) {
    return vpnState is! VpnConnecting &&
        vpnState is! VpnDisconnecting &&
        vpnState is! VpnReconnecting;
  }

  void _onTap(VpnConnectionState vpnState) {
    // Trigger heavy haptic on button press for significant actions.
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.heavy());

    final notifier = ref.read(vpnConnectionProvider.notifier);

    switch (vpnState) {
      case VpnDisconnected():
        // Attempt to connect to the last known or default server.
        final server = ref.read(currentServerProvider);
        if (server != null) {
          unawaited(notifier.connect(server));
        }
      case VpnConnected():
        unawaited(notifier.disconnect());
      case VpnError():
        // Retry: try connecting again.
        final server = ref.read(currentServerProvider);
        if (server != null) {
          unawaited(notifier.connect(server));
        }
      case VpnConnecting():
      case VpnDisconnecting():
      case VpnReconnecting():
        // No action while transitioning.
        break;
    }
  }

  void _syncAnimation(VpnConnectionState vpnState) {
    final shouldPulse =
        vpnState is VpnConnecting || vpnState is VpnReconnecting;

    if (shouldPulse && !_pulseController.isAnimating) {
      unawaited(_pulseController.repeat(reverse: true));
    } else if (!shouldPulse && _pulseController.isAnimating) {
      _pulseController.stop();
      _pulseController.reset();
    }

    // Drive glow blur animation when connected, respecting accessibility
    // and theme (only in Cyberpunk theme).
    final disableAnimations = MediaQuery.of(context).disableAnimations;
    final isCyberpunk = CyberColors.isCyberpunkTheme(context);
    final shouldGlow =
        vpnState is VpnConnected && !disableAnimations && isCyberpunk;

    if (shouldGlow && !_glowController.isAnimating) {
      unawaited(_glowController.repeat(reverse: true));
    } else if (!shouldGlow && _glowController.isAnimating) {
      _glowController.stop();
      _glowController.reset();
    }
  }

  /// Trigger haptic feedback when connection state changes.
  ///
  /// Success pattern when connected, error pattern when connection fails.
  void _triggerHapticOnStateChange(VpnConnectionState currentState) {
    // Only trigger haptics on state transitions.
    if (_previousState.runtimeType == currentState.runtimeType) {
      return;
    }

    final haptics = ref.read(hapticServiceProvider);

    // Success haptic when connection is established.
    if (currentState is VpnConnected && _previousState is! VpnConnected) {
      unawaited(haptics.success());
    }

    // Error haptic when connection fails.
    if (currentState is VpnError && _previousState is! VpnError) {
      unawaited(haptics.error());
    }

    _previousState = currentState;
  }

  _ButtonConfig _resolveConfig(
    VpnConnectionState vpnState,
    AppLocalizations l10n,
    ColorScheme colorScheme,
  ) {
    return switch (vpnState) {
      VpnDisconnected() => _ButtonConfig(
          color: colorScheme.outline,
          label: l10n.connect,
          icon: Icons.power_settings_new,
        ),
      VpnConnecting() => _ButtonConfig(
          color: colorScheme.primary,
          label: l10n.connecting,
          icon: Icons.sync,
        ),
      VpnConnected() => _ButtonConfig(
          color: colorScheme.tertiary,
          label: l10n.connected,
          icon: Icons.shield,
        ),
      VpnDisconnecting() => _ButtonConfig(
          color: Colors.orange.shade600,
          label: l10n.disconnecting,
          icon: Icons.power_off,
        ),
      VpnReconnecting() => _ButtonConfig(
          color: Colors.orange.shade700,
          label: l10n.connectionStatusReconnecting,
          icon: Icons.sync_problem,
        ),
      VpnError() => _ButtonConfig(
          color: colorScheme.error,
          label: l10n.retry,
          icon: Icons.refresh,
        ),
    };
  }
}

/// Internal helper that holds resolved visual config for each button state.
class _ButtonConfig {
  final Color color;
  final String label;
  final IconData icon;

  const _ButtonConfig({
    required this.color,
    required this.label,
    required this.icon,
  });
}

/// An [AnimatedBuilder] that rebuilds when the given [animation] changes.
///
/// This is a thin wrapper around [AnimatedWidget] exposed as a builder-style
/// widget so that the parent can supply an arbitrary [builder] callback.
class AnimatedBuilder extends AnimatedWidget {
  final Widget? child;
  final Widget Function(BuildContext context, Widget? child) builder;

  const AnimatedBuilder({
    super.key,
    required Animation<double> animation,
    required this.builder,
    this.child,
  }) : super(listenable: animation);

  @override
  Widget build(BuildContext context) => builder(context, child);
}
