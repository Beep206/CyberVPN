# Integration Tests

This directory contains end-to-end (E2E) integration tests for the CyberVPN mobile app.

## Running E2E Tests

### Prerequisites

1. **Flutter SDK** (3.27.1+)
2. **Connected device or emulator** (required for integration tests)
3. **Dependencies installed**: `flutter pub get`

### Running on a Device/Emulator

```bash
# Run all integration tests
flutter test integration_test/

# Run specific E2E auth flow tests
flutter test integration_test/e2e_auth_flow_test.dart

# Run with verbose output
flutter test integration_test/ --reporter expanded

# Run on a specific device
flutter test integration_test/ -d <device_id>
```

### Running in CI Pipeline

For CI environments, use the `flutter drive` command with proper setup:

```bash
# Run with headless Chrome (for web)
flutter drive \
  --driver=test_driver/integration_test.dart \
  --target=integration_test/e2e_auth_flow_test.dart

# Run on Android emulator
flutter drive \
  --driver=test_driver/integration_test.dart \
  --target=integration_test/e2e_auth_flow_test.dart \
  -d emulator-5554
```

## Test Structure

### E2E Auth Flow Tests (`e2e_auth_flow_test.dart`)

Critical authentication flow tests:

| Test Group | Description |
|------------|-------------|
| Full Registration Flow | User registers → Home screen |
| Full Login Flow | User logs in → Home screen |
| Session Persistence | App relaunch → Auto-login |
| Biometric Login Flow | Biometric auth → Home screen |
| Offline Mode Access | Offline + cached session → Limited access |

### Navigation Flow Tests (`navigation_flow_test.dart`)

Tests for app navigation between screens.

### VPN Flow Tests (`vpn_flow_test.dart`)

Tests for VPN connection lifecycle.

## Test Architecture

Tests use **mocked backends** via mocktail:

- `MockAuthRepository` - Authentication operations
- `MockBiometricService` - Biometric authentication
- `MockNetworkInfo` - Network connectivity
- `FakeSecureStorage` - In-memory secure storage
- `FakeLocalStorage` - In-memory shared preferences

## Writing New Tests

1. Create test file in `integration_test/`
2. Use `IntegrationTestWidgetsFlutterBinding.ensureInitialized()`
3. Set up mocks in `setUp()`
4. Clean up in `tearDown()`
5. Use `pumpAndSettle()` with timeout for async operations

Example:

```dart
testWidgets('My test', (tester) async {
  // Setup mocks
  when(() => mockAuthRepo.isAuthenticated())
      .thenAnswer((_) async => true);

  // Pump app
  await tester.pumpWidget(/* app with overrides */);
  await tester.pumpAndSettle();

  // Interact and verify
  await tester.tap(find.byType(ElevatedButton));
  await tester.pumpAndSettle();
  expect(find.text('Success'), findsOneWidget);
});
```

## Troubleshooting

### Tests timing out

- Increase timeout: `pumpAndSettle(timeout: Duration(seconds: 30))`
- Check for infinite animations
- Ensure network mocks return immediately

### Tests failing on CI

- Verify emulator/device is connected
- Check for platform-specific code paths
- Ensure all dependencies are mocked

### Biometric tests not running

- Biometric tests require device hardware or mocks
- Use `MockBiometricService` to simulate biometric auth
