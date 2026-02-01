import 'package:cybervpn_mobile/features/referral/domain/entities/referral.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ReferralStatus', () {
    test('has all expected values', () {
      expect(ReferralStatus.values, hasLength(3));
      expect(ReferralStatus.values, contains(ReferralStatus.pending));
      expect(ReferralStatus.values, contains(ReferralStatus.active));
      expect(ReferralStatus.values, contains(ReferralStatus.completed));
    });
  });

  group('ReferralStats', () {
    test('creates with required fields', () {
      const stats = ReferralStats(
        totalInvited: 10,
        paidUsers: 3,
        pointsEarned: 150.5,
        balance: 50.0,
      );

      expect(stats.totalInvited, 10);
      expect(stats.paidUsers, 3);
      expect(stats.pointsEarned, 150.5);
      expect(stats.balance, 50.0);
    });

    test('copyWith updates specified fields', () {
      const stats = ReferralStats(
        totalInvited: 10,
        paidUsers: 3,
        pointsEarned: 150.5,
        balance: 50.0,
      );

      final updated = stats.copyWith(paidUsers: 5, balance: 75.0);

      expect(updated.totalInvited, 10);
      expect(updated.paidUsers, 5);
      expect(updated.pointsEarned, 150.5);
      expect(updated.balance, 75.0);
    });

    test('equality for identical stats', () {
      const stats1 = ReferralStats(
        totalInvited: 10,
        paidUsers: 3,
        pointsEarned: 150.5,
        balance: 50.0,
      );
      const stats2 = ReferralStats(
        totalInvited: 10,
        paidUsers: 3,
        pointsEarned: 150.5,
        balance: 50.0,
      );

      expect(stats1, equals(stats2));
      expect(stats1.hashCode, equals(stats2.hashCode));
    });

    test('inequality for different stats', () {
      const stats1 = ReferralStats(
        totalInvited: 10,
        paidUsers: 3,
        pointsEarned: 150.5,
        balance: 50.0,
      );
      const stats2 = ReferralStats(
        totalInvited: 10,
        paidUsers: 5,
        pointsEarned: 150.5,
        balance: 50.0,
      );

      expect(stats1, isNot(equals(stats2)));
    });

    test('toString returns meaningful representation', () {
      const stats = ReferralStats(
        totalInvited: 10,
        paidUsers: 3,
        pointsEarned: 150.5,
        balance: 50.0,
      );

      expect(stats.toString(), contains('ReferralStats'));
    });
  });

  group('ReferralEntry', () {
    test('creates with required fields', () {
      final joinDate = DateTime(2026, 1, 15);
      final entry = ReferralEntry(
        code: 'REF123',
        joinDate: joinDate,
        status: ReferralStatus.active,
      );

      expect(entry.code, 'REF123');
      expect(entry.joinDate, joinDate);
      expect(entry.status, ReferralStatus.active);
    });

    test('copyWith updates specified fields', () {
      final entry = ReferralEntry(
        code: 'REF123',
        joinDate: DateTime(2026, 1, 15),
        status: ReferralStatus.pending,
      );

      final updated = entry.copyWith(status: ReferralStatus.completed);

      expect(updated.code, 'REF123');
      expect(updated.status, ReferralStatus.completed);
    });

    test('equality for identical entries', () {
      final joinDate = DateTime(2026, 1, 15);
      final entry1 = ReferralEntry(
        code: 'REF123',
        joinDate: joinDate,
        status: ReferralStatus.active,
      );
      final entry2 = ReferralEntry(
        code: 'REF123',
        joinDate: joinDate,
        status: ReferralStatus.active,
      );

      expect(entry1, equals(entry2));
      expect(entry1.hashCode, equals(entry2.hashCode));
    });

    test('inequality for different entries', () {
      final entry1 = ReferralEntry(
        code: 'REF123',
        joinDate: DateTime(2026, 1, 15),
        status: ReferralStatus.active,
      );
      final entry2 = ReferralEntry(
        code: 'REF456',
        joinDate: DateTime(2026, 1, 15),
        status: ReferralStatus.active,
      );

      expect(entry1, isNot(equals(entry2)));
    });

    test('toString returns meaningful representation', () {
      final entry = ReferralEntry(
        code: 'REF123',
        joinDate: DateTime(2026, 1, 15),
        status: ReferralStatus.pending,
      );

      expect(entry.toString(), contains('ReferralEntry'));
    });
  });
}
