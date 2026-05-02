abstract interface class TelegramNativeAuthClient {
  Future<TelegramNativeAuthResult> login({required bool requestPhone});
}

class TelegramNativeAuthResult {
  final String idToken;
  final String? username;
  final String? displayName;
  final String? phoneNumber;

  const TelegramNativeAuthResult({
    required this.idToken,
    this.username,
    this.displayName,
    this.phoneNumber,
  });
}

sealed class TelegramNativeAuthFailure implements Exception {
  const TelegramNativeAuthFailure();

  String get code;
  String get message;

  @override
  String toString() => '$runtimeType($code): $message';
}

final class TelegramNativeAuthCancelled extends TelegramNativeAuthFailure {
  const TelegramNativeAuthCancelled();

  @override
  String get code => 'CANCELLED';

  @override
  String get message => 'Telegram login was cancelled.';
}

final class TelegramNativeAuthNotConfigured extends TelegramNativeAuthFailure {
  const TelegramNativeAuthNotConfigured();

  @override
  String get code => 'NOT_CONFIGURED';

  @override
  String get message => 'Telegram native login is not configured.';
}

final class TelegramNativeAuthSdkError extends TelegramNativeAuthFailure {
  final String details;

  const TelegramNativeAuthSdkError(this.details);

  @override
  String get code => 'SDK_ERROR';

  @override
  String get message => details;
}
