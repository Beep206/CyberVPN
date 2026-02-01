# Android Source Sets

This directory contains flavor-specific and build-type-specific source sets for the CyberVPN Android app.

## Structure

```
src/
├── main/               # Main source set (shared across all flavors)
├── debug/              # Debug build type specific
├── profile/            # Profile build type specific
├── dev/                # Dev flavor specific
│   └── google-services.json
├── staging/            # Staging flavor specific
│   └── google-services.json
└── prod/               # Production flavor specific
    └── google-services.json
```

## Flavor-Specific Resources

Each flavor directory (`dev/`, `staging/`, `prod/`) contains:

- **google-services.json**: Firebase configuration specific to that environment
  - The files currently in version control are PLACEHOLDERS
  - Replace with real Firebase config files from Firebase Console
  - See `../FLAVOR_CONFIGURATION.md` for setup instructions

## Build Variants

Android Gradle combines flavors and build types to create build variants:

| Flavor  | Build Type | Variant Name     | Application ID                    |
|---------|------------|------------------|-----------------------------------|
| dev     | debug      | devDebug         | com.cybervpn.cybervpn_mobile.dev  |
| dev     | release    | devRelease       | com.cybervpn.cybervpn_mobile.dev  |
| staging | debug      | stagingDebug     | com.cybervpn.cybervpn_mobile.staging |
| staging | release    | stagingRelease   | com.cybervpn.cybervpn_mobile.staging |
| prod    | debug      | prodDebug        | com.cybervpn.cybervpn_mobile      |
| prod    | release    | prodRelease      | com.cybervpn.cybervpn_mobile      |

## Adding Flavor-Specific Resources

To add flavor-specific resources (beyond google-services.json):

1. Create the resource directory structure in the flavor directory:
   ```
   src/[flavor]/res/
   ├── values/
   ├── drawable/
   └── mipmap/
   ```

2. Add flavor-specific resources following standard Android resource structure

3. Resources in flavor-specific directories override those in `main/`

## Security Notes

- **DO NOT commit real Firebase configuration files** to public repositories
- Placeholder files are tracked to document structure
- For private repositories, you may track real configs, but consider using secrets management
- For CI/CD, use environment variables or secure secret storage

## More Information

See `../FLAVOR_CONFIGURATION.md` for complete configuration documentation.
