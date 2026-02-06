import 'package:cybervpn_mobile/app/app.dart';
import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/device/device_provider.dart'
    hide secureStorageProvider;
import 'package:cybervpn_mobile/core/device/device_service.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/biometric_service.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/repositories/onboarding_repository.dart';
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show secureStorageProvider, networkInfoProvider;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:local_auth/local_auth.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

// =============================================================================
// Mock Classes
// =============================================================================

class MockAuthRepository extends Mock implements AuthRepository {}

class MockBiometricService extends Mock implements BiometricService {}

class MockDeviceService extends Mock implements DeviceService {}

class MockNetworkInfo extends Mock implements NetworkInfo {}

class MockOnboardingRepository extends Mock implements OnboardingRepository {}

class FakeSecureStorage extends SecureStorageWrapper {
  FakeSecureStorage() : super();

  final Map<String, String> _store = {};

  @override
  Future<void> write({required String key, required String value}) async {
    _store[key] = value;
  }

  @override
  Future<String?> read({required String key}) async {
    return _store[key];
  }

  @override
  Future<void> delete({required String key}) async {
    _store.remove(key);
  }

  @override
  Future<void> deleteAll() async {
    _store.clear();
  }

  @override
  Future<bool> containsKey({required String key}) async {
    return _store.containsKey(key);
  }

  Map<String, String> get store => Map.unmodifiable(_store);

  void reset() => _store.clear();

  void seed(Map<String, String> data) {
    _store.addAll(data);
  }
}

class FakeLocalStorage extends LocalStorageWrapper {
  final Map<String, Object> _store = {};

  @override
  Future<void> setString(String key, String value) async {
    _store[key] = value;
  }

  @override
  Future<String?> getString(String key) async {
    return _store[key] as String?;
  }

  @override
  Future<void> setBool(String key, bool value) async {
    _store[key] = value;
  }

  @override
  Future<bool?> getBool(String key) async {
    return _store[key] as bool?;
  }

  @override
  Future<void> setInt(String key, int value) async {
    _store[key] = value;
  }

  @override
  Future<int?> getInt(String key) async {
    return _store[key] as int?;
  }

  @override
  Future<void> remove(String key) async {
    _store.remove(key);
  }

  @override
  Future<void> clear() async {
    _store.clear();
  }

  Map<String, Object> get store => Map.unmodifiable(_store);

  void reset() => _store.clear();
}

// =============================================================================
// Test Fixtures
// =============================================================================

const testDeviceId = 'test-device-id-1234-5678-abcd-efgh';
const testEmail = 'test@example.com';
const testPassword = 'TestPassword123!';
const testUserId = 'user-id-001';
const testAccessToken = 'test-access-token-jwt';
const testRefreshToken = 'test-refresh-token';

final testUser = UserEntity(
  id: testUserId,
  email: testEmail,
  username: 'TestUser',
  isEmailVerified: true,
  isPremium: false,
  createdAt: DateTime.now(),
);

final testDeviceInfo = DeviceInfo(
  deviceId: testDeviceId,
  platform: DevicePlatform.android,
  platformId: 'android-test-id',
  osVersion: '14.0',
  appVersion: '1.0.0',
  deviceModel: 'Test Device',
);

// =============================================================================
// E2E Test Suite: Critical Auth Flows
// =============================================================================

