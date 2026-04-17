import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/features/settings/presentation/providers/app_reset_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/reset_settings_screen.dart';

class _FakeAppResetController extends AppResetController {
  int resetSettingsCalls = 0;
  int fullResetCalls = 0;

  @override
  FutureOr<void> build() {}

  @override
  Future<void> resetSettings() async {
    resetSettingsCalls++;
    state = const AsyncData(null);
  }

  @override
  Future<void> performFullAppReset() async {
    fullResetCalls++;
    state = const AsyncData(null);
  }
}

void main() {
  late _FakeAppResetController controller;
  late GoRouter router;

  setUp(() {
    controller = _FakeAppResetController();
    router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => const ResetSettingsScreen(),
        ),
        GoRoute(
          path: '/onboarding',
          builder: (context, state) =>
              const Scaffold(body: Text('Onboarding target')),
        ),
      ],
    );
  });

  Widget buildScreen() {
    return ProviderScope(
      overrides: [
        appResetControllerProvider.overrideWith(() => controller),
      ],
      child: MaterialApp.router(routerConfig: router),
    );
  }

  testWidgets('renders reset actions and scope contract', (tester) async {
    await tester.pumpWidget(buildScreen());
    await tester.pumpAndSettle();

    expect(find.text('Actions'), findsOneWidget);
    expect(find.byKey(const Key('reset_settings_action')), findsOneWidget);
    expect(find.byKey(const Key('full_app_reset_action')), findsOneWidget);
    expect(find.text('Full Reset Scope'), findsOneWidget);
    expect(find.byKey(const Key('reset_scope_preserved')), findsOneWidget);
  });

  testWidgets('reset settings action confirms and executes', (tester) async {
    await tester.pumpWidget(buildScreen());
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('reset_settings_action')));
    await tester.pumpAndSettle();

    expect(find.text('Reset Settings'), findsAtLeastNWidgets(2));
    await tester.tap(find.text('Reset Settings').last);
    await tester.pumpAndSettle();

    expect(controller.resetSettingsCalls, 1);
    expect(find.text('Settings reset complete'), findsOneWidget);
  });

  testWidgets('full app reset action confirms and navigates to onboarding', (
    tester,
  ) async {
    await tester.pumpWidget(buildScreen());
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('full_app_reset_action')));
    await tester.pumpAndSettle();

    expect(find.text('Full App Reset'), findsAtLeastNWidgets(2));
    await tester.tap(find.text('Full App Reset').last);
    await tester.pumpAndSettle();

    expect(controller.fullResetCalls, 1);
    expect(find.text('Onboarding target'), findsOneWidget);
  });
}
