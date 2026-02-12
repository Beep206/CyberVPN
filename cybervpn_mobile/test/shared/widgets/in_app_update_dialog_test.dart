import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/shared/services/version_service.dart';
import 'package:cybervpn_mobile/shared/widgets/in_app_update_dialog.dart';

void main() {
  late SharedPreferences prefs;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
  });

  group('InAppUpdateDialog - Mandatory mode', () {
    const mandatoryUpdate = UpdateStatus(
      needsUpdate: true,
      isMandatory: true,
      currentVersion: '1.0.0',
      latestVersion: '2.0.0',
    );

    testWidgets('renders without dismiss option and blocks interaction',
        (tester) async {
      bool updateCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: InAppUpdateDialog(
              updateInfo: mandatoryUpdate,
              onUpdate: () => updateCalled = true,
              prefs: prefs,
            ),
          ),
        ),
      );

      // Verify mandatory dialog elements
      expect(find.text('Update Required'), findsOneWidget);
      expect(find.text('Update Now'), findsOneWidget);
      expect(find.text('Later'), findsNothing);
      expect(find.text('Remind me in 3 days'), findsNothing);

      // Verify version info displayed
      expect(find.text('Current Version:'), findsOneWidget);
      expect(find.text('1.0.0'), findsOneWidget);
      expect(find.text('Latest Version:'), findsOneWidget);
      expect(find.text('2.0.0'), findsOneWidget);

      // Verify error color/icon for mandatory
      expect(find.byIcon(Icons.warning_rounded), findsOneWidget);

      // Verify "Update Now" button works
      await tester.tap(find.text('Update Now'));
      await tester.pumpAndSettle();
      expect(updateCalled, isTrue);
    });

    testWidgets('cannot be dismissed by tapping outside', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  await InAppUpdateDialog.show(
                    context: context,
                    updateInfo: mandatoryUpdate,
                    onUpdate: () {},
                    prefs: prefs,
                  );
                },
                child: const Text('Show Dialog'),
              ),
            ),
          ),
        ),
      );

      // Show dialog
      await tester.tap(find.text('Show Dialog'));
      await tester.pumpAndSettle();

      // Verify dialog is shown
      expect(find.text('Update Required'), findsOneWidget);

      // Try to dismiss by tapping barrier (should fail)
      await tester.tapAt(const Offset(10, 10));
      await tester.pumpAndSettle();

      // Dialog should still be visible
      expect(find.text('Update Required'), findsOneWidget);
    });

    testWidgets('blocks back button navigation', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () {
                  unawaited(showDialog<void>(
                    context: context,
                    barrierDismissible: false,
                    builder: (context) => InAppUpdateDialog(
                      updateInfo: mandatoryUpdate,
                      onUpdate: () {},
                      prefs: prefs,
                    ),
                  ));
                },
                child: const Text('Show Dialog'),
              ),
            ),
          ),
        ),
      );

      // Show dialog
      await tester.tap(find.text('Show Dialog'));
      await tester.pumpAndSettle();

      // Verify dialog is shown
      expect(find.text('Update Required'), findsOneWidget);

      // Try to pop dialog (should be blocked by PopScope with canPop: false)
      final NavigatorState navigator = tester.state(find.byType(Navigator));
      final bool didPop = await navigator.maybePop();

      // Pop should succeed in closing the dialog but the dialog blocks back button internally
      // The dialog should still be there because PopScope prevents it
      await tester.pumpAndSettle();
      expect(find.text('Update Required'), findsOneWidget);
    });
  });

  group('InAppUpdateDialog - Optional mode', () {
    const optionalUpdate = UpdateStatus(
      needsUpdate: true,
      isMandatory: false,
      currentVersion: '1.0.0',
      latestVersion: '1.1.0',
    );

    testWidgets('renders with dismiss option and snooze checkbox',
        (tester) async {
      bool updateCalled = false;
      bool dismissCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: InAppUpdateDialog(
              updateInfo: optionalUpdate,
              onUpdate: () => updateCalled = true,
              onDismiss: () => dismissCalled = true,
              prefs: prefs,
            ),
          ),
        ),
      );

      // Verify optional dialog elements
      expect(find.text('Update Available'), findsOneWidget);
      expect(find.text('Update Now'), findsOneWidget);
      expect(find.text('Later'), findsOneWidget);
      expect(find.text('Remind me in 3 days'), findsOneWidget);

      // Verify info icon for optional
      expect(find.byIcon(Icons.info_rounded), findsOneWidget);

      // Verify checkbox is unchecked by default
      final checkbox = tester.widget<CheckboxListTile>(
        find.byType(CheckboxListTile),
      );
      expect(checkbox.value, isFalse);
    });

    testWidgets('dismisses when "Later" is tapped', (tester) async {
      bool dismissCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => InAppUpdateDialog(
                updateInfo: optionalUpdate,
                onUpdate: () {},
                onDismiss: () => dismissCalled = true,
                prefs: prefs,
              ),
            ),
          ),
        ),
      );

      // Tap "Later"
      await tester.tap(find.text('Later'));
      await tester.pumpAndSettle();

      // Verify onDismiss called
      expect(dismissCalled, isTrue);
    });

    testWidgets('stores snooze timestamp when checkbox is checked',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => InAppUpdateDialog(
                updateInfo: optionalUpdate,
                onUpdate: () {},
                prefs: prefs,
              ),
            ),
          ),
        ),
      );

      // Check the snooze checkbox
      await tester.tap(find.byType(Checkbox));
      await tester.pump();

      // Verify checkbox is checked
      final checkbox = tester.widget<CheckboxListTile>(
        find.byType(CheckboxListTile),
      );
      expect(checkbox.value, isTrue);

      // Tap "Later"
      await tester.tap(find.text('Later'));
      await tester.pumpAndSettle();

      // Verify snooze timestamp was stored
      final snoozeTimestamp = prefs.getInt(InAppUpdateDialog.snoozeKey);
      expect(snoozeTimestamp, isNotNull);
      expect(snoozeTimestamp, greaterThan(0));
    });

    testWidgets('does not store snooze when checkbox is unchecked',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => InAppUpdateDialog(
                updateInfo: optionalUpdate,
                onUpdate: () {},
                prefs: prefs,
              ),
            ),
          ),
        ),
      );

      // Don't check the checkbox, just tap "Later"
      await tester.tap(find.text('Later'));
      await tester.pumpAndSettle();

      // Verify snooze timestamp was NOT stored
      final snoozeTimestamp = prefs.getInt(InAppUpdateDialog.snoozeKey);
      expect(snoozeTimestamp, isNull);
    });
  });

  group('InAppUpdateDialog - shouldShowDialog', () {
    const mandatoryUpdate = UpdateStatus(
      needsUpdate: true,
      isMandatory: true,
      currentVersion: '1.0.0',
      latestVersion: '2.0.0',
    );

    const optionalUpdate = UpdateStatus(
      needsUpdate: true,
      isMandatory: false,
      currentVersion: '1.0.0',
      latestVersion: '1.1.0',
    );

    const noUpdate = UpdateStatus(
      needsUpdate: false,
      isMandatory: false,
      currentVersion: '1.0.0',
      latestVersion: '1.0.0',
    );

    test('returns false when no update needed', () {
      final shouldShow = InAppUpdateDialog.shouldShowDialog(
        updateInfo: noUpdate,
        prefs: prefs,
      );

      expect(shouldShow, isFalse);
    });

    test('returns true for mandatory update regardless of snooze', () async {
      // Set snooze timestamp to 1 day ago
      final oneDayAgo =
          DateTime.now().subtract(const Duration(days: 1)).millisecondsSinceEpoch;
      await prefs.setInt(InAppUpdateDialog.snoozeKey, oneDayAgo);

      final shouldShow = InAppUpdateDialog.shouldShowDialog(
        updateInfo: mandatoryUpdate,
        prefs: prefs,
      );

      expect(shouldShow, isTrue);
    });

    test('returns true for optional update when never snoozed', () {
      final shouldShow = InAppUpdateDialog.shouldShowDialog(
        updateInfo: optionalUpdate,
        prefs: prefs,
      );

      expect(shouldShow, isTrue);
    });

    test('returns false for optional update within 3-day snooze period',
        () async {
      // Set snooze timestamp to 1 day ago
      final oneDayAgo =
          DateTime.now().subtract(const Duration(days: 1)).millisecondsSinceEpoch;
      await prefs.setInt(InAppUpdateDialog.snoozeKey, oneDayAgo);

      final shouldShow = InAppUpdateDialog.shouldShowDialog(
        updateInfo: optionalUpdate,
        prefs: prefs,
      );

      expect(shouldShow, isFalse);
    });

    test('returns true for optional update after 3-day snooze expires',
        () async {
      // Set snooze timestamp to 4 days ago
      final fourDaysAgo =
          DateTime.now().subtract(const Duration(days: 4)).millisecondsSinceEpoch;
      await prefs.setInt(InAppUpdateDialog.snoozeKey, fourDaysAgo);

      final shouldShow = InAppUpdateDialog.shouldShowDialog(
        updateInfo: optionalUpdate,
        prefs: prefs,
      );

      expect(shouldShow, isTrue);
    });
  });

  group('InAppUpdateDialog - clearSnooze', () {
    test('clears snooze timestamp', () async {
      // Set snooze timestamp
      await prefs.setInt(InAppUpdateDialog.snoozeKey, 12345678);

      // Verify it's set
      expect(prefs.getInt(InAppUpdateDialog.snoozeKey), 12345678);

      // Clear it
      await InAppUpdateDialog.clearSnooze(prefs);

      // Verify it's cleared
      expect(prefs.getInt(InAppUpdateDialog.snoozeKey), isNull);
    });
  });
}