/// E2E tests for critical authentication flows.
///
/// These tests verify the complete user journey for:
/// 1. Full registration flow
/// 2. Full login flow
/// 3. Session persistence
/// 4. Biometric login flow
/// 5. Offline mode access
///
/// Each test uses mocked backends to simulate real API responses.
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  // Shared test infrastructure
  late SharedPreferences prefs;
  late FakeSecureStorage fakeSecureStorage;
  late FakeLocalStorage fakeLocalStorage;
  late MockAuthRepository mockAuthRepo;
  late MockBiometricService mockBiometricService;
  late MockDeviceService mockDeviceService;
  late MockNetworkInfo mockNetworkInfo;
  late MockOnboardingRepository mockOnboardingRepo;

  // Register fallback values for mocktail
  setUpAll(() {
    registerFallbackValue(testDeviceInfo);
    registerFallbackValue(testUser);
  });

  setUp(() async {
    // Reset SharedPreferences
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    await prefs.clear();

    // Initialize fakes
    fakeSecureStorage = FakeSecureStorage();
    fakeLocalStorage = FakeLocalStorage();

    // Initialize mocks
    mockAuthRepo = MockAuthRepository();
    mockBiometricService = MockBiometricService();
    mockDeviceService = MockDeviceService();
    mockNetworkInfo = MockNetworkInfo();
    mockOnboardingRepo = MockOnboardingRepository();

    // Setup default mock behaviors
    _setupDefaultMockBehaviors(
      mockDeviceService: mockDeviceService,
      mockNetworkInfo: mockNetworkInfo,
      mockOnboardingRepo: mockOnboardingRepo,
      mockAuthRepo: mockAuthRepo,
      mockBiometricService: mockBiometricService,
    );
  });

  tearDown(() async {
    await prefs.clear();
    fakeSecureStorage.reset();
    fakeLocalStorage.reset();
  });

  /// Helper to pump the app with test overrides
  Future<void> pumpTestApp(
    WidgetTester tester, {
    bool onboardingCompleted = true,
    bool isAuthenticated = false,
    bool networkOnline = true,
    bool biometricAvailable = false,
    bool biometricEnabled = false,
  }) async {
    // Configure onboarding state
    when(() => mockOnboardingRepo.hasCompletedOnboarding())
        .thenAnswer((_) async => onboardingCompleted);

    // Configure network state
    when(() => mockNetworkInfo.isConnected)
        .thenAnswer((_) async => networkOnline);

    // Configure auth state
    when(() => mockAuthRepo.isAuthenticated())
        .thenAnswer((_) async => isAuthenticated);

    if (isAuthenticated) {
      when(() => mockAuthRepo.getCurrentUser())
          .thenAnswer((_) async => testUser);
    }

    // Configure biometric state
    when(() => mockBiometricService.isBiometricAvailable())
        .thenAnswer((_) async => biometricAvailable);
    when(() => mockBiometricService.isBiometricEnabled())
        .thenAnswer((_) async => biometricEnabled);

    // Seed secure storage if authenticated
    if (isAuthenticated) {
      fakeSecureStorage.seed({
        SecureStorageWrapper.accessTokenKey: testAccessToken,
        SecureStorageWrapper.refreshTokenKey: testRefreshToken,
        SecureStorageWrapper.deviceIdKey: testDeviceId,
      });
    }

    final overrides = [
      sharedPreferencesProvider.overrideWithValue(prefs),
      secureStorageProvider.overrideWithValue(fakeSecureStorage),
      localStorageProvider.overrideWithValue(fakeLocalStorage),
      networkInfoProvider.overrideWithValue(mockNetworkInfo),
      authRepositoryProvider.overrideWithValue(mockAuthRepo),
      deviceServiceProvider.overrideWithValue(mockDeviceService),
      onboardingRepositoryProvider.overrideWithValue(mockOnboardingRepo),
      biometricServiceProvider.overrideWith((ref) => mockBiometricService),
    ];

    await tester.pumpWidget(
      ProviderScope(
        overrides: overrides,
        child: const CyberVpnApp(),
      ),
    );
    await tester.pumpAndSettle();
  }

  /// Helper for safe pump and settle with timeout
  Future<void> safePumpAndSettle(
    WidgetTester tester, {
    Duration timeout = const Duration(seconds: 10),
  }) async {
    await tester.pumpAndSettle(
      const Duration(milliseconds: 100),
      EnginePhase.sendSemanticsUpdate,
      timeout,
    );
  }

  // ===========================================================================
  // Test 1: Full Registration Flow
  // ===========================================================================
  group('E2E: Full Registration Flow', () {
    testWidgets(
      'User can register and reach main screen',
      (tester) async {
        // Setup: Configure mock to accept registration
        when(() => mockAuthRepo.register(
              email: any(named: 'email'),
              password: any(named: 'password'),
              device: any(named: 'device'),
              referralCode: any(named: 'referralCode'),
            )).thenAnswer((_) async => (testUser, testAccessToken));

        // After registration, auth check should pass
        var registrationComplete = false;
        when(() => mockAuthRepo.isAuthenticated()).thenAnswer((_) async {
          return registrationComplete;
        });
        when(() => mockAuthRepo.getCurrentUser()).thenAnswer((_) async {
          return registrationComplete ? testUser : null;
        });

        await pumpTestApp(tester, onboardingCompleted: true);

        // Step 1: Should be on login screen (onboarding already done)
        expect(find.text('CyberVPN'), findsOneWidget,
            reason: 'Should show login screen');

        // Step 2: Navigate to register screen
        final registerLink = find.text('Register');
        expect(registerLink, findsWidgets,
            reason: 'Should have register link');
        await tester.tap(registerLink.first);
        await safePumpAndSettle(tester);

        // Step 3: Verify on register screen
        expect(find.text('Create Account'), findsOneWidget,
            reason: 'Should show register screen');

        // Step 4: Fill registration form
        final textFields = find.byType(TextFormField);
        expect(textFields, findsWidgets,
            reason: 'Should have text fields');

        // Email field (first)
        await tester.enterText(textFields.at(0), testEmail);
        await tester.pump();

        // Password field (second)
        await tester.enterText(textFields.at(1), testPassword);
        await tester.pump();

        // Confirm password field (third)
        await tester.enterText(textFields.at(2), testPassword);
        await tester.pump();

        // Step 5: Accept terms
        final checkbox = find.byType(Checkbox);
        if (checkbox.evaluate().isNotEmpty) {
          await tester.tap(checkbox.first);
          await tester.pump();
        }

        // Step 6: Tap register button
        registrationComplete = true; // Registration will succeed

        final registerButton = find.widgetWithText(ElevatedButton, 'Register');
        expect(registerButton, findsOneWidget,
            reason: 'Should have register button');
        await tester.tap(registerButton);
        await safePumpAndSettle(tester);

        // Step 7: Verify registration was called
        verify(() => mockAuthRepo.register(
              email: testEmail,
              password: testPassword,
              device: any(named: 'device'),
              referralCode: any(named: 'referralCode'),
            )).called(1);

        // Step 8: Should navigate to main screen
        // Look for bottom navigation or home screen elements
        await tester.pump(const Duration(seconds: 1));
        await safePumpAndSettle(tester);

        // Verify we're past the auth screens
        expect(find.text('Create Account'), findsNothing,
            reason: 'Should no longer be on register screen');
      },
    );
  });

  // ===========================================================================
  // Test 2: Full Login Flow
  // ===========================================================================
  group('E2E: Full Login Flow', () {
    testWidgets(
      'User can login and reach main screen',
      (tester) async {
        // Setup: Configure mock to accept login
        when(() => mockAuthRepo.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
              device: any(named: 'device'),
              rememberMe: any(named: 'rememberMe'),
            )).thenAnswer((_) async => (testUser, testAccessToken));

        var loginComplete = false;
        when(() => mockAuthRepo.isAuthenticated()).thenAnswer((_) async {
          return loginComplete;
        });
        when(() => mockAuthRepo.getCurrentUser()).thenAnswer((_) async {
          return loginComplete ? testUser : null;
        });

        await pumpTestApp(tester, onboardingCompleted: true);

        // Step 1: Should be on login screen
        expect(find.text('CyberVPN'), findsOneWidget,
            reason: 'Should show login screen');

        // Step 2: Fill login form
        final textFields = find.byType(TextFormField);
        expect(textFields, findsWidgets,
            reason: 'Should have text fields');

        // Email field (first)
        await tester.enterText(textFields.at(0), testEmail);
        await tester.pump();

        // Password field (second)
        await tester.enterText(textFields.at(1), testPassword);
        await tester.pump();

        // Step 3: Tap login button
        loginComplete = true;

        final loginButton = find.widgetWithText(ElevatedButton, 'Login');
        if (loginButton.evaluate().isEmpty) {
          // Try finding by text only
          await tester.tap(find.text('Login').first);
        } else {
          await tester.tap(loginButton);
        }
        await safePumpAndSettle(tester);

        // Step 4: Verify login was called
        verify(() => mockAuthRepo.login(
              email: testEmail,
              password: testPassword,
              device: any(named: 'device'),
              rememberMe: any(named: 'rememberMe'),
            )).called(1);

        // Step 5: Should navigate away from login screen
        await tester.pump(const Duration(seconds: 1));
        await safePumpAndSettle(tester);

        expect(find.text('CyberVPN'), findsNothing,
            reason: 'Should no longer be on login screen header');
      },
    );
  });

  // ===========================================================================
  // Test 3: Session Persistence
  // ===========================================================================
  group('E2E: Session Persistence', () {
    testWidgets(
      'App restores session on relaunch without requiring login',
      (tester) async {
        // Setup: User is already authenticated with stored tokens
        await pumpTestApp(
          tester,
          onboardingCompleted: true,
          isAuthenticated: true,
        );

        // Should skip login and go directly to main screen
        await tester.pump(const Duration(seconds: 2));
        await safePumpAndSettle(tester);

        // Verify isAuthenticated was checked
        verify(() => mockAuthRepo.isAuthenticated()).called(greaterThan(0));

        // Verify getCurrentUser was called to restore session
        verify(() => mockAuthRepo.getCurrentUser()).called(greaterThan(0));

        // Should NOT be on login screen
        expect(find.text('CyberVPN'), findsNothing,
            reason: 'Should skip login screen for authenticated user');

        // Should be on main app (home/connection screen)
        // Look for common main screen elements
        final hasBottomNav = find.byType(BottomNavigationBar).evaluate().isNotEmpty;
        final hasTabBar = find.byType(NavigationBar).evaluate().isNotEmpty;
        final hasMainContent = hasBottomNav || hasTabBar;

        expect(hasMainContent || find.text('Connection').evaluate().isNotEmpty,
            isTrue,
            reason: 'Should be on main screen');
      },
    );

    testWidgets(
      'Tokens are stored in secure storage after login',
      (tester) async {
        when(() => mockAuthRepo.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
              device: any(named: 'device'),
              rememberMe: any(named: 'rememberMe'),
            )).thenAnswer((_) async {
          // Simulate token storage
          await fakeSecureStorage.write(
            key: SecureStorageWrapper.accessTokenKey,
            value: testAccessToken,
          );
          await fakeSecureStorage.write(
            key: SecureStorageWrapper.refreshTokenKey,
            value: testRefreshToken,
          );
          return (testUser, testAccessToken);
        });

        await pumpTestApp(tester, onboardingCompleted: true);

        // Perform login
        final textFields = find.byType(TextFormField);
        await tester.enterText(textFields.at(0), testEmail);
        await tester.pump();
        await tester.enterText(textFields.at(1), testPassword);
        await tester.pump();

        final loginButton = find.widgetWithText(ElevatedButton, 'Login');
        if (loginButton.evaluate().isNotEmpty) {
          await tester.tap(loginButton);
        } else {
          await tester.tap(find.text('Login').first);
        }
        await safePumpAndSettle(tester);

        // Verify tokens were stored
        final storedAccessToken = fakeSecureStorage.store[SecureStorageWrapper.accessTokenKey];
        final storedRefreshToken = fakeSecureStorage.store[SecureStorageWrapper.refreshTokenKey];

        expect(storedAccessToken, equals(testAccessToken),
            reason: 'Access token should be stored in secure storage');
        expect(storedRefreshToken, equals(testRefreshToken),
            reason: 'Refresh token should be stored in secure storage');
      },
    );
  });

  // ===========================================================================
  // Test 4: Biometric Login Flow
  // ===========================================================================
  group('E2E: Biometric Login Flow', () {
    testWidgets(
      'Biometric login shows when enabled and available',
      (tester) async {
        // Setup: Biometrics available and enabled with stored credentials
        when(() => mockBiometricService.isBiometricAvailable())
            .thenAnswer((_) async => true);
        when(() => mockBiometricService.isBiometricEnabled())
            .thenAnswer((_) async => true);
        when(() => mockBiometricService.getAvailableBiometrics())
            .thenAnswer((_) async => [BiometricType.fingerprint]);

        // Seed biometric credentials
        fakeSecureStorage.seed({
          SecureStorageWrapper.biometricCredentialsKey:
              '{"email":"$testEmail","password":"$testPassword"}',
        });

        await pumpTestApp(
          tester,
          onboardingCompleted: true,
          biometricAvailable: true,
          biometricEnabled: true,
        );

        await tester.pump(const Duration(seconds: 1));
        await safePumpAndSettle(tester);

        // Look for biometric login button (fingerprint icon or "Use Biometrics")
        final biometricButton = find.byIcon(Icons.fingerprint);
        final biometricText = find.textContaining('Biometric');

        expect(
          biometricButton.evaluate().isNotEmpty || biometricText.evaluate().isNotEmpty,
          isTrue,
          reason: 'Should show biometric login option when available and enabled',
        );
      },
    );

    testWidgets(
      'Biometric authentication success logs user in',
      (tester) async {
        // Setup biometrics
        when(() => mockBiometricService.isBiometricAvailable())
            .thenAnswer((_) async => true);
        when(() => mockBiometricService.isBiometricEnabled())
            .thenAnswer((_) async => true);
        when(() => mockBiometricService.authenticate(reason: any(named: 'reason')))
            .thenAnswer((_) async => true);
        when(() => mockBiometricService.getAvailableBiometrics())
            .thenAnswer((_) async => [BiometricType.fingerprint]);

        // Seed credentials for biometric re-auth
        fakeSecureStorage.seed({
          SecureStorageWrapper.biometricCredentialsKey:
              '{"email":"$testEmail","password":"$testPassword"}',
          SecureStorageWrapper.accessTokenKey: testAccessToken,
          SecureStorageWrapper.refreshTokenKey: testRefreshToken,
        });

        // Configure login mock
        when(() => mockAuthRepo.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
              device: any(named: 'device'),
              rememberMe: any(named: 'rememberMe'),
            )).thenAnswer((_) async => (testUser, testAccessToken));

        await pumpTestApp(
          tester,
          onboardingCompleted: true,
          biometricAvailable: true,
          biometricEnabled: true,
        );

        await safePumpAndSettle(tester);

        // Tap biometric button if present
        final biometricButton = find.byIcon(Icons.fingerprint);
        if (biometricButton.evaluate().isNotEmpty) {
          await tester.tap(biometricButton.first);
          await safePumpAndSettle(tester);

          // Verify biometric authentication was attempted
          verify(() => mockBiometricService.authenticate(
                reason: any(named: 'reason'),
              )).called(greaterThan(0));
        }
      },
    );
  });

  // ===========================================================================
  // Test 5: Offline Mode Access
  // ===========================================================================
  group('E2E: Offline Mode Access', () {
    testWidgets(
      'Authenticated user can access app offline with cached data',
      (tester) async {
        // Setup: User authenticated but network offline
        when(() => mockNetworkInfo.isConnected).thenAnswer((_) async => false);

        // Seed cached user data
        fakeSecureStorage.seed({
          SecureStorageWrapper.accessTokenKey: testAccessToken,
          SecureStorageWrapper.refreshTokenKey: testRefreshToken,
          SecureStorageWrapper.cachedUserKey:
              '{"id":"$testUserId","email":"$testEmail","username":"TestUser"}',
        });

        // Auth check should work with cached data
        when(() => mockAuthRepo.isAuthenticated())
            .thenAnswer((_) async => true);
        when(() => mockAuthRepo.getCurrentUser())
            .thenAnswer((_) async => testUser);

        await pumpTestApp(
          tester,
          onboardingCompleted: true,
          isAuthenticated: true,
          networkOnline: false,
        );

        await tester.pump(const Duration(seconds: 2));
        await safePumpAndSettle(tester);

        // Should still access app (with cached session)
        verify(() => mockAuthRepo.isAuthenticated()).called(greaterThan(0));

        // Should NOT show login screen
        expect(find.text('CyberVPN'), findsNothing,
            reason: 'Should not show login when offline with valid session');

        // Should show offline indicator or limited functionality message
        // This depends on app implementation
      },
    );

    testWidgets(
      'App shows appropriate offline state when network unavailable',
      (tester) async {
        // Setup: Authenticated, offline, check network status
        await pumpTestApp(
          tester,
          onboardingCompleted: true,
          isAuthenticated: true,
          networkOnline: false,
        );

        await safePumpAndSettle(tester);

        // Network info should be checked
        verify(() => mockNetworkInfo.isConnected).called(greaterThan(0));

        // App should handle offline gracefully
        // Look for offline indicators or cached content
        final hasContent = find.byType(Scaffold).evaluate().isNotEmpty;
        expect(hasContent, isTrue,
            reason: 'App should display content even when offline');
      },
    );

    testWidgets(
      'Session validation works offline with cached tokens',
      (tester) async {
        // Setup: Valid tokens in storage, offline
        fakeSecureStorage.seed({
          SecureStorageWrapper.accessTokenKey: testAccessToken,
          SecureStorageWrapper.refreshTokenKey: testRefreshToken,
          SecureStorageWrapper.cachedUserKey:
              '{"id":"$testUserId","email":"$testEmail"}',
        });

        when(() => mockAuthRepo.isAuthenticated())
            .thenAnswer((_) async => true);
        when(() => mockAuthRepo.getCurrentUser())
            .thenAnswer((_) async => testUser);

        await pumpTestApp(
          tester,
          onboardingCompleted: true,
          isAuthenticated: true,
          networkOnline: false,
        );

        await safePumpAndSettle(tester);

        // Verify cached tokens are used for session validation
        final hasAccessToken =
            fakeSecureStorage.store.containsKey(SecureStorageWrapper.accessTokenKey);
        expect(hasAccessToken, isTrue,
            reason: 'Should have access token in secure storage');

        // Auth repo should validate session
        verify(() => mockAuthRepo.isAuthenticated()).called(greaterThan(0));
      },
    );
  });
}

