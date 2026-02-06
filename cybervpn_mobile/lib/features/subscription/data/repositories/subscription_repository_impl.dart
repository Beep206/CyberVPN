import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
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
  Future<Result<List<PlanEntity>>> getPlans() async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      final plans = await _remoteDataSource.fetchPlans();
      return Success(plans);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<SubscriptionEntity?>> getActiveSubscription() async {
    if (!await _networkInfo.isConnected) {
      return const Success(null);
    }
    try {
      final subscription = await _remoteDataSource.fetchActiveSubscription();
      return Success(subscription);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<SubscriptionEntity>> subscribe(String planId, {String? paymentMethod}) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      final subscription = await _remoteDataSource.createSubscription(planId, paymentMethod: paymentMethod);
      return Success(subscription);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<void>> cancelSubscription(String subscriptionId) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      await _remoteDataSource.cancelSubscription(subscriptionId);
      return const Success(null);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<void>> restorePurchases() async {
    // RevenueCat handles restore; this is a placeholder
    return const Success(null);
  }
}
