# OAuth Provider Setup Guide

## Overview

CyberVPN uses a unified OAuth authentication system that supports **7 providers** for both the admin dashboard (web) and the mobile app (iOS/Android). The backend implements the OAuth 2.0 authorization code flow with CSRF state tokens (stored in Redis with 10-minute TTL) and optional PKCE (RFC 7636) for providers that require it.

**Supported providers:**

| Provider | Flow Type | PKCE Required | Login | Account Linking |
|----------|-----------|---------------|-------|-----------------|
| Google | OAuth 2.0 Authorization Code | Yes | Yes | Yes |
| Apple | OAuth 2.0 + JWT client secret | Yes | Yes | Yes |
| GitHub | OAuth 2.0 Authorization Code | No | Yes | Yes |
| Discord | OAuth 2.0 Authorization Code | No | Yes | Yes |
| Microsoft | OAuth 2.0 Authorization Code | Yes | Yes | Yes |
| X (Twitter) | OAuth 2.0 + PKCE (mandatory) | Yes | Yes | Yes |
| Telegram | Widget-based HMAC-SHA256 | N/A | N/A | Yes |

**API endpoints:**

- `GET /api/v1/oauth/{provider}/login` -- Get authorization URL (unauthenticated)
- `POST /api/v1/oauth/{provider}/login/callback` -- Exchange code for JWT tokens (unauthenticated)
- `GET /api/v1/oauth/{provider}/authorize` -- Get authorization URL (authenticated, for account linking)
- `POST /api/v1/oauth/{provider}/callback` -- Link account to current user (authenticated)
- `DELETE /api/v1/oauth/{provider}` -- Unlink provider from current user (authenticated)

---

## Environment Variables

All OAuth settings are defined in `backend/src/config/settings.py` and loaded from `.env`. Every credential uses `SecretStr` for safe handling.

### Complete Variable Reference

| Variable | Type | Default | Required For | Description |
|----------|------|---------|-------------|-------------|
| `GOOGLE_CLIENT_ID` | `str` | `""` | Google | OAuth 2.0 Client ID |
| `GOOGLE_CLIENT_SECRET` | `SecretStr` | `""` | Google | OAuth 2.0 Client Secret |
| `APPLE_CLIENT_ID` | `str` | `""` | Apple | Service ID (e.g., `com.cybervpn.auth`) |
| `APPLE_TEAM_ID` | `str` | `""` | Apple | 10-character Apple Team ID |
| `APPLE_KEY_ID` | `str` | `""` | Apple | Key ID from the .p8 key file |
| `APPLE_PRIVATE_KEY` | `SecretStr` | `""` | Apple | Full PEM content of the .p8 key |
| `GITHUB_CLIENT_ID` | `str` | `""` | GitHub | OAuth App Client ID |
| `GITHUB_CLIENT_SECRET` | `SecretStr` | `""` | GitHub | OAuth App Client Secret |
| `DISCORD_CLIENT_ID` | `str` | `""` | Discord | Application Client ID |
| `DISCORD_CLIENT_SECRET` | `SecretStr` | `""` | Discord | Application Client Secret |
| `MICROSOFT_CLIENT_ID` | `str` | `""` | Microsoft | Application (client) ID |
| `MICROSOFT_CLIENT_SECRET` | `SecretStr` | `""` | Microsoft | Client secret value |
| `MICROSOFT_TENANT_ID` | `str` | `"common"` | Microsoft | Tenant ID or `common`/`consumers`/`organizations` |
| `TWITTER_CLIENT_ID` | `str` | `""` | X (Twitter) | OAuth 2.0 Client ID |
| `TWITTER_CLIENT_SECRET` | `SecretStr` | `""` | X (Twitter) | OAuth 2.0 Client Secret |
| `TELEGRAM_BOT_TOKEN` | `SecretStr` | `""` | Telegram | Bot token from BotFather |
| `TELEGRAM_BOT_USERNAME` | `str` | `""` | Telegram | Bot username without `@` prefix |
| `TELEGRAM_AUTH_MAX_AGE_SECONDS` | `int` | `86400` | Telegram | Max age of auth_date (default 24h) |

