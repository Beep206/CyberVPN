import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_remote_ds.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/repositories/subscription_repository.dart';

class SubscriptionRepositoryImpl with NetworkErrorHandler implements SubscriptionRepository {
  final SubscriptionRemoteDataSource _remoteDataSource;
  final NetworkInfo _networkInfo;

  SubscriptionRepositoryImpl({required SubscriptionRemoteDataSource remoteDataSource, required NetworkInfo networkInfo})
      : _remoteDataSource = remoteDataSource,
        _networkInfo = networkInfo;

  @override
  Future<List<PlanEntity>> getPlans() async {
    if (!await _networkInfo.isConnected) {
      throw const NetworkFailure(message: 'No internet connection');
    }
    return _remoteDataSource.fetchPlans();
  }

  @override
  Future<SubscriptionEntity?> getActiveSubscription() async {
    if (!await _networkInfo.isConnected) return null;
    return _remoteDataSource.fetchActiveSubscription();
  }

  @override
  Future<SubscriptionEntity> subscribe(String planId, {String? paymentMethod}) async {
    if (!await _networkInfo.isConnected) {
      throw const NetworkFailure(message: 'No internet connection');
    }
    return _remoteDataSource.createSubscription(planId, paymentMethod: paymentMethod);
  }

  @override
  Future<void> cancelSubscription(String subscriptionId) async {
    if (!await _networkInfo.isConnected) {
      throw const NetworkFailure(message: 'No internet connection');
    }
    await _remoteDataSource.cancelSubscription(subscriptionId);
  }

  @override
  Future<void> restorePurchases() async {
    // RevenueCat handles restore; this is a placeholder
  }
}
