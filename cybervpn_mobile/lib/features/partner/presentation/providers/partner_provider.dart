import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/partner/domain/entities/partner.dart';
import 'package:cybervpn_mobile/features/partner/domain/repositories/partner_repository.dart';
import 'package:cybervpn_mobile/core/di/providers.dart' show partnerRepositoryProvider;

// Re-export so dependents can import from this file.
export 'package:cybervpn_mobile/core/di/providers.dart'
    show partnerRepositoryProvider;

// ---------------------------------------------------------------------------
// Partner State
// ---------------------------------------------------------------------------

/// Immutable snapshot of the partner feature state.
///
/// When [isAvailable] is `false` the UI should hide partner features entirely
/// (graceful degradation). When [isPartner] is `false`, show bind code UI.
class PartnerState {
  const PartnerState({
    this.isAvailable = false,
    this.isPartner = false,
    this.partnerInfo,
    this.partnerCodes = const [],
    this.earnings = const [],
  });

  /// Whether the partner feature is supported by the backend.
  final bool isAvailable;

  /// Whether the current user is a partner.
  final bool isPartner;

  /// Partner information, if user is a partner.
  final PartnerInfo? partnerInfo;

  /// List of partner codes, if user is a partner.
  final List<PartnerCode> partnerCodes;

  /// Earnings history, if user is a partner.
  final List<Earnings> earnings;

