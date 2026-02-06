import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' as errors;
import 'package:cybervpn_mobile/core/security/app_attestation.dart';
import 'package:cybervpn_mobile/core/services/fcm_token_service.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Mock AuthRepository
// ---------------------------------------------------------------------------

class MockAuthRepository implements AuthRepository {
  bool isAuthenticatedValue = false;
  UserEntity? currentUser;
  UserEntity? loginUser;
  UserEntity? registerUser;
  String loginToken = 'access-token-123';
  String registerToken = 'access-token-456';

  Exception? loginException;
  Exception? registerException;
  Exception? logoutException;
  Exception? isAuthenticatedException;
  Exception? getCurrentUserException;

  bool loginCalled = false;
  bool registerCalled = false;
  bool logoutCalled = false;

  String? lastLoginEmail;
  String? lastLoginPassword;
  String? lastRegisterEmail;
  String? lastRegisterPassword;
  String? lastRegisterReferralCode;

  @override
  Future<Result<bool>> isAuthenticated() async {
    if (isAuthenticatedException != null) throw isAuthenticatedException!;
    return Success(isAuthenticatedValue);
  }

  @override
  Future<Result<UserEntity?>> getCurrentUser() async {
    if (getCurrentUserException != null) throw getCurrentUserException!;
    return Success(currentUser);
  }

  @override
  Future<Result<(UserEntity, String)>> login({
    required String email,
    required String password,
    required DeviceInfo device,
    bool rememberMe = false,
  }) async {
    loginCalled = true;
    lastLoginEmail = email;
    lastLoginPassword = password;
    if (loginException != null) throw loginException!;
    return Success((loginUser!, loginToken));
  }

  @override
  Future<Result<(UserEntity, String)>> register({
    required String email,
    required String password,
    required DeviceInfo device,
    String? referralCode,
  }) async {
    registerCalled = true;
    lastRegisterEmail = email;
    lastRegisterPassword = password;
    lastRegisterReferralCode = referralCode;
    if (registerException != null) throw registerException!;
    return Success((registerUser!, registerToken));
  }

  @override
  Future<Result<void>> logout({
    required String refreshToken,
    required String deviceId,
  }) async {
    logoutCalled = true;
    if (logoutException != null) throw logoutException!;
    return const Success<void>(null);
  }

  @override
  Future<Result<String>> refreshToken({
    required String refreshToken,
    required String deviceId,
  }) async {
    return const Success('new-access-token');
  }
}

// ---------------------------------------------------------------------------
// Mock FcmTokenService (simple fake that doesn't extend the real class)
// ---------------------------------------------------------------------------

class FakeFcmTokenService implements FcmTokenService {
  bool registerTokenCalled = false;

