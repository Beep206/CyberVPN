import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Canonical [SharedPreferences] provider.
///
/// Must be overridden with a pre-initialized [SharedPreferences] instance
/// in the root [ProviderScope] before the app starts.
final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError(
    'sharedPreferencesProvider must be overridden with a SharedPreferences '
    'instance in a ProviderScope.',
  );
});
