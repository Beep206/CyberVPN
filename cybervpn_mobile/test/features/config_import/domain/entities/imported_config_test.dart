import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ImportSource', () {
    test('has all expected values', () {
      expect(ImportSource.values, hasLength(5));
      expect(ImportSource.values, contains(ImportSource.qrCode));
      expect(ImportSource.values, contains(ImportSource.clipboard));
      expect(ImportSource.values, contains(ImportSource.deepLink));
      expect(ImportSource.values, contains(ImportSource.subscriptionUrl));
      expect(ImportSource.values, contains(ImportSource.manual));
    });
  });

  group('ImportedConfig', () {
    late ImportedConfig config;
    late DateTime importedAt;

    setUp(() {
      importedAt = DateTime(2026, 1, 31, 12, 0, 0);
      config = ImportedConfig(
        id: 'test-id-1',
        name: 'Test Server',
        rawUri: 'vless://uuid@example.com:443?security=tls#TestServer',
        protocol: 'vless',
        serverAddress: 'example.com',
        port: 443,
        source: ImportSource.clipboard,
        importedAt: importedAt,
      );
    });

    test('creates entity with all required fields', () {
      expect(config.id, 'test-id-1');
      expect(config.name, 'Test Server');
      expect(config.rawUri, 'vless://uuid@example.com:443?security=tls#TestServer');
      expect(config.protocol, 'vless');
      expect(config.serverAddress, 'example.com');
      expect(config.port, 443);
      expect(config.source, ImportSource.clipboard);
      expect(config.importedAt, importedAt);
    });

    test('optional fields default to null', () {
      expect(config.subscriptionUrl, isNull);
      expect(config.lastTestedAt, isNull);
      expect(config.isReachable, isNull);
    });

    test('creates entity with all optional fields', () {
      final testedAt = DateTime(2026, 1, 31, 13, 0, 0);
      final fullConfig = ImportedConfig(
        id: 'test-id-2',
        name: 'Sub Server',
        rawUri: 'vmess://base64data',
        protocol: 'vmess',
        serverAddress: '10.0.0.1',
        port: 8080,
        source: ImportSource.subscriptionUrl,
        subscriptionUrl: 'https://sub.example.com/api',
        importedAt: importedAt,
        lastTestedAt: testedAt,
        isReachable: true,
      );

      expect(fullConfig.subscriptionUrl, 'https://sub.example.com/api');
      expect(fullConfig.lastTestedAt, testedAt);
      expect(fullConfig.isReachable, true);
    });

    test('copyWith preserves unchanged fields', () {
      final updated = config.copyWith(name: 'Updated Server');

      expect(updated.name, 'Updated Server');
      expect(updated.id, config.id);
      expect(updated.rawUri, config.rawUri);
      expect(updated.protocol, config.protocol);
      expect(updated.serverAddress, config.serverAddress);
      expect(updated.port, config.port);
      expect(updated.source, config.source);
      expect(updated.importedAt, config.importedAt);
      expect(updated.subscriptionUrl, config.subscriptionUrl);
      expect(updated.lastTestedAt, config.lastTestedAt);
      expect(updated.isReachable, config.isReachable);
    });

    test('copyWith updates specified fields', () {
      final testedAt = DateTime(2026, 1, 31, 14, 0, 0);
      final updated = config.copyWith(
        lastTestedAt: testedAt,
        isReachable: false,
      );

      expect(updated.lastTestedAt, testedAt);
      expect(updated.isReachable, false);
      expect(updated.id, config.id);
    });

    test('equality for identical configs', () {
      final config2 = ImportedConfig(
        id: 'test-id-1',
        name: 'Test Server',
        rawUri: 'vless://uuid@example.com:443?security=tls#TestServer',
        protocol: 'vless',
        serverAddress: 'example.com',
        port: 443,
        source: ImportSource.clipboard,
        importedAt: importedAt,
      );

      expect(config, equals(config2));
      expect(config.hashCode, equals(config2.hashCode));
    });

    test('inequality for different configs', () {
      final config2 = ImportedConfig(
        id: 'test-id-different',
        name: 'Test Server',
        rawUri: 'vless://uuid@example.com:443?security=tls#TestServer',
        protocol: 'vless',
        serverAddress: 'example.com',
        port: 443,
        source: ImportSource.clipboard,
        importedAt: importedAt,
      );

      expect(config, isNot(equals(config2)));
    });

    test('toString returns meaningful representation', () {
      final str = config.toString();
      expect(str, contains('ImportedConfig'));
      expect(str, contains('test-id-1'));
    });

    test('works with all ImportSource values', () {
      for (final source in ImportSource.values) {
        final c = ImportedConfig(
          id: 'id-${source.name}',
          name: 'Config ${source.name}',
          rawUri: 'vless://test',
          protocol: 'vless',
          serverAddress: 'example.com',
          port: 443,
          source: source,
          importedAt: importedAt,
        );
        expect(c.source, source);
      }
    });
  });
}