  @override
  Future<bool> registerToken() async {
    registerTokenCalled = true;
    return true;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Mock AppAttestationService (simple fake)
// ---------------------------------------------------------------------------

class FakeAppAttestationService implements AppAttestationService {
  bool generateTokenCalled = false;
  AttestationTrigger? lastTrigger;

  @override
  Future<AttestationResult> generateToken({
    required AttestationTrigger trigger,
    String? challenge,
  }) async {
    generateTokenCalled = true;
    lastTrigger = trigger;
    return const AttestationResult(
      status: AttestationStatus.disabled,
      platform: 'test',
    );
  }

  @override
  bool get isSupported => false;

  @override
  bool get enforceAttestation => false;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

final testUser = UserEntity(
  id: 'user-001',
  email: 'test@example.com',
  username: 'testuser',
  isEmailVerified: true,
  isPremium: false,
  createdAt: DateTime(2026, 1, 1),
  lastLoginAt: DateTime(2026, 2, 1),
);

/// Creates a [ProviderContainer] with all mocks wired up.
ProviderContainer createContainer({
  required MockAuthRepository mockRepo,
  FakeFcmTokenService? mockFcm,
  FakeAppAttestationService? mockAttestation,
}) {
  return ProviderContainer(
    overrides: [
      authRepositoryProvider.overrideWithValue(mockRepo),
      if (mockFcm != null) fcmTokenServiceProvider.overrideWithValue(mockFcm),
      if (mockAttestation != null)
        appAttestationServiceProvider.overrideWithValue(mockAttestation),
    ],
  );
}

/// Waits for the [authProvider] to finish loading.
Future<AuthState> waitForState(ProviderContainer container) async {
  final sub = container.listen(authProvider, (_, _) {});
  await container.read(authProvider.future);
  sub.close();
  return container.read(authProvider).requireValue;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('AuthState', () {
    test('AuthLoading is a valid state', () {
      const state = AuthLoading();
      expect(state, isA<AuthState>());
    });

    test('AuthAuthenticated holds user', () {
      final state = AuthAuthenticated(testUser);
      expect(state.user, equals(testUser));
    });

    test('AuthUnauthenticated is a valid state', () {
      const state = AuthUnauthenticated();
      expect(state, isA<AuthState>());
    });

    test('AuthError holds message', () {
      const state = AuthError('Something went wrong');
      expect(state.message, equals('Something went wrong'));
    });

    test('AuthAuthenticated equality works', () {
      final a = AuthAuthenticated(testUser);
      final b = AuthAuthenticated(testUser);
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('AuthError equality works', () {
      const a = AuthError('error');
      const b = AuthError('error');
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  group('AuthNotifier build()', () {
    late MockAuthRepository mockRepo;
    late ProviderContainer container;

    setUp(() {
      mockRepo = MockAuthRepository();
    });

    tearDown(() {
      container.dispose();
    });

    test('returns AuthUnauthenticated when not authenticated', () async {
      mockRepo.isAuthenticatedValue = false;

      container = createContainer(mockRepo: mockRepo);
      final state = await waitForState(container);

      expect(state, isA<AuthUnauthenticated>());
    });

    test('returns AuthAuthenticated when authenticated with user', () async {
      mockRepo.isAuthenticatedValue = true;
      mockRepo.currentUser = testUser;

      container = createContainer(mockRepo: mockRepo);
      final state = await waitForState(container);

      expect(state, isA<AuthAuthenticated>());
      expect((state as AuthAuthenticated).user, equals(testUser));
    });

    test('returns AuthUnauthenticated when authenticated but no user', () async {
      mockRepo.isAuthenticatedValue = true;
      mockRepo.currentUser = null;

      container = createContainer(mockRepo: mockRepo);
      final state = await waitForState(container);

      expect(state, isA<AuthUnauthenticated>());
    });

    test('returns AuthError when isAuthenticated throws', () async {
      mockRepo.isAuthenticatedException = Exception('Auth check failed');

      container = createContainer(mockRepo: mockRepo);
      final state = await waitForState(container);

      expect(state, isA<AuthError>());
      expect((state as AuthError).message, contains('Auth check failed'));
    });

    test('returns AuthError when getCurrentUser throws', () async {
      mockRepo.isAuthenticatedValue = true;
      mockRepo.getCurrentUserException = Exception('User fetch failed');

      container = createContainer(mockRepo: mockRepo);
      final state = await waitForState(container);

      expect(state, isA<AuthError>());
      expect((state as AuthError).message, contains('User fetch failed'));
    });
  });

  group('AuthNotifier.login()', () {
    late MockAuthRepository mockRepo;
    late FakeFcmTokenService mockFcm;
    late FakeAppAttestationService mockAttestation;
    late ProviderContainer container;

    setUp(() {
      mockRepo = MockAuthRepository();
      mockFcm = FakeFcmTokenService();
      mockAttestation = FakeAppAttestationService();
    });

    tearDown(() {
      container.dispose();
    });

    test('transitions to AuthLoading then AuthAuthenticated on success', () async {
      mockRepo.isAuthenticatedValue = false;
      mockRepo.loginUser = testUser;

      container = createContainer(
        mockRepo: mockRepo,
        mockFcm: mockFcm,
        mockAttestation: mockAttestation,
      );

      await waitForState(container);

      // Track state changes
      final states = <AuthState>[];
      container.listen(
        authProvider,
        (_, next) {
          if (next.value != null) states.add(next.value!);
        },
        fireImmediately: false,
      );

      final notifier = container.read(authProvider.notifier);
      await notifier.login('test@example.com', 'password123');

      // Verify final state
      final finalState = container.read(authProvider).requireValue;
      expect(finalState, isA<AuthAuthenticated>());
      expect((finalState as AuthAuthenticated).user, equals(testUser));

      // Verify repository was called with correct params
      expect(mockRepo.loginCalled, isTrue);
      expect(mockRepo.lastLoginEmail, equals('test@example.com'));
      expect(mockRepo.lastLoginPassword, equals('password123'));
    });

    test('transitions to AuthError on login failure', () async {
      mockRepo.isAuthenticatedValue = false;
      mockRepo.loginException = Exception('Invalid credentials');

      container = createContainer(mockRepo: mockRepo);

      await waitForState(container);

      final notifier = container.read(authProvider.notifier);
      await notifier.login('test@example.com', 'wrongpassword');

      final finalState = container.read(authProvider).requireValue;
      expect(finalState, isA<AuthError>());
      expect((finalState as AuthError).message, contains('Invalid credentials'));
    });
  });

  group('AuthNotifier.register()', () {
    late MockAuthRepository mockRepo;
    late FakeFcmTokenService mockFcm;
    late ProviderContainer container;

    setUp(() {
      mockRepo = MockAuthRepository();
      mockFcm = FakeFcmTokenService();
    });

    tearDown(() {
      container.dispose();
    });

    test('transitions to AuthAuthenticated on success', () async {
      mockRepo.isAuthenticatedValue = false;
      mockRepo.registerUser = testUser;

      container = createContainer(mockRepo: mockRepo, mockFcm: mockFcm);

      await waitForState(container);

      final notifier = container.read(authProvider.notifier);
      await notifier.register('new@example.com', 'password123');

      final finalState = container.read(authProvider).requireValue;
      expect(finalState, isA<AuthAuthenticated>());
      expect((finalState as AuthAuthenticated).user, equals(testUser));

      // Verify repository was called
      expect(mockRepo.registerCalled, isTrue);
      expect(mockRepo.lastRegisterEmail, equals('new@example.com'));
      expect(mockRepo.lastRegisterPassword, equals('password123'));
      expect(mockRepo.lastRegisterReferralCode, isNull);
    });

    test('passes referral code to repository', () async {
      mockRepo.isAuthenticatedValue = false;
      mockRepo.registerUser = testUser;

      container = createContainer(mockRepo: mockRepo, mockFcm: mockFcm);

      await waitForState(container);

      final notifier = container.read(authProvider.notifier);
      await notifier.register('new@example.com', 'password123', referralCode: 'REFERRAL123');

      expect(mockRepo.lastRegisterReferralCode, equals('REFERRAL123'));
    });

    test('transitions to AuthError on register failure', () async {
      mockRepo.isAuthenticatedValue = false;
      mockRepo.registerException = Exception('Email already exists');

      container = createContainer(mockRepo: mockRepo);

      await waitForState(container);

      final notifier = container.read(authProvider.notifier);
      await notifier.register('existing@example.com', 'password123');

      final finalState = container.read(authProvider).requireValue;
      expect(finalState, isA<AuthError>());
      expect((finalState as AuthError).message, contains('Email already exists'));
    });
  });

  group('AuthNotifier.logout()', () {
    late MockAuthRepository mockRepo;
    late ProviderContainer container;

    setUp(() {
      mockRepo = MockAuthRepository();
    });

    tearDown(() {
      container.dispose();
    });

    test('transitions to AuthUnauthenticated on success', () async {
      mockRepo.isAuthenticatedValue = true;
      mockRepo.currentUser = testUser;

      container = createContainer(mockRepo: mockRepo);

      await waitForState(container);

      final notifier = container.read(authProvider.notifier);
      await notifier.logout();

      final finalState = container.read(authProvider).requireValue;
      expect(finalState, isA<AuthUnauthenticated>());
      expect(mockRepo.logoutCalled, isTrue);
    });

    test('transitions to AuthError on logout failure', () async {
      mockRepo.isAuthenticatedValue = true;
      mockRepo.currentUser = testUser;
      mockRepo.logoutException = Exception('Logout failed');

      container = createContainer(mockRepo: mockRepo);

      await waitForState(container);

      final notifier = container.read(authProvider.notifier);
      await notifier.logout();

      final finalState = container.read(authProvider).requireValue;
      expect(finalState, isA<AuthError>());
      expect((finalState as AuthError).message, contains('Logout failed'));
    });
  });

  group('AuthNotifier.checkAuthStatus()', () {
    late MockAuthRepository mockRepo;
    late ProviderContainer container;

    setUp(() {
      mockRepo = MockAuthRepository();
    });

    tearDown(() {
      container.dispose();
    });

    test('re-checks authentication and updates state', () async {
      mockRepo.isAuthenticatedValue = false;

      container = createContainer(mockRepo: mockRepo);

      await waitForState(container);

      // Now change the mock state
      mockRepo.isAuthenticatedValue = true;
      mockRepo.currentUser = testUser;

      final notifier = container.read(authProvider.notifier);
      await notifier.checkAuthStatus();

      final finalState = container.read(authProvider).requireValue;
      expect(finalState, isA<AuthAuthenticated>());
    });
  });

  group('Derived providers', () {
    late MockAuthRepository mockRepo;
    late ProviderContainer container;

    setUp(() {
      mockRepo = MockAuthRepository();
    });

    tearDown(() {
      container.dispose();
    });

    test('currentUserProvider returns null when unauthenticated', () async {
      mockRepo.isAuthenticatedValue = false;

      container = createContainer(mockRepo: mockRepo);

      await waitForState(container);

      final user = container.read(currentUserProvider);
      expect(user, isNull);
    });

    test('currentUserProvider returns user when authenticated', () async {
      mockRepo.isAuthenticatedValue = true;
      mockRepo.currentUser = testUser;

      container = createContainer(mockRepo: mockRepo);

      await waitForState(container);

      final user = container.read(currentUserProvider);
      expect(user, equals(testUser));
    });

    test('isAuthenticatedProvider returns false when unauthenticated', () async {
      mockRepo.isAuthenticatedValue = false;

      container = createContainer(mockRepo: mockRepo);

      await waitForState(container);

      final isAuth = container.read(isAuthenticatedProvider);
      expect(isAuth, isFalse);
    });

    test('isAuthenticatedProvider returns true when authenticated', () async {
      mockRepo.isAuthenticatedValue = true;
      mockRepo.currentUser = testUser;

      container = createContainer(mockRepo: mockRepo);

      await waitForState(container);

      final isAuth = container.read(isAuthenticatedProvider);
      expect(isAuth, isTrue);
    });
  });
}
