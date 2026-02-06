// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Polish (`pl`).
class AppLocalizationsPl extends AppLocalizations {
  AppLocalizationsPl([String locale = 'pl']) : super(locale);

  @override
  String get appName => 'CyberVPN';

  @override
  String get login => 'Log In';

  @override
  String get register => 'Sign Up';

  @override
  String get email => 'Email';

  @override
  String get password => 'Password';

  @override
  String get confirmPassword => 'Confirm Password';

  @override
  String get forgotPassword => 'Forgot Password?';

  @override
  String get orContinueWith => 'Or continue with';

  @override
  String get connect => 'Connect';

  @override
  String get disconnect => 'Disconnect';

  @override
  String get connecting => 'Connecting...';

  @override
  String get disconnecting => 'Disconnecting...';

  @override
  String get connected => 'Connected';

  @override
  String get disconnected => 'Disconnected';

  @override
  String get servers => 'Servers';

  @override
  String get subscription => 'Subscription';

  @override
  String get settings => 'Settings';

  @override
  String get profile => 'Profile';

  @override
  String get selectServer => 'Select Server';

  @override
  String get autoSelect => 'Auto Select';

  @override
  String get fastestServer => 'Fastest Server';

  @override
  String get nearestServer => 'Nearest Server';

  @override
  String get killSwitch => 'Kill Switch';

  @override
  String get splitTunneling => 'Split Tunneling';

  @override
  String get autoConnect => 'Auto Connect';

  @override
  String get language => 'Language';

  @override
  String get theme => 'Theme';

  @override
  String get darkMode => 'Dark Mode';

  @override
  String get lightMode => 'Light Mode';

  @override
  String get systemDefault => 'System Default';

  @override
  String get logout => 'Log Out';

  @override
  String get logoutConfirm => 'Are you sure you want to log out?';

  @override
  String get cancel => 'Cancel';

  @override
  String get confirm => 'Confirm';

  @override
  String get retry => 'Retry';

  @override
  String get errorOccurred => 'An error occurred';

  @override
  String get noInternet => 'No internet connection';

  @override
  String get downloadSpeed => 'Download';

  @override
  String get uploadSpeed => 'Upload';

  @override
  String get connectionTime => 'Connection Time';

  @override
  String get dataUsed => 'Data Used';

  @override
  String get currentPlan => 'Current Plan';

  @override
  String get upgradePlan => 'Upgrade Plan';

