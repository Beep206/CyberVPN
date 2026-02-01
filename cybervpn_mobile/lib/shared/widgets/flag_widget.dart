import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import 'package:cybervpn_mobile/core/constants/flag_assets.dart';

/// A widget that displays a country flag based on ISO 3166-1 alpha-2 code.
///
/// Uses SVG flag assets from circle-flags for optimal size and quality.
/// Includes error handling and a fallback placeholder for missing flags.
///
/// Example:
/// ```dart
/// FlagWidget(
///   countryCode: 'US',
///   size: FlagSize.medium,
/// )
/// ```
class FlagWidget extends StatelessWidget {
  const FlagWidget({
    super.key,
    required this.countryCode,
    this.size = FlagSize.medium,
    this.placeholder,
  });

  /// ISO 3166-1 alpha-2 country code (e.g., 'US', 'DE').
  final String countryCode;

  /// Size preset for the flag.
  final FlagSize size;

  /// Optional custom placeholder widget when flag is not found.
  /// Defaults to a circle with country code text.
  final Widget? placeholder;

  @override
  Widget build(BuildContext context) {
    final flagPath = FlagAssets.getFlag(countryCode);
    final dimension = size.dimension;

    if (flagPath == null) {
      return _buildPlaceholder(context, dimension);
    }

    return RepaintBoundary(
      child: SizedBox(
        width: dimension,
        height: dimension,
        child: SvgPicture.asset(
          flagPath,
          width: dimension,
          height: dimension,
          fit: BoxFit.cover,
          placeholderBuilder: (BuildContext context) => _buildPlaceholder(
            context,
            dimension,
          ),
        ),
      ),
    );
  }

  Widget _buildPlaceholder(BuildContext context, double dimension) {
    if (placeholder != null) return placeholder!;

    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Container(
      width: dimension,
      height: dimension,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: colorScheme.surfaceContainerHighest,
        border: Border.all(
          color: colorScheme.outline.withValues(alpha: 0.2),
          width: 1,
        ),
      ),
      child: Center(
        child: Text(
          countryCode.toUpperCase(),
          style: theme.textTheme.labelSmall?.copyWith(
            color: colorScheme.onSurfaceVariant,
            fontWeight: FontWeight.w600,
            fontSize: dimension * 0.25,
          ),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}

/// Predefined flag size presets.
enum FlagSize {
  /// Small flag (20x20 logical pixels).
  small(20.0),

  /// Medium flag (28x28 logical pixels).
  medium(28.0),

  /// Large flag (40x40 logical pixels).
  large(40.0),

  /// Extra large flag (56x56 logical pixels).
  extraLarge(56.0);

  const FlagSize(this.dimension);

  /// Dimension (width and height) in logical pixels.
  final double dimension;
}
