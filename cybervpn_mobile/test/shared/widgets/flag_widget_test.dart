import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/constants/flag_assets.dart';
import 'package:cybervpn_mobile/shared/widgets/flag_widget.dart';

void main() {
  group('FlagWidget', () {
    testWidgets('renders FlagWidget with valid country code', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: FlagWidget(
              countryCode: 'US',
              size: FlagSize.medium,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify the widget builds without errors
      expect(find.byType(FlagWidget), findsOneWidget);
    });

    testWidgets('renders placeholder for invalid country code', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: FlagWidget(
              countryCode: 'XX',
              size: FlagSize.medium,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should render placeholder with country code text
      expect(find.text('XX'), findsOneWidget);
      expect(find.byType(Container), findsWidgets);
    });

    testWidgets('uses correct size from FlagSize enum', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: FlagWidget(
              countryCode: 'US',
              size: FlagSize.large,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Find the SizedBox that wraps the flag
      final sizedBox = tester.widget<SizedBox>(
        find.descendant(
          of: find.byType(FlagWidget),
          matching: find.byType(SizedBox),
        ).first,
      );

      expect(sizedBox.width, equals(FlagSize.large.dimension));
      expect(sizedBox.height, equals(FlagSize.large.dimension));
    });

    testWidgets('renders custom placeholder when provided', (tester) async {
      const customPlaceholder = Icon(Icons.flag, key: Key('custom-placeholder'));

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: FlagWidget(
              countryCode: 'XX',
              size: FlagSize.medium,
              placeholder: customPlaceholder,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should render custom placeholder
      expect(find.byKey(const Key('custom-placeholder')), findsOneWidget);
    });

    testWidgets('handles case-insensitive country codes', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                FlagWidget(countryCode: 'us', size: FlagSize.small),
                FlagWidget(countryCode: 'US', size: FlagSize.small),
                FlagWidget(countryCode: 'Us', size: FlagSize.small),
              ],
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // All three should render without errors
      expect(find.byType(FlagWidget), findsNWidgets(3));
    });
  });

  group('FlagAssets', () {
    test('getFlag returns correct path for valid country codes', () {
      expect(FlagAssets.getFlag('US'), isNotNull);
      expect(FlagAssets.getFlag('US'), contains('us.svg'));
      expect(FlagAssets.getFlag('DE'), contains('de.svg'));
      expect(FlagAssets.getFlag('JP'), contains('jp.svg'));
    });

    test('getFlag returns null for invalid country codes', () {
      expect(FlagAssets.getFlag('XX'), isNull);
      expect(FlagAssets.getFlag('ZZ'), isNull);
      expect(FlagAssets.getFlag(''), isNull);
    });

    test('getFlag handles case-insensitive input', () {
      expect(FlagAssets.getFlag('us'), equals(FlagAssets.getFlag('US')));
      expect(FlagAssets.getFlag('de'), equals(FlagAssets.getFlag('DE')));
    });

    test('hasFlag returns correct boolean', () {
      expect(FlagAssets.hasFlag('US'), isTrue);
      expect(FlagAssets.hasFlag('DE'), isTrue);
      expect(FlagAssets.hasFlag('XX'), isFalse);
      expect(FlagAssets.hasFlag(''), isFalse);
    });

    test('availableCodes returns list of country codes', () {
      final codes = FlagAssets.availableCodes;
      expect(codes, isNotEmpty);
      expect(codes, contains('US'));
      expect(codes, contains('DE'));
      expect(codes, contains('JP'));
    });

    test('count returns correct number of flags', () {
      expect(FlagAssets.count, greaterThan(0));
      expect(FlagAssets.count, equals(19)); // We added 19 flags
    });
  });

  group('FlagSize', () {
    test('enum has correct dimension values', () {
      expect(FlagSize.small.dimension, equals(20.0));
      expect(FlagSize.medium.dimension, equals(28.0));
      expect(FlagSize.large.dimension, equals(40.0));
      expect(FlagSize.extraLarge.dimension, equals(56.0));
    });
  });
}