  @override
  String daysRemaining(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Pozostało $count dni',
      many: 'Pozostało $count dni',
      few: 'Pozostały $count dni',
      one: 'Pozostał $count dzień',
    );
    return '$_temp0';
  }

  @override
  String get referral => 'Referral';

  @override
  String get shareReferralCode => 'Share Referral Code';

  @override
  String get support => 'Support';

  @override
  String get privacyPolicy => 'Privacy Policy';

  @override
  String get termsOfService => 'Terms of Service';

  @override
  String version(String version) {
    return 'Version $version';
  }

  @override
  String get onboardingWelcomeTitle => 'Welcome to CyberVPN';

  @override
  String get onboardingWelcomeDescription =>
      'Secure, fast, and private internet access at your fingertips.';

  @override
  String get onboardingFeaturesTitle => 'Powerful Features';

  @override
  String get onboardingFeaturesDescription =>
      'Kill switch, split tunneling, and military-grade encryption to keep you safe.';

  @override
  String get onboardingPrivacyTitle => 'Your Privacy Matters';

  @override
  String get onboardingPrivacyDescription =>
      'Zero-log policy. We never track, store, or share your browsing data.';

  @override
  String get onboardingSpeedTitle => 'Lightning Fast';

  @override
  String get onboardingSpeedDescription =>
      'Connect to optimized servers worldwide for the best speeds.';

  @override
  String get onboardingSkip => 'Skip';

  @override
  String get onboardingNext => 'Next';

  @override
  String get onboardingGetStarted => 'Get Started';

  @override
  String get onboardingBack => 'Back';

  @override
  String onboardingPageIndicator(int current, int total) {
    return 'Page $current of $total';
  }

  @override
  String get settingsTitle => 'Settings';

  @override
  String get settingsGeneral => 'General';

  @override
  String get settingsVpn => 'VPN Settings';

  @override
  String get settingsAppearance => 'Appearance';

  @override
  String get settingsDebug => 'Debug';

  @override
  String get settingsNotifications => 'Notifications';

  @override
  String get settingsAbout => 'About';

  @override
  String get settingsVpnProtocolLabel => 'Protocol';

  @override
  String get settingsVpnProtocolDescription =>
      'Select the VPN protocol to use for connections.';

  @override
  String get settingsAutoConnectLabel => 'Auto Connect';

  @override
  String get settingsAutoConnectDescription =>
      'Automatically connect when the app starts.';

  @override
  String get settingsKillSwitchLabel => 'Kill Switch';

  @override
  String get settingsKillSwitchDescription =>
      'Block internet if VPN connection drops.';

  @override
  String get settingsDnsLabel => 'Custom DNS';

  @override
  String get settingsDnsDescription =>
      'Use a custom DNS server for resolution.';

  @override
  String get settingsDnsPlaceholder => 'Enter DNS address';

  @override
  String get settingsSplitTunnelingLabel => 'Split Tunneling';

  @override
  String get settingsSplitTunnelingDescription =>
      'Choose which apps use the VPN connection.';

  @override
  String get settingsThemeModeLabel => 'Theme Mode';

  @override
  String get settingsThemeModeDescription =>
      'Choose between light, dark, or system theme.';

  @override
  String get settingsLanguageLabel => 'Language';

  @override
  String get settingsLanguageDescription => 'Select your preferred language.';

  @override
  String get settingsDebugLogsLabel => 'Debug Logs';

  @override
  String get settingsDebugLogsDescription =>
      'Enable verbose logging for troubleshooting.';

  @override
  String get settingsExportLogsLabel => 'Export Logs';

  @override
  String get settingsExportLogsDescription => 'Export debug logs for support.';

  @override
  String get settingsResetLabel => 'Reset Settings';

  @override
  String get settingsResetDescription =>
      'Restore all settings to default values.';

  @override
  String get settingsResetConfirm =>
      'Are you sure you want to reset all settings to defaults?';

  @override
  String get settingsStartOnBootLabel => 'Start on Boot';

  @override
  String get settingsStartOnBootDescription =>
      'Automatically launch CyberVPN when your device starts.';

  @override
  String get settingsConnectionTimeoutLabel => 'Connection Timeout';

  @override
  String get settingsConnectionTimeoutDescription =>
      'Maximum time to wait before a connection attempt is aborted.';

  @override
  String settingsConnectionTimeoutSeconds(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count sekund',
      many: '$count sekund',
      few: '$count sekundy',
      one: '$count sekunda',
    );
    return '$_temp0';
  }

  @override
  String get profileDashboard => 'Profile Dashboard';

  @override
  String get profileEditProfile => 'Edit Profile';

  @override
  String get profileDisplayName => 'Display Name';

  @override
  String get profileEmailAddress => 'Email Address';

  @override
  String get profileChangePassword => 'Change Password';

  @override
  String get profileCurrentPassword => 'Current Password';

  @override
  String get profileNewPassword => 'New Password';

  @override
  String get profileConfirmNewPassword => 'Confirm New Password';

  @override
  String get profileTwoFactorAuth => 'Two-Factor Authentication';

  @override
  String get profileTwoFactorAuthDescription =>
      'Add an extra layer of security to your account.';

  @override
  String get profileTwoFactorEnable => 'Enable 2FA';

  @override
  String get profileTwoFactorDisable => 'Disable 2FA';

  @override
  String get profileTwoFactorSetup => 'Set Up Two-Factor Authentication';

  @override
  String get profileTwoFactorScanQr =>
      'Scan this QR code with your authenticator app.';

  @override
  String get profileTwoFactorEnterCode =>
      'Enter the 6-digit code from your authenticator app.';

  @override
  String get profileTwoFactorBackupCodes => 'Backup Codes';

  @override
  String get profileTwoFactorBackupCodesDescription =>
      'Save these codes in a safe place. You can use them to sign in if you lose access to your authenticator app.';

  @override
  String get profileOauthAccounts => 'Linked Accounts';

  @override
  String get profileOauthAccountsDescription =>
      'Manage your linked social accounts.';

  @override
  String get profileOauthLink => 'Link Account';

  @override
  String get profileOauthUnlink => 'Unlink';

  @override
  String get profileOauthUnlinkConfirm =>
      'Are you sure you want to unlink this account?';

  @override
  String get profileTrustedDevices => 'Trusted Devices';

  @override
  String get profileTrustedDevicesDescription =>
      'Manage the devices that can access your account.';

  @override
  String get profileDeviceCurrent => 'Current Device';

  @override
  String profileDeviceLastActive(String date) {
    return 'Last active $date';
  }

  @override
  String get profileDeviceRevoke => 'Revoke Access';

  @override
  String get profileDeviceRevokeConfirm =>
      'Are you sure you want to revoke access for this device?';

  @override
  String get profileDeviceRevokeAll => 'Revoke All Devices';

  @override
  String get profileDeleteAccount => 'Delete Account';

  @override
  String get profileDeleteAccountDescription =>
      'Permanently delete your account and all associated data.';

  @override
  String get profileDeleteAccountConfirm =>
      'Are you sure you want to delete your account? This action cannot be undone.';

  @override
  String get profileDeleteAccountButton => 'Delete My Account';

  @override
  String get profileSubscriptionStatus => 'Subscription Status';

  @override
  String profileMemberSince(String date) {
    return 'Member since $date';
  }

  @override
  String get configImportTitle => 'Import Configuration';

  @override
  String get configImportQrScanTitle => 'Scan QR Code';

  @override
  String get configImportQrScanDescription =>
      'Point your camera at a VPN configuration QR code.';

  @override
  String get configImportScanQrButton => 'Scan QR Code';

  @override
  String get configImportFromClipboard => 'Import from Clipboard';

  @override
  String get configImportFromClipboardDescription =>
      'Paste a configuration link or text from your clipboard.';

  @override
  String get configImportFromFile => 'Import from File';

  @override
  String get configImportFromFileDescription =>
      'Select a configuration file from your device.';

  @override
  String get configImportPreviewTitle => 'Configuration Preview';

  @override
  String get configImportPreviewServer => 'Server';

  @override
  String get configImportPreviewProtocol => 'Protocol';

  @override
  String get configImportPreviewPort => 'Port';

  @override
  String get configImportConfirmButton => 'Import Configuration';

  @override
  String get configImportCancelButton => 'Cancel Import';

  @override
  String get configImportSuccess => 'Configuration imported successfully.';

  @override
  String get configImportError => 'Failed to import configuration.';

  @override
  String get configImportInvalidFormat => 'Invalid configuration format.';

  @override
  String get configImportDuplicate => 'This configuration already exists.';

  @override
  String get configImportCameraPermission =>
      'Camera permission is required to scan QR codes.';

  @override
  String get notificationCenterTitle => 'Notifications';

  @override
  String get notificationCenterEmpty => 'No notifications yet.';

  @override
  String get notificationCenterMarkAllRead => 'Mark All as Read';

  @override
  String get notificationCenterClearAll => 'Clear All';

  @override
  String get notificationTypeConnectionStatus => 'Connection Status';

  @override
  String get notificationTypeServerSwitch => 'Server Switch';

  @override
  String get notificationTypeSubscriptionExpiry => 'Subscription Expiry';

  @override
  String get notificationTypeSecurityAlert => 'Security Alert';

  @override
  String get notificationTypePromotion => 'Promotion';

  @override
  String get notificationTypeSystemUpdate => 'System Update';

  @override
  String notificationConnected(String serverName) {
    return 'Connected to $serverName';
  }

  @override
  String get notificationDisconnected => 'Disconnected from VPN.';

  @override
  String notificationServerSwitched(String serverName) {
    return 'Switched to $serverName.';
  }

  @override
  String notificationSubscriptionExpiring(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count dni',
      many: '$count dni',
      few: '$count dni',
      one: '$count dzień',
    );
    return 'Twoja subskrypcja wygasa za $_temp0.';
  }

  @override
  String get notificationSubscriptionExpired =>
      'Your subscription has expired. Renew to continue using CyberVPN.';

  @override
  String notificationUnreadCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count nieprzeczytanych powiadomień',
      many: '$count nieprzeczytanych powiadomień',
      few: '$count nieprzeczytane powiadomienia',
      one: '$count nieprzeczytane powiadomienie',
      zero: 'Brak nieprzeczytanych powiadomień',
    );
    return '$_temp0';
  }

  @override
  String get referralDashboardTitle => 'Referral Program';

  @override
  String get referralDashboardDescription => 'Invite friends and earn rewards.';

  @override
  String get referralShareLink => 'Share Referral Link';

  @override
  String get referralCopyLink => 'Copy Link';

  @override
  String get referralLinkCopied => 'Referral link copied to clipboard.';

  @override
  String get referralCodeLabel => 'Your Referral Code';

  @override
  String referralRewardsEarned(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count nagród zdobytych',
      many: '$count nagród zdobytych',
      few: '$count nagrody zdobyte',
      one: '$count nagroda zdobyta',
      zero: 'Brak zdobytych nagród',
    );
    return '$_temp0';
  }

  @override
  String referralFriendsInvited(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count znajomych zaproszonych',
      many: '$count znajomych zaproszonych',
      few: '$count znajomych zaproszonych',
      one: '$count znajomy zaproszony',
      zero: 'Brak zaproszonych znajomych',
    );
    return '$_temp0';
  }

  @override
  String referralRewardDescription(int days) {
    return 'Get $days free days for each friend who subscribes.';
  }

  @override
  String get referralHistory => 'Referral History';

  @override
  String get referralPending => 'Pending';

  @override
  String get referralCompleted => 'Completed';

  @override
  String get referralExpired => 'Expired';

  @override
  String get diagnosticsTitle => 'Diagnostics';

  @override
  String get diagnosticsDescription =>
      'Test your connection and troubleshoot issues.';

  @override
  String get speedTestTitle => 'Speed Test';

  @override
  String get speedTestStart => 'Start Speed Test';

  @override
  String get speedTestRunning => 'Testing...';

  @override
  String get speedTestDownloadSpeed => 'Download Speed';

  @override
  String get speedTestUploadSpeed => 'Upload Speed';

  @override
  String get speedTestPing => 'Ping';

  @override
  String speedTestPingMs(int value) {
    return '$value ms';
  }

  @override
  String speedTestMbps(String value) {
    return '$value Mbps';
  }

  @override
  String get speedTestResult => 'Speed Test Result';

  @override
  String get speedTestHistory => 'Speed Test History';

  @override
  String get speedTestStepConnecting => 'Connecting to test server...';

  @override
  String get speedTestStepDownload => 'Testing download speed...';

  @override
  String get speedTestStepUpload => 'Testing upload speed...';

  @override
  String get speedTestStepPing => 'Measuring latency...';

  @override
  String get speedTestStepComplete => 'Test complete.';

  @override
  String get speedTestNoVpn => 'Connect to VPN before running a speed test.';

  @override
  String get logViewerTitle => 'Log Viewer';

  @override
  String get logViewerEmpty => 'No logs available.';

  @override
  String get logViewerExportButton => 'Export Logs';

  @override
  String get logViewerClearButton => 'Clear Logs';

  @override
  String get logViewerClearConfirm =>
      'Are you sure you want to clear all logs?';

  @override
  String get logViewerFilterLabel => 'Filter';

  @override
  String get logViewerFilterAll => 'All';

  @override
  String get logViewerFilterError => 'Errors';

  @override
  String get logViewerFilterWarning => 'Warnings';

  @override
  String get logViewerFilterInfo => 'Info';

  @override
  String get logViewerCopied => 'Log entry copied to clipboard.';

  @override
  String get logViewerExportSuccess => 'Logs exported successfully.';

  @override
  String get logViewerExportError => 'Failed to export logs.';

  @override
  String get widgetConnectLabel => 'Connect VPN';

  @override
  String get widgetDisconnectLabel => 'Disconnect VPN';

  @override
  String get widgetStatusLabel => 'VPN Status';

  @override
  String get widgetServerLabel => 'Current Server';

  @override
  String get quickActionConnect => 'Connect';

  @override
  String get quickActionDisconnect => 'Disconnect';

  @override
  String get quickActionServers => 'Servers';

  @override
  String get quickActionSpeedTest => 'Speed Test';

  @override
  String get quickActionSettings => 'Settings';

  @override
  String get quickActionSupport => 'Support';

  @override
  String get errorConnectionFailed => 'Connection failed. Please try again.';

  @override
  String get errorConnectionTimeout =>
      'Connection timed out. Check your internet connection.';

  @override
  String get errorServerUnavailable =>
      'Server is currently unavailable. Try another server.';

  @override
  String get errorInvalidConfig =>
      'Invalid configuration. Please reimport your settings.';

  @override
  String get errorSubscriptionExpired =>
      'Your subscription has expired. Please renew to continue.';

  @override
  String get errorSubscriptionRequired =>
      'A subscription is required to use this feature.';

  @override
  String get errorAuthenticationFailed =>
      'Authentication failed. Please log in again.';

  @override
  String get errorTokenExpired => 'Session expired. Please log in again.';

  @override
  String get errorNetworkUnreachable =>
      'Network unreachable. Check your connection.';

  @override
  String get errorPermissionDenied => 'Permission denied.';

  @override
  String get errorRateLimited => 'Too many requests. Please wait a moment.';

  @override
  String get errorUnexpected =>
      'An unexpected error occurred. Please try again.';

  @override
  String get errorServerError => 'Server error. Please try again later.';

  @override
  String get errorInvalidCredentials => 'Invalid email or password.';

  @override
  String get errorAccountLocked =>
      'Your account has been locked. Please contact support.';

  @override
  String get errorWeakPassword =>
      'Password is too weak. Use at least 8 characters with letters and numbers.';

  @override
  String get errorEmailAlreadyInUse => 'This email is already registered.';

  @override
  String get errorInvalidEmail => 'Please enter a valid email address.';

  @override
  String get errorFieldRequired => 'This field is required.';

  @override
  String get errorPaymentFailed =>
      'Payment failed. Please try again or use a different method.';

  @override
  String get errorQrScanFailed => 'Failed to scan QR code. Please try again.';

  @override
  String get errorTelegramAuthCancelled => 'Telegram login was cancelled.';

  @override
  String get errorTelegramAuthFailed =>
      'Telegram authentication failed. Please try again.';

  @override
  String get errorTelegramAuthExpired =>
      'Telegram login expired. Please try again.';

  @override
  String get errorTelegramNotInstalled =>
      'Telegram is not installed on this device.';

  @override
  String get errorTelegramAuthInvalid =>
      'Invalid Telegram authentication data.';

  @override
  String get errorBiometricUnavailable =>
      'Biometric authentication is not available on this device.';

  @override
  String get errorBiometricNotEnrolled =>
      'No biometric data enrolled. Please set up fingerprint or face recognition in device settings.';

  @override
  String get errorBiometricFailed =>
      'Biometric authentication failed. Please try again.';

  @override
  String get errorBiometricLocked =>
      'Biometric authentication is locked. Try again later or use your password.';

  @override
  String get errorSessionExpired =>
      'Your session has expired. Please log in again.';

  @override
  String get errorAccountDisabled =>
      'Your account has been disabled. Please contact support.';

  @override
  String errorRateLimitedWithCountdown(int seconds) {
    String _temp0 = intl.Intl.pluralLogic(
      seconds,
      locale: localeName,
      other: '$seconds seconds',
      one: '1 second',
    );
    return 'Too many attempts. Please try again in $_temp0.';
  }

  @override
  String get errorOfflineLoginRequired =>
      'You need to be online to log in. Please check your connection.';

  @override
  String get errorOfflineSessionExpired =>
      'Your cached session has expired. Please connect to the internet to log in.';

  @override
  String get a11yConnectButton => 'Connect to VPN server';

  @override
  String get a11yDisconnectButton => 'Disconnect from VPN server';

  @override
  String get a11yServerStatusOnline => 'Server is online';

  @override
  String get a11yServerStatusOffline => 'Server is offline';

  @override
  String get a11yServerStatusMaintenance => 'Server is under maintenance';

  @override
  String a11ySpeedIndicator(String speed) {
    return 'Current speed: $speed';
  }

  @override
  String a11yConnectionStatus(String status) {
    return 'Connection status: $status';
  }

  @override
  String a11yServerSelect(String name, String country) {
    return 'Select server $name in $country';
  }

  @override
  String get a11yNavigationMenu => 'Navigation menu';

  @override
  String get a11yCloseDialog => 'Close dialog';

  @override
  String a11yToggleSwitch(String label) {
    return 'Toggle $label';
  }

  @override
  String a11yNotificationBadge(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count powiadomień',
      many: '$count powiadomień',
      few: '$count powiadomienia',
      one: '$count powiadomienie',
      zero: 'Brak powiadomień',
    );
    return '$_temp0';
  }

  @override
  String get a11yLoadingIndicator => 'Loading';

  @override
  String get a11yRefreshContent => 'Refresh content';

  @override
  String get a11yBackButton => 'Go back';

  @override
  String get a11ySearchField => 'Search';

  @override
  String get rootDetectionDialogTitle => 'Rooted/Jailbroken Device Detected';

  @override
  String get rootDetectionDialogDescription =>
      'Your device appears to be rooted (Android) or jailbroken (iOS). While CyberVPN will continue to work, please note that using a rooted/jailbroken device may expose you to security risks.\n\nWe understand that users in censored regions often rely on rooted devices for additional privacy tools. CyberVPN will not block your access, but we recommend being cautious about the apps you install and the permissions you grant.';

  @override
  String get rootDetectionDialogDismiss => 'I Understand';

  @override
  String get loginEmailLabel => 'Email';

  @override
  String get loginEmailHint => 'Enter your email';

  @override
  String get loginPasswordLabel => 'Password';

  @override
  String get loginPasswordHint => 'Enter your password';

  @override
  String get loginShowPassword => 'Show password';

  @override
  String get loginHidePassword => 'Hide password';

  @override
  String get loginRememberMe => 'Remember me';

  @override
  String get loginButton => 'Login';

  @override
  String get loginContinueWithTelegram => 'Continue with Telegram';

  @override
  String get registerTitle => 'Create Account';

  @override
  String get registerSubtitle => 'Join CyberVPN for a secure experience';

  @override
  String get registerPasswordHint => 'Create a password';

  @override
  String get registerConfirmPasswordLabel => 'Confirm Password';

  @override
  String get registerConfirmPasswordHint => 'Re-enter your password';

  @override
  String get registerConfirmPasswordError => 'Please confirm your password';

  @override
  String get registerPasswordMismatch => 'Passwords do not match';

  @override
  String get registerReferralCodeLabel => 'Referral Code (optional)';

  @override
  String get registerReferralCodeHint => 'Enter referral code';

  @override
  String get registerReferralApplied => 'Applied!';

  @override
  String get registerReferralFromLink => 'Referral code applied from link';

  @override
  String get registerAgreePrefix => 'I agree to the ';

  @override
  String get registerTermsAndConditions => 'Terms & Conditions';

  @override
  String get registerAndSeparator => ' and ';

  @override
  String get registerAcceptTermsError => 'Please accept the Terms & Conditions';

  @override
  String get registerButton => 'Register';

  @override
  String get registerOrSeparator => 'OR';

  @override
  String get registerAlreadyHaveAccount => 'Already have an account? ';

  @override
  String get registerLoginLink => 'Login';

  @override
  String get telegramNotInstalledTitle => 'Telegram Not Installed';

  @override
  String get telegramNotInstalledMessage =>
      'The Telegram app is not installed on your device. You can install it from the app store or use the web version.';

  @override
  String get telegramUseWeb => 'Use Web';

  @override
  String get telegramInstall => 'Install';

  @override
  String get appLockTitle => 'CyberVPN Locked';

  @override
  String get appLockSubtitle => 'Authenticate to continue';

  @override
  String get appLockUnlockButton => 'Unlock';

  @override
  String appLockUnlockWithBiometric(String biometricLabel) {
    return 'Unlock with $biometricLabel';
  }

  @override
  String get appLockTooManyAttempts => 'Too many failed attempts';

  @override
  String get appLockUsePin => 'Use device PIN';

  @override
  String appLockTryAgain(String biometricLabel) {
    return 'Try $biometricLabel again';
  }

  @override
  String get appLockLocalizedReason => 'Unlock CyberVPN with your device PIN';

  @override
  String get biometricSettingsTitle => 'Security';

  @override
  String get biometricAuthSection => 'Biometric Authentication';

  @override
  String get biometricLoginLabel => 'Biometric Login';

  @override
  String get biometricLoginDescription => 'Use biometrics to sign in quickly';

  @override
  String get biometricLoginEnabled => 'Biometric login enabled';

  @override
  String get biometricLoginDisabled => 'Biometric login disabled';

  @override
  String get biometricVerificationRequired => 'Biometric verification required';

  @override
  String get biometricEnterCredentialsTitle => 'Enter credentials';

  @override
  String get biometricEnterCredentialsMessage =>
      'Enter your login credentials to enable quick sign-in with biometrics.';

  @override
  String get biometricSave => 'Save';

  @override
  String get biometricAppLockLabel => 'App Lock';

  @override
  String get biometricAppLockDescription =>
      'Require biometrics when returning to app (30+ seconds)';

  @override
  String get biometricAppLockEnabled => 'App lock enabled';

  @override
  String get biometricAppLockDisabled => 'App lock disabled';

  @override
  String get biometricUnavailableTitle => 'Biometrics Unavailable';

  @override
  String get biometricUnavailableMessage =>
      'Your device does not support biometric authentication, or no biometrics are enrolled.';

  @override
  String get biometricLoadingState => 'Loading...';

  @override
  String get biometricUnavailableState => 'Unavailable';

  @override
  String get biometricLabelFingerprint => 'Fingerprint';

  @override
  String get biometricLabelGeneric => 'Biometrics';

  @override
  String get biometricAvailableOnDevice => 'Available on this device';

  @override
  String get biometricSettingsChanged =>
      'Your biometric settings have changed. Please sign in with your password and re-enable biometric login in settings.';

  @override
  String get biometricPasswordChanged =>
      'Your password has changed. Please sign in with your password.';

  @override
  String get settingsNotificationPrefsTitle => 'Notification Preferences';

  @override
  String get settingsNotificationConnectionLabel => 'Connection Status';

  @override
  String get settingsNotificationConnectionDescription =>
      'Get notified when VPN connects or disconnects';

  @override
  String get settingsNotificationServerLabel => 'Server Changes';

  @override
  String get settingsNotificationServerDescription =>
      'Get notified when server is switched';

  @override
  String get settingsNotificationSubscriptionLabel => 'Subscription Alerts';

  @override
  String get settingsNotificationSubscriptionDescription =>
      'Get notified about subscription expiry';

  @override
  String get settingsNotificationSecurityLabel => 'Security Alerts';

  @override
  String get settingsNotificationSecurityDescription =>
      'Get notified about security events';

  @override
  String get settingsNotificationPromotionLabel => 'Promotions';

  @override
  String get settingsNotificationPromotionDescription =>
      'Receive promotional notifications';

  @override
  String get settingsNotificationUpdateLabel => 'System Updates';

  @override
  String get settingsNotificationUpdateDescription =>
      'Get notified about app updates';

  @override
  String get settingsVpnProtocolWireGuard => 'WireGuard';

  @override
  String get settingsVpnProtocolOpenVpn => 'OpenVPN';

  @override
  String get settingsVpnProtocolIkev2 => 'IKEv2';

  @override
  String get settingsVpnProtocolAuto => 'Auto';

  @override
  String get settingsThemeDark => 'Dark';

  @override
  String get settingsThemeLight => 'Light';

  @override
  String get settingsThemeSystem => 'System';

  @override
  String get settingsLanguageSearchHint => 'Search languages';

  @override
  String get settingsVersionInfo => 'Version Info';

  @override
  String get settingsPrivacyAndTerms => 'Privacy & Terms';

  @override
  String get settingsContactSupport => 'Contact Support';

  @override
  String settingsAppVersion(String version) {
    return 'App version $version';
  }

  @override
  String settingsBuildNumber(String build) {
    return 'Build $build';
  }

  @override
  String get settingsRateApp => 'Rate CyberVPN';

  @override
  String get settingsShareApp => 'Share with Friends';

  @override
  String get settingsDeleteData => 'Delete All Data';

  @override
  String get profileSaveButton => 'Save';

  @override
  String get profileSaveSuccess => 'Profile updated successfully';

  @override
  String get profileAvatarChange => 'Change Avatar';

  @override
  String get profileAvatarRemove => 'Remove Avatar';

  @override
  String get profilePasswordUpdated => 'Password updated successfully';

  @override
  String get profilePasswordRequirements =>
      'Password must be at least 8 characters with letters and numbers';

  @override
  String get profileAccountInfo => 'Account Information';

  @override
  String get profileSecuritySection => 'Security';

  @override
  String get profileDangerZone => 'Danger Zone';

  @override
  String get profileDeleteConfirmInput => 'Type DELETE to confirm';

  @override
  String get profileDeleteInProgress => 'Deleting account...';

  @override
  String get profileSessionInfo => 'Session Information';

  @override
  String profileLastLogin(String date) {
    return 'Last login: $date';
  }

  @override
  String profileCreatedAt(String date) {
    return 'Account created: $date';
  }

  @override
  String get configImportManualEntry => 'Manual Entry';

  @override
  String get configImportManualDescription =>
      'Enter VPN configuration details manually.';

  @override
  String get configImportServerAddress => 'Server Address';

  @override
  String get configImportServerPort => 'Port';

  @override
  String get configImportProtocol => 'Protocol';

  @override
  String get configImportPrivateKey => 'Private Key';

  @override
  String get configImportPublicKey => 'Public Key';

  @override
  String get configImportConfigName => 'Configuration Name';

  @override
  String get configImportConfigNameHint =>
      'Enter a name for this configuration';

  @override
  String get configImportSaving => 'Saving configuration...';

  @override
  String get configImportDeleteConfirm =>
      'Are you sure you want to delete this configuration?';

  @override
  String get configImportDeleteSuccess => 'Configuration deleted.';

  @override
  String get configImportNoConfigs => 'No imported configurations yet.';

  @override
  String get configImportManageTitle => 'Manage Configurations';

  @override
  String get configImportActiveLabel => 'Active';

  @override
  String get configImportConnectButton => 'Connect';

  @override
  String get configImportEditButton => 'Edit';

  @override
  String get configImportDeleteButton => 'Delete';

  @override
  String get subscriptionTitle => 'Subscription Plans';

  @override
  String get subscriptionCurrentPlan => 'Current Plan';

  @override
  String get subscriptionFreePlan => 'Free';

  @override
  String get subscriptionTrialPlan => 'Trial';

  @override
  String get subscriptionBasicPlan => 'Basic';

  @override
  String get subscriptionPremiumPlan => 'Premium';

  @override
  String get subscriptionMonthly => 'Monthly';

  @override
  String get subscriptionYearly => 'Yearly';

  @override
  String get subscriptionLifetime => 'Lifetime';

  @override
  String subscriptionPricePerMonth(String price) {
    return '$price/month';
  }

  @override
  String subscriptionPricePerYear(String price) {
    return '$price/year';
  }

  @override
  String subscriptionSavePercent(int percent) {
    return 'Save $percent%';
  }

  @override
  String get subscriptionSubscribeButton => 'Subscribe';

  @override
  String get subscriptionRestorePurchases => 'Restore Purchases';

  @override
  String get subscriptionRestoreSuccess => 'Purchases restored successfully';

  @override
  String get subscriptionRestoreNotFound => 'No previous purchases found';

  @override
  String get subscriptionCancelButton => 'Cancel Subscription';

  @override
  String get subscriptionCancelConfirm =>
      'Are you sure you want to cancel your subscription?';

  @override
  String get subscriptionCancelSuccess => 'Subscription cancelled';

  @override
  String get subscriptionRenewButton => 'Renew Subscription';

  @override
  String subscriptionExpiresOn(String date) {
    return 'Expires on $date';
  }

  @override
  String get subscriptionAutoRenew => 'Auto-renew enabled';

  @override
  String get subscriptionFeatureUnlimitedData => 'Unlimited data';

  @override
  String get subscriptionFeatureAllServers => 'Access to all servers';

  @override
  String get subscriptionFeatureNoAds => 'No ads';

  @override
  String get subscriptionFeaturePriority => 'Priority support';

  @override
  String subscriptionFeatureDevices(int count) {
    return 'Up to $count devices';
  }

  @override
  String subscriptionTrafficUsed(String used, String total) {
    return '$used of $total used';
  }

  @override
  String get subscriptionUpgradePrompt => 'Upgrade for more features';

  @override
  String get subscriptionProcessing => 'Processing payment...';

  @override
  String get subscriptionPaymentMethod => 'Payment Method';

  @override
  String get serverListTitle => 'Server List';

  @override
  String get serverListSearchHint => 'Search servers...';

  @override
  String get serverListFilterAll => 'All';

  @override
  String get serverListFilterFavorites => 'Favorites';

  @override
  String get serverListFilterRecommended => 'Recommended';

  @override
  String get serverListNoResults => 'No servers found';

  @override
  String serverListPing(int ping) {
    return '$ping ms';
  }

  @override
  String serverListLoad(int load) {
    return '$load% load';
  }

  @override
  String get serverListAddFavorite => 'Add to favorites';

  @override
  String get serverListRemoveFavorite => 'Remove from favorites';

  @override
  String serverListConnecting(String server) {
    return 'Connecting to $server...';
  }

  @override
  String get serverListSortBy => 'Sort by';

  @override
  String get serverListSortName => 'Name';

  @override
  String get serverListSortPing => 'Ping';

  @override
  String get serverListSortLoad => 'Load';

  @override
  String get notificationSettingsTitle => 'Notification Settings';

  @override
  String get notificationEnablePush => 'Enable Push Notifications';

  @override
  String get notificationEnablePushDescription =>
      'Receive important updates about your VPN connection';

  @override
  String get notificationSoundLabel => 'Notification Sound';

  @override
  String get notificationVibrationLabel => 'Vibration';

  @override
  String get notificationQuietHoursLabel => 'Quiet Hours';

  @override
  String get notificationQuietHoursDescription =>
      'Mute notifications during specified hours';

  @override
  String get diagnosticsNetworkCheck => 'Network Check';

  @override
  String get diagnosticsDnsCheck => 'DNS Resolution';

  @override
  String get diagnosticsLatencyCheck => 'Latency Check';

  @override
  String get diagnosticsFirewallCheck => 'Firewall Check';

  @override
  String get diagnosticsStatusPassed => 'Passed';

  @override
  String get diagnosticsStatusFailed => 'Failed';

  @override
  String get diagnosticsStatusRunning => 'Running...';

  @override
  String get diagnosticsRunAll => 'Run All Checks';

  @override
  String get diagnosticsShareResults => 'Share Results';

  @override
  String get commonSave => 'Save';

  @override
  String get commonDelete => 'Delete';

  @override
  String get commonEdit => 'Edit';

  @override
  String get commonClose => 'Close';

  @override
  String get commonBack => 'Back';

  @override
  String get commonNext => 'Next';

  @override
  String get commonDone => 'Done';

  @override
  String get commonSearch => 'Search';

  @override
  String get commonLoading => 'Loading...';

  @override
  String get commonNoData => 'No data available';

  @override
  String get commonRefresh => 'Refresh';

  @override
  String get commonCopy => 'Copy';

  @override
  String get commonCopied => 'Copied to clipboard';

  @override
  String get commonShare => 'Share';

  @override
  String get commonYes => 'Yes';

  @override
  String get commonNo => 'No';

  @override
  String get commonOk => 'OK';

  @override
  String get commonContinue => 'Continue';

  @override
  String get commonSkip => 'Skip';

  @override
  String get commonLearnMore => 'Learn More';

  @override
  String get errorNoConnection =>
      'No internet connection. Please check your network.';

  @override
  String get errorTimeout => 'Request timed out. Please try again.';

  @override
  String get errorGeneric => 'Something went wrong. Please try again.';

  @override
  String get errorLoadingData => 'Failed to load data.';

  @override
  String get errorSavingData => 'Failed to save data.';

  @override
  String get errorSessionInvalid =>
      'Your session is invalid. Please log in again.';

  @override
  String get a11yShowPassword => 'Show password';

  @override
  String get a11yHidePassword => 'Hide password';

  @override
  String a11yServerPing(int ping) {
    return 'Server ping: $ping milliseconds';
  }

  @override
  String a11yServerLoad(int load) {
    return 'Server load: $load percent';
  }

  @override
  String get a11yFavoriteServer => 'Favorite server';

  @override
  String get a11yRemoveFavorite => 'Remove from favorites';

  @override
  String get a11ySubscriptionActive => 'Active subscription';

  @override
  String get a11ySubscriptionExpired => 'Expired subscription';

  @override
  String get a11yBiometricLogin => 'Biometric login toggle';

  @override
  String get a11yAppLockToggle => 'App lock toggle';

  @override
  String get a11yProtocolSelect => 'Select VPN protocol';

  @override
  String get a11yThemeSelect => 'Select theme mode';

  @override
  String get a11yLanguageSelect => 'Select language';

  @override
  String a11yNotificationToggle(String type) {
    return 'Toggle notification for $type';
  }

  @override
  String get a11ySpeedTestProgress => 'Speed test in progress';

  @override
  String get a11yDiagnosticsProgress => 'Diagnostics in progress';

  @override
  String a11yTrafficUsage(int percent) {
    return 'Traffic usage: $percent percent';
  }

  @override
  String a11yConnectionDuration(String duration) {
    return 'Connected for $duration';
  }

  @override
  String get quickSetupTitle => 'Quick Setup';

  @override
  String get quickSetupWelcome => 'Let\'s get you connected';

  @override
  String get quickSetupSelectServer => 'Select a server to get started';

  @override
  String get quickSetupRecommended => 'Recommended for you';

  @override
  String get quickSetupConnectButton => 'Connect Now';

  @override
  String get quickSetupSkip => 'Skip for now';

  @override
  String get quickSetupComplete => 'You\'re all set!';

  @override
  String get splashLoading => 'Loading...';

  @override
  String get splashInitializing => 'Initializing...';
}