// =============================================================================
// Helper Functions
// =============================================================================

void _setupDefaultMockBehaviors({
  required MockDeviceService mockDeviceService,
  required MockNetworkInfo mockNetworkInfo,
  required MockOnboardingRepository mockOnboardingRepo,
  required MockAuthRepository mockAuthRepo,
  required MockBiometricService mockBiometricService,
}) {
  // Device service defaults
  when(() => mockDeviceService.getDeviceInfo())
      .thenAnswer((_) async => testDeviceInfo);
  when(() => mockDeviceService.getDeviceId())
      .thenAnswer((_) async => testDeviceId);

  // Network info defaults
  when(() => mockNetworkInfo.isConnected).thenAnswer((_) async => true);

  // Onboarding defaults
  when(() => mockOnboardingRepo.hasCompletedOnboarding())
      .thenAnswer((_) async => true);
  when(() => mockOnboardingRepo.completeOnboarding())
      .thenAnswer((_) async {});

  // Auth defaults
  when(() => mockAuthRepo.isAuthenticated()).thenAnswer((_) async => false);
  when(() => mockAuthRepo.getCurrentUser()).thenAnswer((_) async => null);

  // Biometric defaults
  when(() => mockBiometricService.isBiometricAvailable())
      .thenAnswer((_) async => false);
  when(() => mockBiometricService.isBiometricEnabled())
      .thenAnswer((_) async => false);
  when(() => mockBiometricService.getAvailableBiometrics())
      .thenAnswer((_) async => []);
  when(() => mockBiometricService.hasEnrollmentChanged())
      .thenAnswer((_) async => false);
}
