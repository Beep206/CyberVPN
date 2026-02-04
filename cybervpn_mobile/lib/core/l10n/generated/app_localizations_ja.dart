// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Japanese (`ja`).
class AppLocalizationsJa extends AppLocalizations {
  AppLocalizationsJa([String locale = 'ja']) : super(locale);

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
      other: '$count days remaining',
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
      other: '$count seconds',
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
      other: '$count days',
    );
    return 'Your subscription expires in $_temp0.';
  }

  @override
  String get notificationSubscriptionExpired =>
      'Your subscription has expired. Renew to continue using CyberVPN.';

  @override
  String notificationUnreadCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count unread notifications',
      zero: 'No unread notifications',
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
      other: '$count rewards earned',
      zero: 'No rewards earned',
    );
    return '$_temp0';
  }

  @override
  String referralFriendsInvited(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count friends invited',
      zero: 'No friends invited',
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
      other: '$count notifications',
      zero: 'No notifications',
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
}
