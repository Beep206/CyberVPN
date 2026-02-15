import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/subscription_info.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('SubscriptionInfo', () {
    test('creates with defaults', () {
      const info = SubscriptionInfo();

      expect(info.title, isNull);
      expect(info.uploadBytes, 0);
      expect(info.downloadBytes, 0);
      expect(info.totalBytes, 0);
      expect(info.expiresAt, isNull);
      expect(info.updateIntervalMinutes, 60);
      expect(info.supportUrl, isNull);
    });

    test('creates with all fields', () {
      final expires = DateTime(2026, 3, 15);
      final info = SubscriptionInfo(
        title: 'Premium Plan',
        uploadBytes: 1000,
        downloadBytes: 2000,
        totalBytes: 10000,
        expiresAt: expires,
        updateIntervalMinutes: 120,
        supportUrl: 'https://support.example.com',
      );

      expect(info.title, 'Premium Plan');
      expect(info.uploadBytes, 1000);
      expect(info.downloadBytes, 2000);
      expect(info.totalBytes, 10000);
      expect(info.expiresAt, expires);
      expect(info.updateIntervalMinutes, 120);
      expect(info.supportUrl, 'https://support.example.com');
    });

    test('copyWith preserves unchanged fields', () {
      final info = SubscriptionInfo(
        title: 'Plan A',
        uploadBytes: 500,
        downloadBytes: 1000,
        totalBytes: 5000,
      );
      final updated = info.copyWith(title: 'Plan B');

      expect(updated.title, 'Plan B');
      expect(updated.uploadBytes, info.uploadBytes);
      expect(updated.downloadBytes, info.downloadBytes);
      expect(updated.totalBytes, info.totalBytes);
    });

    test('equality for identical infos', () {
      final expires = DateTime(2026, 3, 15);
      final info1 = SubscriptionInfo(
        title: 'Plan',
        uploadBytes: 100,
        downloadBytes: 200,
        totalBytes: 1000,
        expiresAt: expires,
      );
      final info2 = SubscriptionInfo(
        title: 'Plan',
        uploadBytes: 100,
        downloadBytes: 200,
        totalBytes: 1000,
        expiresAt: expires,
      );

      expect(info1, equals(info2));
      expect(info1.hashCode, equals(info2.hashCode));
    });

    test('inequality when fields differ', () {
      const info1 = SubscriptionInfo(uploadBytes: 100);
      const info2 = SubscriptionInfo(uploadBytes: 200);

      expect(info1, isNot(equals(info2)));
    });
  });

  group('SubscriptionInfo.consumedBytes', () {
    test('returns sum of upload and download', () {
      const info = SubscriptionInfo(
        uploadBytes: 1000,
        downloadBytes: 2000,
      );

      expect(info.consumedBytes, 3000);
    });

    test('returns 0 when both are 0', () {
      const info = SubscriptionInfo();

      expect(info.consumedBytes, 0);
    });

    test('handles large byte values', () {
      const info = SubscriptionInfo(
        uploadBytes: 5368709120, // ~5 GB
        downloadBytes: 10737418240, // ~10 GB
      );

      expect(info.consumedBytes, 16106127360); // ~15 GB
    });
  });

  group('SubscriptionInfo.usageRatio', () {
    test('returns correct ratio', () {
      const info = SubscriptionInfo(
        uploadBytes: 300,
        downloadBytes: 700,
        totalBytes: 2000,
      );

      expect(info.usageRatio, 0.5);
    });

    test('returns 0.0 when totalBytes is 0 (unlimited)', () {
      const info = SubscriptionInfo(
        uploadBytes: 1000,
        downloadBytes: 2000,
        totalBytes: 0,
      );

      expect(info.usageRatio, 0.0);
    });

    test('returns 0.0 when no traffic consumed', () {
      const info = SubscriptionInfo(totalBytes: 10000);

      expect(info.usageRatio, 0.0);
    });

    test('clamps to 1.0 when overused', () {
      const info = SubscriptionInfo(
        uploadBytes: 5000,
        downloadBytes: 7000,
        totalBytes: 10000,
      );

      expect(info.usageRatio, 1.0);
    });

    test('returns 1.0 when exactly at limit', () {
      const info = SubscriptionInfo(
        uploadBytes: 500,
        downloadBytes: 500,
        totalBytes: 1000,
      );

      expect(info.usageRatio, 1.0);
    });

    test('handles small ratios', () {
      const info = SubscriptionInfo(
        uploadBytes: 1,
        downloadBytes: 0,
        totalBytes: 1000000,
      );

      expect(info.usageRatio, closeTo(0.000001, 0.0000001));
    });
  });

  group('SubscriptionInfo.isExpired', () {
    test('returns false when expiresAt is null', () {
      const info = SubscriptionInfo();

      expect(info.isExpired, false);
    });

    test('returns true when expiresAt is in the past', () {
      final info = SubscriptionInfo(
        expiresAt: DateTime(2020, 1, 1),
      );

      expect(info.isExpired, true);
    });

    test('returns false when expiresAt is in the future', () {
      final info = SubscriptionInfo(
        expiresAt: DateTime(2099, 12, 31),
      );

      expect(info.isExpired, false);
    });
  });

  group('SubscriptionInfo.remaining', () {
    test('returns Duration.zero when expiresAt is null', () {
      const info = SubscriptionInfo();

      expect(info.remaining, Duration.zero);
    });

    test('returns Duration.zero when already expired', () {
      final info = SubscriptionInfo(
        expiresAt: DateTime(2020, 1, 1),
      );

      expect(info.remaining, Duration.zero);
    });

    test('returns positive duration when not expired', () {
      final info = SubscriptionInfo(
        expiresAt: DateTime(2099, 12, 31),
      );

      expect(info.remaining.inDays, greaterThan(0));
    });

    test('remaining is non-negative', () {
      final info = SubscriptionInfo(
        expiresAt: DateTime(2020, 6, 15),
      );

      expect(info.remaining.isNegative, false);
    });
  });
}
