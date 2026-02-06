# Test Directory Structure Audit

## Current Layout

```
test/
  widget_test.dart                        # Flutter default (orphan)

  app/                                    # App-level tests (router, theme)
    router/app_router_test.dart
    theme/{cyberpunk,material_you,theme_provider,tokens}_test.dart

  core/                                   # Core utility tests
    analytics/                            # analytics_providers, noop_analytics
    auth/jwt_parser_test.dart
    config/{certificate_fingerprints,environment_config}_test.dart
    constants/api_constants_test.dart
    data/cache_strategy_test.dart
    di/providers_test.dart
    errors/app_error_test.dart
    haptics/haptic_service_test.dart
    l10n/locale_config_test.dart
    network/{api_client,auth_interceptor,certificate_pinning,retry_interceptor,websocket_client}_test.dart
    routing/{deep_link_handler,deep_link_parser}_test.dart
    security/sentry_privacy_test.dart
    storage/secure_storage_test.dart
    utils/l10n_formatters_test.dart

  features/                               # Feature-centric (mirrors lib/)
    auth/presentation/providers/auth_provider_test.dart
    config_import/{data,domain,presentation}/**
    diagnostics/{data,domain,presentation}/**
    notifications/{data,domain,presentation}/**
    onboarding/{data,domain,presentation}/**
    profile/{data,presentation}/**
    quick_setup/presentation/**
    referral/{data,domain,presentation}/**
    review/{data,integration}/**
    servers/presentation/providers/**
    settings/{domain,presentation}/**
    subscription/presentation/{providers,screens}/**
    vpn/{data,presentation}/**
    widgets/widget_bridge_service_test.dart

  helpers/                                # Shared test infrastructure
    fakes/{fake_api_client,fake_local_storage,fake_secure_storage}.dart
    fixture_loader.dart
    mock_factories.dart
    mock_repositories.dart
    test_app.dart
    test_infrastructure_test.dart
    test_utils.dart

  integration/                            # Integration tests at root level
    certificate_pinning_integration_test.dart
    deep_link_integration_test.dart

  shared/                                 # Shared widget/service tests
    services/{tooltip_preferences,version}_service_test.dart
    widgets/{feature_tooltip,flag_widget,in_app_update_dialog,skeleton_loader}_test.dart

  unit/                                   # DUPLICATE location for unit tests
    auth/{data/repositories,domain/usecases}/**
    config_import/**_realworld_test.dart
    core/{errors,security,utils}/**
    diagnostics/**
    profile/**
    quick_actions/**
    servers/**
    settings/**
    vpn/**

  widget/                                 # DUPLICATE location for widget tests
    auth_test_helpers.dart
    connection_screen_test.dart
    diagnostics/**
    global_error_screen_test.dart
    login_screen_test.dart
    notifications/**
    onboarding/**
    qr_flutter_test.dart
    register_screen_test.dart
    server_list_screen_test.dart
    settings/**
```

## Identified Inconsistencies

### 1. Duplicate Test Locations (Critical)

| Feature    | `test/features/` location                              | `test/unit/` or `test/widget/` location                |
|-----------|-------------------------------------------------------|-------------------------------------------------------|
| **auth**   | `features/auth/presentation/providers/`               | `unit/auth/data/repositories/`, `unit/auth/domain/usecases/` |
| **config_import** | `features/config_import/{data,domain,presentation}/` | `unit/config_import/*_realworld_test.dart`            |
| **diagnostics** | `features/diagnostics/{data,domain,presentation}/` | `unit/diagnostics/`                                   |
| **profile** | `features/profile/{data,presentation}/`              | `unit/profile/`                                       |
| **servers** | `features/servers/presentation/providers/`           | `unit/servers/`                                       |
| **settings** | `features/settings/{domain,presentation}/`          | `unit/settings/`                                      |
| **vpn**    | `features/vpn/{data,presentation}/`                  | `unit/vpn/`                                           |
| **core**   | `core/{analytics,auth,config,...}`                    | `unit/core/{errors,security,utils}`                   |

### 2. Widget Tests Split

Widget tests exist in two locations:
- `test/features/*/presentation/screens/*_test.dart` (newer pattern)
- `test/widget/*_test.dart` (older pattern)

