# Firebase Configuration Files

This directory contains environment-specific Firebase configuration files for iOS.

## Setup

Replace the placeholder `GoogleService-Info-*.plist` files with actual Firebase project configurations:

### 1. Dev Environment
- **File**: `GoogleService-Info-Dev.plist`
- **Bundle ID**: `com.cybervpn.app.dev`
- **Firebase Project**: Create or use existing dev project
- Download from Firebase Console → Project Settings → iOS App

### 2. Staging Environment
- **File**: `GoogleService-Info-Staging.plist`
- **Bundle ID**: `com.cybervpn.app.staging`
- **Firebase Project**: Create or use existing staging project
- Download from Firebase Console → Project Settings → iOS App

### 3. Production Environment
- **File**: `GoogleService-Info-Prod.plist`
- **Bundle ID**: `com.cybervpn.app`
- **Firebase Project**: Create or use existing production project
- Download from Firebase Console → Project Settings → iOS App

## How It Works

The build process automatically selects the correct `GoogleService-Info.plist` based on the build configuration:
- `Debug-Dev` → Uses `GoogleService-Info-Dev.plist`
- `Debug-Staging` → Uses `GoogleService-Info-Staging.plist`
- `Release-Dev` → Uses `GoogleService-Info-Dev.plist`
- `Release-Staging` → Uses `GoogleService-Info-Staging.plist`
- `Release-Prod` → Uses `GoogleService-Info-Prod.plist`

The "Copy Firebase Config" build phase script handles this automatically during the build.

## Security Note

**Never commit actual Firebase configuration files to version control!**
- Add `GoogleService-Info-*.plist` to `.gitignore`
- Store actual configs in secure secret management
- Use CI/CD secrets for automated builds
