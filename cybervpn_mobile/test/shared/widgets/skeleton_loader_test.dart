import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shimmer/shimmer.dart';

import 'package:cybervpn_mobile/shared/widgets/skeleton_loader.dart';

void main() {
  group('SkeletonLoader', () {
    testWidgets('renders child with shimmer effect', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SkeletonLoader(
              child: Container(
                width: 100,
                height: 100,
                color: Colors.grey,
              ),
            ),
          ),
        ),
      );

      // Verify Shimmer widget is present
      expect(find.byType(Shimmer), findsOneWidget);

      // Verify child container is present
      expect(find.byType(Container), findsWidgets);
    });

    testWidgets('adapts to dark theme', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: Scaffold(
            body: SkeletonLoader(
              child: Container(
                width: 100,
                height: 100,
                color: Colors.grey,
              ),
            ),
          ),
        ),
      );

      // Verify Shimmer widget is present
      expect(find.byType(Shimmer), findsOneWidget);
    });

    testWidgets('adapts to light theme', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.light(),
          home: Scaffold(
            body: SkeletonLoader(
              child: Container(
                width: 100,
                height: 100,
                color: Colors.grey,
              ),
            ),
          ),
        ),
      );

      // Verify Shimmer widget is present
      expect(find.byType(Shimmer), findsOneWidget);
    });
  });

  group('SkeletonLine', () {
    testWidgets('renders with specified dimensions', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SkeletonLine(
              width: 200,
              height: 20,
              borderRadius: 8,
            ),
          ),
        ),
      );

      // Verify SkeletonLoader is present
      expect(find.byType(SkeletonLoader), findsOneWidget);

      // Verify Shimmer effect is applied
      expect(find.byType(Shimmer), findsOneWidget);

      // Verify Container is present
      expect(find.byType(Container), findsWidgets);
    });

    testWidgets('uses default height and borderRadius', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SkeletonLine(width: 100),
          ),
        ),
      );

      expect(find.byType(SkeletonLine), findsOneWidget);
      expect(find.byType(Shimmer), findsOneWidget);
    });
  });

  group('SkeletonCircle', () {
    testWidgets('renders circular skeleton', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SkeletonCircle(size: 50),
          ),
        ),
      );

      // Verify SkeletonLoader is present
      expect(find.byType(SkeletonLoader), findsOneWidget);

      // Verify Shimmer effect is applied
      expect(find.byType(Shimmer), findsOneWidget);

      // Verify Container is present
      expect(find.byType(Container), findsWidgets);
    });
  });

  group('SkeletonCard', () {
    testWidgets('renders card skeleton with default properties', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SkeletonCard(),
          ),
        ),
      );

      // Verify SkeletonLoader is present
      expect(find.byType(SkeletonLoader), findsOneWidget);

      // Verify Shimmer effect is applied
      expect(find.byType(Shimmer), findsOneWidget);
    });

    testWidgets('renders card skeleton with custom dimensions', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SkeletonCard(
              width: 300,
              height: 150,
              borderRadius: 16,
            ),
          ),
        ),
      );

      expect(find.byType(SkeletonCard), findsOneWidget);
      expect(find.byType(Shimmer), findsOneWidget);
    });
  });

  group('ServerCardSkeleton', () {
    testWidgets('renders server card skeleton structure', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ServerCardSkeleton(),
          ),
        ),
      );

      // Verify Card is present
      expect(find.byType(Card), findsOneWidget);

      // Verify SkeletonCircle for flag
      expect(find.byType(SkeletonCircle), findsNWidgets(2)); // flag + star

      // Verify SkeletonLine elements
      expect(find.byType(SkeletonLine), findsWidgets);

      // Verify shimmer is applied to all skeleton elements
      expect(find.byType(Shimmer), findsWidgets);
    });

    testWidgets('matches ServerCard layout structure', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ServerCardSkeleton(),
          ),
        ),
      );

      // Verify layout structure with Row
      expect(find.byType(Row), findsWidgets);

      // Verify Column for title/subtitle area
      expect(find.byType(Column), findsWidgets);
    });
  });

  group('ProfileCardSkeleton', () {
    testWidgets('renders profile card skeleton structure', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ProfileCardSkeleton(),
          ),
        ),
      );

      // Verify Card is present
      expect(find.byType(Card), findsOneWidget);

      // Verify SkeletonCircle for avatar
      expect(find.byType(SkeletonCircle), findsOneWidget);

      // Verify SkeletonLine elements (name, email, badge)
      expect(find.byType(SkeletonLine), findsNWidgets(3));

      // Verify shimmer is applied
      expect(find.byType(Shimmer), findsWidgets);
    });

    testWidgets('has proper layout with Row and Column', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ProfileCardSkeleton(),
          ),
        ),
      );

      // Verify Row for horizontal layout
      expect(find.byType(Row), findsWidgets);

      // Verify Column for vertical stacking of details
      expect(find.byType(Column), findsWidgets);
    });
  });

  group('PlanCardSkeleton', () {
    testWidgets('renders plan card skeleton structure', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PlanCardSkeleton(),
          ),
        ),
      );

      // Verify Card is present
      expect(find.byType(Card), findsOneWidget);

      // Verify SkeletonCircle for feature checkmarks
      expect(find.byType(SkeletonCircle), findsNWidgets(3));

      // Verify SkeletonLine elements
      // Header (name + tag) + description + 3 features + price + duration + button
      expect(find.byType(SkeletonLine), findsWidgets);

      // Verify shimmer is applied
      expect(find.byType(Shimmer), findsWidgets);
    });

    testWidgets('renders feature list skeleton items', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PlanCardSkeleton(),
          ),
        ),
      );

      // Verify Column for vertical layout
      expect(find.byType(Column), findsWidgets);

      // Verify Row elements for features
      expect(find.byType(Row), findsWidgets);
    });

    testWidgets('renders action button skeleton', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PlanCardSkeleton(),
          ),
        ),
      );

      // Find the button skeleton (full width line at bottom)
      final skeletonLines = find.byType(SkeletonLine);
      expect(skeletonLines, findsWidgets);
    });
  });

  group('Shimmer animation', () {
    testWidgets('all skeleton components have shimmer animation', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ListView(
              children: const [
                SkeletonLine(width: 100),
                SkeletonCircle(size: 50),
                SkeletonCard(),
                ServerCardSkeleton(),
                ProfileCardSkeleton(),
                PlanCardSkeleton(),
              ],
            ),
          ),
        ),
      );

      // Verify all skeleton components render with shimmer
      expect(find.byType(Shimmer), findsWidgets);

      // Verify each skeleton type is rendered
      expect(find.byType(SkeletonLine), findsWidgets);
      expect(find.byType(SkeletonCircle), findsWidgets);
      expect(find.byType(SkeletonCard), findsOneWidget);
      expect(find.byType(ServerCardSkeleton), findsOneWidget);
      expect(find.byType(ProfileCardSkeleton), findsOneWidget);
      expect(find.byType(PlanCardSkeleton), findsOneWidget);
    });
  });
}
