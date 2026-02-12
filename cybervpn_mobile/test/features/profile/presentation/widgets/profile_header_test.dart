import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';

import 'package:cybervpn_mobile/app/theme/cyberpunk_theme.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/presentation/widgets/profile_header.dart';

void main() {
  group('ProfileHeader', () {
    // Helper to wrap widget with MaterialApp for theme
    Widget buildWidget(Profile profile) {
      return MaterialApp(
        theme: cyberpunkDarkTheme(),
        home: Scaffold(
          body: ProfileHeader(profile: profile),
        ),
      );
    }

    testWidgets('displays user initials from username', (tester) async {
      const profile = Profile(
        id: '1',
        email: 'test@example.com',
        username: 'John Doe',
      );

      await tester.pumpWidget(buildWidget(profile));

      expect(find.text('JD'), findsOneWidget);
    });

    testWidgets('displays user initials from email when no username',
        (tester) async {
      const profile = Profile(
        id: '1',
        email: 'john.doe@example.com',
      );

      await tester.pumpWidget(buildWidget(profile));

      expect(find.text('JD'), findsOneWidget);
    });

    testWidgets('displays single initial for single name', (tester) async {
      const profile = Profile(
        id: '1',
        email: 'test@example.com',
        username: 'John',
      );

      await tester.pumpWidget(buildWidget(profile));

      expect(find.text('J'), findsOneWidget);
    });

    testWidgets('displays username', (tester) async {
      const profile = Profile(
        id: '1',
        email: 'test@example.com',
        username: 'JohnDoe',
      );

      await tester.pumpWidget(buildWidget(profile));

      expect(find.text('JohnDoe'), findsOneWidget);
    });

    testWidgets('displays email username when no username provided',
        (tester) async {
      const profile = Profile(
        id: '1',
        email: 'test@example.com',
      );

      await tester.pumpWidget(buildWidget(profile));

      expect(find.text('test'), findsOneWidget);
    });

    testWidgets('displays full email', (tester) async {
      const profile = Profile(
        id: '1',
        email: 'test@example.com',
        username: 'JohnDoe',
      );

      await tester.pumpWidget(buildWidget(profile));

      expect(find.text('test@example.com'), findsOneWidget);
    });

    testWidgets('displays member since date when available', (tester) async {
      final createdAt = DateTime(2024, 1, 15);
      final profile = Profile(
        id: '1',
        email: 'test@example.com',
        createdAt: createdAt,
      );

      await tester.pumpWidget(buildWidget(profile));

      final expectedText = 'Member since ${DateFormat.yMMMM().format(createdAt)}';
      expect(find.text(expectedText), findsOneWidget);
    });

    testWidgets('does not display member since when date is null',
        (tester) async {
      const profile = Profile(
        id: '1',
        email: 'test@example.com',
      );

      await tester.pumpWidget(buildWidget(profile));

      expect(find.textContaining('Member since'), findsNothing);
    });

    testWidgets('uses custom avatar radius', (tester) async {
      const profile = Profile(
        id: '1',
        email: 'test@example.com',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: cyberpunkDarkTheme(),
          home: const Scaffold(
            body: ProfileHeader(profile: profile, avatarRadius: 50),
          ),
        ),
      );

      final avatar = tester.widget<CircleAvatar>(find.byType(CircleAvatar));
      expect(avatar.radius, 50);
    });

    testWidgets('has CircleAvatar with initials', (tester) async {
      const profile = Profile(
        id: '1',
        email: 'test@example.com',
        username: 'Alice',
      );

      await tester.pumpWidget(buildWidget(profile));

      expect(find.byType(CircleAvatar), findsOneWidget);
      final avatar = tester.widget<CircleAvatar>(find.byType(CircleAvatar));
      final text = (avatar.child as Text).data;
      expect(text, 'A');
    });
  });
}
