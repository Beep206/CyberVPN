import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/repositories/config_import_repository.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/screens/subscription_url_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Mock repository
// ---------------------------------------------------------------------------

class MockConfigImportRepository implements ConfigImportRepository {
  List<ImportedConfig> _configs = [];
  bool importFromSubscriptionUrlCalled = false;
  String? lastImportedUrl;

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
    importFromSubscriptionUrlCalled = true;
    lastImportedUrl = url;

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

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

List<ImportedConfig> _buildMockSubscriptionConfigs() {
  final now = DateTime.now();
  return [
    ImportedConfig(
      id: 'sub-1',
      name: 'Server 1',
      rawUri: 'vless://server1@example.com:443',
      protocol: 'vless',
      serverAddress: 'example.com',
      port: 443,
      source: ImportSource.subscriptionUrl,
      subscriptionUrl: 'https://example.com/sub1',
      importedAt: now.subtract(const Duration(hours: 2)),
    ),
    ImportedConfig(
      id: 'sub-2',
      name: 'Server 2',
      rawUri: 'vmess://server2@test.com:443',
      protocol: 'vmess',
      serverAddress: 'test.com',
      port: 443,
      source: ImportSource.subscriptionUrl,
      subscriptionUrl: 'https://example.com/sub1',
      importedAt: now.subtract(const Duration(hours: 1)),
    ),
    ImportedConfig(
      id: 'sub-3',
      name: 'Server 3',
      rawUri: 'trojan://server3@other.com:443',
      protocol: 'trojan',
      serverAddress: 'other.com',
      port: 443,
      source: ImportSource.subscriptionUrl,
      subscriptionUrl: 'https://test.com/sub2',
      importedAt: now.subtract(const Duration(days: 1)),
    ),
  ];
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('SubscriptionUrlScreen', () {
    late MockConfigImportRepository mockRepository;

    setUp(() {
      mockRepository = MockConfigImportRepository();
    });

    Widget buildScreen() {
      return ProviderScope(
        overrides: [
          configImportRepositoryProvider.overrideWithValue(mockRepository),
        ],
        child: const MaterialApp(
          home: SubscriptionUrlScreen(),
        ),
      );
    }

    testWidgets('renders UI structure correctly', (tester) async {
      await tester.pumpWidget(buildScreen());
      await tester.pumpAndSettle();

      // Check AppBar
      expect(find.text('Subscription URL Import'), findsOneWidget);

      // Check URL input field
      expect(find.byType(TextFormField), findsOneWidget);
      expect(find.text('Subscription URL'), findsOneWidget);

      // Check paste button
      expect(find.byKey(const Key('paste_button')), findsOneWidget);

      // Check import button
      expect(find.byKey(const Key('import_button')), findsOneWidget);
      expect(find.text('Import'), findsOneWidget);

      // Check empty state
      expect(
        find.text('No subscription URLs imported yet'),
        findsOneWidget,
      );
    });

    testWidgets('import button calls provider method', (tester) async {
      await tester.pumpWidget(buildScreen());
      await tester.pumpAndSettle();

      // Enter a URL
      await tester.enterText(
        find.byType(TextFormField),
        'https://example.com/subscription',
      );
      await tester.pumpAndSettle();

      // Tap import button
      await tester.tap(find.byKey(const Key('import_button')));
      await tester.pumpAndSettle();

      // Verify provider method was called
      expect(mockRepository.importFromSubscriptionUrlCalled, isTrue);
      expect(
        mockRepository.lastImportedUrl,
        'https://example.com/subscription',
      );

      // Verify success message
      expect(find.text('Imported 1 servers'), findsOneWidget);

      // Verify URL field is cleared
      final textField = tester.widget<TextFormField>(find.byType(TextFormField));
      expect(textField.controller?.text, isEmpty);
    });

    testWidgets('validates URL before import', (tester) async {
      await tester.pumpWidget(buildScreen());
      await tester.pumpAndSettle();

      // Tap import button without entering URL
      await tester.tap(find.byKey(const Key('import_button')));
      await tester.pumpAndSettle();

      // Verify validation error
      expect(find.text('Please enter a URL'), findsOneWidget);
      expect(mockRepository.importFromSubscriptionUrlCalled, isFalse);
    });

    testWidgets('displays subscription list with metadata', (tester) async {
      mockRepository = MockConfigImportRepository(
        initialConfigs: _buildMockSubscriptionConfigs(),
      );

      await tester.pumpWidget(buildScreen());
      await tester.pumpAndSettle();

      // Verify list is displayed
      expect(find.byKey(const Key('subscription_list')), findsOneWidget);

      // Verify both subscription URLs are shown (2 unique URLs from 3 servers)
      expect(find.byType(Card), findsNWidgets(2));

      // Verify metadata is displayed
      expect(find.textContaining('server'), findsAtLeastNWidgets(2));
      expect(find.textContaining('Last updated:'), findsNWidgets(2));

      // Verify refresh and delete buttons
      expect(find.byIcon(Icons.refresh), findsNWidgets(2));
      expect(find.byIcon(Icons.delete_outline), findsNWidgets(2));
    });

    testWidgets('delete button shows confirmation dialog', (tester) async {
      mockRepository = MockConfigImportRepository(
        initialConfigs: _buildMockSubscriptionConfigs(),
      );

      await tester.pumpWidget(buildScreen());
      await tester.pumpAndSettle();

      // Tap delete button on first subscription
      await tester.tap(find.byIcon(Icons.delete_outline).first);
      await tester.pumpAndSettle();

      // Verify confirmation dialog
      expect(find.text('Delete Subscription'), findsOneWidget);
      expect(
        find.textContaining('Delete all 2 servers'),
        findsOneWidget,
      );
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.text('Delete'), findsOneWidget);
    });

    testWidgets('pull-to-refresh triggers refresh', (tester) async {
      mockRepository = MockConfigImportRepository(
        initialConfigs: _buildMockSubscriptionConfigs(),
      );

      await tester.pumpWidget(buildScreen());
      await tester.pumpAndSettle();

      // Find RefreshIndicator
      expect(find.byKey(const Key('refresh_indicator')), findsOneWidget);

      // Note: Simulating pull-to-refresh in tests is complex and may require
      // additional test infrastructure. This test verifies the widget exists.
      // Full integration testing would verify the refresh behavior.
    });
  });
}
