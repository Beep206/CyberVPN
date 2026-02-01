import 'package:freezed_annotation/freezed_annotation.dart';

part 'imported_config.freezed.dart';

/// Source of the imported configuration
enum ImportSource {
  qrCode,
  clipboard,
  deepLink,
  subscriptionUrl,
  manual,
}

/// Represents an imported VPN configuration
@freezed
abstract class ImportedConfig with _$ImportedConfig {
  const factory ImportedConfig({
    required String id,
    required String name,
    required String rawUri,
    required String protocol,
    required String serverAddress,
    required int port,
    required ImportSource source,
    String? subscriptionUrl,
    required DateTime importedAt,
    DateTime? lastTestedAt,
    bool? isReachable,
  }) = _ImportedConfig;
}
