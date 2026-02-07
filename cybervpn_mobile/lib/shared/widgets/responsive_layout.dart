import 'package:flutter/material.dart';

/// Breakpoints for responsive layouts.
class Breakpoints {
  const Breakpoints._();

  /// Phone max width.
  static const double phone = 600;

  /// Tablet max width.
  static const double tablet = 1024;

  /// Material 3 compact window class upper bound (exclusive).
  ///
  /// Compact: width < 600dp.
  static const double compact = 600;

  /// Material 3 medium window class upper bound (exclusive).
  ///
  /// Medium: 600dp <= width < 840dp.
  static const double medium = 840;

  // Expanded: width >= 840dp (no upper constant needed).
}

/// Material 3 window size class.
///
/// See https://m3.material.io/foundations/layout/applying-layout/window-size-classes
enum WindowSizeClass {
  /// Width < 600dp. Phones in portrait and small foldables.
  compact,

  /// 600dp <= width < 840dp. Small tablets, foldables, large phones in landscape.
  medium,

  /// Width >= 840dp. Large tablets, desktops, foldables in landscape.
  expanded,
}

/// A responsive layout builder that selects between phone and tablet layouts
/// based on screen width.
///
/// Usage:
/// ```dart
/// ResponsiveLayout(
///   phone: (context) => PhoneLayout(),
///   tablet: (context) => TabletLayout(),
/// )
/// ```
class ResponsiveLayout extends StatelessWidget {
  final Widget Function(BuildContext context) phone;
  final Widget Function(BuildContext context)? tablet;

  const ResponsiveLayout({
    required this.phone,
    this.tablet,
    super.key,
  });

  /// Returns the [WindowSizeClass] for the given [width] in logical pixels.
  static WindowSizeClass windowSizeClass(double width) {
    if (width >= Breakpoints.medium) return WindowSizeClass.expanded;
    if (width >= Breakpoints.compact) return WindowSizeClass.medium;
    return WindowSizeClass.compact;
  }

  /// Returns the [WindowSizeClass] based on the current screen width
  /// from [MediaQuery].
  static WindowSizeClass windowSizeClassOf(BuildContext context) {
    return windowSizeClass(MediaQuery.sizeOf(context).width);
  }

  /// Returns the number of grid columns appropriate for the given [width].
  ///
  /// Compact: 2, Medium: 3, Expanded: 4.
  static int adaptiveGridColumns(double width) {
    return switch (windowSizeClass(width)) {
      WindowSizeClass.compact => 2,
      WindowSizeClass.medium => 3,
      WindowSizeClass.expanded => 4,
    };
  }

  /// Returns the number of grid columns for the current screen width.
  static int gridColumns(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    if (width >= Breakpoints.tablet) return 3;
    if (width >= Breakpoints.phone) return 2;
    return 1;
  }

  /// Whether the current screen is at least tablet-sized (>= 600dp).
  static bool isTablet(BuildContext context) =>
      MediaQuery.sizeOf(context).width >= Breakpoints.phone;

  /// Whether the given [width] is at least medium (>= 600dp).
  static bool isAtLeastMedium(double width) =>
      width >= Breakpoints.compact;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    if (width >= Breakpoints.phone && tablet != null) {
      return tablet!(context);
    }
    return phone(context);
  }
}
