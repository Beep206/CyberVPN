# Test Directory Structure

Tests mirror the `lib/` source tree using a feature-centric layout.

```
test/
  core/                          # Core utilities, errors, security, storage
    analytics/
    errors/
    security/
    utils/
    ...
  features/                      # Feature tests mirror lib/features/
    auth/
      data/repositories/         # Repository unit tests
      domain/usecases/           # Use case unit tests
      presentation/
        providers/               # Notifier/provider unit tests
        screens/                 # Widget tests for screens
    vpn/
      data/
        datasources/
        repositories/
      domain/
      presentation/
        providers/
        screens/
    subscription/
    servers/
    settings/
    referral/
    diagnostics/
    notifications/
    onboarding/
    config_import/
    profile/
    review/
    quick_actions/
    quick_setup/
  helpers/                       # Shared test utilities
    fakes/                       # Fake implementations
    fixtures/                    # Test data factories
  shared/                        # Cross-cutting test utilities
    services/
    widgets/
  integration/                   # End-to-end integration tests
  app/                           # App-level tests (router, theme)
```

## Conventions

### File Naming

- Unit tests: `<source_file>_test.dart`
- Widget tests: `<screen_name>_test.dart`
- Test helpers: `<name>_test_helpers.dart`

### Directory Mapping

| Source path | Test path |
|---|---|
| `lib/features/vpn/data/repositories/vpn_repository_impl.dart` | `test/features/vpn/data/repositories/vpn_repository_impl_test.dart` |
| `lib/features/auth/presentation/providers/auth_provider.dart` | `test/features/auth/presentation/providers/auth_provider_test.dart` |
| `lib/core/utils/app_logger.dart` | `test/core/utils/app_logger_test.dart` |

### Mocking Strategy

- **Hand-written mocks** for simple interfaces (implement the abstract class directly)
- **mocktail** for complex interfaces requiring `when()`/`verify()` patterns
- Mock classes are prefixed with `_Mock` and defined in the test file

### Running Tests

```bash
# All tests
flutter test

# Single test file
flutter test test/features/vpn/presentation/providers/vpn_connection_provider_test.dart

# Feature suite
flutter test test/features/vpn/

# With coverage
flutter test --coverage
```
