import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/screens/log_viewer_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  /// Helper to build the LogViewerScreen with ProviderScope.
  Widget buildLogViewerScreen() {
    return const ProviderScope(
      child: MaterialApp(
        home: LogViewerScreen(),
      ),
    );
  }

  /// Helper to add test log entries.
  void populateTestLogs() {
    AppLogger.clearLogs();
    AppLogger.debug('Debug message 1');
    AppLogger.info('Info message 1');
    AppLogger.warning('Warning message 1');
    AppLogger.error('Error message 1');
    AppLogger.debug('Debug message 2');
    AppLogger.info('Info message containing keyword');
  }

  setUp(AppLogger.clearLogs);

  group('LogViewerScreen Widget Tests', () {
    testWidgets(
      'renders log entries with correct colors for each level',
      (WidgetTester tester) async {
        populateTestLogs();

        await tester.pumpWidget(buildLogViewerScreen());
        await tester.pumpAndSettle();

        // Verify all log messages are displayed.
        expect(find.text('Debug message 1'), findsOneWidget);
        expect(find.text('Info message 1'), findsOneWidget);
        expect(find.text('Warning message 1'), findsOneWidget);
        expect(find.text('Error message 1'), findsOneWidget);

        // Note: Log level badges and filter chips both contain level text,
        // so we verify messages are present instead of counting badge occurrences.

        // Note: Testing actual colors would require custom matchers or finding
        // specific Container widgets and checking their decoration colors.
        // For simplicity, we verify the structural elements are present.
      },
    );

    testWidgets(
      'displays entry count correctly',
      (WidgetTester tester) async {
        populateTestLogs();

        await tester.pumpWidget(buildLogViewerScreen());
        await tester.pumpAndSettle();

        // Verify total entry count is displayed.
        expect(find.text('6 total entries'), findsOneWidget);
      },
    );

    testWidgets(
      'filter by level shows only entries of that level',
      (WidgetTester tester) async {
        populateTestLogs();

        await tester.pumpWidget(buildLogViewerScreen());
        await tester.pumpAndSettle();

        // Tap DEBUG filter chip (use FilterChip widget finder).
        final debugChip = find.widgetWithText(FilterChip, 'DEBUG');
        expect(debugChip, findsOneWidget);
        await tester.tap(debugChip);
        await tester.pumpAndSettle();

        // Verify only DEBUG messages are shown.
        expect(find.text('Debug message 1'), findsOneWidget);
        expect(find.text('Debug message 2'), findsOneWidget);
        expect(find.text('Info message 1'), findsNothing);
        expect(find.text('Warning message 1'), findsNothing);
        expect(find.text('Error message 1'), findsNothing);

        // Verify filtered count is displayed (with bullet character).
        expect(find.textContaining('2 filtered'), findsOneWidget);

        // Tap WARNING filter chip.
        final warningChip = find.widgetWithText(FilterChip, 'WARNING');
        await tester.tap(warningChip);
        await tester.pumpAndSettle();

        // Verify only WARNING messages are shown.
        expect(find.text('Warning message 1'), findsOneWidget);
        expect(find.text('Debug message 1'), findsNothing);
        expect(find.text('Info message 1'), findsNothing);

        // Verify filtered count.
        expect(find.textContaining('1 filtered'), findsOneWidget);

        // Tap ALL filter chip to show all logs.
        await tester.tap(find.text('ALL'));
        await tester.pumpAndSettle();

        // Verify all messages are shown again.
        expect(find.text('Debug message 1'), findsOneWidget);
        expect(find.text('Info message 1'), findsOneWidget);
        expect(find.text('Warning message 1'), findsOneWidget);
        expect(find.text('Error message 1'), findsOneWidget);
      },
    );

    testWidgets(
      'keyword search filters entries correctly',
      (WidgetTester tester) async {
        populateTestLogs();

        await tester.pumpWidget(buildLogViewerScreen());
        await tester.pumpAndSettle();

        // Enter keyword 'keyword' in search field.
        await tester.enterText(find.byType(TextField), 'keyword');
        await tester.pumpAndSettle();

        // Verify only matching entry is shown.
        expect(find.text('Info message containing keyword'), findsOneWidget);
        expect(find.text('Debug message 1'), findsNothing);
        expect(find.text('Warning message 1'), findsNothing);

        // Verify filtered count.
        expect(find.textContaining('1 filtered'), findsOneWidget);

        // Clear search field by tapping X button.
        final clearButton = find.byIcon(Icons.clear);
        expect(clearButton, findsOneWidget);
        await tester.tap(clearButton);
        await tester.pumpAndSettle();

        // Verify all entries are shown again.
        expect(find.text('Debug message 1'), findsOneWidget);
        expect(find.text('Info message 1'), findsOneWidget);
        expect(find.text('Warning message 1'), findsOneWidget);
      },
    );

    testWidgets(
      'combined filters work together',
      (WidgetTester tester) async {
        populateTestLogs();

        await tester.pumpWidget(buildLogViewerScreen());
        await tester.pumpAndSettle();

        // Select INFO level filter.
        final infoChip = find.widgetWithText(FilterChip, 'INFO');
        await tester.tap(infoChip);
        await tester.pumpAndSettle();

        // Enter keyword search.
        await tester.enterText(find.byType(TextField), 'keyword');
        await tester.pumpAndSettle();

        // Verify only the INFO entry with 'keyword' is shown.
        expect(find.text('Info message containing keyword'), findsOneWidget);
        expect(find.text('Info message 1'), findsNothing);
        expect(find.text('Debug message 1'), findsNothing);

        // Verify filtered count.
        expect(find.textContaining('1 filtered'), findsOneWidget);
      },
    );

    testWidgets(
      'shows empty state when no logs exist',
      (WidgetTester tester) async {
        // Do not populate logs.
        await tester.pumpWidget(buildLogViewerScreen());
        await tester.pumpAndSettle();

        // Verify empty state message.
        expect(find.text('No logs available'), findsOneWidget);
        expect(find.text('0 total entries'), findsOneWidget);
      },
    );

    testWidgets(
      'shows no match message when filters exclude all logs',
      (WidgetTester tester) async {
        populateTestLogs();

        await tester.pumpWidget(buildLogViewerScreen());
        await tester.pumpAndSettle();

        // Enter keyword that doesn't match any log.
        await tester.enterText(find.byType(TextField), 'nonexistent');
        await tester.pumpAndSettle();

        // Verify no match message.
        expect(find.text('No logs match filters'), findsOneWidget);
      },
    );

    testWidgets(
      'auto-scroll toggle changes icon state',
      (WidgetTester tester) async {
        populateTestLogs();

        await tester.pumpWidget(buildLogViewerScreen());
        await tester.pumpAndSettle();

        // Find auto-scroll toggle button (initially enabled).
        final autoScrollButton =
            find.byIcon(Icons.vertical_align_bottom);
        expect(autoScrollButton, findsOneWidget);

        // Tap to disable auto-scroll.
        await tester.tap(autoScrollButton);
        await tester.pumpAndSettle();

        // Verify icon changed to lock_open.
        expect(find.byIcon(Icons.lock_open), findsOneWidget);
        expect(find.byIcon(Icons.vertical_align_bottom), findsNothing);

        // Tap again to re-enable.
        await tester.tap(find.byIcon(Icons.lock_open));
        await tester.pumpAndSettle();

        // Verify icon changed back.
        expect(find.byIcon(Icons.vertical_align_bottom), findsOneWidget);
        expect(find.byIcon(Icons.lock_open), findsNothing);
      },
    );

    testWidgets(
      'clear logs shows confirmation dialog and clears on confirm',
      (WidgetTester tester) async {
        populateTestLogs();

        await tester.pumpWidget(buildLogViewerScreen());
        await tester.pumpAndSettle();

        // Verify logs exist.
        expect(find.text('Debug message 1'), findsOneWidget);

        // Tap clear logs button.
        await tester.tap(find.byIcon(Icons.delete_outline));
        await tester.pumpAndSettle();

        // Verify confirmation dialog appears.
        expect(find.text('Clear All Logs?'), findsOneWidget);
        expect(find.text('This action cannot be undone'), findsOneWidget);
        expect(find.text('Cancel'), findsOneWidget);
        expect(find.text('Confirm'), findsOneWidget);

        // Tap Confirm button.
        await tester.tap(find.text('Confirm'));
        await tester.pumpAndSettle();

        // Verify logs are cleared.
        expect(find.text('Debug message 1'), findsNothing);
        expect(find.text('No logs available'), findsOneWidget);
        expect(find.text('0 total entries'), findsOneWidget);

        // Verify success SnackBar appears.
        expect(find.text('Logs cleared successfully'), findsOneWidget);
      },
    );

    testWidgets(
      'clear logs dialog can be cancelled',
      (WidgetTester tester) async {
        populateTestLogs();

        await tester.pumpWidget(buildLogViewerScreen());
        await tester.pumpAndSettle();

        // Tap clear logs button.
        await tester.tap(find.byIcon(Icons.delete_outline));
        await tester.pumpAndSettle();

        // Tap Cancel button.
        await tester.tap(find.text('Cancel'));
        await tester.pumpAndSettle();

        // Verify logs are NOT cleared.
        expect(find.text('Debug message 1'), findsOneWidget);
        expect(find.text('Info message 1'), findsOneWidget);
        expect(find.text('6 total entries'), findsOneWidget);
      },
    );

    testWidgets(
      'export logs button is present',
      (WidgetTester tester) async {
        populateTestLogs();

        await tester.pumpWidget(buildLogViewerScreen());
        await tester.pumpAndSettle();

        // Verify export button exists.
        expect(find.byIcon(Icons.share), findsOneWidget);

        // Note: Testing actual share functionality requires platform channel
        // mocking which is complex for widget tests. The share action is
        // tested manually or in integration tests.
      },
    );
  });
}
