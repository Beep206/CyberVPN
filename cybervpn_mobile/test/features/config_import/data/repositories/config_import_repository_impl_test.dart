import 'package:cybervpn_mobile/features/config_import/data/parsers/subscription_url_parser.dart';
import 'package:cybervpn_mobile/features/config_import/data/repositories/config_import_repository_impl.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/parsed_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/usecases/parse_vpn_uri.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

// --- Mocks ---

class MockSubscriptionUrlParser extends Mock
    implements SubscriptionUrlParser {}

class MockParseVpnUri extends Mock implements ParseVpnUri {}

// --- Test data ---

const _validVlessUri =
    'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@vless.example.com:443'
    '?security=tls&type=ws#VLESS-test';

const _validTrojanUri = 'trojan://mypassword@trojan.example.com:443#Trojan-test';

const _parsedVlessConfig = ParsedConfig(
  protocol: 'vless',
  serverAddress: 'vless.example.com',
  port: 443,
  uuid: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
  remark: 'VLESS-test',
);

const _parsedTrojanConfig = ParsedConfig(
  protocol: 'trojan',
  serverAddress: 'trojan.example.com',
  port: 443,
  uuid: '',
  password: 'mypassword',
  remark: 'Trojan-test',
);

void main() {
  late SharedPreferences prefs;
  late MockSubscriptionUrlParser mockSubParser;
  late MockParseVpnUri mockParseVpnUri;
  late ConfigImportRepositoryImpl repo;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    mockSubParser = MockSubscriptionUrlParser();
    mockParseVpnUri = MockParseVpnUri();
    repo = ConfigImportRepositoryImpl(
      sharedPreferences: prefs,
      subscriptionUrlParser: mockSubParser,
      parseVpnUri: mockParseVpnUri,
    );
  });

  group('getImportedConfigs', () {
    test('returns empty list when no configs stored', () async {
      final result = await repo.getImportedConfigs();
      expect(result, isEmpty);
    });

    test('returns stored configs after import', () async {
      when(() => mockParseVpnUri.call(_validVlessUri))
          .thenReturn(ParseSuccess(_parsedVlessConfig));

      await repo.importFromUri(_validVlessUri, ImportSource.manual);
      final configs = await repo.getImportedConfigs();

      expect(configs, hasLength(1));
      expect(configs.first.protocol, 'vless');
      expect(configs.first.serverAddress, 'vless.example.com');
      expect(configs.first.port, 443);
      expect(configs.first.source, ImportSource.manual);
    });

    test('returns empty list and clears storage on corrupted JSON', () async {
      // Store corrupted data directly
      await prefs.setString('config_import.imported_configs', '{bad json[');
      final result = await repo.getImportedConfigs();
      expect(result, isEmpty);
      // Verify storage was cleared
      expect(prefs.getString('config_import.imported_configs'), isNull);
    });
  });

  group('importFromUri', () {
    test('saves parsed config to storage', () async {
      when(() => mockParseVpnUri.call(_validVlessUri))
          .thenReturn(ParseSuccess(_parsedVlessConfig));

      final imported =
          await repo.importFromUri(_validVlessUri, ImportSource.clipboard);

      expect(imported.name, 'VLESS-test');
      expect(imported.rawUri, _validVlessUri);
      expect(imported.source, ImportSource.clipboard);

      // Verify persistence
      final stored = await repo.getImportedConfigs();
      expect(stored, hasLength(1));
      expect(stored.first.id, imported.id);
    });

    test('deduplicates by raw URI', () async {
      when(() => mockParseVpnUri.call(_validVlessUri))
          .thenReturn(ParseSuccess(_parsedVlessConfig));

      await repo.importFromUri(_validVlessUri, ImportSource.manual);
      await repo.importFromUri(_validVlessUri, ImportSource.clipboard);

      final configs = await repo.getImportedConfigs();
      expect(configs, hasLength(1));
    });

    test('throws ConfigImportException on parse failure', () async {
      when(() => mockParseVpnUri.call('invalid://uri'))
          .thenReturn(const ParseFailure('Unsupported scheme'));

      expect(
        () => repo.importFromUri('invalid://uri', ImportSource.manual),
        throwsA(isA<ConfigImportException>()),
      );
    });
  });

  group('importFromSubscriptionUrl', () {
    test('saves multiple configs from subscription', () async {
      final configs = [
        ImportedConfig(
          id: 'id1',
          name: 'VLESS-test',
          rawUri: _validVlessUri,
          protocol: 'vless',
          serverAddress: 'vless.example.com',
          port: 443,
          source: ImportSource.subscriptionUrl,
          subscriptionUrl: 'https://sub.example.com',
          importedAt: DateTime.now(),
        ),
        ImportedConfig(
          id: 'id2',
          name: 'Trojan-test',
          rawUri: _validTrojanUri,
          protocol: 'trojan',
          serverAddress: 'trojan.example.com',
          port: 443,
          source: ImportSource.subscriptionUrl,
          subscriptionUrl: 'https://sub.example.com',
          importedAt: DateTime.now(),
        ),
      ];

      when(() => mockSubParser.parse('https://sub.example.com')).thenAnswer(
        (_) async => SubscriptionParseResult(configs: configs, errors: []),
      );

      final result =
          await repo.importFromSubscriptionUrl('https://sub.example.com');

      expect(result, hasLength(2));

      final stored = await repo.getImportedConfigs();
      expect(stored, hasLength(2));
    });

    test('throws on empty subscription result', () async {
      when(() => mockSubParser.parse('https://sub.example.com')).thenAnswer(
        (_) async => const SubscriptionParseResult(
          configs: [],
          errors: [
            SubscriptionParseError(
              lineNumber: 1,
              rawUri: 'garbage',
              message: 'Invalid',
            ),
          ],
        ),
      );

      expect(
        () => repo.importFromSubscriptionUrl('https://sub.example.com'),
        throwsA(isA<ConfigImportException>()),
      );
    });
  });

  group('deleteConfig', () {
    test('removes correct config by ID', () async {
      when(() => mockParseVpnUri.call(_validVlessUri))
          .thenReturn(ParseSuccess(_parsedVlessConfig));
      when(() => mockParseVpnUri.call(_validTrojanUri))
          .thenReturn(ParseSuccess(_parsedTrojanConfig));

      final vless =
          await repo.importFromUri(_validVlessUri, ImportSource.manual);
      await repo.importFromUri(_validTrojanUri, ImportSource.manual);

      await repo.deleteConfig(vless.id);

      final remaining = await repo.getImportedConfigs();
      expect(remaining, hasLength(1));
      expect(remaining.first.protocol, 'trojan');
    });
  });

  group('deleteAll', () {
    test('clears all configs', () async {
      when(() => mockParseVpnUri.call(_validVlessUri))
          .thenReturn(ParseSuccess(_parsedVlessConfig));

      await repo.importFromUri(_validVlessUri, ImportSource.manual);
      await repo.deleteAll();

      final configs = await repo.getImportedConfigs();
      expect(configs, isEmpty);
    });
  });

  group('shouldRefreshSubscription', () {
    test('returns true when no metadata exists', () {
      expect(repo.shouldRefreshSubscription('https://sub.example.com'), isTrue);
    });

    test('returns false immediately after subscription import', () async {
      final configs = [
        ImportedConfig(
          id: 'id1',
          name: 'test',
          rawUri: _validVlessUri,
          protocol: 'vless',
          serverAddress: 'vless.example.com',
          port: 443,
          source: ImportSource.subscriptionUrl,
          subscriptionUrl: 'https://sub.example.com',
          importedAt: DateTime.now(),
        ),
      ];

      when(() => mockSubParser.parse('https://sub.example.com')).thenAnswer(
        (_) async => SubscriptionParseResult(configs: configs, errors: []),
      );

      await repo.importFromSubscriptionUrl('https://sub.example.com');

      expect(
        repo.shouldRefreshSubscription('https://sub.example.com'),
        isFalse,
      );
    });
  });

  group('JSON serialization roundtrip', () {
    test('config survives save and reload', () async {
      when(() => mockParseVpnUri.call(_validVlessUri))
          .thenReturn(ParseSuccess(_parsedVlessConfig));

      final original =
          await repo.importFromUri(_validVlessUri, ImportSource.deepLink);

      // Create a new repo instance pointing to the same prefs
      final repo2 = ConfigImportRepositoryImpl(
        sharedPreferences: prefs,
        subscriptionUrlParser: mockSubParser,
        parseVpnUri: mockParseVpnUri,
      );

      final loaded = await repo2.getImportedConfigs();
      expect(loaded, hasLength(1));
      expect(loaded.first.id, original.id);
      expect(loaded.first.name, original.name);
      expect(loaded.first.rawUri, original.rawUri);
      expect(loaded.first.protocol, original.protocol);
      expect(loaded.first.serverAddress, original.serverAddress);
      expect(loaded.first.port, original.port);
      expect(loaded.first.source, original.source);
    });
  });
}
