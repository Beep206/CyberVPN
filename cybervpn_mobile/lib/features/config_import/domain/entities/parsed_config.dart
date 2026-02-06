import 'package:freezed_annotation/freezed_annotation.dart';

part 'parsed_config.freezed.dart';

/// Represents a parsed VPN configuration from a URI
@freezed
sealed class ParsedConfig with _$ParsedConfig {
  const factory ParsedConfig({
    required String protocol,
    required String serverAddress,
    required int port,
    required String uuid,
    String? password,
    String? remark,
    Map<String, dynamic>? transportSettings,
    Map<String, dynamic>? tlsSettings,
    Map<String, dynamic>? additionalParams,
  }) = _ParsedConfig;
}
