import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

void main() {
  // ── CyberColors ──────────────────────────────────────────────────────

  group('CyberColors', () {
    test('matrixGreen is #00FF88', () {
      expect(CyberColors.matrixGreen, const Color(0xFF00FF88));
    });

    test('neonCyan is #00FFFF', () {
      expect(CyberColors.neonCyan, const Color(0xFF00FFFF));
    });

    test('neonPink is #FF00FF', () {
      expect(CyberColors.neonPink, const Color(0xFFFF00FF));
    });

    test('deepNavy is #0A0E1A', () {
      expect(CyberColors.deepNavy, const Color(0xFF0A0E1A));
    });

    test('darkBg is #111827', () {
      expect(CyberColors.darkBg, const Color(0xFF111827));
    });
  });

  // ── MaterialColors ───────────────────────────────────────────────────

  group('MaterialColors', () {
    test('seed is teal #00BFA5', () {
      expect(MaterialColors.seed, const Color(0xFF00BFA5));
    });
  });

  // ── Spacing ──────────────────────────────────────────────────────────

  group('Spacing', () {
    test('xs is 4.0', () => expect(Spacing.xs, 4.0));
    test('sm is 8.0', () => expect(Spacing.sm, 8.0));
    test('md is 16.0', () => expect(Spacing.md, 16.0));
    test('lg is 24.0', () => expect(Spacing.lg, 24.0));
    test('xl is 32.0', () => expect(Spacing.xl, 32.0));
  });

  // ── Radii ────────────────────────────────────────────────────────────

  group('Radii', () {
    test('sm is 8.0', () => expect(Radii.sm, 8.0));
    test('md is 12.0', () => expect(Radii.md, 12.0));
    test('lg is 16.0', () => expect(Radii.lg, 16.0));
    test('xl is 24.0', () => expect(Radii.xl, 24.0));
  });

  // ── Elevation ────────────────────────────────────────────────────────

  group('Elevation', () {
    test('none is 0.0', () => expect(Elevation.none, 0.0));
    test('low is 1.0', () => expect(Elevation.low, 1.0));
    test('medium is 2.0', () => expect(Elevation.medium, 2.0));
    test('high is 4.0', () => expect(Elevation.high, 4.0));
  });

  // ── AnimDurations ────────────────────────────────────────────────────

  group('AnimDurations', () {
    test('fast is 150ms', () {
      expect(AnimDurations.fast, const Duration(milliseconds: 150));
    });

    test('normal is 300ms', () {
      expect(AnimDurations.normal, const Duration(milliseconds: 300));
    });

    test('slow is 500ms', () {
      expect(AnimDurations.slow, const Duration(milliseconds: 500));
    });
  });

  // ── AppTypography ────────────────────────────────────────────────────

  group('AppTypography', () {
    test('heading returns correct TextStyle', () {
      final style = AppTypography.heading(fontFamily: 'Orbitron');
      expect(style.fontFamily, 'Orbitron');
      expect(style.fontSize, 24);
      expect(style.fontWeight, FontWeight.w700);
      expect(style.letterSpacing, 1.2);
    });

    test('body returns correct TextStyle', () {
      final style = AppTypography.body(fontFamily: 'Roboto');
      expect(style.fontFamily, 'Roboto');
      expect(style.fontSize, 16);
      expect(style.fontWeight, FontWeight.w400);
      expect(style.letterSpacing, 0.5);
    });

    test('label returns correct TextStyle', () {
      final style = AppTypography.label(fontFamily: 'Roboto');
      expect(style.fontFamily, 'Roboto');
      expect(style.fontSize, 12);
      expect(style.fontWeight, FontWeight.w500);
      expect(style.letterSpacing, 0.8);
    });

    test('data returns correct TextStyle', () {
      final style = AppTypography.data(fontFamily: 'JetBrains Mono');
      expect(style.fontFamily, 'JetBrains Mono');
      expect(style.fontSize, 14);
      expect(style.fontWeight, FontWeight.w400);
      expect(style.letterSpacing, 1.0);
    });

    test('heading accepts different font families', () {
      final cyber = AppTypography.heading(fontFamily: 'Orbitron');
      final material = AppTypography.heading(fontFamily: 'Roboto');
      expect(cyber.fontFamily, 'Orbitron');
      expect(material.fontFamily, 'Roboto');
      // All other properties should remain identical.
      expect(cyber.fontSize, material.fontSize);
      expect(cyber.fontWeight, material.fontWeight);
      expect(cyber.letterSpacing, material.letterSpacing);
    });
  });
}
