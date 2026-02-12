import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/repositories/config_import_repository.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show configImportRepositoryProvider;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Mock repository
// ---------------------------------------------------------------------------

class MockConfigImportRepository implements ConfigImportRepository {
  List<ImportedConfig> _configs = [];

  @override
  Future<List<ImportedConfig>> getImportedConfigs() async {
    return List.unmodifiable(_configs);
  }

  @override
  Future<ImportedConfig> importFromUri(String uri, ImportSource source) async {
    final config = ImportedConfig(
      id: 'test-id-${_configs.length + 1}',
      name: 'Test Server',
      rawUri: uri,
      protocol: 'vless',
      serverAddress: '1.2.3.4',
      port: 443,
      source: source,
      importedAt: DateTime.now(),
    );
    _configs = [..._configs, config];
    return config;
  }

  @override
  Future<List<ImportedConfig>> importFromSubscriptionUrl(String url) async {
    final config = ImportedConfig(
      id: 'sub-id-${_configs.length + 1}',
      name: 'Sub Server',
      rawUri: 'vless://sub@server:443',
      protocol: 'vless',
      serverAddress: 'sub.example.com',
      port: 443,
      source: ImportSource.subscriptionUrl,
      subscriptionUrl: url,
      importedAt: DateTime.now(),
    );
    _configs = [..._configs, config];
    return [config];
  }

  @override
  Future<void> deleteConfig(String id) async {
    _configs = _configs.where((c) => c.id != id).toList();
  }

  @override
  Future<void> deleteAll() async {
    _configs = [];
  }

  @override
  Future<bool> testConnection(String id) async {
    return true;
  }
}

class FailingConfigImportRepository extends MockConfigImportRepository {
  @override
  Future<ImportedConfig> importFromUri(String uri, ImportSource source) async {
    throw Exception('Import failed');
  }
}

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

/// Creates a [ProviderContainer] with the given [repository] override.
ProviderContainer createContainer(ConfigImportRepository repository) {
  return ProviderContainer(
    overrides: [
      configImportRepositoryProvider.overrideWithValue(repository),
    ],
  );
}

/// Waits for the [configImportProvider] to finish loading.
Future<ConfigImportState> waitForState(ProviderContainer container) async {
  // Wait for the async notifier to build
  final sub = container.listen(configImportProvider, (_, _) {});
  await container.read(configImportProvider.future);
  sub.close();
  return container.read(configImportProvider).requireValue;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('ConfigImportState', () {
    test('default state has empty servers, not importing, no error', () {
      const state = ConfigImportState();
      expect(state.customServers, isEmpty);
      expect(state.isImporting, isFalse);
      expect(state.lastError, isNull);
    });

    test('copyWith replaces fields correctly', () {
      const state = ConfigImportState();
      final updated = state.copyWith(
        isImporting: true,
        lastError: () => 'some error',
      );
      expect(updated.isImporting, isTrue);
      expect(updated.lastError, 'some error');
      expect(updated.customServers, isEmpty);
    });

    test('copyWith can set lastError back to null', () {
      final state = const ConfigImportState().copyWith(
        lastError: () => 'error',
      );
      final cleared = state.copyWith(lastError: () => null);
      expect(cleared.lastError, isNull);
    });

    test('equality works correctly', () {
      const a = ConfigImportState();
      const b = ConfigImportState();
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  group('ConfigImportNotifier', () {
    late MockConfigImportRepository repository;
    late ProviderContainer container;

    setUp(() {
      repository = MockConfigImportRepository();
      container = createContainer(repository);
    });

    tearDown(() {
      container.dispose();
    });

    test('initial state loads configs from repository', () async {
      final state = await waitForState(container);
      expect(state.customServers, isEmpty);
      expect(state.isImporting, isFalse);
      expect(state.lastError, isNull);
    });

    test('importFromUri adds config to state', () async {
      await waitForState(container);

      final notifier = container.read(configImportProvider.notifier);
      final result = await notifier.importFromUri('vless://test@server:443');

      expect(result, isNotNull);
      expect(result!.protocol, 'vless');

      final state = container.read(configImportProvider).requireValue;
      expect(state.customServers, hasLength(1));
      expect(state.customServers.first.rawUri, 'vless://test@server:443');
      expect(state.isImporting, isFalse);
      expect(state.lastError, isNull);
    });

    test('importFromUri sets error on failure', () async {
      final failRepo = FailingConfigImportRepository();
      final failContainer = createContainer(failRepo);

      await waitForState(failContainer);

      final notifier = failContainer.read(configImportProvider.notifier);
      final result = await notifier.importFromUri('vless://bad');

      expect(result, isNull);

      final state = failContainer.read(configImportProvider).requireValue;
      expect(state.lastError, isNotNull);
      expect(state.lastError, contains('Import failed'));
      expect(state.isImporting, isFalse);

      failContainer.dispose();
    });

    test('deleteConfig removes config from state', () async {
      await waitForState(container);

      final notifier = container.read(configImportProvider.notifier);
      await notifier.importFromUri('vless://test@server:443');

      var state = container.read(configImportProvider).requireValue;
      expect(state.customServers, hasLength(1));

      final configId = state.customServers.first.id;
      await notifier.deleteConfig(configId);

      state = container.read(configImportProvider).requireValue;
      expect(state.customServers, isEmpty);
    });

    test('importFromSubscriptionUrl adds configs to state', () async {
      await waitForState(container);

      final notifier = container.read(configImportProvider.notifier);
      final result = await notifier.importFromSubscriptionUrl(
        'https://example.com/sub',
      );

      expect(result, hasLength(1));

      final state = container.read(configImportProvider).requireValue;
      expect(state.customServers, hasLength(1));
      expect(
        state.customServers.first.subscriptionUrl,
        'https://example.com/sub',
      );
    });
  });

  group('Derived providers', () {
    late MockConfigImportRepository repository;
    late ProviderContainer container;

    setUp(() {
      repository = MockConfigImportRepository();
      container = createContainer(repository);
    });

    tearDown(() {
      container.dispose();
    });

    test('importedConfigsProvider returns empty list initially', () async {
      await waitForState(container);
      final configs = container.read(importedConfigsProvider);
      expect(configs, isEmpty);
    });

    test('importedConfigsProvider reflects imported configs', () async {
      await waitForState(container);

      final notifier = container.read(configImportProvider.notifier);
      await notifier.importFromUri('vless://test@server:443');

      final configs = container.read(importedConfigsProvider);
      expect(configs, hasLength(1));
    });

    test('subscriptionUrlsProvider returns unique subscription URLs',
        () async {
      await waitForState(container);

      final notifier = container.read(configImportProvider.notifier);
      await notifier.importFromSubscriptionUrl('https://example.com/sub');

      final urls = container.read(subscriptionUrlsProvider);
      expect(urls, hasLength(1));
      expect(urls.first, 'https://example.com/sub');
    });

    test('isImportingProvider reflects importing state', () async {
      await waitForState(container);
      final importing = container.read(isImportingProvider);
      expect(importing, isFalse);
    });
  });
}
