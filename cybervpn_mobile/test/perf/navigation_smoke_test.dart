import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

class _NavigationHomeScreen extends StatelessWidget {
  const _NavigationHomeScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: TextButton(
          key: const ValueKey<String>('go-detail'),
          onPressed: () => GoRouter.of(context).go('/detail'),
          child: const Text('Open detail'),
        ),
      ),
    );
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('router navigation smoke stays within basic budget', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1080, 1920));

    final router = GoRouter(
      routes: <RouteBase>[
        GoRoute(
          path: '/',
          builder: (BuildContext context, GoRouterState state) {
            return const _NavigationHomeScreen();
          },
        ),
        GoRoute(
          path: '/detail',
          builder: (BuildContext context, GoRouterState state) {
            return const Scaffold(body: Center(child: Text('Detail screen')));
          },
        ),
      ],
    );

    final startupStopwatch = Stopwatch()..start();
    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pumpAndSettle();
    startupStopwatch.stop();

    expect(startupStopwatch.elapsed, lessThan(const Duration(seconds: 3)));
    expect(find.text('Open detail'), findsOneWidget);

    final navigationStopwatch = Stopwatch()..start();
    await tester.tap(find.byKey(const ValueKey<String>('go-detail')));
    await tester.pumpAndSettle();
    navigationStopwatch.stop();

    expect(navigationStopwatch.elapsed, lessThan(const Duration(seconds: 3)));
    expect(find.text('Detail screen'), findsOneWidget);
  });
}
