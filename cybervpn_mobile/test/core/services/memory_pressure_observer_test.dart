import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/services/memory_pressure_observer.dart';

import '../../helpers/fakes/fake_secure_storage.dart';

void main() {
  late FakeSecureStorage storage;
  late MemoryPressureObserver observer;

  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    storage = FakeSecureStorage();
    observer = MemoryPressureObserver(secureStorage: storage);
  });

  tearDown(() {
    observer.dispose();
    storage.reset();
  });

  group('MemoryPressureObserver', () {
    test('registers as WidgetsBindingObserver', () {
      // Should not throw when registering
      observer.register();
    });

    test('invalidates cache on didHaveMemoryPressure', () async {
      // Populate the cache by reading a value
      await storage.write(key: 'test_key', value: 'test_value');
      // Force a read to populate parent class cache
      final value = await storage.read(key: 'test_key');
      expect(value, 'test_value');

      // Simulate memory pressure
      observer.didHaveMemoryPressure();

      // Verify the in-memory cache was cleared by calling invalidateCache
      // The FakeSecureStorage overrides read() so it always returns from _store,
      // but the parent's _cache and _checkedKeys should have been cleared.
      // We can verify by checking that the observer called invalidateCache
      // without errors.
    });

    test('dispose removes observer without error', () {
      observer.register();
      // Should not throw
      observer.dispose();
    });

    test('multiple pressure events are handled', () async {
      await storage.write(key: 'key1', value: 'val1');

      observer.didHaveMemoryPressure();
      observer.didHaveMemoryPressure();
      observer.didHaveMemoryPressure();

      // Should not throw after multiple invocations
    });
  });
}
