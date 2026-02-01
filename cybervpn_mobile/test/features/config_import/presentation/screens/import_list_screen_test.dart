import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/repositories/config_import_repository.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/screens/import_list_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Mock repository
// ---------------------------------------------------------------------------

class MockConfigImportRepository implements ConfigImportRepository {
  List<ImportedConfig> _configs = [];
  bool deleteConfigCalled = false;
  bool deleteAllCalled = false;
  String? lastDeletedId;

  MockConfigImportRepository({List<ImportedConfig>? initialConfigs}) {
    if (initialConfigs != null) {
      _configs = List.of(initialConfigs);
    }
  }

  @override
  Future<List<ImportedConfig>> getImportedConfigs() async {
    return List.unmodifiable(_configs);
  }

  @override
  Future<ImportedConfig> importFromUri(
    String uri,
    ImportSource source,
  ) async {
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
    return [];
  }

  @override
  Future<void> deleteConfig(String id) async {
    deleteConfigCalled = true;
    lastDeletedId = id;
    _configs = _configs.where((c) => c.id != id).toList();
  }

  @override
  Future<void> deleteAll() async {
    deleteAllCalled = true;
    _configs = [];
  }

  @override
  Future<bool> testConnection(String id) async {
    return true;
  }
}

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

List<ImportedConfig> _buildMockConfigs() {
  return [
    ImportedConfig(
      id: 'qr-1',
      name: 'QR Server US',
      rawUri: 'vless://test@1.2.3.4:443',
      protocol: 'vless',
      serverAddress: '1.2.3.4',
      port: 443,
      source: ImportSource.qrCode,
      importedAt: DateTime(2024, 1, 1),
    ),
    ImportedConfig(
      id: 'clip-1',
      name: 'Clipboard Server DE',
      rawUri: 'vmess://test@5.6.7.8:443',
      protocol: 'vmess',
      serverAddress: '5.6.7.8',
      port: 443,
      source: ImportSource.clipboard,
      importedAt: DateTime(2024, 1, 2),
    ),
    ImportedConfig(
      id: 'sub-1',
      name: 'Subscription Server JP',
      rawUri: 'trojan://test@9.10.11.12:443',
      protocol: 'trojan',
      serverAddress: '9.10.11.12',
      port: 443,
      source: ImportSource.subscriptionUrl,
      subscriptionUrl: 'https://example.com/sub',
      importedAt: DateTime(2024, 1, 3),
    ),
    ImportedConfig(
      id: 'qr-2',
      name: 'QR Server UK',
      rawUri: 'ss://test@13.14.15.16:443',
      protocol: 'ss',
      serverAddress: '13.14.15.16',
      port: 443,
      source: ImportSource.qrCode,
      importedAt: DateTime(2024, 1, 4),
    ),
  ];
}

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

Widget _buildTestWidget({required MockConfigImportRepository repository}) {
  return ProviderScope(
    overrides: [
      configImportRepositoryProvider.overrideWithValue(repository),
    ],
    child: const MaterialApp(
      home: ImportListScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('ImportListScreen', () {
    testWidgets('renders grouped display with mock configs', (tester) async {
      final repository = MockConfigImportRepository(
        initialConfigs: _buildMockConfigs(),
      );

      await tester.pumpWidget(_buildTestWidget(repository: repository));
      // Wait for async provider to load
      await tester.pumpAndSettle();

      // Verify screen title
      expect(find.text('Custom Servers'), findsOneWidget);

      // Verify group headers
      expect(find.text('QR Code'), findsOneWidget);
      expect(find.text('Clipboard'), findsOneWidget);
      expect(find.text('Subscription'), findsOneWidget);

      // Verify server names are displayed
      expect(find.text('QR Server US'), findsOneWidget);
      expect(find.text('Clipboard Server DE'), findsOneWidget);
      expect(find.text('Subscription Server JP'), findsOneWidget);
      expect(find.text('QR Server UK'), findsOneWidget);

      // Verify protocol badges
      expect(find.text('VLESS'), findsOneWidget);
      expect(find.text('VMESS'), findsOneWidget);
      expect(find.text('TROJAN'), findsOneWidget);
      expect(find.text('SS'), findsOneWidget);

      // Verify FAB is present
      expect(find.byKey(const Key('import_fab')), findsOneWidget);
    });

    testWidgets('shows empty state when no configs', (tester) async {
      final repository = MockConfigImportRepository();

      await tester.pumpWidget(_buildTestWidget(repository: repository));
      await tester.pumpAndSettle();

      // Verify empty state
      expect(find.text('No Custom Servers'), findsOneWidget);
      expect(
        find.text(
          'Import VPN configurations via QR code, clipboard, or subscription URL.',
        ),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('empty_state_import_button')),
        findsOneWidget,
      );
    });

    testWidgets('delete action removes server from list', (tester) async {
      final repository = MockConfigImportRepository(
        initialConfigs: _buildMockConfigs(),
      );

      await tester.pumpWidget(_buildTestWidget(repository: repository));
      await tester.pumpAndSettle();

      // Verify the server is present
      expect(find.text('QR Server US'), findsOneWidget);

      // Open the popup menu for the first server
      await tester.tap(find.byKey(const Key('server_menu_qr-1')));
      await tester.pumpAndSettle();

      // Tap Delete
      await tester.tap(find.text('Delete'));
      await tester.pumpAndSettle();

      // Confirmation dialog should appear
      expect(find.text('Delete Server'), findsOneWidget);
      expect(
        find.text('Remove "QR Server US" from your custom servers?'),
        findsOneWidget,
      );

      // Confirm deletion
      await tester.tap(find.widgetWithText(FilledButton, 'Delete'));
      await tester.pumpAndSettle();

      // Verify the repository was called
      expect(repository.deleteConfigCalled, isTrue);
      expect(repository.lastDeletedId, equals('qr-1'));
    });

    testWidgets('group header shows correct count badge', (tester) async {
      final repository = MockConfigImportRepository(
        initialConfigs: _buildMockConfigs(),
      );

      await tester.pumpWidget(_buildTestWidget(repository: repository));
      await tester.pumpAndSettle();

      // QR Code group should show count 2
      expect(find.text('2'), findsOneWidget);
      // Clipboard and Subscription groups should show count 1
      // (There are two "1" badges)
      expect(find.text('1'), findsNWidgets(2));
    });
  });
}
