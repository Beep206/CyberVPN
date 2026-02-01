import 'package:flutter/services.dart';
import 'package:purchases_flutter/purchases_flutter.dart'
    hide PurchaseResult; // Hide RevenueCat's PurchaseResult to avoid ambiguity.

import 'package:cybervpn_mobile/features/subscription/data/models/purchase_result.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';

/// Data source that wraps the RevenueCat Purchases SDK.
///
/// Responsible for initializing the SDK, fetching offerings, performing
/// purchases, restoring transactions, and mapping RevenueCat models into
/// the app's domain entities.
class RevenueCatDataSource {
  RevenueCatDataSource();

  bool _isInitialized = false;

  // ---------------------------------------------------------------------------
  // Initialization
  // ---------------------------------------------------------------------------

  /// Configure the RevenueCat SDK with the given [apiKey].
  ///
  /// Must be called once before any other method. Typically invoked during
  /// app startup.
  Future<void> initialize(String apiKey) async {
    if (_isInitialized) return;

    final configuration = PurchasesConfiguration(apiKey);
    await Purchases.configure(configuration);

    _isInitialized = true;
  }

  /// Set the RevenueCat app user ID (call after user login).
  Future<void> setUserId(String userId) async {
    _assertInitialized();
    await Purchases.logIn(userId);
  }

  /// Reset to anonymous user (call on logout).
  Future<void> resetUser() async {
    _assertInitialized();
    await Purchases.logOut();
  }

  // ---------------------------------------------------------------------------
  // Offerings
  // ---------------------------------------------------------------------------

  /// Fetch current offerings from RevenueCat and map to domain [PlanEntity].
  Future<List<PlanEntity>> getOfferings() async {
    _assertInitialized();

    final offerings = await Purchases.getOfferings();
    final current = offerings.current;
    if (current == null) return [];

    return current.availablePackages
        .map(_mapPackageToPlanEntity)
        .toList();
  }

  // ---------------------------------------------------------------------------
  // Purchases
  // ---------------------------------------------------------------------------

  /// Purchase a specific [Package] and return an [AppPurchaseResult].
  ///
  /// Uses the non-deprecated `Purchases.purchase(PurchaseParams)` API.
  /// Handles common RevenueCat error codes and maps them to a typed result.
  Future<AppPurchaseResult> purchase(Package package) async {
    _assertInitialized();

    try {
      final result = await Purchases.purchase(PurchaseParams.package(package));
      final customerInfo = result.customerInfo;

      // Determine the entitlement granted.
      final entitlements = customerInfo.entitlements.active;
      String? entitlementId;
      DateTime? expiration;

      if (entitlements.isNotEmpty) {
        final entry = entitlements.entries.first;
        entitlementId = entry.key;
        final expirationStr = entry.value.expirationDate;
        if (expirationStr != null) {
          expiration = DateTime.tryParse(expirationStr);
        }
      }

      return AppPurchaseResult.success(
        productId: package.storeProduct.identifier,
        transactionId: result.storeTransaction.transactionIdentifier,
        entitlementId: entitlementId,
        expirationDate: expiration,
      );
    } on PlatformException catch (e) {
      final errorCode = PurchasesErrorHelper.getErrorCode(e);

      switch (errorCode) {
        case PurchasesErrorCode.purchaseCancelledError:
          return AppPurchaseResult.cancelled(
            productId: package.storeProduct.identifier,
          );

        case PurchasesErrorCode.storeProblemError:
          return AppPurchaseResult.failure(
            productId: package.storeProduct.identifier,
            errorMessage:
                'There was a problem with the app store. Please try again later.',
            errorCode: 'STORE_PROBLEM',
          );

        case PurchasesErrorCode.purchaseNotAllowedError:
          return AppPurchaseResult.failure(
            productId: package.storeProduct.identifier,
            errorMessage:
                'Purchases are not allowed on this device. Please check your settings.',
            errorCode: 'PURCHASE_NOT_ALLOWED',
          );

        case PurchasesErrorCode.productNotAvailableForPurchaseError:
          return AppPurchaseResult.failure(
            productId: package.storeProduct.identifier,
            errorMessage:
                'This product is not currently available for purchase.',
            errorCode: 'PRODUCT_NOT_AVAILABLE',
          );

        default:
          return AppPurchaseResult.failure(
            productId: package.storeProduct.identifier,
            errorMessage: e.message ?? 'An unknown purchase error occurred.',
            errorCode: errorCode.name,
          );
      }
    } catch (e) {
      return AppPurchaseResult.failure(
        productId: package.storeProduct.identifier,
        errorMessage: e.toString(),
        errorCode: 'UNKNOWN',
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Restore
  // ---------------------------------------------------------------------------

  /// Restore previously completed purchases.
  Future<CustomerInfo> restorePurchases() async {
    _assertInitialized();
    return Purchases.restorePurchases();
  }

  // ---------------------------------------------------------------------------
  // Customer Info
  // ---------------------------------------------------------------------------

  /// Get the current customer info (entitlements, subscriptions, etc.).
  Future<CustomerInfo> getCustomerInfo() async {
    _assertInitialized();
    return Purchases.getCustomerInfo();
  }

  // ---------------------------------------------------------------------------
  // Mapping
  // ---------------------------------------------------------------------------

  /// Map a RevenueCat [Package] to the domain [PlanEntity].
  PlanEntity _mapPackageToPlanEntity(Package package) {
    final product = package.storeProduct;

    return PlanEntity(
      id: product.identifier,
      name: product.title,
      description: product.description,
      price: product.price,
      currency: product.currencyCode,
      duration: _mapPackageTypeToDuration(package.packageType),
      durationDays: _packageTypeToDays(package.packageType),
      maxDevices: _defaultMaxDevices,
      trafficLimitGb: _defaultTrafficLimitGb,
      storeProductId: product.identifier,
      features: const [],
    );
  }

  /// Map RevenueCat PackageType to domain PlanDuration.
  PlanDuration _mapPackageTypeToDuration(PackageType type) {
    switch (type) {
      case PackageType.monthly:
        return PlanDuration.monthly;
      case PackageType.threeMonth:
        return PlanDuration.quarterly;
      case PackageType.annual:
        return PlanDuration.yearly;
      case PackageType.lifetime:
        return PlanDuration.lifetime;
      default:
        return PlanDuration.monthly;
    }
  }

  /// Approximate number of days for each package type.
  int _packageTypeToDays(PackageType type) {
    switch (type) {
      case PackageType.weekly:
        return 7;
      case PackageType.monthly:
        return 30;
      case PackageType.twoMonth:
        return 60;
      case PackageType.threeMonth:
        return 90;
      case PackageType.sixMonth:
        return 180;
      case PackageType.annual:
        return 365;
      case PackageType.lifetime:
        return 36500;
      default:
        return 30;
    }
  }

  // ---------------------------------------------------------------------------
  // Defaults & Helpers
  // ---------------------------------------------------------------------------

  static const int _defaultMaxDevices = 5;
  static const int _defaultTrafficLimitGb = 0; // 0 = unlimited

  void _assertInitialized() {
    if (!_isInitialized) {
      throw StateError(
        'RevenueCatDataSource has not been initialized. '
        'Call initialize(apiKey) before using this data source.',
      );
    }
  }
}
