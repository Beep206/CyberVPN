import 'package:cybervpn_mobile/core/errors/failures.dart' as errors;

/// Re-export the base failure type under a non-colliding name.
///
/// The existing failure hierarchy in `core/errors/failures.dart` uses the
/// name `Failure` for the base class. Because this file also defines a
/// [Failure] class (the [Result] variant), we re-export the base failure
/// type as [AppFailure] to avoid ambiguity.
///
/// All existing failure subtypes ([errors.ServerFailure],
/// [errors.NetworkFailure], etc.) extend [AppFailure] and can be used
/// directly when constructing [Failure] result variants:
///
/// ```dart
/// import 'package:cybervpn_mobile/core/types/result.dart';
/// import 'package:cybervpn_mobile/core/errors/failures.dart' as errors;
///
/// Result<User> fetchUser() {
///   return const Failure(errors.ServerFailure(message: 'Not found', code: 404));
/// }
/// ```
typedef AppFailure = errors.Failure;

/// A sealed type representing either a successful result or a failure.
///
/// Used throughout the repository and use case layers to provide
/// type-safe error handling without relying on exceptions for control flow.
///
/// Example usage with pattern matching:
/// ```dart
/// final result = await repository.fetchUser(id);
/// switch (result) {
///   case Success(:final data):
///     print('User: ${data.name}');
///   case Failure(:final failure):
///     print('Error: ${failure.message}');
/// }
/// ```
///
/// Or using the [when] extension:
/// ```dart
/// result.when(
///   success: (user) => showUser(user),
///   failure: (error) => showError(error.message),
/// );
/// ```
sealed class Result<T> {
  const Result();
}

/// Represents a successful operation with a [data] payload.
final class Success<T> extends Result<T> {
  const Success(this.data);

  /// The successful result data.
  final T data;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Success<T> &&
          runtimeType == other.runtimeType &&
          data == other.data;

  @override
  int get hashCode => data.hashCode;

  @override
  String toString() => 'Success($data)';
}

/// Represents a failed operation with a [failure] payload.
final class Failure<T> extends Result<T> {
  const Failure(this.failure);

  /// The failure that caused the operation to fail.
  final AppFailure failure;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Failure<T> &&
          runtimeType == other.runtimeType &&
          failure == other.failure;

  @override
  int get hashCode => failure.hashCode;

  @override
  String toString() => 'Failure($failure)';
}

/// Extension methods for convenient pattern matching on [Result].
extension ResultExtension<T> on Result<T> {
  /// Returns the success data if this is a [Success], or `null` if it is
  /// a [Failure].
  T? get dataOrNull => switch (this) {
        Success(:final data) => data,
        Failure() => null,
      };

  /// Returns the [AppFailure] if this is a [Failure], or `null` if it is
  /// a [Success].
  AppFailure? get failureOrNull => switch (this) {
        Success() => null,
        Failure(:final failure) => failure,
      };

  /// Whether this result represents a successful operation.
  bool get isSuccess => this is Success<T>;

  /// Whether this result represents a failed operation.
  bool get isFailure => this is Failure<T>;

  /// Exhaustive pattern match on this [Result].
  ///
  /// Both [success] and [failure] callbacks are required, ensuring that
  /// all cases are handled.
  R when<R>({
    required R Function(T data) success,
    required R Function(AppFailure failure) failure,
  }) {
    return switch (this) {
      Success(:final data) => success(data),
      Failure(failure: final f) => failure(f),
    };
  }

  /// Maps the success value using [transform], leaving failures untouched.
  ///
  /// Useful for transforming data between layers (e.g. model to entity).
  Result<R> map<R>(R Function(T data) transform) => switch (this) {
        Success(:final data) => Success(transform(data)),
        Failure(:final failure) => Failure(failure),
      };

  /// Maps the success value using [transform] which itself returns a
  /// [Result], allowing chaining of fallible operations.
  Result<R> flatMap<R>(Result<R> Function(T data) transform) => switch (this) {
        Success(:final data) => transform(data),
        Failure(:final failure) => Failure(failure),
      };
}
