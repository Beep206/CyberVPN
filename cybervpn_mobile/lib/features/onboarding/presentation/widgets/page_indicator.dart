import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// A row of animated dots indicating the current page in a page-based flow.
///
/// The active dot is wider and uses [ColorScheme.primary]; inactive dots are
/// smaller circles with reduced opacity.
class PageIndicator extends StatelessWidget {
  const PageIndicator({
    super.key,
    required this.pageCount,
    required this.currentPage,
  });

  /// Total number of pages.
  final int pageCount;

  /// Zero-based index of the currently active page.
  final int currentPage;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(pageCount, (index) {
        final isActive = index == currentPage;
        return AnimatedContainer(
          duration: AnimDurations.normal,
          curve: Curves.easeInOut,
          margin: const EdgeInsets.symmetric(horizontal: 4),
          width: isActive ? 24 : 8,
          height: 8,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(4),
            color: isActive
                ? colorScheme.primary
                : colorScheme.onSurface.withAlpha(60),
          ),
        );
      }),
    );
  }
}
