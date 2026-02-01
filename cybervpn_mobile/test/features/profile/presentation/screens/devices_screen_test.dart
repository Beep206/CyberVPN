import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/devices_screen.dart';

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

final _testProfile = Profile(
  id: 'user-1',
  email: 'test@example.com',
  username: 'Test User',
  isEmailVerified: true,
  is2FAEnabled: false,
  linkedProviders: [],
  createdAt: DateTime(2024, 1, 1),
);

final _currentDevice = Device(
  id: 'device-1',
  name: 'iPhone 15',
  platform: 'iOS',
  lastActiveAt: DateTime.now(),
  isCurrent: true,
);

final _otherDevice = Device(
  id: 'device-2',
  name: 'MacBook Pro',
  platform: 'macOS',
  lastActiveAt: DateTime.now().subtract(const Duration(hours: 2)),
  isCurrent: false,
);

// ---------------------------------------------------------------------------
// Fake profile notifier
// ---------------------------------------------------------------------------

class _FakeProfileNotifier extends AsyncNotifier<ProfileState>
    implements ProfileNotifier {
  _FakeProfileNotifier(this._state);

  final ProfileState _state;
  bool refreshCalled = false;
  String? removedDeviceId;

  @override
  FutureOr<ProfileState> build() async => _state;

  @override
  Future<void> refreshProfile() async {
    refreshCalled = true;
  }

  @override
  Future<void> removeDevice({
    required String deviceId,
    required String currentDeviceId,
  }) async {
    removedDeviceId = deviceId;
  }

  // Stubs for methods not used in devices screen tests.
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('DevicesScreen', () {
    testWidgets('renders device list with current device badge', (tester) async {
      // Arrange
      final state = ProfileState(
        profile: _testProfile,
        devices: [_currentDevice, _otherDevice],
      );
      final notifier = _FakeProfileNotifier(state);

      // Act
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileProvider.overrideWith(() => notifier),
          ],
          child: const MaterialApp(home: DevicesScreen()),
        ),
      );

      // Wait for async operations
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('Device Management'), findsOneWidget);
      expect(find.text('2 devices connected'), findsOneWidget);
      expect(find.text('iPhone 15'), findsOneWidget);
      expect(find.text('MacBook Pro'), findsOneWidget);
      expect(find.text('This device'), findsOneWidget);
    });

    testWidgets('current device has no delete button', (tester) async {
      // Arrange
      final state = ProfileState(
        profile: _testProfile,
        devices: [_currentDevice],
      );
      final notifier = _FakeProfileNotifier(state);

      // Act
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileProvider.overrideWith(() => notifier),
          ],
          child: const MaterialApp(home: DevicesScreen()),
        ),
      );

      await tester.pumpAndSettle();

      // Assert - current device should not have a delete button
      expect(find.byKey(const Key('delete_btn_device-1')), findsNothing);
    });

    testWidgets('other device has delete button', (tester) async {
      // Arrange
      final state = ProfileState(
        profile: _testProfile,
        devices: [_currentDevice, _otherDevice],
      );
      final notifier = _FakeProfileNotifier(state);

      // Act
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileProvider.overrideWith(() => notifier),
          ],
          child: const MaterialApp(home: DevicesScreen()),
        ),
      );

      await tester.pumpAndSettle();

      // Assert - other device should have a delete button
      expect(find.byKey(const Key('delete_btn_device-2')), findsOneWidget);
    });

    testWidgets('shows warning banner when device limit reached', (tester) async {
      // Arrange - 5 devices (at limit)
      final devices = List.generate(
        5,
        (i) => Device(
          id: 'device-$i',
          name: 'Device $i',
          platform: 'iOS',
          isCurrent: i == 0,
        ),
      );
      final state = ProfileState(
        profile: _testProfile,
        devices: devices,
      );
      final notifier = _FakeProfileNotifier(state);

      // Act
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileProvider.overrideWith(() => notifier),
          ],
          child: const MaterialApp(home: DevicesScreen()),
        ),
      );

      await tester.pumpAndSettle();

      // Assert
      expect(
        find.text('Device limit reached. Remove a device to add new ones.'),
        findsOneWidget,
      );
    });

    testWidgets('shows empty state when no devices', (tester) async {
      // Arrange
      final state = ProfileState(
        profile: _testProfile,
        devices: [],
      );
      final notifier = _FakeProfileNotifier(state);

      // Act
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileProvider.overrideWith(() => notifier),
          ],
          child: const MaterialApp(home: DevicesScreen()),
        ),
      );

      await tester.pumpAndSettle();

      // Assert
      expect(find.text('No devices connected'), findsOneWidget);
      expect(
        find.text('Connect to VPN to register this device'),
        findsOneWidget,
      );
    });

    testWidgets('pull to refresh calls refreshProfile', (tester) async {
      // Arrange
      final state = ProfileState(
        profile: _testProfile,
        devices: [_currentDevice],
      );
      final notifier = _FakeProfileNotifier(state);

      // Act
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileProvider.overrideWith(() => notifier),
          ],
          child: const MaterialApp(home: DevicesScreen()),
        ),
      );

      await tester.pumpAndSettle();

      // Simulate pull-to-refresh
      await tester.drag(
        find.byType(RefreshIndicator),
        const Offset(0, 300),
      );
      await tester.pumpAndSettle();

      // Assert
      expect(notifier.refreshCalled, isTrue);
    });
  });
}
