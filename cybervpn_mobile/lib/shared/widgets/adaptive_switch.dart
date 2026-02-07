import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

/// A platform-adaptive switch that renders [CupertinoSwitch] on iOS and
/// [Switch.adaptive] on Android (and other platforms).
///
/// The API mirrors the standard [Switch] widget so it can be used as a
/// drop-in replacement anywhere a toggle is needed.
///
/// Example:
/// ```dart
/// AdaptiveSwitch(
///   value: isEnabled,
///   onChanged: (v) => setState(() => isEnabled = v),
///   activeColor: CyberColors.neonCyan,
/// )
/// ```
class AdaptiveSwitch extends StatelessWidget {
  /// Whether the switch is currently on.
  final bool value;

  /// Called when the user toggles the switch.
  ///
  /// Pass `null` to disable interaction and grey out the switch.
  final ValueChanged<bool>? onChanged;

  /// The color used when the switch is in the on position.
  ///
  /// Defaults to the platform's primary color when omitted.
  final Color? activeColor;

  const AdaptiveSwitch({
    super.key,
    required this.value,
    required this.onChanged,
    this.activeColor,
  });

  @override
  Widget build(BuildContext context) {
    final platform = Theme.of(context).platform;

    if (platform == TargetPlatform.iOS) {
      return CupertinoSwitch(
        value: value,
        onChanged: onChanged,
        activeTrackColor: activeColor,
      );
    }

    return Switch.adaptive(
      value: value,
      onChanged: onChanged,
      activeTrackColor: activeColor,
    );
  }
}
