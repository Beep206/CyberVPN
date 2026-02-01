import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/config_import/presentation/widgets/clipboard_import_button.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';

void main() {
  group('ClipboardImportObserver', () {
    testWidgets('wraps child widget correctly', (WidgetTester tester) async {
      // Arrange
      const testWidget = Text('Test Child');

      // Act
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith((ref) {
              return _MockSettingsNotifier();
            }),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: ClipboardImportObserver(
                child: testWidget,
              ),
            ),
          ),
        ),
      );

      // Assert
      expect(find.text('Test Child'), findsOneWidget);
    });
  });

  group('DetectedConfig', () {
    test('creates config with uri and preview', () {
      const config = DetectedConfig(
        uri: 'vless://test',
        preview: 'vless://test',
      );

      expect(config.uri, 'vless://test');
      expect(config.preview, 'vless://test');
    });

    test('equality based on uri', () {
      const config1 = DetectedConfig(
        uri: 'vless://test',
        preview: 'vless://test',
      );
      const config2 = DetectedConfig(
        uri: 'vless://test',
        preview: 'different preview',
      );
      const config3 = DetectedConfig(
        uri: 'vless://different',
        preview: 'vless://different',
      );

      expect(config1, equals(config2));
      expect(config1, isNot(equals(config3)));
    });

    test('hashCode based on uri', () {
      const config1 = DetectedConfig(
        uri: 'vless://test',
        preview: 'vless://test',
      );
      const config2 = DetectedConfig(
        uri: 'vless://test',
        preview: 'different preview',
      );

      expect(config1.hashCode, equals(config2.hashCode));
    });
  });
}

// Mock SettingsNotifier for testing
class _MockSettingsNotifier extends SettingsNotifier {
  _MockSettingsNotifier({this.clipboardAutoDetect = true});

  final bool clipboardAutoDetect;

  @override
  Future<AppSettings> build() async {
    return AppSettings(clipboardAutoDetect: clipboardAutoDetect);
  }

  @override
  Future<void> toggleClipboardAutoDetect() async {
    state = AsyncData(
      state.value!.copyWith(clipboardAutoDetect: !clipboardAutoDetect),
    );
  }
}
