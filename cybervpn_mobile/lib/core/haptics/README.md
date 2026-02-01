# Haptic Feedback Service

This module provides a semantic haptic feedback service for the CyberVPN mobile application.

## Overview

The `HapticService` provides tactile feedback throughout the app with semantic methods that make it clear what type of interaction is occurring. It respects user settings and platform capabilities.

## Features

- **Semantic Methods**: Clear, intention-revealing method names (`selection()`, `success()`, `error()`)
- **Platform Detection**: Automatically detects iOS/Android support
- **Settings Integration**: Respects user preference to disable haptics
- **Error Handling**: Gracefully handles unsupported platforms and errors
- **Riverpod Integration**: Easy dependency injection throughout the app

## Usage

### Basic Usage

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';

class MyWidget extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final haptics = ref.read(hapticServiceProvider);

    return ElevatedButton(
      onPressed: () async {
        await haptics.selection(); // Trigger haptic on button tap
        // Handle button action
      },
      child: Text('Connect'),
    );
  }
}
```

### Available Methods

| Method | Use Case | Platform Feedback |
|--------|----------|-------------------|
| `selection()` | Button taps, toggle switches, radio selections | Light, subtle (selectionClick) |
| `impact()` | Navigation, card dismissals, form submissions | Medium impact |
| `heavy()` | VPN connect/disconnect, delete actions, important confirmations | Heavy impact |
| `success()` | Completed payments, successful connections, saved settings | Light → Medium pattern |
| `error()` | Validation errors, network failures, operation failures | Heavy impact |

### Example Scenarios

#### Button Tap
```dart
ElevatedButton(
  onPressed: () async {
    await haptics.selection();
    Navigator.push(...);
  },
  child: Text('Settings'),
)
```

#### VPN Connection
```dart
Future<void> connectToVPN() async {
  try {
    await vpnService.connect();
    await haptics.success(); // Success pattern
  } catch (e) {
    await haptics.error(); // Error feedback
  }
}
```

#### Toggle Switch
```dart
Switch(
  value: isEnabled,
  onChanged: (value) async {
    await haptics.selection();
    setState(() => isEnabled = value);
  },
)
```

#### Form Validation Error
```dart
if (!isValid) {
  await haptics.error();
  showErrorDialog();
}
```

## Settings Integration

The service automatically checks the user's haptics preference from `AppSettings`:

```dart
// User can toggle haptics in settings
final settings = AppSettings(
  hapticsEnabled: false, // Disable all haptics
);
```

When `hapticsEnabled` is `false`, all haptic methods become no-ops.

## Platform Support

- **iOS**: Full support for all haptic methods
- **Android**: Full support for all haptic methods
- **Web/Desktop**: Automatically disabled (no-ops)

## Implementation Details

### Architecture

- **Service Class**: `HapticService` - Core implementation
- **Provider**: `hapticServiceProvider` - Riverpod DI provider
- **Settings Entity**: `AppSettings.hapticsEnabled` - User preference

### Dependencies

- `flutter/services.dart` - HapticFeedback API
- `flutter_riverpod` - Dependency injection
- `dart:io` - Platform detection

### Error Handling

All methods are wrapped in try-catch blocks. Errors are logged via `AppLogger` but don't throw exceptions, ensuring haptic failures never crash the app.

## Testing

Unit tests are provided in `test/core/haptics/haptic_service_test.dart`:

```bash
flutter test test/core/haptics/haptic_service_test.dart
```

Tests verify:
- Correct HapticFeedback methods are called
- Settings toggle properly enables/disables haptics
- Error handling works correctly
- Platform detection works as expected

## Future Enhancements

Potential improvements:
- Custom haptic patterns for specific actions
- Haptic intensity settings
- Platform-specific optimizations
- Accessibility enhancements

## Related Files

- `lib/core/haptics/haptic_service.dart` - Service implementation
- `lib/features/settings/domain/entities/app_settings.dart` - Settings entity
- `test/core/haptics/haptic_service_test.dart` - Unit tests
