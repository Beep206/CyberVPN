import 'package:flutter/material.dart';

/// Breakpoints for responsive layouts.
class Breakpoints {
  const Breakpoints._();

  /// Phone max width.
  static const double phone = 600;

  /// Tablet max width.
  static const double tablet = 1024;
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

  /// Returns the number of grid columns for the current screen width.
  static int gridColumns(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    if (width >= Breakpoints.tablet) return 3;
    if (width >= Breakpoints.phone) return 2;
    return 1;
  }

  /// Whether the current screen is at least tablet-sized.
  static bool isTablet(BuildContext context) =>
      MediaQuery.sizeOf(context).width >= Breakpoints.phone;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    if (width >= Breakpoints.phone && tablet != null) {
      return tablet!(context);
    }
    return phone(context);
  }
}
