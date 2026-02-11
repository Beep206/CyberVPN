import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' as failures;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/security/data/datasources/security_remote_ds.dart';
import 'package:cybervpn_mobile/features/security/domain/entities/antiphishing_code.dart';
import 'package:cybervpn_mobile/features/security/domain/repositories/security_repository.dart';

/// Implementation of [SecurityRepository] using remote data source.
class SecurityRepositoryImpl implements SecurityRepository {
  const SecurityRepositoryImpl(this._remoteDataSource);

  final SecurityRemoteDataSource _remoteDataSource;

  @override
  Future<Result<AntiphishingCode>> getAntiphishingCode() async {
    try {
      final code = await _remoteDataSource.getAntiphishingCode();
      return Success(code);
    } on ServerException catch (e) {
      return Failure(failures.ServerFailure(message: e.message, code: e.code));
    } on NetworkException catch (e) {
      return Failure(failures.NetworkFailure(message: e.message, code: e.code));
    } catch (e) {
      return Failure(failures.UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<AntiphishingCode>> setAntiphishingCode(String code) async {
    try {
      final updatedCode = await _remoteDataSource.setAntiphishingCode(code);
      return Success(updatedCode);
    } on ServerException catch (e) {
      return Failure(failures.ServerFailure(message: e.message, code: e.code));
    } on NetworkException catch (e) {
      return Failure(failures.NetworkFailure(message: e.message, code: e.code));
    } catch (e) {
      return Failure(failures.UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<void>> deleteAntiphishingCode() async {
    try {
      await _remoteDataSource.deleteAntiphishingCode();
      return const Success(null);
    } on ServerException catch (e) {
      return Failure(failures.ServerFailure(message: e.message, code: e.code));
    } on NetworkException catch (e) {
      return Failure(failures.NetworkFailure(message: e.message, code: e.code));
    } catch (e) {
      return Failure(failures.UnknownFailure(message: e.toString()));
    }
  }
}
