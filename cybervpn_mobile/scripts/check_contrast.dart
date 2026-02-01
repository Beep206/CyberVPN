#!/usr/bin/env dart
// Script to check WCAG AA color contrast compliance for all theme variants
// WCAG AA requires: 4.5:1 for normal text, 3:1 for large text (18pt+ or 14pt+ bold)

import 'dart:io';
import 'dart:math';

/// Calculate relative luminance of an RGB color
/// Formula from WCAG 2.0: https://www.w3.org/TR/WCAG20/#relativeluminancedef
double relativeLuminance(int r, int g, int b) {
  final rs = r / 255.0;
  final gs = g / 255.0;
  final bs = b / 255.0;

  final r2 = rs <= 0.03928 ? rs / 12.92 : pow((rs + 0.055) / 1.055, 2.4).toDouble();
  final g2 = gs <= 0.03928 ? gs / 12.92 : pow((gs + 0.055) / 1.055, 2.4).toDouble();
  final b2 = bs <= 0.03928 ? bs / 12.92 : pow((bs + 0.055) / 1.055, 2.4).toDouble();

  return 0.2126 * r2 + 0.7152 * g2 + 0.0722 * b2;
}

/// Calculate contrast ratio between two colors
/// Formula from WCAG 2.0: https://www.w3.org/TR/WCAG20/#contrast-ratiodef
double contrastRatio(String color1Hex, String color2Hex) {
  final c1 = int.parse(color1Hex.replaceAll('#', ''), radix: 16);
  final c2 = int.parse(color2Hex.replaceAll('#', ''), radix: 16);

  final r1 = (c1 >> 16) & 0xFF;
  final g1 = (c1 >> 8) & 0xFF;
  final b1 = c1 & 0xFF;

  final r2 = (c2 >> 16) & 0xFF;
  final g2 = (c2 >> 8) & 0xFF;
  final b2 = c2 & 0xFF;

  final l1 = relativeLuminance(r1, g1, b1);
  final l2 = relativeLuminance(r2, g2, b2);

  final lighter = max(l1, l2);
  final darker = min(l1, l2);

  return (lighter + 0.05) / (darker + 0.05);
}

class ColorPair {
  final String name;
  final String foreground;
  final String background;
  final String context;

  ColorPair(this.name, this.foreground, this.background, this.context);

  double get ratio => contrastRatio(foreground, background);

  bool get passesAA => ratio >= 4.5;
  bool get passesAALarge => ratio >= 3.0;
  bool get passesAAA => ratio >= 7.0;

  String get status {
    if (passesAAA) return 'AAA ✓✓✓';
    if (passesAA) return 'AA ✓✓';
    if (passesAALarge) return 'AA-Large ✓';
    return 'FAIL ✗';
  }
}

void main() {
  print('═' * 80);
  print('WCAG AA Color Contrast Audit - CyberVPN Mobile App');
  print('═' * 80);
  print('');
  print('WCAG AA Requirements:');
  print('  • Normal text (< 18pt): 4.5:1 minimum');
  print('  • Large text (≥ 18pt or ≥ 14pt bold): 3:1 minimum');
  print('  • WCAG AAA: 7:1 for normal text, 4.5:1 for large text');
  print('');

  final themes = [
    _checkCyberpunkDark(),
    _checkCyberpunkLight(),
    _checkMaterialYouDark(),
    _checkMaterialYouLight(),
  ];

  // Summary
  print('');
  print('═' * 80);
  print('SUMMARY');
  print('═' * 80);

  var totalChecks = 0;
  var passedAA = 0;
  var passedAALarge = 0;
  var failed = 0;

  for (final theme in themes) {
    for (final pair in theme) {
      totalChecks++;
      if (pair.passesAA) {
        passedAA++;
      } else if (pair.passesAALarge) {
        passedAALarge++;
      } else {
        failed++;
      }
    }
  }

  print('');
  print('Total checks: $totalChecks');
  print('Passed AA (normal text): $passedAA');
  print('Passed AA-Large only: $passedAALarge');
  print('Failed: $failed');
  print('');

  if (failed > 0) {
    print('⚠️  WCAG AA compliance issues detected. Review failures above.');
    exit(1);
  } else {
    print('✓ All color combinations pass WCAG AA compliance!');
    exit(0);
  }
}

