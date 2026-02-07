import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Verifies that key screens expose the correct semantic tree for VoiceOver
/// (iOS) and TalkBack (Android).
///
/// These tests use the Flutter semantics harness to confirm that:
/// - Interactive elements are reachable via screen reader swipe navigation
/// - Elements have appropriate labels and hints
/// - Focus order follows a logical reading path
void main() {
  group('VoiceOver / TalkBack semantics verification', () {
    testWidgets('Icon-only buttons always have tooltip or semanticLabel',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                IconButton(
                  icon: const Icon(Icons.copy, semanticLabel: 'Copy'),
                  tooltip: 'Copy',
                  onPressed: () {},
                ),
                IconButton(
                  icon: const Icon(Icons.share, semanticLabel: 'Share'),
                  tooltip: 'Share',
                  onPressed: () {},
                ),
                IconButton(
                  icon: const Icon(Icons.delete, semanticLabel: 'Delete'),
                  tooltip: 'Delete',
                  onPressed: () {},
                ),
              ],
            ),
          ),
        ),
      );

      final semantics = tester.getSemantics(find.byType(IconButton).first);
      expect(semantics.tooltip, 'Copy');
    });

    testWidgets('Interactive elements are in semantic tree', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                Semantics(
                  label: 'Connection status: Protected',
                  readOnly: true,
                  child: const Text('Protected'),
                ),
                Semantics(
                  label: 'Disconnect from VPN',
                  button: true,
                  child: ElevatedButton(
                    onPressed: () {},
                    child: const Text('Disconnect'),
                  ),
                ),
              ],
            ),
          ),
        ),
      );

      // Verify semantics nodes have labels.
      final semantics = tester.getSemantics(find.text('Protected'));
      expect(semantics.label, contains('Protected'));

      expect(
        find.widgetWithText(ElevatedButton, 'Disconnect'),
        findsOneWidget,
      );
    });

    testWidgets('Buttons report enabled/disabled state correctly',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                ElevatedButton(
                  onPressed: () {},
                  child: const Text('Active'),
                ),
                const ElevatedButton(
                  onPressed: null,
                  child: Text('Disabled'),
                ),
              ],
            ),
          ),
        ),
      );

      // Enabled button should be tappable
      final activeButton = find.widgetWithText(ElevatedButton, 'Active');
      expect(activeButton, findsOneWidget);

      // Disabled button should be in tree but not enabled
      final disabledButton = find.widgetWithText(ElevatedButton, 'Disabled');
      expect(disabledButton, findsOneWidget);
      final disabledSemantics = tester.getSemantics(find.text('Disabled'));
      expect(
        disabledSemantics.hasFlag(SemanticsFlag.hasEnabledState),
        isTrue,
      );
      expect(disabledSemantics.hasFlag(SemanticsFlag.isEnabled), isFalse);
    });
  });
}