  PartnerState copyWith({
    bool? isAvailable,
    bool? isPartner,
    PartnerInfo? Function()? partnerInfo,
    List<PartnerCode>? partnerCodes,
    List<Earnings>? earnings,
  }) {
    return PartnerState(
      isAvailable: isAvailable ?? this.isAvailable,
      isPartner: isPartner ?? this.isPartner,
      partnerInfo: partnerInfo != null ? partnerInfo() : this.partnerInfo,
      partnerCodes: partnerCodes ?? this.partnerCodes,
      earnings: earnings ?? this.earnings,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PartnerState &&
          runtimeType == other.runtimeType &&
          isAvailable == other.isAvailable &&
          isPartner == other.isPartner &&
          partnerInfo == other.partnerInfo &&
          partnerCodes == other.partnerCodes &&
          earnings == other.earnings;

  @override
  int get hashCode => Object.hash(
        isAvailable,
        isPartner,
        partnerInfo,
        partnerCodes,
        earnings,
      );

  @override
  String toString() =>
      'PartnerState(isAvailable: $isAvailable, isPartner: $isPartner, '
      'codes: ${partnerCodes.length}, earnings: ${earnings.length})';
}

// ---------------------------------------------------------------------------
// PartnerNotifier
// ---------------------------------------------------------------------------

/// Manages partner feature state with backend availability checking.
///
/// On [build] it checks whether the partner backend is available and if the
/// user is a partner. If so, it loads partner info, codes, and earnings.
/// When the backend is unavailable or user is not a partner, the state
/// reflects that for graceful UI degradation.
///
/// Uses [autoDispose] because partner state is only needed while the
/// partner screen is active. Resources are released when navigating away.
class PartnerNotifier extends AsyncNotifier<PartnerState> {
  PartnerRepository get _repo => ref.read(partnerRepositoryProvider);

  // ---- Lifecycle -----------------------------------------------------------

  @override
  FutureOr<PartnerState> build() async {
    final availableResult = await _repo.isAvailable();
    final available = switch (availableResult) {
      Success(:final data) => data,
      Failure() => false,
    };

    if (!available) {
      return const PartnerState(isAvailable: false);
    }

    final isPartnerResult = await _repo.isPartner();
    final isPartner = switch (isPartnerResult) {
      Success(:final data) => data,
      Failure() => false,
    };

    if (!isPartner) {
      return const PartnerState(isAvailable: true, isPartner: false);
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
        state = const AsyncData(PartnerState(isAvailable: false));
        return;
      }

      final isPartnerResult = await _repo.isPartner();
      final isPartner = switch (isPartnerResult) {
        Success(:final data) => data,
        Failure() => false,
      };

      if (!isPartner) {
        state = const AsyncData(PartnerState(isAvailable: true, isPartner: false));
        return;
      }

      state = AsyncData(await _loadAllData());
    } catch (e, st) {
      AppLogger.error(
        'Failed to check partner availability',
        error: e,
        stackTrace: st,
      );
      state = AsyncError(e, st);
    }
  }

  /// Refreshes partner info, codes, and earnings from the backend.
  Future<void> refreshData() async {
    final current = state.value;
    if (current == null || !current.isAvailable || !current.isPartner) return;

    try {
      final newState = await _loadAllData();
      state = AsyncData(newState);
    } catch (e, st) {
      AppLogger.error(
        'Failed to refresh partner data',
        error: e,
        stackTrace: st,
      );
      state = AsyncError(e, st);
    }
  }

  /// Creates a new partner code.
  Future<Result<PartnerCode>> createCode({
    required double markup,
    String? description,
  }) async {
    final result = await _repo.createPartnerCode(
      markup: markup,
      description: description,
    );
    // Refresh codes list on success.
    if (result is Success) {
      await refreshData();
    }
    return result;
  }

  /// Updates the markup for a partner code.
  Future<Result<PartnerCode>> updateMarkup({
    required String code,
    required double markup,
  }) async {
    final result = await _repo.updateCodeMarkup(code: code, markup: markup);
    // Refresh codes list on success.
    if (result is Success) {
      await refreshData();
    }
    return result;
  }

  /// Toggles the active status of a partner code.
  Future<Result<PartnerCode>> toggleCodeStatus({
    required String code,
    required bool isActive,
  }) async {
    final result = await _repo.toggleCodeStatus(code: code, isActive: isActive);
    // Refresh codes list on success.
    if (result is Success) {
      await refreshData();
    }
    return result;
  }

  /// Binds a partner code to become a partner (for non-partners).
  Future<Result<BindCodeResult>> bindCode(String code) async {
    final result = await _repo.bindPartnerCode(code);
    // Refresh state on success to check if user is now a partner.
    if (result is Success) {
      await checkAvailability();
    }
    return result;
  }

  /// Shares a partner code using the platform share sheet.
  Future<void> shareCode(String code) async {
    try {
      await _repo.sharePartnerCode(code);
    } catch (e, st) {
      AppLogger.error(
        'Failed to share partner code',
        error: e,
        stackTrace: st,
      );
    }
  }

  // ---- Private helpers -----------------------------------------------------

  /// Loads partner info, codes, and earnings in parallel.
  ///
  /// Assumes the user is a partner. Returns a fully populated [PartnerState]
  /// with [isAvailable] and [isPartner] set to `true`.
  Future<PartnerState> _loadAllData() async {
    final results = await Future.wait([
      _repo.getPartnerInfo(),
      _repo.getPartnerCodes(),
      _repo.getEarnings(),
    ]);

    final infoResult = results[0] as Result<PartnerInfo>;
    final codesResult = results[1] as Result<List<PartnerCode>>;
    final earningsResult = results[2] as Result<List<Earnings>>;

    final info = switch (infoResult) {
      Success(:final data) => data,
      Failure(:final failure) => throw failure,
    };
    final codes = switch (codesResult) {
      Success(:final data) => data,
      Failure(:final failure) => throw failure,
    };
    final earnings = switch (earningsResult) {
      Success(:final data) => data,
      Failure(:final failure) => throw failure,
    };

    return PartnerState(
      isAvailable: true,
      isPartner: true,
      partnerInfo: info,
      partnerCodes: codes,
      earnings: earnings,
    );
  }
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

/// Primary partner state provider backed by [PartnerNotifier].
final partnerProvider =
    AsyncNotifierProvider.autoDispose<PartnerNotifier, PartnerState>(
  PartnerNotifier.new,
);

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// Whether the partner feature is available on the backend.
final isPartnerAvailableProvider = Provider.autoDispose<bool>((ref) {
  final partnerState = ref.watch(partnerProvider).value;
  return partnerState?.isAvailable ?? false;
});

/// Whether the current user is a partner.
final isPartnerProvider = Provider.autoDispose<bool>((ref) {
  final partnerState = ref.watch(partnerProvider).value;
  return partnerState?.isPartner ?? false;
});

/// Partner information for the current user.
final partnerInfoProvider = Provider.autoDispose<PartnerInfo?>((ref) {
  final partnerState = ref.watch(partnerProvider).value;
  return partnerState?.partnerInfo;
});

/// List of partner codes.
final partnerCodesProvider = Provider.autoDispose<List<PartnerCode>>((ref) {
  final partnerState = ref.watch(partnerProvider).value;
  return partnerState?.partnerCodes ?? [];
});

/// Earnings history.
final partnerEarningsProvider = Provider.autoDispose<List<Earnings>>((ref) {
  final partnerState = ref.watch(partnerProvider).value;
  return partnerState?.earnings ?? [];
});
