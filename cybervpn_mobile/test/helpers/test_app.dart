import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// A test wrapper that provides a [MaterialApp] inside a [ProviderScope]
/// with optional provider overrides for isolated widget testing.
///
/// Usage:
/// ```dart
/// await tester.pumpWidget(
///   TestApp(
///     overrides: [myProvider.overrideWithValue(mockValue)],
///     child: const MyWidget(),
///   ),
/// );
/// ```
class TestApp extends StatelessWidget {
  const TestApp({
    required this.child,
    this.overrides = const [],
    this.themeMode = ThemeMode.light,
    this.locale = const Locale('en'),
    this.textDirection = TextDirection.ltr,
    super.key,
  });

  /// The widget under test.
  final Widget child;

  /// Riverpod provider overrides for dependency injection in tests.
  ///
  /// Pass the result of `.overrideWithValue()` or `.overrideWith()` calls.
  final List<dynamic> overrides;

  /// Theme mode for the test (light or dark).
  final ThemeMode themeMode;

  /// Locale for localization testing.
  final Locale locale;

  /// Text direction for RTL/LTR layout testing.
  final TextDirection textDirection;

  @override
  Widget build(BuildContext context) {
    return ProviderScope(
      overrides: overrides.cast(),
      child: MaterialApp(
        home: Directionality(
          textDirection: textDirection,
          child: child,
        ),
        themeMode: themeMode,
        theme: ThemeData.light(useMaterial3: true),
        darkTheme: ThemeData.dark(useMaterial3: true),
        locale: locale,
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}

/// Extension on [WidgetTester] for convenience methods.
extension TestAppPumper on WidgetTester {
  /// Pumps a [TestApp] with the given [child] and optional overrides.
  ///
  /// This is a shorthand for:
  /// ```dart
  /// await tester.pumpWidget(TestApp(child: child, overrides: overrides));
  /// ```
  Future<void> pumpTestApp(
    Widget child, {
    List<dynamic> overrides = const [],
    ThemeMode themeMode = ThemeMode.light,
    Locale locale = const Locale('en'),
    TextDirection textDirection = TextDirection.ltr,
  }) async {
    await pumpWidget(
      TestApp(
        overrides: overrides,
        themeMode: themeMode,
        locale: locale,
        textDirection: textDirection,
        child: child,
      ),
    );
  }

  /// Pumps and settles a [TestApp] with the given [child].
  Future<void> pumpAndSettleTestApp(
    Widget child, {
    List<dynamic> overrides = const [],
    ThemeMode themeMode = ThemeMode.light,
    Locale locale = const Locale('en'),
    TextDirection textDirection = TextDirection.ltr,
  }) async {
    await pumpTestApp(
      child,
      overrides: overrides,
      themeMode: themeMode,
      locale: locale,
      textDirection: textDirection,
    );
    await pumpAndSettle();
  }
}