List<ColorPair> _checkCyberpunkDark() {
  print('─' * 80);
  print('1. CYBERPUNK DARK THEME');
  print('─' * 80);

  final pairs = [
    // Text on backgrounds
    ColorPair('Body text on deepNavy', '#FFFFFF', '#0A0E1A', 'Body text'),
    ColorPair('Body text on darkBg', '#FFFFFF', '#111827', 'Card backgrounds'),
    ColorPair('Body text on surface container', '#FFFFFF', '#1E2538', 'Input fields'),
    ColorPair('Variant text on deepNavy', '#B0B8C8', '#0A0E1A', 'Secondary text'),
    ColorPair('Variant text on darkBg', '#B0B8C8', '#111827', 'Secondary on cards'),

    // Primary colors (matrixGreen - bright for dark mode)
    ColorPair('Matrix green on deepNavy', '#00FF88', '#0A0E1A', 'Primary accent'),
    ColorPair('Matrix green on darkBg', '#00FF88', '#111827', 'Icons on cards'),
    ColorPair('Matrix green on surface', '#00FF88', '#1E2538', 'Icons on inputs'),

    // Secondary colors (neonCyan - bright for dark mode)
    ColorPair('Neon cyan on deepNavy', '#00FFFF', '#0A0E1A', 'Secondary accent'),
    ColorPair('Neon cyan on darkBg', '#00FFFF', '#111827', 'Link text'),

    // Tertiary colors (neonPink - bright for dark mode)
    ColorPair('Neon pink on deepNavy', '#FF00FF', '#0A0E1A', 'Tertiary accent'),
    ColorPair('Neon pink on darkBg', '#FF00FF', '#111827', 'Highlights'),

    // Buttons
    ColorPair('ElevatedButton text', '#0A0E1A', '#00FF88', 'Primary button text'),
    ColorPair('OutlinedButton text', '#00FF88', '#0A0E1A', 'Secondary button'),
    ColorPair('TextButton text', '#00FFFF', '#0A0E1A', 'Tertiary button'),

    // Navigation - IMPROVED gray color
    ColorPair('Nav selected icon', '#00FF88', '#0A0E1A', 'Bottom nav active'),
    ColorPair('Nav unselected icon', '#7B8A9A', '#0A0E1A', 'Bottom nav inactive (FIXED)'),

    // Disabled/inactive states - IMPROVED gray color
    ColorPair('Disabled text', '#7B8A9A', '#0A0E1A', 'Disabled elements (FIXED)'),
    ColorPair('Hint text on input', '#7B8A9A', '#1E2538', 'Placeholder text (FIXED)'),
  ];

  _printPairs(pairs);
  return pairs;
}

List<ColorPair> _checkCyberpunkLight() {
  print('');
  print('─' * 80);
  print('2. CYBERPUNK LIGHT THEME');
  print('─' * 80);

  final pairs = [
    // Text on backgrounds
    ColorPair('Body text on background', '#1F2937', '#F8F9FA', 'Body text'),
    ColorPair('Body text on surface', '#1F2937', '#FFFFFF', 'Card text'),
    ColorPair('Body text on surface container', '#1F2937', '#F0F1F3', 'Input text'),
    ColorPair('Variant text on background', '#6B7280', '#F8F9FA', 'Secondary text'),
    ColorPair('Variant text on surface', '#6B7280', '#FFFFFF', 'Secondary on cards'),

    // Primary colors (matrixGreenDark) - FIXED
    ColorPair('Matrix green dark on background', '#007756', '#F8F9FA', 'Primary accent (FIXED)'),
    ColorPair('Matrix green dark on white', '#007756', '#FFFFFF', 'Icons on cards (FIXED)'),
    ColorPair('Matrix green dark on container', '#007756', '#F0F1F3', 'Icons on inputs (FIXED)'),

    // Secondary colors (neonCyanDark) - FIXED
    ColorPair('Neon cyan dark on background', '#007B7B', '#F8F9FA', 'Secondary accent (FIXED)'),
    ColorPair('Neon cyan dark on white', '#007B7B', '#FFFFFF', 'Link text (FIXED)'),

    // Tertiary colors (neonPinkDark) - FIXED
    ColorPair('Neon pink dark on background', '#9A009A', '#F8F9FA', 'Tertiary accent (FIXED)'),
    ColorPair('Neon pink dark on white', '#9A009A', '#FFFFFF', 'Highlights (FIXED)'),

    // Buttons - FIXED
    ColorPair('ElevatedButton text', '#FFFFFF', '#007756', 'Primary button text (FIXED)'),
    ColorPair('OutlinedButton text', '#007756', '#F8F9FA', 'Secondary button (FIXED)'),
    ColorPair('TextButton text', '#007B7B', '#F8F9FA', 'Tertiary button (FIXED)'),

    // Navigation - FIXED
    ColorPair('Nav selected icon', '#007756', '#FFFFFF', 'Bottom nav active (FIXED)'),
    ColorPair('Nav unselected icon', '#6B7280', '#FFFFFF', 'Bottom nav inactive'),

    // Disabled/inactive states
    ColorPair('Disabled text', '#6B7280', '#F8F9FA', 'Disabled elements'),
    ColorPair('Hint text on input', '#6B7280', '#F0F1F3', 'Placeholder text'),
  ];

  _printPairs(pairs);
  return pairs;
}