**Example `.env` block:**

```env
# OAuth Configuration
GOOGLE_CLIENT_ID=123456789-abcdef.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret-here

APPLE_CLIENT_ID=com.cybervpn.auth
APPLE_TEAM_ID=ABCDE12345
APPLE_KEY_ID=FGHIJ67890
APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIGTAgEA...your-key...\n-----END PRIVATE KEY-----"

GITHUB_CLIENT_ID=Iv1.abc123def456
GITHUB_CLIENT_SECRET=abc123def456ghi789

DISCORD_CLIENT_ID=123456789012345678
DISCORD_CLIENT_SECRET=abcdefghijklmnopqrstuvwxyz123456

MICROSOFT_CLIENT_ID=12345678-abcd-efgh-ijkl-123456789012
MICROSOFT_CLIENT_SECRET=your-secret-value
MICROSOFT_TENANT_ID=common

TWITTER_CLIENT_ID=abcdefghijklmnopqrstuvwxyz
TWITTER_CLIENT_SECRET=abcdefghijklmnopqrstuvwxyz123456789012345678

TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_BOT_USERNAME=CyberVPNBot
```

---

## Provider Setup Instructions

### Google

**Console:** [Google Cloud Console](https://console.cloud.google.com/) > APIs & Services > Credentials

**Steps:**

1. Create a new project or select the existing CyberVPN project.
2. Navigate to **APIs & Services > OAuth consent screen**.
   - Choose **External** user type.
   - Fill in App name ("CyberVPN"), support email, and developer contact.
   - Add scopes: `openid`, `email`, `profile`.
   - Add test users if the app is not yet verified.
3. Navigate to **APIs & Services > Credentials > Create Credentials > OAuth client ID**.
   - Application type: **Web application**.
   - Name: `CyberVPN Web + Mobile`.
4. Configure **Authorized redirect URIs**:
   - Web: `https://cybervpn.app/en/oauth/callback`
   - Mobile: `cybervpn://oauth/callback`
   - Development: `http://localhost:3001/en/oauth/callback`
5. Copy the **Client ID** and **Client Secret**.

**Required scopes (set in backend):** `openid email profile`

**Additional settings in backend:**
- `access_type=offline` is set to receive refresh tokens.
- `prompt=consent` forces the consent screen to get refresh tokens on every login.
- PKCE (S256) is enabled for this provider.

**Backend endpoints used:**
- Token exchange: `https://oauth2.googleapis.com/token`
- User info: `https://www.googleapis.com/oauth2/v3/userinfo`

**Env vars:**

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret
```

---

### Apple

**Console:** [Apple Developer Portal](https://developer.apple.com/) > Certificates, Identifiers & Profiles

Apple Sign In is different from other providers. It uses a JWT-based client secret signed with an ES256 private key, and the user's identity is extracted from an `id_token` JWT validated against Apple's JWKS endpoint.

**Steps:**

1. **Create an App ID** (if not already done):
   - Identifiers > App IDs > Register a new identifier.
   - Enable **Sign In with Apple** capability.
   - Bundle ID: `com.cybervpn.app` (must match your iOS app).

2. **Create a Service ID** (for web authentication):
   - Identifiers > Services IDs > Register a new identifier.
   - Description: `CyberVPN Web Auth`.
   - Identifier: `com.cybervpn.auth` (this becomes `APPLE_CLIENT_ID`).
   - Enable **Sign In with Apple**.
   - Configure:
     - Primary App ID: select your main app.
     - Domains: `cybervpn.app`
     - Return URLs:
       - `https://cybervpn.app/en/oauth/callback`
       - `cybervpn://oauth/callback`

3. **Create a Key** (for signing the client secret JWT):
   - Keys > Create a new key.
   - Name: `CyberVPN Sign In`.
   - Enable **Sign In with Apple**, configure with your Primary App ID.
   - Download the `.p8` file (you can only download it once).
   - Note the **Key ID** displayed (this is `APPLE_KEY_ID`).

4. **Find your Team ID:**
   - Displayed at the top-right of the developer portal, or under Membership.
   - 10-character alphanumeric string (this is `APPLE_TEAM_ID`).

**How the backend uses these:**
- A JWT client secret is generated on-the-fly, signed with ES256 using the private key.
- The JWT has `iss=APPLE_TEAM_ID`, `sub=APPLE_CLIENT_ID`, `aud=https://appleid.apple.com`.
- Maximum validity: 6 months (180 days).
- The `id_token` from Apple is validated against `https://appleid.apple.com/auth/keys` (JWKS).

**Required scopes:** `name email`

**Response mode:** `form_post` (Apple POSTs the callback data)

**Important notes:**
- Apple only sends the user's name on the **first authorization**. Store it on the first callback.
- The `id_token` is an RS256 JWT; the backend validates it against Apple's JWKS.
- PKCE is supported and enabled in the backend.

**Env vars:**

```env
APPLE_CLIENT_ID=com.cybervpn.auth
APPLE_TEAM_ID=ABCDE12345
APPLE_KEY_ID=FGHIJ67890
APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIGTAgEA...(full .p8 contents, newlines escaped as \\n)...\n-----END PRIVATE KEY-----"
```

**Tip:** For the private key in `.env`, you can either:
- Escape newlines: replace each newline in the .p8 file with `\n` and wrap in quotes.
- Use a file reference in your deployment system (e.g., Docker secrets, Vault).

---

### GitHub

**Console:** [GitHub Settings](https://github.com/settings/developers) > Developer settings > OAuth Apps

**Steps:**

1. Click **New OAuth App** (or select existing).
2. Fill in:
   - Application name: `CyberVPN`
   - Homepage URL: `https://cybervpn.app`
   - Authorization callback URL: `https://cybervpn.app/en/oauth/callback`
3. Click **Register application**.
4. Copy the **Client ID**.
5. Click **Generate a new client secret** and copy it immediately.

**Required scopes (set in backend):** `read:user user:email`

**Notes:**
- GitHub does not support PKCE; the backend uses the standard authorization code flow.
- GitHub returns the user email as `null` if the user has set their email to private. The backend fetches it from the user endpoint.
- No refresh token is provided by GitHub; the access token is long-lived.

**Backend endpoints used:**
- Token exchange: `https://github.com/login/oauth/access_token`
- User info: `https://api.github.com/user`

**Env vars:**

```env
GITHUB_CLIENT_ID=Iv1.abc123def456
GITHUB_CLIENT_SECRET=abc123def456ghi789jkl012
```

---

### Discord

**Console:** [Discord Developer Portal](https://discord.com/developers/applications) > Applications

**Steps:**

1. Click **New Application** (or select existing).
   - Name: `CyberVPN`
2. Navigate to **OAuth2** in the left sidebar.
3. Copy the **Client ID** and **Client Secret** (click Reset Secret if needed).
4. Add **Redirects**:
   - `https://cybervpn.app/en/oauth/callback`
   - `cybervpn://oauth/callback`
   - Development: `http://localhost:3001/en/oauth/callback`
5. Under **OAuth2 URL Generator** (for testing):
   - Select scopes: `identify`, `email`
   - Use to verify your redirect URIs work.

**Required scopes (set in backend):** `identify email`

**Notes:**
- Discord does not require PKCE; the backend uses the standard authorization code flow.
- Discord provides a refresh token.
- Avatar URL is constructed from the user ID and avatar hash: `https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png`.

**Backend endpoints used:**
- Token exchange: `https://discord.com/api/oauth2/token`
- User info: `https://discord.com/api/users/@me`

**Env vars:**

```env
DISCORD_CLIENT_ID=123456789012345678
DISCORD_CLIENT_SECRET=abcdefghijklmnopqrstuvwxyz123456
```

---

### Microsoft

**Console:** [Azure Portal](https://portal.azure.com/) > Microsoft Entra ID (Azure AD) > App registrations

**Steps:**

1. Click **New registration**.
   - Name: `CyberVPN`
   - Supported account types: Choose based on your needs:
     - **Personal Microsoft accounts only** -- for consumer apps
     - **Accounts in any organizational directory and personal Microsoft accounts** -- broadest reach
     - The `MICROSOFT_TENANT_ID` controls this at runtime (see below).
2. Set **Redirect URIs** (Platform: Web):
   - `https://cybervpn.app/en/oauth/callback`
   - `cybervpn://oauth/callback` (add as Mobile/Desktop platform)
   - Development: `http://localhost:3001/en/oauth/callback`
3. Copy the **Application (client) ID** (this is `MICROSOFT_CLIENT_ID`).
4. Navigate to **Certificates & secrets > Client secrets > New client secret**.
   - Description: `CyberVPN Production`
   - Expiry: 24 months (set a calendar reminder to rotate).
   - Copy the secret **Value** (not the Secret ID).
5. Navigate to **API permissions** and ensure these are granted:
   - `openid`, `email`, `profile`, `User.Read` (Microsoft Graph).

**Tenant ID options:**

| Value | Accepts |
|-------|---------|
| `common` | Work/school + personal Microsoft accounts |
| `organizations` | Work/school accounts only |
| `consumers` | Personal Microsoft accounts only |
| `{tenant-id}` | Specific Azure AD tenant only |

The default in the backend is `common`.

**Required scopes (set in backend):** `openid email profile User.Read`

**Notes:**
- PKCE is supported and enabled.
- For work accounts, email comes from the `mail` field; for personal accounts, it falls back to `userPrincipalName`.
- The backend uses Microsoft Graph API v1.0 (`https://graph.microsoft.com/v1.0/me`) for user info.

**Backend endpoints used (tenant-dependent):**
- Authorize: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize`
- Token exchange: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`
- User info: `https://graph.microsoft.com/v1.0/me`

**Env vars:**

```env
MICROSOFT_CLIENT_ID=12345678-abcd-efgh-ijkl-123456789012
MICROSOFT_CLIENT_SECRET=your-client-secret-value
MICROSOFT_TENANT_ID=common
```

---

### X (Twitter)

**Console:** [X Developer Portal](https://developer.twitter.com/en/portal) > Projects & Apps

**Steps:**

1. Create a new Project and App (or select existing).
2. Navigate to **User authentication settings > Set up**.
3. Configure:
   - App permissions: **Read** (minimum).
   - Type of App: **Web App, Automated App or Bot**.
   - Callback URI / Redirect URL:
     - `https://cybervpn.app/en/oauth/callback`
     - `cybervpn://oauth/callback`
   - Website URL: `https://cybervpn.app`
4. Navigate to **Keys and tokens > OAuth 2.0 Client ID and Client Secret**.
   - Copy both values.

**Required scopes (set in backend):** `users.read tweet.read`

**PKCE is mandatory for X/Twitter OAuth 2.0.** The backend automatically generates the code verifier/challenge pair (S256).

**Important notes:**
- X/Twitter uses HTTP Basic Auth (`client_id:client_secret` base64-encoded) for the token exchange endpoint.
- The `email` field is **not available** in the basic scope (`users.read`). Users who sign in via X will not have an email address linked.
- No refresh token is provided.
- User info is fetched from the Twitter API v2 with `user.fields=profile_image_url,name,username`.

**Backend endpoints used:**
- Authorize: `https://twitter.com/i/oauth2/authorize`
- Token exchange: `https://api.twitter.com/2/oauth2/token`
- User info: `https://api.twitter.com/2/users/me`

**Env vars:**

```env
TWITTER_CLIENT_ID=your-oauth2-client-id
TWITTER_CLIENT_SECRET=your-oauth2-client-secret
```

---

### Telegram

**Console:** [BotFather](https://t.me/BotFather) on Telegram

Telegram uses a **widget-based authentication** flow, not a standard OAuth 2.0 code exchange. The user authorizes via Telegram's login widget, and the server validates the callback using HMAC-SHA256 with the bot token.

**Steps:**

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot` (or use your existing bot).
3. Follow the prompts to set the bot name and username.
4. Copy the **bot token** (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`).
5. Send `/setdomain` to BotFather:
   - Select your bot.
   - Set the domain: `cybervpn.app` (for the Telegram Login Widget).
6. Note your bot's **username** (without the `@`).

**Security model:**
- The backend validates callbacks with HMAC-SHA256: `HMAC_SHA256(SHA256(bot_token), data_check_string)`.
- The `auth_date` is checked to prevent replay attacks (default max age: 24 hours).
- Constant-time comparison is used for hash validation.

**Notes:**
- Telegram auth is used only for **account linking** (not for unauthenticated login), because there is no authorization code flow.
- The authorize URL points to `https://oauth.telegram.org/auth` with the bot ID and origin.

**Env vars:**

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_BOT_USERNAME=CyberVPNBot
TELEGRAM_AUTH_MAX_AGE_SECONDS=86400
```

---

## Mobile Platform Configuration

### iOS

**File:** `cybervpn_mobile/ios/Runner/Info.plist`

The following are already configured:

1. **URL Scheme** (`cybervpn://`):
   ```xml
   <key>CFBundleURLTypes</key>
   <array>
       <dict>
           <key>CFBundleTypeRole</key>
           <string>Editor</string>
           <key>CFBundleURLName</key>
           <string>com.cybervpn.app</string>
           <key>CFBundleURLSchemes</key>
           <array>
               <string>cybervpn</string>
           </array>
       </dict>
   </array>
   ```

2. **Deep Linking enabled:**
   ```xml
   <key>FlutterDeepLinkingEnabled</key>
   <true/>
   ```

**Additional setup required for Sign In with Apple:**

1. In Xcode, open the project and select the Runner target.
2. Go to **Signing & Capabilities**.
3. Click **+ Capability** and add **Sign In with Apple**.
4. Ensure the App ID in the Apple Developer Portal has Sign In with Apple enabled.

**Associated Domains (for universal links):**

1. Add the **Associated Domains** capability in Xcode.
2. Add domain: `applinks:cybervpn.app`
3. Host an `apple-app-site-association` file at `https://cybervpn.app/.well-known/apple-app-site-association`:
   ```json
   {
     "applinks": {
       "apps": [],
       "details": [
         {
           "appID": "TEAM_ID.com.cybervpn.app",
           "paths": ["/*/oauth/callback", "/magic-link/*"]
         }
       ]
     }
   }
   ```

**Google Sign-In on iOS:**
- Add the reversed client ID from Google to `CFBundleURLSchemes` in `Info.plist`.
- Format: `com.googleusercontent.apps.YOUR_CLIENT_ID` (reversed).

### Android

**File:** `cybervpn_mobile/android/app/src/main/AndroidManifest.xml`

The following deep link intent filters are already configured:

1. **Generic `cybervpn://` scheme handler** (with `autoVerify`):
   ```xml
   <intent-filter android:autoVerify="true">
       <action android:name="android.intent.action.VIEW"/>
       <category android:name="android.intent.category.DEFAULT"/>
       <category android:name="android.intent.category.BROWSABLE"/>
       <data android:scheme="cybervpn"/>
   </intent-filter>
   ```

2. **OAuth callback handler** (`cybervpn://oauth/callback`):
   ```xml
   <intent-filter>
       <action android:name="android.intent.action.VIEW"/>
       <category android:name="android.intent.category.DEFAULT"/>
       <category android:name="android.intent.category.BROWSABLE"/>
       <data android:scheme="cybervpn" android:host="oauth" android:pathPrefix="/callback"/>
   </intent-filter>
   ```

3. **Telegram callback handler** (`cybervpn://telegram/callback`):
   ```xml
   <intent-filter>
       <action android:name="android.intent.action.VIEW"/>
       <category android:name="android.intent.category.DEFAULT"/>
       <category android:name="android.intent.category.BROWSABLE"/>
       <data android:scheme="cybervpn" android:host="telegram" android:pathPrefix="/callback"/>
   </intent-filter>
   ```

4. **Universal link handler** (`https://cybervpn.app`):
   ```xml
   <intent-filter android:autoVerify="true">
       <action android:name="android.intent.action.VIEW"/>
       <category android:name="android.intent.category.DEFAULT"/>
       <category android:name="android.intent.category.BROWSABLE"/>
       <data android:scheme="https" android:host="cybervpn.app"/>
   </intent-filter>
   ```

**Additional setup for Google Sign-In on Android:**

1. In [Firebase Console](https://console.firebase.google.com/), add your Android app if not already added.
2. Download `google-services.json` and place it in `cybervpn_mobile/android/app/`.
3. Add your app's SHA-1 and SHA-256 fingerprints in the Firebase console:
   ```bash
   # Debug fingerprint
   cd cybervpn_mobile/android && ./gradlew signingReport

   # Release fingerprint (from your keystore)
   keytool -list -v -keystore your-release-key.jks
   ```
4. Also add the SHA-1 fingerprint in the Google Cloud Console credential for the Android OAuth client.

**App Links verification (for `https://cybervpn.app`):**

Host an `assetlinks.json` file at `https://cybervpn.app/.well-known/assetlinks.json`:
```json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "com.cybervpn.app",
      "sha256_cert_fingerprints": [
        "YOUR_SHA256_FINGERPRINT_HERE"
      ]
    }
  }
]
```

---

## Redirect URI Patterns

All OAuth providers redirect back to the app after authentication. The mobile app uses a custom URL scheme (`cybervpn://`) and the web dashboard uses HTTPS URLs.

| Provider | Web Redirect URI | Mobile Redirect URI | Dev Redirect URI |
|----------|-----------------|---------------------|------------------|
| Google | `https://cybervpn.app/en/oauth/callback` | `cybervpn://oauth/callback` | `http://localhost:3001/en/oauth/callback` |
| Apple | `https://cybervpn.app/en/oauth/callback` | `cybervpn://oauth/callback` | `http://localhost:3001/en/oauth/callback` |
| GitHub | `https://cybervpn.app/en/oauth/callback` | `cybervpn://oauth/callback` | `http://localhost:3001/en/oauth/callback` |
| Discord | `https://cybervpn.app/en/oauth/callback` | `cybervpn://oauth/callback` | `http://localhost:3001/en/oauth/callback` |
| Microsoft | `https://cybervpn.app/en/oauth/callback` | `cybervpn://oauth/callback` | `http://localhost:3001/en/oauth/callback` |
| X (Twitter) | `https://cybervpn.app/en/oauth/callback` | `cybervpn://oauth/callback` | `http://localhost:3001/en/oauth/callback` |
| Telegram | `https://cybervpn.app` (widget origin) | `cybervpn://telegram/callback` | `http://localhost:3001` |

**Important:** Every redirect URI listed above must be registered in the corresponding provider's developer console. Missing or mismatched URIs are the most common cause of OAuth failures.

---

## Testing

### Development Environment

1. **Start the backend:**
   ```bash
   cd backend && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Verify provider availability:**
   ```bash
   # Check that a provider is configured (returns authorize URL if credentials are set)
   curl -s "http://localhost:8000/api/v1/oauth/google/login?redirect_uri=http://localhost:3001/en/oauth/callback" | jq .
   ```
   A successful response returns `{ "authorize_url": "...", "state": "..." }`.
   If credentials are missing, the provider will return an error during code exchange.

3. **Test the full flow manually:**
   ```bash
   # Step 1: Get authorization URL
   AUTH_RESPONSE=$(curl -s "http://localhost:8000/api/v1/oauth/google/login?redirect_uri=http://localhost:3001/en/oauth/callback")
   AUTH_URL=$(echo $AUTH_RESPONSE | jq -r '.authorize_url')
   STATE=$(echo $AUTH_RESPONSE | jq -r '.state')

   # Step 2: Open AUTH_URL in a browser, complete authentication, capture the code from the redirect

   # Step 3: Exchange the code
   curl -s -X POST "http://localhost:8000/api/v1/oauth/google/login/callback" \
     -H "Content-Type: application/json" \
     -d "{\"code\": \"CAPTURED_CODE\", \"state\": \"$STATE\", \"redirect_uri\": \"http://localhost:3001/en/oauth/callback\"}" | jq .
   ```

4. **Verify state token expiry:**
   State tokens expire after 10 minutes (600 seconds). Waiting longer than 10 minutes between getting the authorize URL and completing the callback should return `"Invalid or expired OAuth state."`.

### Production Verification

1. Ensure all environment variables are set (non-empty) for each provider you want to enable.
2. Test each provider end-to-end using the mobile app and the web dashboard.
3. Verify that:
   - New users are created with `role=viewer` and `is_active=true`.
   - Existing users with matching email are auto-linked (no duplicate accounts).
   - Users with TOTP enabled are prompted for 2FA after OAuth login (`requires_2fa=true`).
   - Account linking works for authenticated users.
   - Unlinking works and removes the `oauth_accounts` row.

### Provider-Specific Testing Notes

| Provider | Gotcha |
|----------|--------|
| Google | Must set `prompt=consent` to get refresh tokens. Without it, refresh_token is only sent on first authorization. |
| Apple | User name is only provided on first authorization. Test with a fresh Apple ID or revoke access at `appleid.apple.com` > Security > Apps. |
| GitHub | Email may be `null` if user has a private email. The user will be created without an email. |
| Discord | Test with a verified email account; unverified emails are not returned. |
| Microsoft | Personal vs. work accounts behave differently for the `mail` field. Test both if `MICROSOFT_TENANT_ID=common`. |
| X (Twitter) | Email is never available with `users.read` scope. Users signing in via X will not have an email. |
| Telegram | Test that auth_date validation rejects requests older than 24 hours. Test clock skew rejection (future dates beyond 5 minutes). |

### Disabling a Provider

To disable a specific provider, leave its environment variables empty (the default). The backend checks for non-empty `client_id` and `client_secret` before attempting code exchange and returns `None` if credentials are missing, which results in a `401 Unauthorized` response.

---

## Security Considerations

- **State tokens** are stored in Redis with a 10-minute TTL and are single-use (deleted atomically on validation). This prevents CSRF and replay attacks.
- **PKCE** (RFC 7636, S256) is used for Google, Apple, Microsoft, and Twitter. The code verifier is stored in Redis alongside the state token.
- **IP address logging:** The client IP is logged with the state token for audit purposes. IP changes during the OAuth flow are logged as warnings but do not block the flow (to accommodate mobile/NAT users).
- **Apple client secret:** Generated as a JWT signed with ES256, valid for up to 6 months. Rotate the .p8 key if compromised.
- **Telegram:** Uses constant-time HMAC comparison to prevent timing attacks.
- All provider tokens (`access_token`, `refresh_token`) are stored in the `oauth_accounts` database table. Ensure the database is encrypted at rest in production.

---

## Source Code Reference

| File | Purpose |
|------|---------|
| `backend/src/config/settings.py` | All OAuth env var definitions (lines 37-67) |
| `backend/src/infrastructure/oauth/google.py` | Google provider implementation |
| `backend/src/infrastructure/oauth/apple.py` | Apple provider implementation |
| `backend/src/infrastructure/oauth/github.py` | GitHub provider implementation |
| `backend/src/infrastructure/oauth/discord.py` | Discord provider implementation |
| `backend/src/infrastructure/oauth/microsoft.py` | Microsoft provider implementation |
| `backend/src/infrastructure/oauth/twitter.py` | X/Twitter provider implementation |
| `backend/src/infrastructure/oauth/telegram.py` | Telegram provider implementation |
| `backend/src/application/services/oauth_state_service.py` | CSRF state + PKCE management |
| `backend/src/application/use_cases/auth/oauth_login.py` | Find-or-create user from OAuth data |
| `backend/src/presentation/api/v1/oauth/routes.py` | All OAuth API routes |
| `backend/src/presentation/api/v1/oauth/schemas.py` | Request/response Pydantic schemas |
| `backend/src/infrastructure/database/models/oauth_account_model.py` | OAuth accounts DB model |
| `backend/.env.example` | Example env configuration |
| `cybervpn_mobile/android/app/src/main/AndroidManifest.xml` | Android deep link intent filters |
| `cybervpn_mobile/ios/Runner/Info.plist` | iOS URL scheme and deep link config |
| `cybervpn_mobile/lib/features/auth/data/datasources/oauth_remote_ds.dart` | Mobile OAuth API client |
| `cybervpn_mobile/lib/features/profile/domain/entities/oauth_provider.dart` | Mobile provider enum |
