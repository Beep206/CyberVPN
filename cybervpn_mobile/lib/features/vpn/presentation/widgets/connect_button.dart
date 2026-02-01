import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
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
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;
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
  }

  @override
  void dispose() {
    _pulseController.dispose();
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

    final config = _resolveConfig(vpnState);

    return RepaintBoundary(
      child: AnimatedBuilder(
        animation: _pulseAnimation,
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
              child: child,
            ),
          );
        },
        child: _buildButton(context, vpnState, config),
      ),
    );
  }

  Widget _buildButton(
    BuildContext context,
    VpnConnectionState vpnState,
    _ButtonConfig config,
  ) {
    final semanticLabel = _getSemanticLabel(vpnState);
    final semanticHint = _getSemanticHint(vpnState);
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
                  blurRadius: 24,
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

  String _getSemanticLabel(VpnConnectionState vpnState) {
    return switch (vpnState) {
      VpnDisconnected() => 'Connect to VPN',
      VpnConnecting() => 'Connecting to VPN',
      VpnConnected() => 'Disconnect from VPN',
      VpnDisconnecting() => 'Disconnecting from VPN',
      VpnReconnecting() => 'Reconnecting to VPN',
      VpnError() => 'Retry VPN connection',
    };
  }

  String _getSemanticHint(VpnConnectionState vpnState) {
    return switch (vpnState) {
      VpnDisconnected() => 'Tap to connect to the VPN server',
      VpnConnected() => 'Tap to disconnect from the VPN server',
      VpnError() => 'Tap to retry the connection',
      VpnConnecting() || VpnDisconnecting() || VpnReconnecting() =>
        'Please wait, connection in progress',
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
    haptics.heavy();

    final notifier = ref.read(vpnConnectionProvider.notifier);

    switch (vpnState) {
      case VpnDisconnected():
        // Attempt to connect to the last known or default server.
        final server = ref.read(currentServerProvider);
        if (server != null) {
          notifier.connect(server);
        }
      case VpnConnected():
        notifier.disconnect();
      case VpnError():
        // Retry: try connecting again.
        final server = ref.read(currentServerProvider);
        if (server != null) {
          notifier.connect(server);
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
      _pulseController.repeat(reverse: true);
    } else if (!shouldPulse && _pulseController.isAnimating) {
      _pulseController.stop();
      _pulseController.reset();
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
      haptics.success();
    }

    // Error haptic when connection fails.
    if (currentState is VpnError && _previousState is! VpnError) {
      haptics.error();
    }

    _previousState = currentState;
  }

  _ButtonConfig _resolveConfig(VpnConnectionState vpnState) {
    return switch (vpnState) {
      VpnDisconnected() => _ButtonConfig(
          color: Colors.grey.shade600,
          label: 'Connect',
          icon: Icons.power_settings_new,
        ),
      VpnConnecting() => _ButtonConfig(
          color: Colors.blue.shade600,
          label: 'Connecting...',
          icon: Icons.sync,
        ),
      VpnConnected() => _ButtonConfig(
          color: Colors.green.shade600,
          label: 'Connected',
          icon: Icons.shield,
        ),
      VpnDisconnecting() => _ButtonConfig(
          color: Colors.orange.shade600,
          label: 'Disconnecting...',
          icon: Icons.power_off,
        ),
      VpnReconnecting() => _ButtonConfig(
          color: Colors.orange.shade700,
          label: 'Reconnecting...',
          icon: Icons.sync_problem,
        ),
      VpnError() => _ButtonConfig(
          color: Colors.red.shade600,
          label: 'Retry',
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
