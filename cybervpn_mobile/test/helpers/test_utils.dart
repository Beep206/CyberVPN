import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Utility functions and matchers for tests.

/// Finds a widget of type [T] and verifies it exists.
Finder findByType<T>() => find.byType(T);

/// Finds a widget containing the given [text].
Finder findByText(String text) => find.text(text);

/// Finds a widget by its [Key].
Finder findByKey(Key key) => find.byKey(key);

/// Verifies that a single widget of type [T] exists in the tree.
void expectSingleWidget<T>() {
  expect(find.byType(T), findsOneWidget);
}

/// Verifies that no widget of type [T] exists in the tree.
void expectNoWidget<T>() {
  expect(find.byType(T), findsNothing);
}

/// Verifies that at least one widget of type [T] exists in the tree.
void expectAtLeastOneWidget<T>() {
  expect(find.byType(T), findsAtLeast(1));
}

/// Waits for all pending microtasks and timers to complete.
///
/// Use this when async operations need to settle before assertions.
Future<void> waitForAsync(WidgetTester tester) async {
  await tester.pumpAndSettle(const Duration(milliseconds: 100));
}

/// Creates a unique test key for widget identification.
Key testKey(String name) => Key('test_$name');