### 3. Integration Tests Split

- `test/integration/` — root-level integration tests (certificate pinning, deep links)
- `test/features/review/integration/` — feature-level integration tests

### 4. Orphan Files

- `test/widget_test.dart` — Flutter default test, likely unused
- `test/widget/auth_test_helpers.dart` — helper in widget/ not in helpers/

## Statistics

| Location         | Count | Description                     |
|-----------------|-------|---------------------------------|
| `test/features/` | 62    | Feature-centric tests (newer)   |
| `test/unit/`     | 28    | Type-centric unit tests (older) |
| `test/widget/`   | 15    | Type-centric widget tests (older) |
| `test/core/`     | 18    | Core utility tests              |
| `test/app/`      | 5     | App-level tests                 |
| `test/helpers/`  | 7     | Shared test infrastructure      |
| `test/integration/` | 2  | Root-level integration tests    |
| `test/shared/`   | 6     | Shared widgets/services tests   |
| **Total**        | **143** |                               |

## Proposed Structure (Option A: Feature-Centric)

Consolidate all tests under `test/features/` (matching `lib/features/`), move core tests under `test/core/`, keep `test/helpers/` and `test/integration/`:

```
test/
  app/                    # Keep as-is (app-level)
  core/                   # Merge test/unit/core/ here
  features/               # ALL feature tests
    auth/
      data/repositories/  # From unit/auth/data/
      domain/usecases/    # From unit/auth/domain/
      presentation/       # Already here
    vpn/
      data/               # Already here + from unit/vpn/
      presentation/       # Already here
    ...
  helpers/                # Shared infrastructure
  integration/            # Root-level integration tests
  shared/                 # Shared widgets (or merge into helpers/)
```

### Migration Steps

1. Move `test/unit/<feature>/` contents → `test/features/<feature>/`
2. Move `test/widget/<feature>/` contents → `test/features/<feature>/presentation/`
3. Move `test/unit/core/` contents → `test/core/`
4. Move `test/widget/auth_test_helpers.dart` → `test/helpers/`
5. Delete empty `test/unit/` and `test/widget/` directories
6. Delete orphan `test/widget_test.dart`

---

## Decision: Feature-Centric (Option A) - APPROVED

**Chosen**: Option A — Feature-centric structure mirroring `lib/`.

### Rationale

1. **Consistency with lib/**: `lib/features/auth/data/` → `test/features/auth/data/` is intuitive
2. **Flutter community convention**: Feature-first is the dominant pattern in clean architecture Flutter projects
3. **Tooling**: `flutter test test/features/auth/` runs all auth tests; coverage maps cleanly
4. **Co-location**: Data layer, domain layer, and presentation layer tests live together under each feature
5. **Scalability**: New features follow the same pattern without creating cross-cutting directories

### Canonical Structure

```
test/
  app/                                  # App-level (router, theme)
  core/                                 # Core utilities (mirrors lib/core/)
    analytics/
    auth/
    config/
    errors/
    network/
    security/
    storage/
    utils/
  features/                             # ALL feature tests (mirrors lib/features/)
    <feature>/
      data/
        datasources/
        repositories/
      domain/
        entities/
        usecases/
      presentation/
        providers/
        screens/
        widgets/
      integration/                      # Per-feature integration tests
  helpers/                              # Shared fakes, mocks, fixtures, test_app
  integration/                          # Cross-feature integration tests
  shared/                               # Shared services/widgets tests
```

### Naming Conventions

- Unit tests: `<class_name>_test.dart` (e.g., `auth_repository_impl_test.dart`)
- Widget tests: `<screen_name>_test.dart` (e.g., `login_screen_test.dart`)
- Integration tests: `<flow>_integration_test.dart` (e.g., `auth_flow_integration_test.dart`)
- Benchmark tests: `<subject>_benchmark_test.dart` (e.g., `server_list_filtering_benchmark_test.dart`)

### New Test Placement Rule

All new tests MUST be placed in `test/features/<feature>/` or `test/core/` matching their source location in `lib/`. Never create new tests in `test/unit/` or `test/widget/`.
