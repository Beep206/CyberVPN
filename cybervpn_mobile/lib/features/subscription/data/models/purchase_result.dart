/// Represents the outcome of an in-app purchase attempt.
///
/// Named [AppPurchaseResult] to avoid collision with RevenueCat's own
/// `PurchaseResult` class from `purchases_flutter`.
class AppPurchaseResult {
  const AppPurchaseResult({
    required this.isSuccess,
    required this.productId,
    this.transactionId,
    this.entitlementId,
    this.expirationDate,
    this.isCancelled = false,
    this.errorMessage,
    this.errorCode,
  });

  /// Whether the purchase completed successfully.
  final bool isSuccess;

  /// The store product identifier that was purchased.
  final String productId;

  /// Platform transaction ID (e.g. Google Play order ID or App Store txn).
  final String? transactionId;

  /// The RevenueCat entitlement identifier granted, if any.
  final String? entitlementId;

  /// When the purchased entitlement expires (null for lifetime).
  final DateTime? expirationDate;

  /// Whether the user explicitly cancelled the purchase flow.
  final bool isCancelled;

  /// Human-readable error message when [isSuccess] is false.
  final String? errorMessage;

  /// Machine-readable error code from the store / RevenueCat.
  final String? errorCode;

  /// Convenience factory for a successful purchase.
  factory AppPurchaseResult.success({
    required String productId,
    String? transactionId,
    String? entitlementId,
    DateTime? expirationDate,
  }) {
    return AppPurchaseResult(
      isSuccess: true,
      productId: productId,
      transactionId: transactionId,
      entitlementId: entitlementId,
      expirationDate: expirationDate,
    );
  }

  /// Convenience factory for a cancelled purchase.
  factory AppPurchaseResult.cancelled({required String productId}) {
    return AppPurchaseResult(
      isSuccess: false,
      productId: productId,
      isCancelled: true,
      errorMessage: 'Purchase was cancelled by the user.',
      errorCode: 'CANCELLED',
    );
  }

  /// Convenience factory for a failed purchase.
  factory AppPurchaseResult.failure({
    required String productId,
    required String errorMessage,
    String? errorCode,
  }) {
    return AppPurchaseResult(
      isSuccess: false,
      productId: productId,
      errorMessage: errorMessage,
      errorCode: errorCode,
    );
  }

  @override
  String toString() =>
      'AppPurchaseResult(isSuccess: $isSuccess, productId: $productId, '
      'transactionId: $transactionId, isCancelled: $isCancelled)';
}
