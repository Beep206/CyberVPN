# Integration Tests

This directory contains end-to-end integration tests for the CyberVPN mobile app.

## Overview

Integration tests use Flutter's `integration_test` package to test complete user flows from app launch through multiple screens and interactions.

### Test Coverage

#### auth_flow_test.dart

Comprehensive authentication flow tests covering:

1. **Registration Flow** (skip: true - requires backend)
   - App launch → onboarding screen
   - Skip onboarding → permissions screen
   - Navigate to register screen
   - Fill registration form (email, password, confirm password)
   - Accept terms & conditions
   - Submit registration → verify navigation to main screen

2. **Login Flow** (skip: true - requires backend)
   - App launch → onboarding → login screen
   - Enter existing account credentials
   - Submit login → verify navigation to main screen

3. **Form Validation** (active tests)
   - Invalid email format → shows validation error
   - Password mismatch → shows error message
   - Required fields validation

4. **Navigation Tests** (active tests)
   - Switch between login and register screens
   - Verify screen transitions and navigation flow

## Running Integration Tests

### Prerequisites

- Flutter SDK installed and configured
- Connected Android device or iOS simulator
- Backend API running (for full flow tests) or mock providers configured

### Device Setup

**Android:**
```bash
# List available devices
flutter devices

# Start Android emulator
flutter emulators --launch <emulator_id>
```

**iOS:**
```bash
# List available simulators
xcrun simctl list devices

# Boot simulator
open -a Simulator
```

### Run Tests

**Run all integration tests:**
```bash
flutter test integration_test/
```

**Run specific test file:**
```bash
flutter test integration_test/auth_flow_test.dart
```

**Run on specific device:**
```bash
flutter test integration_test/ -d <device_id>
```

**Run with verbose output:**
```bash
flutter test integration_test/ -v
```

## Test Structure

### Helper Functions

- `pumpCyberVpnApp(tester)` - Initializes app with clean SharedPreferences state
- `safePumpAndSettle(tester)` - Pumps and settles with 10-second timeout
- Widget finders use position-based indexing for TextFormFields

### Test Lifecycle

```dart
setUp(() async {
  // Reset SharedPreferences before each test
  SharedPreferences.setMockInitialValues({});
  prefs = await SharedPreferences.getInstance();
  await prefs.clear();
});

tearDown(() async {
  // Clean up after each test
  await prefs.clear();
});
```

## Backend Integration

### Current Status

Tests that require backend API calls are marked with `skip: true`:
- Registration flow test
- Login flow test

### Enabling Backend Tests

To enable backend-dependent tests:

1. **Option A: Mock Backend**
   - Override auth providers in `pumpCyberVpnApp`
   - Provide mock implementations of `AuthRepository`
   - Remove `skip: true` from test definitions

2. **Option B: Test Backend**
   - Start local backend server
   - Configure test environment variables
   - Remove `skip: true` from test definitions

Example mock provider override:
```dart
await tester.pumpWidget(
  ProviderScope(
    overrides: [
      authRepositoryProvider.overrideWithValue(mockAuthRepository),
      ...buildProviderOverrides(prefs),
    ],
    child: const CyberVpnApp(),
  ),
);
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.10.8'
      - run: flutter pub get
      - name: Run iOS integration tests
        run: flutter test integration_test/ -d iPhone
```

### Android Emulator in CI

```yaml
- name: Setup Android Emulator
  uses: reactivecircus/android-emulator-runner@v2
  with:
    api-level: 33
    script: flutter test integration_test/
```

## Troubleshooting

### "No devices connected"
- Ensure device/emulator is running: `flutter devices`
- Start emulator: `flutter emulators --launch <emulator_id>`

### "Web devices not supported"
- Integration tests require mobile platform (Android/iOS)
- Use `flutter run -d chrome` for widget tests only

### Test timeout
- Increase timeout in `safePumpAndSettle` helper
- Check for animations that never complete
- Verify async operations complete

### Widget not found
- Use `tester.pump()` after interactions
- Check widget tree with `debugDumpApp()`
- Verify widget keys match expectations

## Best Practices

1. **Clean state**: Reset SharedPreferences in setUp
2. **Timeouts**: Use `safePumpAndSettle` with reasonable timeouts
3. **Assertions**: Include descriptive `reason` messages
4. **Mocking**: Override providers for isolated testing
5. **Screenshots**: Capture on failure for debugging
6. **Stability**: Avoid hardcoded delays, use pumpAndSettle

## Future Enhancements

- [ ] Add screenshot capture on test failure
- [ ] Implement mock backend for all auth tests
- [ ] Add deep link integration tests
- [ ] Test 2FA flow when implemented
- [ ] Add performance benchmarks
- [ ] Test offline/error scenarios
