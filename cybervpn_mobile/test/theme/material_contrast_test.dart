import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

// ---------------------------------------------------------------------------
// WCAG 2.1 contrast helpers
// ---------------------------------------------------------------------------

/// WCAG AA minimum contrast ratio for normal/body text (< 18pt).
const double _wcagAABody = 4.5;

/// WCAG AA minimum contrast ratio for large text (>= 18pt normal or >= 14pt bold).
const double _wcagAALarge = 3.0;

/// Computes the relative luminance of a [Color] per WCAG 2.1.
///
/// See https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
double _relativeLuminance(Color color) {
  double linearize(double sRGB) {
    return sRGB <= 0.04045
        ? sRGB / 12.92
        : math.pow((sRGB + 0.055) / 1.055, 2.4).toDouble();
  }

  final r = linearize(color.r);
  final g = linearize(color.g);
  final b = linearize(color.b);

  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/// Computes the WCAG 2.1 contrast ratio between [foreground] and [background].
///
/// Returns a value in the range [1.0, 21.0].
double _contrastRatio(Color foreground, Color background) {
  final lum1 = _relativeLuminance(foreground);
  final lum2 = _relativeLuminance(background);
  final lighter = math.max(lum1, lum2);
  final darker = math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Material You Light Theme - WCAG AA contrast', () {
    late ColorScheme cs;

    setUp(() {
      cs = ColorScheme.fromSeed(
        seedColor: MaterialColors.seed,
        brightness: Brightness.light,
      );
    });

    // --- Primary surface pairs ---------------------------------------------

    test('primary on surface meets AA for large text (3:1)', () {
      final ratio = _contrastRatio(cs.primary, cs.surface);
      expect(ratio, greaterThanOrEqualTo(_wcagAALarge),
          reason: 'primary on surface: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onPrimary on primary meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onPrimary, cs.primary);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onPrimary on primary: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onPrimaryContainer on primaryContainer meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onPrimaryContainer, cs.primaryContainer);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason:
              'onPrimaryContainer on primaryContainer: ${ratio.toStringAsFixed(2)}:1');
    });

    // --- Secondary surface pairs -------------------------------------------

    test('onSecondary on secondary meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onSecondary, cs.secondary);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onSecondary on secondary: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onSecondaryContainer on secondaryContainer meets AA for body text (4.5:1)', () {
      final ratio =
          _contrastRatio(cs.onSecondaryContainer, cs.secondaryContainer);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason:
              'onSecondaryContainer on secondaryContainer: ${ratio.toStringAsFixed(2)}:1');
    });

    // --- Tertiary surface pairs --------------------------------------------

    test('onTertiary on tertiary meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onTertiary, cs.tertiary);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onTertiary on tertiary: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onTertiaryContainer on tertiaryContainer meets AA for body text (4.5:1)', () {
      final ratio =
          _contrastRatio(cs.onTertiaryContainer, cs.tertiaryContainer);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason:
              'onTertiaryContainer on tertiaryContainer: ${ratio.toStringAsFixed(2)}:1');
    });

    // --- Error pairs -------------------------------------------------------

    test('onError on error meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onError, cs.error);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onError on error: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onErrorContainer on errorContainer meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onErrorContainer, cs.errorContainer);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason:
              'onErrorContainer on errorContainer: ${ratio.toStringAsFixed(2)}:1');
    });

    // --- Surface text pairs ------------------------------------------------

    test('onSurface on surface meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onSurface, cs.surface);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onSurface on surface: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onSurfaceVariant on surface meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onSurfaceVariant, cs.surface);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onSurfaceVariant on surface: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onSurface on surfaceContainerHighest meets AA for body text (4.5:1)', () {
      final ratio =
          _contrastRatio(cs.onSurface, cs.surfaceContainerHighest);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason:
              'onSurface on surfaceContainerHighest: ${ratio.toStringAsFixed(2)}:1');
    });
  });

  group('Material You Dark Theme - WCAG AA contrast', () {
    late ColorScheme cs;

    setUp(() {
      cs = ColorScheme.fromSeed(
        seedColor: MaterialColors.seed,
        brightness: Brightness.dark,
      );
    });

    // --- Primary surface pairs ---------------------------------------------

    test('primary on surface meets AA for large text (3:1)', () {
      final ratio = _contrastRatio(cs.primary, cs.surface);
      expect(ratio, greaterThanOrEqualTo(_wcagAALarge),
          reason: 'primary on surface: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onPrimary on primary meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onPrimary, cs.primary);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onPrimary on primary: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onPrimaryContainer on primaryContainer meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onPrimaryContainer, cs.primaryContainer);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason:
              'onPrimaryContainer on primaryContainer: ${ratio.toStringAsFixed(2)}:1');
    });

    // --- Secondary surface pairs -------------------------------------------

    test('onSecondary on secondary meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onSecondary, cs.secondary);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onSecondary on secondary: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onSecondaryContainer on secondaryContainer meets AA for body text (4.5:1)', () {
      final ratio =
          _contrastRatio(cs.onSecondaryContainer, cs.secondaryContainer);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason:
              'onSecondaryContainer on secondaryContainer: ${ratio.toStringAsFixed(2)}:1');
    });

    // --- Tertiary surface pairs --------------------------------------------

    test('onTertiary on tertiary meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onTertiary, cs.tertiary);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onTertiary on tertiary: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onTertiaryContainer on tertiaryContainer meets AA for body text (4.5:1)', () {
      final ratio =
          _contrastRatio(cs.onTertiaryContainer, cs.tertiaryContainer);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason:
              'onTertiaryContainer on tertiaryContainer: ${ratio.toStringAsFixed(2)}:1');
    });

    // --- Error pairs -------------------------------------------------------

    test('onError on error meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onError, cs.error);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onError on error: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onErrorContainer on errorContainer meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onErrorContainer, cs.errorContainer);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason:
              'onErrorContainer on errorContainer: ${ratio.toStringAsFixed(2)}:1');
    });

    // --- Surface text pairs ------------------------------------------------

    test('onSurface on surface meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onSurface, cs.surface);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onSurface on surface: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onSurfaceVariant on surface meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onSurfaceVariant, cs.surface);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onSurfaceVariant on surface: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onSurface on surfaceContainerHighest meets AA for body text (4.5:1)', () {
      final ratio =
          _contrastRatio(cs.onSurface, cs.surfaceContainerHighest);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason:
              'onSurface on surfaceContainerHighest: ${ratio.toStringAsFixed(2)}:1');
    });
  });
}
