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

## Test Files

### vpn_flow_test.dart

VPN connection flow tests covering:

1. **Server Selection → Connect → Verify → Disconnect** (skip: true - requires VPN capability)
   - Navigate to servers tab
   - Select a server from the list
   - Initiate connection
   - Verify connection state changes
   - Verify stats update (upload/download bytes)
   - Disconnect and verify disconnection state

2. **Server List Search and Filtering**
   - Test search functionality on server list
   - Verify search results update

3. **Connection Screen UI Verification**
   - Verify connection screen renders properly
   - Check for connection-related UI elements

### navigation_flow_test.dart

Navigation flow tests covering:

1. **Tab Navigation**
   - Switch between all 4 tabs (Connection, Servers, Profile, Settings)
   - Verify each tab renders expected content
   - Test state preservation when switching tabs

2. **Back Navigation**
   - Navigate into nested screens and back
   - System back button behavior
   - Deep navigation stack handling

3. **Deep Link Navigation**
   - Settings route navigation
   - Server detail route navigation
   - Parse and resolve various deep link formats (connect, referral, subscribe)

4. **Navigation Error Handling**
   - Invalid route handling
   - Rapid tab switching stability

## Running Integration Tests

### Prerequisites

- Flutter SDK installed and configured
- Connected Android device or iOS simulator
- VPN integration tests require device with VPN capability or mock VPN repository

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
flutter test integration_test/vpn_flow_test.dart
flutter test integration_test/navigation_flow_test.dart
```

**Run on specific device:**
```bash
flutter test integration_test/ -d <device_id>
```

**Run with verbose output:**
```bash
flutter test integration_test/ -v
```

## CI/CD Integration

The integration tests are configured to run in CI via GitHub Actions. See `.github/workflows/ci.yml`:

- Job: `integration-tests`
- Runs on: `ubuntu-latest`
- Uses Android emulator (API 33, x86_64, google_apis)
- Timeout: 30 minutes
- Uploads test results and coverage artifacts

To run integration tests in CI, the workflow:
1. Sets up Flutter and Java
2. Installs dependencies
3. Runs code generation
4. Launches Android emulator
5. Runs integration tests with coverage
6. Uploads results and coverage

## Future Enhancements

- [ ] Add screenshot capture on test failure
- [ ] Implement mock VPN repository for full VPN flow testing
- [x] Add deep link integration tests
- [ ] Test 2FA flow when implemented
- [ ] Add performance benchmarks
- [ ] Test offline/error scenarios
- [x] Add CI integration test workflow
- [x] Add navigation flow tests
