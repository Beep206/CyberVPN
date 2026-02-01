# Security Module

## Root/Jailbreak Detection

### Overview

The root/jailbreak detection feature warns users when their device is rooted (Android) or jailbroken (iOS). This is a **non-blocking** feature designed to inform users about potential security risks while still allowing full app functionality.

### Why Non-Blocking?

VPN users in censored regions often rely on rooted devices for additional privacy tools and circumvention capabilities. Blocking rooted devices would prevent these users from accessing the VPN service when they need it most.

### Components

#### DeviceIntegrityChecker (`device_integrity.dart`)

Main service class that provides:
- `isDeviceRooted()` - Checks if device is rooted/jailbroken
- `hasUserDismissedWarning()` - Checks if user dismissed the warning
- `dismissWarning()` - Saves dismissal preference
- `resetDismissal()` - Resets dismissal (useful for testing)

#### RootDetectionDialog (`widgets/root_detection_dialog.dart`)

Non-blocking informational dialog that:
- Shows warning icon and message
- Explains security implications
- Emphasizes that app usage is NOT blocked
- Allows user to dismiss permanently
- Tags Sentry scope with `device_rooted: true` for monitoring

### Integration

The check is performed in `MainShellScreen.initState()` which runs after:
- User completes onboarding
- User grants permissions
- User logs in (if required)
- App navigates to main interface

This ensures:
- The dialog appears in a stable UI context
- The user has already committed to using the app
- The warning doesn't interrupt critical onboarding flows

### Localization

Dialog text is fully localized via l10n. Keys:
- `rootDetectionDialogTitle` - Dialog title
- `rootDetectionDialogDescription` - Warning explanation
- `rootDetectionDialogDismiss` - Dismiss button text

Add translations to all language ARB files in `lib/core/l10n/arb/`.

### Testing

Unit tests in `test/unit/core/security/device_integrity_test.dart` cover:
- Dismissal preference storage and retrieval
- Error handling
- Edge cases

Integration testing on rooted/jailbroken devices recommended to verify:
- `flutter_jailbreak_detection` plugin functionality
- Dialog display flow
- Sentry tagging

### Dependencies

- `flutter_jailbreak_detection: ^1.10.0` - Platform detection
- `shared_preferences` - Dismissal preference storage
- `sentry_flutter` - Monitoring and tagging

### Monitoring

Devices with root/jailbreak detected are tagged in Sentry with:
```dart
scope.setTag('device_rooted', 'true');
```

This allows filtering and analyzing issues specific to rooted devices in the Sentry dashboard.