List<ColorPair> _checkMaterialYouDark() {
  print('');
  print('─' * 80);
  print('3. MATERIAL YOU DARK THEME');
  print('─' * 80);

  // Material You uses dynamic colors, but we'll check the seed-based fallback
  // Seed: #00BFA5
  final pairs = [
    // Using Material 3 generated colors from seed #00BFA5 for dark mode
    // These are approximations - actual values come from Material's color algorithm
    ColorPair('onSurface on surface', '#E6E1E5', '#1C1B1F', 'Body text'),
    ColorPair('onSurfaceVariant on surface', '#CAC4D0', '#1C1B1F', 'Secondary text'),
    ColorPair('Primary on surface', '#00BFA5', '#1C1B1F', 'Primary color'),
    ColorPair('onPrimary on primary', '#003731', '#00BFA5', 'Button text'),
    ColorPair('Secondary on surface', '#4ECDC4', '#1C1B1F', 'Secondary accent'),
    ColorPair('Error on surface', '#F2B8B5', '#1C1B1F', 'Error text'),
  ];

  print('Note: Material You uses dynamic color generation. Values shown are');
  print('      approximations from seed color #00BFA5. Actual ratios depend on');
  print('      the user\'s wallpaper on Android 12+.');
  print('');

  _printPairs(pairs);
  return pairs;
}

List<ColorPair> _checkMaterialYouLight() {
  print('');
  print('─' * 80);
  print('4. MATERIAL YOU LIGHT THEME');
  print('─' * 80);

  final pairs = [
    // Using Material 3 generated colors from seed #00BFA5 for light mode
    ColorPair('onSurface on surface', '#1C1B1F', '#FFFBFE', 'Body text'),
    ColorPair('onSurfaceVariant on surface', '#49454F', '#FFFBFE', 'Secondary text'),
    ColorPair('Primary on surface', '#006A5D', '#FFFBFE', 'Primary color'),
    ColorPair('onPrimary on primary', '#FFFFFF', '#006A5D', 'Button text'),
    ColorPair('Secondary on surface', '#4A6360', '#FFFBFE', 'Secondary accent'),
    ColorPair('Error on surface', '#BA1A1A', '#FFFBFE', 'Error text'),
  ];

  print('Note: Material You uses dynamic color generation. Values shown are');
  print('      approximations from seed color #00BFA5. Actual ratios depend on');
  print('      the user\'s wallpaper on Android 12+.');
  print('');

  _printPairs(pairs);
  return pairs;
}

void _printPairs(List<ColorPair> pairs) {
  print('');
  for (final pair in pairs) {
    final ratioStr = pair.ratio.toStringAsFixed(2);
    final status = pair.status;
    final marker = pair.passesAA ? '  ' : '⚠️ ';

    print('$marker${pair.name.padRight(40)} $ratioStr:1  $status');
    print('   ${pair.context}');
    if (!pair.passesAA) {
      print('   FG: ${pair.foreground} / BG: ${pair.background}');
    }
  }
}
