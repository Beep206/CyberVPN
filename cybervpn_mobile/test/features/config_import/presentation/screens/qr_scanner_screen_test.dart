import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/repositories/config_import_repository.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/screens/qr_scanner_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Mock repository
// ---------------------------------------------------------------------------

class MockConfigImportRepository implements ConfigImportRepository {
  List<ImportedConfig> _configs = [];
  bool importCalled = false;
  String? lastImportedUri;

  @override
  Future<List<ImportedConfig>> getImportedConfigs() async {
    return List.unmodifiable(_configs);
  }

  @override
  Future<ImportedConfig> importFromUri(
    String uri,
    ImportSource source,
  ) async {
    importCalled = true;
    lastImportedUri = uri;
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
// Helper
// ---------------------------------------------------------------------------

/// Wraps [QrScannerScreen] in a testable widget tree with required providers.
Widget _buildTestWidget({required MockConfigImportRepository repository}) {
  return ProviderScope(
    overrides: [
      configImportRepositoryProvider.overrideWithValue(repository),
    ],
    child: const MaterialApp(
      home: QrScannerScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('QrScannerScreen', () {
    late MockConfigImportRepository mockRepository;

    setUp(() {
      mockRepository = MockConfigImportRepository();
    });

    testWidgets('renders app bar with title and back button', (tester) async {
      await tester.pumpWidget(_buildTestWidget(repository: mockRepository));
      await tester.pump();

      // App bar title
      expect(find.text('Scan QR Code'), findsOneWidget);

      // Back button
      expect(find.byKey(const Key('qr_back_button')), findsOneWidget);
    });

    testWidgets('renders camera switch button in app bar', (tester) async {
      await tester.pumpWidget(_buildTestWidget(repository: mockRepository));
      await tester.pump();

      expect(find.byKey(const Key('qr_camera_switch')), findsOneWidget);
    });

    testWidgets('renders flash toggle FAB', (tester) async {
      await tester.pumpWidget(_buildTestWidget(repository: mockRepository));
      await tester.pump();

      expect(find.byKey(const Key('qr_flash_toggle')), findsOneWidget);
    });

    testWidgets('renders instruction text', (tester) async {
      await tester.pumpWidget(_buildTestWidget(repository: mockRepository));
      await tester.pump();

      expect(
        find.text('Point your camera at a VPN QR code'),
        findsOneWidget,
      );
    });

    testWidgets('renders MobileScanner widget', (tester) async {
      await tester.pumpWidget(_buildTestWidget(repository: mockRepository));
      await tester.pump();

      expect(find.byKey(const Key('qr_mobile_scanner')), findsOneWidget);
    });
  });
}
