import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/settings/data/repositories/settings_repository_impl.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';

void main() {
  late SettingsRepositoryImpl repository;

  /// Initialises [SharedPreferences] with the given [values] and creates
  /// a fresh [SettingsRepositoryImpl] backed by it.
  Future<void> initRepo([Map<String, Object> values = const {}]) async {
    SharedPreferences.setMockInitialValues(values);
    final prefs = await SharedPreferences.getInstance();
    repository = SettingsRepositoryImpl(sharedPreferences: prefs);
  }

  /// Helper to unwrap getSettings Result for assertion convenience.
  Future<AppSettings> getSettings() async {
    final result = await repository.getSettings();
    expect(result, isA<Success<AppSettings>>());
    return (result as Success<AppSettings>).data;
  }

  // ---------------------------------------------------------------------------
  // getSettings - default values
  // ---------------------------------------------------------------------------
  group('getSettings - default values when no keys present', () {
    setUp(initRepo);

    test('returns AppSettings with all defaults', () async {
      final settings = await getSettings();
      const defaults = AppSettings();

      expect(settings.themeMode, equals(defaults.themeMode));
      expect(settings.brightness, equals(defaults.brightness));
      expect(settings.dynamicColor, equals(defaults.dynamicColor));
      expect(settings.preferredProtocol, equals(defaults.preferredProtocol));
      expect(settings.autoConnectOnLaunch, equals(defaults.autoConnectOnLaunch));
      expect(
        settings.autoConnectUntrustedWifi,
        equals(defaults.autoConnectUntrustedWifi),
      );
      expect(settings.killSwitch, equals(defaults.killSwitch));
      expect(settings.splitTunneling, equals(defaults.splitTunneling));
      expect(settings.dnsProvider, equals(defaults.dnsProvider));
      expect(settings.customDns, isNull);
      expect(settings.mtuMode, equals(defaults.mtuMode));
      expect(settings.mtuValue, equals(defaults.mtuValue));
      expect(settings.locale, equals(defaults.locale));
      expect(
        settings.notificationConnection,
        equals(defaults.notificationConnection),
      );
      expect(settings.notificationExpiry, equals(defaults.notificationExpiry));
      expect(
        settings.notificationPromotional,
        equals(defaults.notificationPromotional),
      );
      expect(
        settings.notificationReferral,
        equals(defaults.notificationReferral),
      );
      expect(
        settings.notificationVpnSpeed,
        equals(defaults.notificationVpnSpeed),
      );
      expect(
        settings.clipboardAutoDetect,
        equals(defaults.clipboardAutoDetect),
      );
      expect(settings.logLevel, equals(defaults.logLevel));
    });

    test('default themeMode is cyberpunk', () async {
      final settings = await getSettings();
      expect(settings.themeMode, AppThemeMode.cyberpunk);
    });

    test('default brightness is system', () async {
      final settings = await getSettings();
      expect(settings.brightness, AppBrightness.system);
    });

    test('default preferredProtocol is auto', () async {
      final settings = await getSettings();
      expect(settings.preferredProtocol, PreferredProtocol.auto);
    });

    test('default locale is en', () async {
      final settings = await getSettings();
      expect(settings.locale, 'en');
    });

    test('default mtuValue is 1400', () async {
      final settings = await getSettings();
      expect(settings.mtuValue, 1400);
    });

    test('default logLevel is info', () async {
      final settings = await getSettings();
      expect(settings.logLevel, LogLevel.info);
    });
  });

  // ---------------------------------------------------------------------------
  // getSettings - reads stored values
  // ---------------------------------------------------------------------------
  group('getSettings - reads stored values', () {
    test('returns correct AppSettings when all keys are present', () async {
      await initRepo({
        'settings.themeMode': 'materialYou',
        'settings.brightness': 'dark',
        'settings.dynamicColor': true,
        'settings.preferredProtocol': 'vlessReality',
        'settings.autoConnectOnLaunch': true,
        'settings.autoConnectUntrustedWifi': true,
        'settings.killSwitch': true,
        'settings.splitTunneling': true,
        'settings.dnsProvider': 'cloudflare',
        'settings.customDns': '1.1.1.1',
        'settings.mtuMode': 'manual',
        'settings.mtuValue': 1500,
        'settings.locale': 'ru',
        'settings.notificationConnection': false,
        'settings.notificationExpiry': false,
        'settings.notificationPromotional': true,
        'settings.notificationReferral': false,
        'settings.notificationVpnSpeed': true,
        'settings.clipboardAutoDetect': false,
        'settings.logLevel': 'debug',
      });

      final settings = await getSettings();

      expect(settings.themeMode, AppThemeMode.materialYou);
      expect(settings.brightness, AppBrightness.dark);
      expect(settings.dynamicColor, isTrue);
      expect(settings.preferredProtocol, PreferredProtocol.vlessReality);
      expect(settings.autoConnectOnLaunch, isTrue);
      expect(settings.autoConnectUntrustedWifi, isTrue);
      expect(settings.killSwitch, isTrue);
      expect(settings.splitTunneling, isTrue);
      expect(settings.dnsProvider, DnsProvider.cloudflare);
      expect(settings.customDns, '1.1.1.1');
      expect(settings.mtuMode, MtuMode.manual);
      expect(settings.mtuValue, 1500);
      expect(settings.locale, 'ru');
      expect(settings.notificationConnection, isFalse);
      expect(settings.notificationExpiry, isFalse);
      expect(settings.notificationPromotional, isTrue);
      expect(settings.notificationReferral, isFalse);
      expect(settings.notificationVpnSpeed, isTrue);
      expect(settings.clipboardAutoDetect, isFalse);
      expect(settings.logLevel, LogLevel.debug);
    });

    test('returns defaults for invalid enum strings', () async {
      await initRepo({
        'settings.themeMode': 'invalidValue',
        'settings.dnsProvider': 'nonexistent',
        'settings.logLevel': 'verbose', // not in enum
      });

      final settings = await getSettings();
      const defaults = AppSettings();

      expect(settings.themeMode, defaults.themeMode);
      expect(settings.dnsProvider, defaults.dnsProvider);
      expect(settings.logLevel, defaults.logLevel);
    });

    test('reads partial keys and defaults the rest', () async {
      await initRepo({
        'settings.locale': 'de',
        'settings.killSwitch': true,
      });

      final settings = await getSettings();

      expect(settings.locale, 'de');
      expect(settings.killSwitch, isTrue);
      // Everything else should be default
      expect(settings.themeMode, AppThemeMode.cyberpunk);
      expect(settings.brightness, AppBrightness.system);
      expect(settings.dynamicColor, isFalse);
    });
  });

  // ---------------------------------------------------------------------------
  // updateSettings
  // ---------------------------------------------------------------------------
  group('updateSettings', () {
    test('persists all fields and reads them back correctly', () async {
      await initRepo();

      const custom = AppSettings(
        themeMode: AppThemeMode.materialYou,
        brightness: AppBrightness.light,
        dynamicColor: true,
        preferredProtocol: PreferredProtocol.vlessXhttp,
        autoConnectOnLaunch: true,
        autoConnectUntrustedWifi: true,
        killSwitch: true,
        splitTunneling: true,
        dnsProvider: DnsProvider.google,
        customDns: '8.8.8.8',
        mtuMode: MtuMode.manual,
        mtuValue: 1300,
        locale: 'ja',
        notificationConnection: false,
        notificationExpiry: false,
        notificationPromotional: true,
        notificationReferral: false,
        notificationVpnSpeed: true,
        clipboardAutoDetect: false,
        logLevel: LogLevel.error,
      );

      await repository.updateSettings(custom);
      final result = await getSettings();

      expect(result.themeMode, AppThemeMode.materialYou);
      expect(result.brightness, AppBrightness.light);
      expect(result.dynamicColor, isTrue);
      expect(result.preferredProtocol, PreferredProtocol.vlessXhttp);
      expect(result.autoConnectOnLaunch, isTrue);
      expect(result.autoConnectUntrustedWifi, isTrue);
      expect(result.killSwitch, isTrue);
      expect(result.splitTunneling, isTrue);
      expect(result.dnsProvider, DnsProvider.google);
      expect(result.customDns, '8.8.8.8');
      expect(result.mtuMode, MtuMode.manual);
      expect(result.mtuValue, 1300);
      expect(result.locale, 'ja');
      expect(result.notificationConnection, isFalse);
      expect(result.notificationExpiry, isFalse);
      expect(result.notificationPromotional, isTrue);
      expect(result.notificationReferral, isFalse);
      expect(result.notificationVpnSpeed, isTrue);
      expect(result.clipboardAutoDetect, isFalse);
      expect(result.logLevel, LogLevel.error);
    });

    test('removes customDns key when value is null', () async {
      await initRepo({'settings.customDns': '1.1.1.1'});

      // First verify it has a value
      var settings = await getSettings();
      expect(settings.customDns, '1.1.1.1');

      // Update with null customDns
      await repository.updateSettings(const AppSettings(customDns: null));

      settings = await getSettings();
      expect(settings.customDns, isNull);
    });

    test('overwrites previously stored values', () async {
      await initRepo({'settings.locale': 'en'});

      await repository.updateSettings(const AppSettings(locale: 'fr'));

      final settings = await getSettings();
      expect(settings.locale, 'fr');
    });

    test('persists each enum as its name string', () async {
      await initRepo();

      const settings = AppSettings(
        themeMode: AppThemeMode.materialYou,
        brightness: AppBrightness.dark,
        preferredProtocol: PreferredProtocol.vlessWsTls,
        dnsProvider: DnsProvider.quad9,
        mtuMode: MtuMode.manual,
        logLevel: LogLevel.warning,
      );

      await repository.updateSettings(settings);

      // Read back and verify enum round-trip
      final result = await getSettings();
      expect(result.themeMode, AppThemeMode.materialYou);
      expect(result.brightness, AppBrightness.dark);
      expect(result.preferredProtocol, PreferredProtocol.vlessWsTls);
      expect(result.dnsProvider, DnsProvider.quad9);
      expect(result.mtuMode, MtuMode.manual);
      expect(result.logLevel, LogLevel.warning);
    });
  });

  // ---------------------------------------------------------------------------
  // resetSettings
  // ---------------------------------------------------------------------------
  group('resetSettings', () {
    test('clears all settings keys so defaults are returned', () async {
      await initRepo({
        'settings.themeMode': 'materialYou',
        'settings.brightness': 'dark',
        'settings.dynamicColor': true,
        'settings.preferredProtocol': 'vlessReality',
        'settings.autoConnectOnLaunch': true,
        'settings.killSwitch': true,
        'settings.locale': 'zh',
        'settings.logLevel': 'error',
        'settings.mtuValue': 1200,
        'settings.customDns': '9.9.9.9',
      });

      // Verify non-default values are present
      var settings = await getSettings();
      expect(settings.themeMode, AppThemeMode.materialYou);
      expect(settings.locale, 'zh');
      expect(settings.mtuValue, 1200);

      // Reset
      await repository.resetSettings();

      // All should be defaults now
      settings = await getSettings();
      const defaults = AppSettings();

      expect(settings.themeMode, defaults.themeMode);
      expect(settings.brightness, defaults.brightness);
      expect(settings.dynamicColor, defaults.dynamicColor);
      expect(settings.preferredProtocol, defaults.preferredProtocol);
      expect(settings.autoConnectOnLaunch, defaults.autoConnectOnLaunch);
      expect(settings.killSwitch, defaults.killSwitch);
      expect(settings.locale, defaults.locale);
      expect(settings.logLevel, defaults.logLevel);
      expect(settings.mtuValue, defaults.mtuValue);
      expect(settings.customDns, isNull);
    });

    test('does not affect non-settings keys', () async {
      SharedPreferences.setMockInitialValues({
        'settings.locale': 'fr',
        'other.key': 'should-remain',
      });
      final prefs = await SharedPreferences.getInstance();
      repository = SettingsRepositoryImpl(sharedPreferences: prefs);

      await repository.resetSettings();

      // Settings key should be cleared
      expect(prefs.getString('settings.locale'), isNull);

      // Other key should remain
      expect(prefs.getString('other.key'), 'should-remain');
    });

    test('update after reset persists new values', () async {
      await initRepo({'settings.locale': 'de'});

      await repository.resetSettings();
      await repository.updateSettings(const AppSettings(locale: 'es'));

      final settings = await getSettings();
      expect(settings.locale, 'es');
    });
  });

  // ---------------------------------------------------------------------------
  // Round-trip: update -> get -> reset -> get
  // ---------------------------------------------------------------------------
  group('full lifecycle', () {
    test('update, read, reset, read cycle works correctly', () async {
      await initRepo();

      // 1. Read defaults
      var settings = await getSettings();
      expect(settings, equals(const AppSettings()));

      // 2. Update with custom values
      const custom = AppSettings(
        themeMode: AppThemeMode.materialYou,
        locale: 'ko',
        killSwitch: true,
        mtuValue: 1200,
        logLevel: LogLevel.debug,
      );
      await repository.updateSettings(custom);

      // 3. Read back custom values
      settings = await getSettings();
      expect(settings.themeMode, AppThemeMode.materialYou);
      expect(settings.locale, 'ko');
      expect(settings.killSwitch, isTrue);
      expect(settings.mtuValue, 1200);
      expect(settings.logLevel, LogLevel.debug);

      // 4. Reset
      await repository.resetSettings();

      // 5. Read defaults again
      settings = await getSettings();
      expect(settings.themeMode, AppThemeMode.cyberpunk);
      expect(settings.locale, 'en');
      expect(settings.killSwitch, isFalse);
      expect(settings.mtuValue, 1400);
      expect(settings.logLevel, LogLevel.info);
    });
  });

  // ---------------------------------------------------------------------------
  // Enum coverage
  // ---------------------------------------------------------------------------
  group('enum value coverage', () {
    test('all AppThemeMode values round-trip correctly', () async {
      for (final mode in AppThemeMode.values) {
        await initRepo({'settings.themeMode': mode.name});
        final settings = await getSettings();
        expect(settings.themeMode, mode, reason: 'Failed for ${mode.name}');
      }
    });

    test('all AppBrightness values round-trip correctly', () async {
      for (final brightness in AppBrightness.values) {
        await initRepo({'settings.brightness': brightness.name});
        final settings = await getSettings();
        expect(settings.brightness, brightness,
            reason: 'Failed for ${brightness.name}');
      }
    });

    test('all PreferredProtocol values round-trip correctly', () async {
      for (final protocol in PreferredProtocol.values) {
        await initRepo({'settings.preferredProtocol': protocol.name});
        final settings = await getSettings();
        expect(settings.preferredProtocol, protocol,
            reason: 'Failed for ${protocol.name}');
      }
    });

    test('all DnsProvider values round-trip correctly', () async {
      for (final dns in DnsProvider.values) {
        await initRepo({'settings.dnsProvider': dns.name});
        final settings = await getSettings();
        expect(settings.dnsProvider, dns, reason: 'Failed for ${dns.name}');
      }
    });

    test('all MtuMode values round-trip correctly', () async {
      for (final mtu in MtuMode.values) {
        await initRepo({'settings.mtuMode': mtu.name});
        final settings = await getSettings();
        expect(settings.mtuMode, mtu, reason: 'Failed for ${mtu.name}');
      }
    });

    test('all LogLevel values round-trip correctly', () async {
      for (final level in LogLevel.values) {
        await initRepo({'settings.logLevel': level.name});
        final settings = await getSettings();
        expect(settings.logLevel, level, reason: 'Failed for ${level.name}');
      }
    });
  });
}
