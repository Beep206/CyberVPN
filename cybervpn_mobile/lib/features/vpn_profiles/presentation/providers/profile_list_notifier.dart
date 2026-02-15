import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
/// App-scoped notifier managing the profile list state.
///
/// Delegates to use cases for mutations; the underlying
/// [profileListProvider] stream handles data updates automatically.
///
/// Actions:
/// - [reorder] — persist a new sort order
/// - [deleteProfile] — delete a profile by ID
/// - [switchProfile] — set a profile as active
/// - [refreshSubscriptions] — refresh all due remote subscriptions
class ProfileListNotifier extends Notifier<ProfileListState> {
  @override
  ProfileListState build() {
    return const ProfileListState();
  }

  /// Reorders profiles to match the given [profileIds] sequence.
  Future<void> reorder(List<String> profileIds) async {
    state = state.copyWith(isReordering: true);

    final result = await ref
        .read(vpnProfileRepositoryProvider)
        .reorder(profileIds);

    switch (result) {
      case Success():
        state = state.copyWith(isReordering: false);
      case Failure(:final failure):
        state = state.copyWith(
          isReordering: false,
          error: failure.toString(),
        );
    }
  }

  /// Deletes the profile with [profileId].
  Future<Result<void>> deleteProfile(String profileId) async {
    state = state.copyWith(deletingId: profileId);

    final result = await ref
        .read(deleteProfileUseCaseProvider)
        .call(profileId);

    state = state.copyWith(deletingId: null);
    return result;
  }

  /// Switches the active profile to [profileId].
  Future<Result<void>> switchProfile(String profileId) async {
    state = state.copyWith(switchingToId: profileId);

    final result = await ref
        .read(switchActiveProfileUseCaseProvider)
        .call(profileId);

    state = state.copyWith(switchingToId: null);
    return result;
  }

  /// Refreshes all remote subscriptions that are due for update.
  ///
  /// Returns the number of profiles updated, or a failure.
  Future<Result<int>> refreshSubscriptions() async {
    state = state.copyWith(isRefreshing: true);

    final result = await ref
        .read(updateSubscriptionsUseCaseProvider)
        .call();

    state = state.copyWith(isRefreshing: false);
    return result;
  }

  /// Clears any transient error.
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Immutable state for [ProfileListNotifier].
///
/// The actual profile list data comes from [profileListProvider] (stream).
/// This state only tracks transient UI state for mutations.
class ProfileListState {
  const ProfileListState({
    this.isRefreshing = false,
    this.isReordering = false,
    this.deletingId,
    this.switchingToId,
    this.error,
  });

  /// Whether a subscription refresh is in progress.
  final bool isRefreshing;

  /// Whether a reorder operation is in progress.
  final bool isReordering;

  /// The profile ID currently being deleted, or `null`.
  final String? deletingId;

  /// The profile ID being switched to, or `null`.
  final String? switchingToId;

  /// Human-readable error from the last failed operation.
  final String? error;

  ProfileListState copyWith({
    bool? isRefreshing,
    bool? isReordering,
    String? deletingId,
    String? switchingToId,
    String? error,
  }) {
    return ProfileListState(
      isRefreshing: isRefreshing ?? this.isRefreshing,
      isReordering: isReordering ?? this.isReordering,
      deletingId: deletingId,
      switchingToId: switchingToId,
      error: error,
    );
  }
}

/// App-scoped provider for [ProfileListNotifier].
///
/// Not auto-disposed because profile mutations can be triggered from
/// multiple screens (list, detail, connection).
final profileListNotifierProvider =
    NotifierProvider<ProfileListNotifier, ProfileListState>(
  ProfileListNotifier.new,
);
