import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/referral/domain/entities/referral.dart';
import 'package:cybervpn_mobile/features/referral/domain/repositories/referral_repository.dart';
import 'package:cybervpn_mobile/core/di/providers.dart' show referralRepositoryProvider;
// Re-export so dependents can import from this file.
export 'package:cybervpn_mobile/core/di/providers.dart' show referralRepositoryProvider;

// ---------------------------------------------------------------------------
// Referral State
// ---------------------------------------------------------------------------

/// Immutable snapshot of the referral feature state.
///
/// When [isAvailable] is `false` the UI should hide referral features entirely
/// (graceful degradation). All nullable fields will be `null` and
/// [recentReferrals] will be empty.
class ReferralState {
  const ReferralState({
    this.isAvailable = false,
    this.referralCode,
    this.stats,
    this.recentReferrals = const [],
  });

  /// Whether the referral feature is supported by the backend.
  final bool isAvailable;

  /// The current user's unique referral code, if available.
  final String? referralCode;

  /// Aggregated referral statistics, if available.
  final ReferralStats? stats;

  /// Most recent referral entries.
  final List<ReferralEntry> recentReferrals;

  ReferralState copyWith({
    bool? isAvailable,
    String? Function()? referralCode,
    ReferralStats? Function()? stats,
    List<ReferralEntry>? recentReferrals,
  }) {
    return ReferralState(
      isAvailable: isAvailable ?? this.isAvailable,
      referralCode:
          referralCode != null ? referralCode() : this.referralCode,
      stats: stats != null ? stats() : this.stats,
      recentReferrals: recentReferrals ?? this.recentReferrals,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ReferralState &&
          runtimeType == other.runtimeType &&
          isAvailable == other.isAvailable &&
          referralCode == other.referralCode &&
          stats == other.stats &&
          recentReferrals == other.recentReferrals;

  @override
  int get hashCode => Object.hash(
        isAvailable,
        referralCode,
        stats,
        recentReferrals,
      );

  @override
  String toString() =>
      'ReferralState(isAvailable: $isAvailable, code: $referralCode, '
      'stats: $stats, recentReferrals: ${recentReferrals.length})';
}

// ---------------------------------------------------------------------------
// ReferralNotifier
// ---------------------------------------------------------------------------

/// Manages referral feature state with backend availability checking.
///
/// On [build] it checks whether the referral backend is available. If so,
/// it loads the referral code, stats, and recent referrals in parallel.
/// When the backend is unavailable, the state reflects an empty/unavailable
/// state for graceful UI degradation.
class ReferralNotifier extends AsyncNotifier<ReferralState> {
  ReferralRepository get _repo => ref.read(referralRepositoryProvider);

  // ---- Lifecycle -----------------------------------------------------------

  @override
  FutureOr<ReferralState> build() async {
    final availableResult = await _repo.isAvailable();
    final available = switch (availableResult) {
      Success(:final data) => data,
      Failure() => false,
    };

    if (!available) {
      return const ReferralState(isAvailable: false);
    }

    return _loadAllData();
  }

  // ---- Public API ----------------------------------------------------------

  /// Re-checks backend availability and reloads all data if available.
  Future<void> checkAvailability() async {
    state = const AsyncLoading();
    try {
      final availableResult = await _repo.isAvailable();
      final available = switch (availableResult) {
        Success(:final data) => data,
        Failure() => false,
      };
      if (!available) {
        state = const AsyncData(ReferralState(isAvailable: false));
        return;
      }
      state = AsyncData(await _loadAllData());
    } catch (e, st) {
      AppLogger.error(
        'Failed to check referral availability',
        error: e,
        stackTrace: st,
      );
      state = AsyncError(e, st);
    }
  }

  /// Refreshes referral stats and recent referrals from the backend.
  ///
  /// Only fetches data if the feature is currently available. Does not
  /// re-check availability -- use [checkAvailability] for that.
  Future<void> refreshStats() async {
    final current = state.value;
    if (current == null || !current.isAvailable) return;

    try {
      final results = await Future.wait([
        _repo.getStats(),
        _repo.getRecentReferrals(),
      ]);

      final statsResult = results[0] as Result<ReferralStats>;
      final referralsResult = results[1] as Result<List<ReferralEntry>>;

      final newStats = switch (statsResult) {
        Success(:final data) => data,
        Failure(:final failure) => throw failure,
      };
      final newReferrals = switch (referralsResult) {
        Success(:final data) => data,
        Failure(:final failure) => throw failure,
      };

      state = AsyncData(
        current.copyWith(
          stats: () => newStats,
          recentReferrals: newReferrals,
        ),
      );
    } catch (e, st) {
      AppLogger.error(
        'Failed to refresh referral stats',
        error: e,
        stackTrace: st,
      );
      state = AsyncError(e, st);
    }
  }

  /// Shares the referral code using the platform share sheet.
  ///
  /// No-op when the referral code is not available.
  Future<void> shareReferralCode() async {
    final current = state.value;
    final code = current?.referralCode;
    if (code == null || code.isEmpty) return;

    try {
      await _repo.shareReferral(code);
    } catch (e, st) {
      AppLogger.error(
        'Failed to share referral code',
        error: e,
        stackTrace: st,
      );
    }
  }

  // ---- Private helpers -----------------------------------------------------

  /// Loads referral code, stats, and recent referrals in parallel.
  ///
  /// Assumes the feature is available. Returns a fully populated
  /// [ReferralState] with [isAvailable] set to `true`.
  Future<ReferralState> _loadAllData() async {
    final results = await Future.wait([
      _repo.getReferralCode(),
      _repo.getStats(),
      _repo.getRecentReferrals(),
    ]);

    final codeResult = results[0] as Result<String>;
    final statsResult = results[1] as Result<ReferralStats>;
    final referralsResult = results[2] as Result<List<ReferralEntry>>;

    final code = switch (codeResult) {
      Success(:final data) => data,
      Failure(:final failure) => throw failure,
    };
    final stats = switch (statsResult) {
      Success(:final data) => data,
      Failure(:final failure) => throw failure,
    };
    final referrals = switch (referralsResult) {
      Success(:final data) => data,
      Failure(:final failure) => throw failure,
    };

    return ReferralState(
      isAvailable: true,
      referralCode: code.isEmpty ? null : code,
      stats: stats,
      recentReferrals: referrals,
    );
  }
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

/// Primary referral state provider backed by [ReferralNotifier].
final referralProvider =
    AsyncNotifierProvider<ReferralNotifier, ReferralState>(
  ReferralNotifier.new,
);

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// Whether the referral feature is available on the backend.
///
/// Use this provider for conditional UI rendering -- when `false`,
/// referral features should be hidden entirely.
final isReferralAvailableProvider = Provider<bool>((ref) {
  final referralState = ref.watch(referralProvider).value;
  return referralState?.isAvailable ?? false;
});

/// The current user's referral code, or `null` if unavailable.
final referralCodeProvider = Provider<String?>((ref) {
  final referralState = ref.watch(referralProvider).value;
  return referralState?.referralCode;
});

/// Aggregated referral statistics, or `null` if unavailable.
final referralStatsProvider = Provider<ReferralStats?>((ref) {
  final referralState = ref.watch(referralProvider).value;
  return referralState?.stats;
});

/// Recent referral entries (empty list when unavailable).
final recentReferralsProvider = Provider<List<ReferralEntry>>((ref) {
  final referralState = ref.watch(referralProvider).value;
  return referralState?.recentReferrals ?? [];
});
