import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

class AnimatedToggle extends StatelessWidget {
  final bool value;
  final ValueChanged<bool> onChanged;
  final double width;
  final double height;
  final Color? activeColor;
  final Color? inactiveColor;

  const AnimatedToggle({
    super.key,
    required this.value,
    required this.onChanged,
    this.width = 60,
    this.height = 32,
    this.activeColor,
    this.inactiveColor,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final active = activeColor ?? theme.colorScheme.primary;
    final inactive = inactiveColor ?? theme.colorScheme.surfaceContainerHighest;
    final thumbSize = height - 4;

    return GestureDetector(
      onTap: () => onChanged(!value),
      child: AnimatedContainer(
        duration: AnimDurations.medium,
        curve: Curves.easeInOut,
        width: width,
        height: height,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(height / 2),
          color: value ? active : inactive,
        ),
        child: AnimatedAlign(
          duration: AnimDurations.medium,
          curve: Curves.easeInOut,
          alignment: value ? AlignmentDirectional.centerEnd : AlignmentDirectional.centerStart,
          child: Container(
            width: thumbSize,
            height: thumbSize,
            margin: const EdgeInsets.all(2),
            decoration: BoxDecoration(shape: BoxShape.circle, color: theme.colorScheme.onPrimary),
          ),
        ),
      ),
    );
  }
}
