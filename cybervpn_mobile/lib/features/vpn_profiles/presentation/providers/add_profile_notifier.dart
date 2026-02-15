import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';

/// Screen-scoped async notifier for the "Add Profile" flow.
///
/// State machine:
/// ```
/// idle → fetching → preview → saving → done
///                  ↘ error (retry → fetching)
/// ```
///
/// Auto-disposed when the AddByUrlScreen is popped from the navigator.
class AddProfileNotifier
    extends AsyncNotifier<AddProfileState> {
  @override
  Future<AddProfileState> build() async {
    return const AddProfileState.idle();
  }

  /// Fetches a subscription URL and transitions to preview or error.
  Future<void> addByUrl(String url, {String? name}) async {
    state = const AsyncData(AddProfileState.fetching());

    final result = await ref
        .read(addRemoteProfileUseCaseProvider)
        .call(url, name: name);

    switch (result) {
      case Success(:final data):
        state = AsyncData(AddProfileState.preview(profile: data));
      case Failure(:final failure):
        state = AsyncData(
          AddProfileState.error(message: failure.toString()),
        );
    }
  }

  /// Creates a profile from an existing imported config set.
  Future<void> addFromImport(String url, {String? name}) async {
    state = const AsyncData(AddProfileState.fetching());

    final result = await ref
        .read(addRemoteProfileUseCaseProvider)
        .call(url, name: name);

    switch (result) {
      case Success(:final data):
        state = AsyncData(AddProfileState.done(profile: data));
      case Failure(:final failure):
        state = AsyncData(
          AddProfileState.error(message: failure.toString()),
        );
    }
  }

  /// Confirms and activates the previewed profile.
  Future<void> confirmSave() async {
    final current = state.value;
    if (current is! _Preview) return;

    state = const AsyncData(AddProfileState.saving());

    // The profile was already persisted during addByUrl; just set it active.
    final result = await ref
        .read(switchActiveProfileUseCaseProvider)
        .call(current.profile.id);

    switch (result) {
      case Success():
        state = AsyncData(AddProfileState.done(profile: current.profile));
      case Failure(:final failure):
        state = AsyncData(
          AddProfileState.error(message: failure.toString()),
        );
    }
  }

  /// Resets to idle for retry.
  void reset() {
    state = const AsyncData(AddProfileState.idle());
  }
}

/// State machine for the add-profile flow.
sealed class AddProfileState {
  const AddProfileState();

  const factory AddProfileState.idle() = _Idle;
  const factory AddProfileState.fetching() = _Fetching;
  const factory AddProfileState.preview({required VpnProfile profile}) =
      _Preview;
  const factory AddProfileState.saving() = _Saving;
  const factory AddProfileState.done({required VpnProfile profile}) = _Done;
  const factory AddProfileState.error({required String message}) = _Error;

  bool get isLoading =>
      this is _Fetching || this is _Saving;
}

class _Idle extends AddProfileState {
  const _Idle();
}

class _Fetching extends AddProfileState {
  const _Fetching();
}

class _Preview extends AddProfileState {
  const _Preview({required this.profile});
  final VpnProfile profile;
}

class _Saving extends AddProfileState {
  const _Saving();
}

class _Done extends AddProfileState {
  const _Done({required this.profile});
  final VpnProfile profile;
}

class _Error extends AddProfileState {
  const _Error({required this.message});
  final String message;
}

/// Screen-scoped provider for [AddProfileNotifier].
///
/// Auto-disposed when AddByUrlScreen leaves the widget tree.
final addProfileNotifierProvider =
    AsyncNotifierProvider.autoDispose<AddProfileNotifier, AddProfileState>(
  AddProfileNotifier.new,
);
