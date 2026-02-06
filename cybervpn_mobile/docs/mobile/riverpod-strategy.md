# Riverpod Code Generation Strategy

## Current State

| Metric | Count |
|--------|-------|
| `@riverpod` codegen annotations | 3 (all in `device_provider.dart`) |
| Manual `final ...Provider = Provider(...)` | 137 across 46 files |
| `.g.dart` files | 1 (`device_provider.g.dart`) |

The codebase is overwhelmingly manual-provider based. Only `device_provider.dart` uses codegen for 3 providers (`secureStorage`, `deviceService`, `deviceIntegrity`).

## Decision: Option B - Remove codegen, standardize on manual providers

### Rationale

1. **Consistency**: 137:3 ratio makes codegen the outlier, not the standard.
2. **Build complexity**: `riverpod_generator` and `build_runner` add CI time and developer friction for 3 providers.
3. **Migration cost**: Converting 137 providers to codegen is high effort with no functional benefit for this codebase size.
4. **Riverpod 3.x**: Codegen becomes the default in Riverpod 3, but the project is on Riverpod 2.x. When upgrading to 3.x, a migration can be planned holistically.
5. **Developer onboarding**: One style (manual) is easier to learn than two.

### Implementation Plan

1. Convert the 3 `@riverpod` providers in `device_provider.dart` to manual syntax.
2. Delete `device_provider.g.dart`.
3. Remove `riverpod_annotation` and `riverpod_generator` from `pubspec.yaml`.
4. Remove `build_runner` if no other generators depend on it (check for `freezed_annotation`, `json_serializable`, etc.).
5. Run `flutter analyze` to verify no breakage.

### Future Consideration

When the project upgrades to Riverpod 3.x, re-evaluate codegen as a full migration at that point. The manual-to-codegen migration tooling should be mature by then.

## Date

2026-02-07
