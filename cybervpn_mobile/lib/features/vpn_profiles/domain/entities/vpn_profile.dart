import 'package:freezed_annotation/freezed_annotation.dart';

import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';

part 'vpn_profile.freezed.dart';

@freezed
sealed class VpnProfile with _$VpnProfile {
  /// A profile backed by a remote subscription URL.
  const factory VpnProfile.remote({
    required String id,
    required String name,
    required String subscriptionUrl,
    @Default(false) bool isActive,
    required int sortOrder,
    required DateTime createdAt,
    DateTime? lastUpdatedAt,
    @Default(0) int uploadBytes,
    @Default(0) int downloadBytes,
    @Default(0) int totalBytes,
    DateTime? expiresAt,
    @Default(60) int updateIntervalMinutes,
    String? supportUrl,
    String? testUrl,
    @Default([]) List<ProfileServer> servers,
  }) = RemoteVpnProfile;

  /// A profile created from locally-imported configurations.
  const factory VpnProfile.local({
    required String id,
    required String name,
    @Default(false) bool isActive,
    required int sortOrder,
    required DateTime createdAt,
    DateTime? lastUpdatedAt,
    @Default([]) List<ProfileServer> servers,
  }) = LocalVpnProfile;
}
