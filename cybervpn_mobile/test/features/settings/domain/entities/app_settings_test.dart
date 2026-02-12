import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AppSettings enums', () {
    test('AppThemeMode has expected values', () {
      expect(AppThemeMode.values, hasLength(2));
      expect(AppThemeMode.values, contains(AppThemeMode.materialYou));
      expect(AppThemeMode.values, contains(AppThemeMode.cyberpunk));
    });

    test('AppBrightness has expected values', () {
      expect(AppBrightness.values, hasLength(3));
      expect(AppBrightness.values, contains(AppBrightness.system));
      expect(AppBrightness.values, contains(AppBrightness.light));
      expect(AppBrightness.values, contains(AppBrightness.dark));
    });

    test('PreferredProtocol has expected values', () {
      expect(PreferredProtocol.values, hasLength(4));
      expect(PreferredProtocol.values, contains(PreferredProtocol.auto));
      expect(PreferredProtocol.values, contains(PreferredProtocol.vlessReality));
      expect(PreferredProtocol.values, contains(PreferredProtocol.vlessXhttp));
      expect(PreferredProtocol.values, contains(PreferredProtocol.vlessWsTls));
    });

    test('DnsProvider has expected values', () {
      expect(DnsProvider.values, hasLength(5));
      expect(DnsProvider.values, contains(DnsProvider.system));
      expect(DnsProvider.values, contains(DnsProvider.cloudflare));
      expect(DnsProvider.values, contains(DnsProvider.google));
      expect(DnsProvider.values, contains(DnsProvider.quad9));
      expect(DnsProvider.values, contains(DnsProvider.custom));
    });

    test('LogLevel has expected values', () {
      expect(LogLevel.values, hasLength(4));
      expect(LogLevel.values, contains(LogLevel.debug));
      expect(LogLevel.values, contains(LogLevel.info));
      expect(LogLevel.values, contains(LogLevel.warning));
      expect(LogLevel.values, contains(LogLevel.error));
    });
  });

  group('AppSettings', () {
    late AppSettings settings;

    setUp(() {
      settings = const AppSettings();
    });

    test('creates entity with sensible defaults', () {
      expect(settings.themeMode, AppThemeMode.cyberpunk);
      expect(settings.brightness, AppBrightness.system);
      expect(settings.dynamicColor, false);
      expect(settings.preferredProtocol, PreferredProtocol.auto);
      expect(settings.autoConnectOnLaunch, false);
      expect(settings.autoConnectUntrustedWifi, false);
      expect(settings.killSwitch, false);
      expect(settings.dnsProvider, DnsProvider.system);
      expect(settings.customDns, isNull);
      expect(settings.locale, 'en');
      expect(settings.notificationConnection, true);
      expect(settings.notificationExpiry, true);
      expect(settings.notificationPromotional, false);
      expect(settings.notificationReferral, true);
      expect(settings.clipboardAutoDetect, true);
      expect(settings.logLevel, LogLevel.info);
    });

    test('creates entity with all fields specified', () {
      const custom = AppSettings(
        themeMode: AppThemeMode.materialYou,
        brightness: AppBrightness.dark,
        dynamicColor: true,
        preferredProtocol: PreferredProtocol.vlessReality,
        autoConnectOnLaunch: true,
        autoConnectUntrustedWifi: true,
        killSwitch: true,
        dnsProvider: DnsProvider.custom,
        customDns: '1.1.1.1',
        locale: 'ru',
        notificationConnection: false,
        notificationExpiry: false,
        notificationPromotional: true,
        notificationReferral: false,
        clipboardAutoDetect: false,
        logLevel: LogLevel.debug,
      );

      expect(custom.themeMode, AppThemeMode.materialYou);
      expect(custom.brightness, AppBrightness.dark);
      expect(custom.dynamicColor, true);
      expect(custom.preferredProtocol, PreferredProtocol.vlessReality);
      expect(custom.autoConnectOnLaunch, true);
      expect(custom.autoConnectUntrustedWifi, true);
      expect(custom.killSwitch, true);
      expect(custom.dnsProvider, DnsProvider.custom);
      expect(custom.customDns, '1.1.1.1');
      expect(custom.locale, 'ru');
      expect(custom.notificationConnection, false);
      expect(custom.notificationExpiry, false);
      expect(custom.notificationPromotional, true);
      expect(custom.notificationReferral, false);
      expect(custom.clipboardAutoDetect, false);
      expect(custom.logLevel, LogLevel.debug);
    });

    test('copyWith preserves unchanged fields', () {
      final updated = settings.copyWith(themeMode: AppThemeMode.materialYou);

      expect(updated.themeMode, AppThemeMode.materialYou);
      // All other fields remain at defaults
      expect(updated.brightness, settings.brightness);
      expect(updated.dynamicColor, settings.dynamicColor);
      expect(updated.preferredProtocol, settings.preferredProtocol);
      expect(updated.autoConnectOnLaunch, settings.autoConnectOnLaunch);
      expect(updated.autoConnectUntrustedWifi, settings.autoConnectUntrustedWifi);
      expect(updated.killSwitch, settings.killSwitch);
      expect(updated.dnsProvider, settings.dnsProvider);
      expect(updated.customDns, settings.customDns);
      expect(updated.locale, settings.locale);
      expect(updated.notificationConnection, settings.notificationConnection);
      expect(updated.notificationExpiry, settings.notificationExpiry);
      expect(updated.notificationPromotional, settings.notificationPromotional);
      expect(updated.notificationReferral, settings.notificationReferral);
      expect(updated.clipboardAutoDetect, settings.clipboardAutoDetect);
      expect(updated.logLevel, settings.logLevel);
    });

    test('copyWith updates multiple fields', () {
      final updated = settings.copyWith(
        killSwitch: true,
        locale: 'de',
        logLevel: LogLevel.error,
      );

      expect(updated.killSwitch, true);
      expect(updated.locale, 'de');
      expect(updated.logLevel, LogLevel.error);
      expect(updated.themeMode, settings.themeMode);
    });

    test('equality for identical settings', () {
      const settings1 = AppSettings();
      const settings2 = AppSettings();

      expect(settings1, equals(settings2));
      expect(settings1.hashCode, equals(settings2.hashCode));
    });

    test('inequality for different settings', () {
      const settings1 = AppSettings();
      const settings2 = AppSettings(themeMode: AppThemeMode.materialYou);

      expect(settings1, isNot(equals(settings2)));
    });

    test('toString returns meaningful representation', () {
      final str = settings.toString();
      expect(str, contains('AppSettings'));
    });
  });
}
