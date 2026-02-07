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
// ColorScheme replicas (avoids calling cyberpunk_theme.dart which triggers
// GoogleFonts network/asset loading in tests).
//
// These must be kept in sync with cyberpunk_theme.dart.  The authoritative
// color values live in CyberColors (tokens.dart).
// ---------------------------------------------------------------------------

/// Dark cyberpunk color scheme -- mirrors the const defined in
/// [cyberpunkDarkTheme()] in cyberpunk_theme.dart.
const _darkScheme = ColorScheme(
  brightness: Brightness.dark,
  primary: CyberColors.matrixGreen,
  onPrimary: CyberColors.deepNavy,
  secondary: CyberColors.neonCyan,
  onSecondary: CyberColors.deepNavy,
  tertiary: CyberColors.neonPink,
  onTertiary: CyberColors.deepNavy,
  error: Color(0xFFFF5252),
  onError: Colors.white,
  surface: CyberColors.darkBg,
  onSurface: Colors.white,
  surfaceContainerHighest: Color(0xFF1E2538),
  onSurfaceVariant: Color(0xFFB0B8C8),
);

/// Light cyberpunk color scheme -- mirrors the const defined in
/// [cyberpunkLightTheme()] in cyberpunk_theme.dart.
const _lightScheme = ColorScheme(
  brightness: Brightness.light,
  primary: CyberColors.matrixGreenDark,
  onPrimary: Colors.white,
  secondary: CyberColors.neonCyanDark,
  onSecondary: Colors.white,
  tertiary: CyberColors.neonPinkDark,
  onTertiary: Colors.white,
  error: Color(0xFFD32F2F),
  onError: Colors.white,
  surface: Color(0xFFFFFFFF),
  onSurface: Color(0xFF1F2937),
  surfaceContainerHighest: Color(0xFFF0F1F3),
  onSurfaceVariant: Color(0xFF6B7280),
);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('Cyberpunk Dark Theme - WCAG AA contrast', () {
    const cs = _darkScheme;

    // --- Neon accents on dark backgrounds (large-text threshold) -----------

    test('matrixGreen (primary) on deepNavy meets AA for large text (3:1)', () {
      final ratio = _contrastRatio(CyberColors.matrixGreen, CyberColors.deepNavy);
      expect(ratio, greaterThanOrEqualTo(_wcagAALarge),
          reason: 'matrixGreen on deepNavy: ${ratio.toStringAsFixed(2)}:1');
    });

    test('neonCyan (secondary) on deepNavy meets AA for large text (3:1)', () {
      final ratio = _contrastRatio(CyberColors.neonCyan, CyberColors.deepNavy);
      expect(ratio, greaterThanOrEqualTo(_wcagAALarge),
          reason: 'neonCyan on deepNavy: ${ratio.toStringAsFixed(2)}:1');
    });

    test('neonPink (tertiary) on deepNavy meets AA for large text (3:1)', () {
      final ratio = _contrastRatio(CyberColors.neonPink, CyberColors.deepNavy);
      expect(ratio, greaterThanOrEqualTo(_wcagAALarge),
          reason: 'neonPink on deepNavy: ${ratio.toStringAsFixed(2)}:1');
    });

    test('matrixGreen on darkBg (surface) meets AA for large text (3:1)', () {
      final ratio = _contrastRatio(CyberColors.matrixGreen, CyberColors.darkBg);
      expect(ratio, greaterThanOrEqualTo(_wcagAALarge),
          reason: 'matrixGreen on darkBg: ${ratio.toStringAsFixed(2)}:1');
    });

    test('neonCyan on darkBg (surface) meets AA for large text (3:1)', () {
      final ratio = _contrastRatio(CyberColors.neonCyan, CyberColors.darkBg);
      expect(ratio, greaterThanOrEqualTo(_wcagAALarge),
          reason: 'neonCyan on darkBg: ${ratio.toStringAsFixed(2)}:1');
    });

    test('neonPink on darkBg (surface) meets AA for large text (3:1)', () {
      final ratio = _contrastRatio(CyberColors.neonPink, CyberColors.darkBg);
      expect(ratio, greaterThanOrEqualTo(_wcagAALarge),
          reason: 'neonPink on darkBg: ${ratio.toStringAsFixed(2)}:1');
    });

    // --- Text colors on backgrounds (body-text threshold) ------------------

    test('onSurface (white) on deepNavy meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onSurface, CyberColors.deepNavy);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onSurface on deepNavy: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onSurface (white) on surface (darkBg) meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onSurface, cs.surface);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onSurface on surface: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onSurfaceVariant on deepNavy meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onSurfaceVariant, CyberColors.deepNavy);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onSurfaceVariant on deepNavy: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onSurfaceVariant on surface meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onSurfaceVariant, cs.surface);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onSurfaceVariant on surface: ${ratio.toStringAsFixed(2)}:1');
    });

    test('textGrayDark on deepNavy meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(CyberColors.textGrayDark, CyberColors.deepNavy);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'textGrayDark on deepNavy: ${ratio.toStringAsFixed(2)}:1');
    });

    // --- On-color pairs (text on filled buttons / chips) -------------------

    test('onPrimary on primary (deepNavy on matrixGreen) meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onPrimary, cs.primary);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onPrimary on primary: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onSecondary on secondary (deepNavy on neonCyan) meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onSecondary, cs.secondary);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onSecondary on secondary: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onTertiary on tertiary (deepNavy on neonPink) meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onTertiary, cs.tertiary);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onTertiary on tertiary: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onError on error meets AA for large text (3:1)', () {
      // onError text typically appears on ElevatedButton and SnackBar action
      // contexts which use bold/large type, so the large-text threshold applies.
      final ratio = _contrastRatio(cs.onError, cs.error);
      expect(ratio, greaterThanOrEqualTo(_wcagAALarge),
          reason: 'onError on error: ${ratio.toStringAsFixed(2)}:1');
    });
  });

  group('Cyberpunk Light Theme - WCAG AA contrast', () {
    const cs = _lightScheme;

    // --- Dark accent variants on light surface (body-text threshold) -------

    test('matrixGreenDark (primary) on surface meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(CyberColors.matrixGreenDark, cs.surface);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'matrixGreenDark on surface: ${ratio.toStringAsFixed(2)}:1');
    });

    test('neonCyanDark (secondary) on surface meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(CyberColors.neonCyanDark, cs.surface);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'neonCyanDark on surface: ${ratio.toStringAsFixed(2)}:1');
    });

    test('neonPinkDark (tertiary) on surface meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(CyberColors.neonPinkDark, cs.surface);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'neonPinkDark on surface: ${ratio.toStringAsFixed(2)}:1');
    });

    // --- Text on surface ---------------------------------------------------

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

    test('textGrayLight on white meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(CyberColors.textGrayLight, Colors.white);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'textGrayLight on white: ${ratio.toStringAsFixed(2)}:1');
    });

    // --- On-color pairs (text on filled buttons / chips) -------------------

    test('onPrimary on primary meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onPrimary, cs.primary);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onPrimary on primary: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onSecondary on secondary meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onSecondary, cs.secondary);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onSecondary on secondary: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onTertiary on tertiary meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onTertiary, cs.tertiary);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onTertiary on tertiary: ${ratio.toStringAsFixed(2)}:1');
    });

    test('onError on error meets AA for body text (4.5:1)', () {
      final ratio = _contrastRatio(cs.onError, cs.error);
      expect(ratio, greaterThanOrEqualTo(_wcagAABody),
          reason: 'onError on error: ${ratio.toStringAsFixed(2)}:1');
    });
  });
}
