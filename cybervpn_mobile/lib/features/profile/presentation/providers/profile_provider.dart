import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/setup_2fa_result.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/features/profile/domain/services/device_registration_service.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/disable_2fa.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/get_devices.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/get_profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/link_social_account.dart'
    show LinkSocialAccountUseCase, CompleteSocialAccountLinkUseCase;
import 'package:cybervpn_mobile/features/profile/domain/use_cases/register_device.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/remove_device.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/setup_2fa.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/unlink_social_account.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/verify_2fa.dart';

// ---------------------------------------------------------------------------
// Repository & use-case providers (override in DI setup / tests)
// ---------------------------------------------------------------------------

/// Provides the [ProfileRepository] implementation.
///
/// Must be overridden in a [ProviderScope] with a configured instance.
final profileRepositoryProvider = Provider<ProfileRepository>((ref) {
  throw UnimplementedError(
    'profileRepositoryProvider must be overridden with a concrete '
    'ProfileRepository (e.g. via ProviderScope overrides).',
  );
});

/// Provides the [GetProfileUseCase].
final getProfileUseCaseProvider = Provider<GetProfileUseCase>((ref) {
  return GetProfileUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [Setup2FAUseCase].
final setup2FAUseCaseProvider = Provider<Setup2FAUseCase>((ref) {
  return Setup2FAUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [Verify2FAUseCase].
final verify2FAUseCaseProvider = Provider<Verify2FAUseCase>((ref) {
  return Verify2FAUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [Disable2FAUseCase].
final disable2FAUseCaseProvider = Provider<Disable2FAUseCase>((ref) {
  return Disable2FAUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [GetDevicesUseCase].
final getDevicesUseCaseProvider = Provider<GetDevicesUseCase>((ref) {
  return GetDevicesUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [RemoveDeviceUseCase].
final removeDeviceUseCaseProvider = Provider<RemoveDeviceUseCase>((ref) {
  return RemoveDeviceUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [RegisterDeviceUseCase].
final registerDeviceUseCaseProvider = Provider<RegisterDeviceUseCase>((ref) {
  return RegisterDeviceUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides [SecureStorageWrapper] for device registration.
final secureStorageWrapperProvider = Provider<SecureStorageWrapper>((ref) {
  return SecureStorageWrapper();
});

/// Provides the [DeviceRegistrationService].
final deviceRegistrationServiceProvider =
    Provider<DeviceRegistrationService>((ref) {
  return DeviceRegistrationService(
    registerDevice: ref.watch(registerDeviceUseCaseProvider),
    storage: ref.watch(secureStorageWrapperProvider),
  );
});

/// Provides the [LinkSocialAccountUseCase].
final linkSocialAccountUseCaseProvider =
    Provider<LinkSocialAccountUseCase>((ref) {
  return LinkSocialAccountUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [CompleteSocialAccountLinkUseCase].
final completeSocialAccountLinkUseCaseProvider =
    Provider<CompleteSocialAccountLinkUseCase>((ref) {
  return CompleteSocialAccountLinkUseCase(ref.watch(profileRepositoryProvider));
});

/// Provides the [UnlinkSocialAccountUseCase].
final unlinkSocialAccountUseCaseProvider =
    Provider<UnlinkSocialAccountUseCase>((ref) {
  return UnlinkSocialAccountUseCase(ref.watch(profileRepositoryProvider));
});

// ---------------------------------------------------------------------------
// Profile State
// ---------------------------------------------------------------------------

/// Immutable state for the profile feature.
class ProfileState {
  const ProfileState({
    this.profile,
    this.devices = const [],
  });

  /// The user's profile data, or null if not yet loaded.
  final Profile? profile;

  /// Active device sessions associated with the account.
  final List<Device> devices;

  /// Whether two-factor authentication is enabled on the account.
  bool get is2FAEnabled => profile?.is2FAEnabled ?? false;

  /// List of linked OAuth providers on the account.
  List<OAuthProvider> get linkedProviders =>
      profile?.linkedProviders ?? const [];

  /// Number of linked OAuth provider accounts.
  int get linkedAccountsCount => linkedProviders.length;

  ProfileState copyWith({
    Profile? Function()? profile,
    List<Device>? devices,
  }) {
    return ProfileState(
      profile: profile != null ? profile() : this.profile,
      devices: devices ?? this.devices,
    );
  }
}

// ---------------------------------------------------------------------------
// ProfileNotifier
// ---------------------------------------------------------------------------

/// Manages user profile state including 2FA, linked accounts, and devices.
///
/// On [build] it loads the user profile and device list. Subsequent
/// mutations update the inner [ProfileState] and re-fetch data
/// from the backend as needed.
class ProfileNotifier extends AsyncNotifier<ProfileState> {
  late final GetProfileUseCase _getProfile;
  late final Setup2FAUseCase _setup2FA;
  late final Verify2FAUseCase _verify2FA;
  late final Disable2FAUseCase _disable2FA;
  late final GetDevicesUseCase _getDevices;
  late final RemoveDeviceUseCase _removeDevice;
  late final LinkSocialAccountUseCase _linkSocialAccount;
  late final CompleteSocialAccountLinkUseCase _completeSocialAccountLink;
  late final UnlinkSocialAccountUseCase _unlinkSocialAccount;

  // ---- Lifecycle -----------------------------------------------------------

  @override
  FutureOr<ProfileState> build() async {
    _getProfile = ref.watch(getProfileUseCaseProvider);
    _setup2FA = ref.watch(setup2FAUseCaseProvider);
    _verify2FA = ref.watch(verify2FAUseCaseProvider);
    _disable2FA = ref.watch(disable2FAUseCaseProvider);
    _getDevices = ref.watch(getDevicesUseCaseProvider);
    _removeDevice = ref.watch(removeDeviceUseCaseProvider);
    _linkSocialAccount = ref.watch(linkSocialAccountUseCaseProvider);
    _completeSocialAccountLink = ref.watch(completeSocialAccountLinkUseCaseProvider);
    _unlinkSocialAccount = ref.watch(unlinkSocialAccountUseCaseProvider);

    final profileResult = await _getProfile.call();
    final devicesResult = await _getDevices.call();

    final profile = switch (profileResult) {
      Success(:final data) => data,
      Failure(:final failure) => throw failure,
    };
    final devices = switch (devicesResult) {
      Success(:final data) => data,
      Failure(:final failure) => throw failure,
    };

    return ProfileState(profile: profile, devices: devices);
  }

  // ---- Public API ----------------------------------------------------------

  /// Refreshes the user profile and device list from the backend.
  Future<void> refreshProfile() async {
    state = const AsyncLoading();
    try {
      final profileResult = await _getProfile.call();
      final devicesResult = await _getDevices.call();

      final profile = switch (profileResult) {
        Success(:final data) => data,
        Failure(:final failure) => throw failure,
      };
      final devices = switch (devicesResult) {
        Success(:final data) => data,
        Failure(:final failure) => throw failure,
      };

      state = AsyncData(ProfileState(profile: profile, devices: devices));
    } catch (e, st) {
      AppLogger.error('Failed to refresh profile', error: e, stackTrace: st);
      state = AsyncError(e, st);
    }
  }

  // -- Two-Factor Authentication ---------------------------------------------

  /// Initiates 2FA setup and returns the secret + QR code URI.
  Future<Setup2FAResult> setup2FA() async {
    try {
      final result = await _setup2FA.call();
      final data = switch (result) {
        Success(:final data) => data,
        Failure(:final failure) => throw failure,
      };
      AppLogger.info('2FA setup initiated');
      return data;
    } catch (e, st) {
      AppLogger.error('Failed to setup 2FA', error: e, stackTrace: st);
      rethrow;
    }
  }

  /// Verifies a TOTP code during 2FA setup and updates state.
  ///
  /// Returns `true` if the code was valid and 2FA is now enabled.
  Future<bool> verify2FA(String code) async {
    try {
      final verifyResult = await _verify2FA.call(code);
      final success = switch (verifyResult) {
        Success(:final data) => data,
        Failure(:final failure) => throw failure,
      };
      if (success) {
        // Refresh profile to pick up the new 2FA-enabled status.
        final profileResult = await _getProfile.call();
        final profile = profileResult.dataOrNull;
        final current = state.value;
        if (current != null) {
          state = AsyncData(current.copyWith(profile: () => profile));
        }
        AppLogger.info('2FA verified and enabled');
      }
      return success;
    } catch (e, st) {
      AppLogger.error('Failed to verify 2FA', error: e, stackTrace: st);
      rethrow;
    }
  }

  /// Disables 2FA on the account using the provided TOTP [code].
  Future<void> disable2FA(String code) async {
    try {
      final disableResult = await _disable2FA.call(code);
      switch (disableResult) {
        case Success():
          break;
        case Failure(:final failure):
          throw failure;
      }
      // Refresh profile to pick up the new 2FA-disabled status.
      final profileResult = await _getProfile.call();
      final profile = profileResult.dataOrNull;
      final current = state.value;
      if (current != null) {
        state = AsyncData(current.copyWith(profile: () => profile));
      }
      AppLogger.info('2FA disabled');
    } catch (e, st) {
      AppLogger.error('Failed to disable 2FA', error: e, stackTrace: st);
      rethrow;
    }
  }

  // -- Device Management -----------------------------------------------------

  /// Removes a device session by its ID.
  ///
  /// Requires [currentDeviceId] to prevent removing the current device.
  /// Updates state with the refreshed device list after successful removal.
  Future<void> removeDevice({
    required String deviceId,
    required String currentDeviceId,
  }) async {
    try {
      final removeResult = await _removeDevice.call(
        deviceId: deviceId,
        currentDeviceId: currentDeviceId,
      );
      switch (removeResult) {
        case Success():
          break;
        case Failure(:final failure):
          throw failure;
      }

      // Refresh devices list to reflect the removal
      final devicesResult = await _getDevices.call();
      final devices = switch (devicesResult) {
        Success(:final data) => data,
        Failure(:final failure) => throw failure,
      };
      final current = state.value;
      if (current != null) {
        state = AsyncData(current.copyWith(devices: devices));
      }
      AppLogger.info('Device removed: $deviceId');
    } catch (e, st) {
      AppLogger.error('Failed to remove device', error: e, stackTrace: st);
      rethrow;
    }
  }

  // -- OAuth Provider Linking ------------------------------------------------

  /// Gets the OAuth authorization URL for Telegram.
  /// The caller must open this URL in a browser.
  Future<String> getTelegramAuthUrl() async {
    return _getAuthUrl(OAuthProvider.telegram);
  }

  /// Gets the OAuth authorization URL for GitHub.
  /// The caller must open this URL in a browser.
  Future<String> getGithubAuthUrl() async {
    return _getAuthUrl(OAuthProvider.github);
  }

  /// Completes the OAuth linking flow with the authorization code.
  Future<void> completeOAuthLink(OAuthProvider provider, String code) async {
    try {
      final linkResult = await _completeSocialAccountLink.call(provider: provider, code: code);
      switch (linkResult) {
        case Success():
          break;
        case Failure(:final failure):
          throw failure;
      }
      // Refresh profile to pick up the updated linked providers list.
      final profileResult = await _getProfile.call();
      final profile = profileResult.dataOrNull;
      final current = state.value;
      if (current != null) {
        state = AsyncData(current.copyWith(profile: () => profile));
      }
      AppLogger.info('Completed OAuth link for ${provider.name}');
    } catch (e, st) {
      AppLogger.error(
        'Failed to complete OAuth link for ${provider.name}',
        error: e,
        stackTrace: st,
      );
      rethrow;
    }
  }

  /// Unlinks the specified OAuth [provider] from the user's account.
  Future<void> unlinkAccount(OAuthProvider provider) async {
    final current = state.value;
    if (current == null) return;

    try {
      final unlinkResult = await _unlinkSocialAccount.call(
        provider: provider,
        currentlyLinked: current.linkedProviders,
      );
      switch (unlinkResult) {
        case Success():
          break;
        case Failure(:final failure):
          throw failure;
      }
      // Refresh profile to pick up the updated linked providers list.
      final profileResult = await _getProfile.call();
      final profile = profileResult.dataOrNull;
      state = AsyncData(current.copyWith(profile: () => profile));
      AppLogger.info('Unlinked ${provider.name}');
    } catch (e, st) {
      AppLogger.error(
        'Failed to unlink ${provider.name}',
        error: e,
        stackTrace: st,
      );
      rethrow;
    }
  }

  // ---- Private helpers -----------------------------------------------------

  /// Gets the OAuth authorization URL for the given [provider].
  Future<String> _getAuthUrl(OAuthProvider provider) async {
    final current = state.value;
    if (current == null) {
      throw StateError('Profile not loaded');
    }

    try {
      final result = await _linkSocialAccount.call(
        provider: provider,
        currentlyLinked: current.linkedProviders,
      );
      return switch (result) {
        Success(:final data) => data,
        Failure(:final failure) => throw failure,
      };
    } catch (e, st) {
      AppLogger.error(
        'Failed to get auth URL for ${provider.name}',
        error: e,
        stackTrace: st,
      );
      rethrow;
    }
  }
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

/// Primary profile state provider backed by [ProfileNotifier].
final profileProvider =
    AsyncNotifierProvider<ProfileNotifier, ProfileState>(
  ProfileNotifier.new,
);

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// Whether two-factor authentication is currently enabled.
final is2FAEnabledProvider = Provider<bool>((ref) {
  final profileState = ref.watch(profileProvider).value;
  return profileState?.is2FAEnabled ?? false;
});

/// The list of linked OAuth providers on the account.
final linkedAccountsProvider = Provider<List<OAuthProvider>>((ref) {
  final profileState = ref.watch(profileProvider).value;
  return profileState?.linkedProviders ?? [];
});

/// The number of linked OAuth provider accounts.
final linkedAccountsCountProvider = Provider<int>((ref) {
  final profileState = ref.watch(profileProvider).value;
  return profileState?.linkedAccountsCount ?? 0;
});

/// The list of active device sessions.
final devicesListProvider = Provider<List<Device>>((ref) {
  final profileState = ref.watch(profileProvider).value;
  return profileState?.devices ?? [];
});

/// The user's profile data, or null if not yet loaded.
final userProfileProvider = Provider<Profile?>((ref) {
  final profileState = ref.watch(profileProvider).value;
  return profileState?.profile;
});
