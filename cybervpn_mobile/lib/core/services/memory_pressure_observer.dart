import 'package:flutter/widgets.dart';

import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Observes system memory pressure events and invalidates in-memory caches.
///
/// When the OS signals memory pressure, clears the [SecureStorageWrapper]
/// in-memory cache so stale entries are evicted. The next read will
/// re-fetch from encrypted storage on demand.
class MemoryPressureObserver with WidgetsBindingObserver {
  final SecureStorageWrapper _secureStorage;

  MemoryPressureObserver({required SecureStorageWrapper secureStorage})
      : _secureStorage = secureStorage;

  /// Registers this observer with the [WidgetsBinding].
  void register() {
    WidgetsBinding.instance.addObserver(this);
  }

  /// Unregisters this observer from the [WidgetsBinding].
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
  }

  @override
  void didHaveMemoryPressure() {
    AppLogger.warning(
      'Memory pressure detected — invalidating secure storage cache',
      category: 'memory',
    );
    _secureStorage.invalidateCache();
  }
}
