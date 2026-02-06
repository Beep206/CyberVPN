import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ar.dart';
import 'app_localizations_cs.dart';
import 'app_localizations_da.dart';
import 'app_localizations_de.dart';
import 'app_localizations_en.dart';
import 'app_localizations_es.dart';
import 'app_localizations_fa.dart';
import 'app_localizations_fr.dart';
import 'app_localizations_he.dart';
import 'app_localizations_hi.dart';
import 'app_localizations_id.dart';
import 'app_localizations_it.dart';
import 'app_localizations_ja.dart';
import 'app_localizations_ko.dart';
import 'app_localizations_ms.dart';
import 'app_localizations_nl.dart';
import 'app_localizations_pl.dart';
import 'app_localizations_pt.dart';
import 'app_localizations_ro.dart';
import 'app_localizations_ru.dart';
import 'app_localizations_sv.dart';
import 'app_localizations_th.dart';
import 'app_localizations_tr.dart';
import 'app_localizations_uk.dart';
import 'app_localizations_vi.dart';
import 'app_localizations_zh.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('ar'),
    Locale('cs'),
    Locale('da'),
    Locale('de'),
    Locale('en'),
    Locale('es'),
    Locale('fa'),
    Locale('fr'),
    Locale('he'),
    Locale('hi'),
    Locale('id'),
    Locale('it'),
    Locale('ja'),
    Locale('ko'),
    Locale('ms'),
    Locale('nl'),
    Locale('pl'),
    Locale('pt'),
    Locale('ro'),
    Locale('ru'),
    Locale('sv'),
    Locale('th'),
    Locale('tr'),
    Locale('uk'),
    Locale('vi'),
    Locale('zh'),
    Locale.fromSubtags(languageCode: 'zh', scriptCode: 'Hant'),
  ];

  /// No description provided for @appName.
  ///
  /// In en, this message translates to:
  /// **'CyberVPN'**
  String get appName;

  /// No description provided for @login.
  ///
  /// In en, this message translates to:
  /// **'Log In'**
  String get login;

  /// No description provided for @register.
  ///
  /// In en, this message translates to:
  /// **'Sign Up'**
  String get register;

  /// No description provided for @email.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get email;

  /// No description provided for @password.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get password;

  /// No description provided for @confirmPassword.
  ///
  /// In en, this message translates to:
  /// **'Confirm Password'**
  String get confirmPassword;

  /// No description provided for @forgotPassword.
  ///
  /// In en, this message translates to:
  /// **'Forgot Password?'**
  String get forgotPassword;

  /// No description provided for @orContinueWith.
  ///
  /// In en, this message translates to:
  /// **'Or continue with'**
  String get orContinueWith;

  /// No description provided for @connect.
  ///
  /// In en, this message translates to:
  /// **'Connect'**
  String get connect;

  /// No description provided for @disconnect.
  ///
  /// In en, this message translates to:
  /// **'Disconnect'**
  String get disconnect;

  /// No description provided for @connecting.
  ///
  /// In en, this message translates to:
  /// **'Connecting...'**
  String get connecting;

  /// No description provided for @disconnecting.
  ///
  /// In en, this message translates to:
  /// **'Disconnecting...'**
  String get disconnecting;

  /// No description provided for @connected.
  ///
  /// In en, this message translates to:
  /// **'Connected'**
  String get connected;

  /// No description provided for @disconnected.
  ///
  /// In en, this message translates to:
  /// **'Disconnected'**
  String get disconnected;

  /// No description provided for @servers.
  ///
  /// In en, this message translates to:
  /// **'Servers'**
  String get servers;

  /// No description provided for @subscription.
  ///
  /// In en, this message translates to:
  /// **'Subscription'**
  String get subscription;

  /// No description provided for @settings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settings;

  /// No description provided for @profile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get profile;

  /// No description provided for @selectServer.
  ///
  /// In en, this message translates to:
  /// **'Select Server'**
  String get selectServer;

  /// No description provided for @autoSelect.
  ///
  /// In en, this message translates to:
  /// **'Auto Select'**
  String get autoSelect;

  /// No description provided for @fastestServer.
  ///
  /// In en, this message translates to:
  /// **'Fastest Server'**
  String get fastestServer;

  /// No description provided for @nearestServer.
  ///
  /// In en, this message translates to:
  /// **'Nearest Server'**
  String get nearestServer;

  /// No description provided for @killSwitch.
  ///
  /// In en, this message translates to:
  /// **'Kill Switch'**
  String get killSwitch;

  /// No description provided for @splitTunneling.
  ///
  /// In en, this message translates to:
  /// **'Split Tunneling'**
  String get splitTunneling;

  /// No description provided for @autoConnect.
  ///
  /// In en, this message translates to:
  /// **'Auto Connect'**
  String get autoConnect;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @theme.
  ///
  /// In en, this message translates to:
  /// **'Theme'**
  String get theme;

  /// No description provided for @darkMode.
  ///
  /// In en, this message translates to:
  /// **'Dark Mode'**
  String get darkMode;

  /// No description provided for @lightMode.
  ///
  /// In en, this message translates to:
  /// **'Light Mode'**
  String get lightMode;

  /// No description provided for @systemDefault.
  ///
  /// In en, this message translates to:
  /// **'System Default'**
  String get systemDefault;

  /// No description provided for @logout.
  ///
  /// In en, this message translates to:
  /// **'Log Out'**
  String get logout;

  /// No description provided for @logoutConfirm.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to log out?'**
  String get logoutConfirm;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @confirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get confirm;

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get retry;

  /// No description provided for @errorOccurred.
  ///
  /// In en, this message translates to:
  /// **'An error occurred'**
  String get errorOccurred;

  /// No description provided for @noInternet.
  ///
  /// In en, this message translates to:
  /// **'No internet connection'**
  String get noInternet;

  /// No description provided for @downloadSpeed.
  ///
  /// In en, this message translates to:
  /// **'Download'**
  String get downloadSpeed;

  /// No description provided for @uploadSpeed.
  ///
  /// In en, this message translates to:
  /// **'Upload'**
  String get uploadSpeed;

  /// No description provided for @connectionTime.
  ///
  /// In en, this message translates to:
  /// **'Connection Time'**
  String get connectionTime;

  /// No description provided for @dataUsed.
  ///
  /// In en, this message translates to:
  /// **'Data Used'**
  String get dataUsed;

  /// No description provided for @currentPlan.
  ///
  /// In en, this message translates to:
  /// **'Current Plan'**
  String get currentPlan;

  /// No description provided for @upgradePlan.
  ///
  /// In en, this message translates to:
  /// **'Upgrade Plan'**
  String get upgradePlan;

  /// No description provided for @daysRemaining.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 day remaining} other{{count} days remaining}}'**
  String daysRemaining(int count);

  /// No description provided for @referral.
  ///
  /// In en, this message translates to:
  /// **'Referral'**
  String get referral;

  /// No description provided for @shareReferralCode.
  ///
  /// In en, this message translates to:
  /// **'Share Referral Code'**
  String get shareReferralCode;

  /// No description provided for @support.
  ///
  /// In en, this message translates to:
  /// **'Support'**
  String get support;

  /// No description provided for @privacyPolicy.
  ///
  /// In en, this message translates to:
  /// **'Privacy Policy'**
  String get privacyPolicy;

  /// No description provided for @termsOfService.
  ///
  /// In en, this message translates to:
  /// **'Terms of Service'**
  String get termsOfService;

  /// No description provided for @version.
  ///
  /// In en, this message translates to:
  /// **'Version {version}'**
  String version(String version);

  /// No description provided for @onboardingWelcomeTitle.
  ///
  /// In en, this message translates to:
  /// **'Welcome to CyberVPN'**
  String get onboardingWelcomeTitle;

  /// No description provided for @onboardingWelcomeDescription.
  ///
  /// In en, this message translates to:
  /// **'Secure, fast, and private internet access at your fingertips.'**
  String get onboardingWelcomeDescription;

  /// No description provided for @onboardingFeaturesTitle.
  ///
  /// In en, this message translates to:
  /// **'Powerful Features'**
  String get onboardingFeaturesTitle;

  /// No description provided for @onboardingFeaturesDescription.
  ///
  /// In en, this message translates to:
  /// **'Kill switch, split tunneling, and military-grade encryption to keep you safe.'**
  String get onboardingFeaturesDescription;

  /// No description provided for @onboardingPrivacyTitle.
  ///
  /// In en, this message translates to:
  /// **'Your Privacy Matters'**
  String get onboardingPrivacyTitle;

  /// No description provided for @onboardingPrivacyDescription.
  ///
  /// In en, this message translates to:
  /// **'Zero-log policy. We never track, store, or share your browsing data.'**
  String get onboardingPrivacyDescription;

  /// No description provided for @onboardingSpeedTitle.
  ///
  /// In en, this message translates to:
  /// **'Lightning Fast'**
  String get onboardingSpeedTitle;

  /// No description provided for @onboardingSpeedDescription.
  ///
  /// In en, this message translates to:
  /// **'Connect to optimized servers worldwide for the best speeds.'**
  String get onboardingSpeedDescription;

  /// No description provided for @onboardingSkip.
  ///
  /// In en, this message translates to:
  /// **'Skip'**
  String get onboardingSkip;

  /// No description provided for @onboardingNext.
  ///
  /// In en, this message translates to:
  /// **'Next'**
  String get onboardingNext;

  /// No description provided for @onboardingGetStarted.
  ///
  /// In en, this message translates to:
  /// **'Get Started'**
  String get onboardingGetStarted;

  /// No description provided for @onboardingBack.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get onboardingBack;

  /// No description provided for @onboardingPageIndicator.
  ///
  /// In en, this message translates to:
  /// **'Page {current} of {total}'**
  String onboardingPageIndicator(int current, int total);

  /// No description provided for @settingsTitle.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settingsTitle;

  /// No description provided for @settingsGeneral.
  ///
  /// In en, this message translates to:
  /// **'General'**
  String get settingsGeneral;

  /// No description provided for @settingsVpn.
  ///
  /// In en, this message translates to:
  /// **'VPN Settings'**
  String get settingsVpn;

  /// No description provided for @settingsAppearance.
  ///
  /// In en, this message translates to:
  /// **'Appearance'**
  String get settingsAppearance;

  /// No description provided for @settingsDebug.
  ///
  /// In en, this message translates to:
  /// **'Debug'**
  String get settingsDebug;

  /// No description provided for @settingsNotifications.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get settingsNotifications;

  /// No description provided for @settingsAbout.
  ///
  /// In en, this message translates to:
  /// **'About'**
  String get settingsAbout;

  /// No description provided for @settingsVpnProtocolLabel.
  ///
  /// In en, this message translates to:
  /// **'Protocol'**
  String get settingsVpnProtocolLabel;

  /// No description provided for @settingsVpnProtocolDescription.
  ///
  /// In en, this message translates to:
  /// **'Select the VPN protocol to use for connections.'**
  String get settingsVpnProtocolDescription;

  /// No description provided for @settingsAutoConnectLabel.
  ///
  /// In en, this message translates to:
  /// **'Auto Connect'**
  String get settingsAutoConnectLabel;

  /// No description provided for @settingsAutoConnectDescription.
  ///
  /// In en, this message translates to:
  /// **'Automatically connect when the app starts.'**
  String get settingsAutoConnectDescription;

  /// No description provided for @settingsKillSwitchLabel.
  ///
  /// In en, this message translates to:
  /// **'Kill Switch'**
  String get settingsKillSwitchLabel;

  /// No description provided for @settingsKillSwitchDescription.
  ///
  /// In en, this message translates to:
  /// **'Block internet if VPN connection drops.'**
  String get settingsKillSwitchDescription;

  /// No description provided for @settingsDnsLabel.
  ///
  /// In en, this message translates to:
  /// **'Custom DNS'**
  String get settingsDnsLabel;

  /// No description provided for @settingsDnsDescription.
  ///
  /// In en, this message translates to:
  /// **'Use a custom DNS server for resolution.'**
  String get settingsDnsDescription;

  /// No description provided for @settingsDnsPlaceholder.
  ///
  /// In en, this message translates to:
  /// **'Enter DNS address'**
  String get settingsDnsPlaceholder;

  /// No description provided for @settingsSplitTunnelingLabel.
  ///
  /// In en, this message translates to:
  /// **'Split Tunneling'**
  String get settingsSplitTunnelingLabel;

  /// No description provided for @settingsSplitTunnelingDescription.
  ///
  /// In en, this message translates to:
  /// **'Choose which apps use the VPN connection.'**
  String get settingsSplitTunnelingDescription;

  /// No description provided for @settingsThemeModeLabel.
  ///
  /// In en, this message translates to:
  /// **'Theme Mode'**
  String get settingsThemeModeLabel;

  /// No description provided for @settingsThemeModeDescription.
  ///
  /// In en, this message translates to:
  /// **'Choose between light, dark, or system theme.'**
  String get settingsThemeModeDescription;

  /// No description provided for @settingsLanguageLabel.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get settingsLanguageLabel;

  /// No description provided for @settingsLanguageDescription.
  ///
  /// In en, this message translates to:
  /// **'Select your preferred language.'**
  String get settingsLanguageDescription;

  /// No description provided for @settingsDebugLogsLabel.
  ///
  /// In en, this message translates to:
  /// **'Debug Logs'**
  String get settingsDebugLogsLabel;

  /// No description provided for @settingsDebugLogsDescription.
  ///
  /// In en, this message translates to:
  /// **'Enable verbose logging for troubleshooting.'**
  String get settingsDebugLogsDescription;

  /// No description provided for @settingsExportLogsLabel.
  ///
  /// In en, this message translates to:
  /// **'Export Logs'**
  String get settingsExportLogsLabel;

  /// No description provided for @settingsExportLogsDescription.
  ///
  /// In en, this message translates to:
  /// **'Export debug logs for support.'**
  String get settingsExportLogsDescription;

  /// No description provided for @settingsResetLabel.
  ///
  /// In en, this message translates to:
  /// **'Reset Settings'**
  String get settingsResetLabel;

  /// No description provided for @settingsResetDescription.
  ///
  /// In en, this message translates to:
  /// **'Restore all settings to default values.'**
  String get settingsResetDescription;

  /// No description provided for @settingsResetConfirm.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to reset all settings to defaults?'**
  String get settingsResetConfirm;

  /// No description provided for @settingsStartOnBootLabel.
  ///
  /// In en, this message translates to:
  /// **'Start on Boot'**
  String get settingsStartOnBootLabel;

  /// No description provided for @settingsStartOnBootDescription.
  ///
  /// In en, this message translates to:
  /// **'Automatically launch CyberVPN when your device starts.'**
  String get settingsStartOnBootDescription;

  /// No description provided for @settingsConnectionTimeoutLabel.
  ///
  /// In en, this message translates to:
  /// **'Connection Timeout'**
  String get settingsConnectionTimeoutLabel;

  /// No description provided for @settingsConnectionTimeoutDescription.
  ///
  /// In en, this message translates to:
  /// **'Maximum time to wait before a connection attempt is aborted.'**
  String get settingsConnectionTimeoutDescription;

  /// No description provided for @settingsConnectionTimeoutSeconds.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 second} other{{count} seconds}}'**
  String settingsConnectionTimeoutSeconds(int count);

  /// No description provided for @profileDashboard.
  ///
  /// In en, this message translates to:
  /// **'Profile Dashboard'**
  String get profileDashboard;

  /// No description provided for @profileEditProfile.
  ///
  /// In en, this message translates to:
  /// **'Edit Profile'**
  String get profileEditProfile;

  /// No description provided for @profileDisplayName.
  ///
  /// In en, this message translates to:
  /// **'Display Name'**
  String get profileDisplayName;

  /// No description provided for @profileEmailAddress.
  ///
  /// In en, this message translates to:
  /// **'Email Address'**
  String get profileEmailAddress;

  /// No description provided for @profileChangePassword.
  ///
  /// In en, this message translates to:
  /// **'Change Password'**
  String get profileChangePassword;

  /// No description provided for @profileCurrentPassword.
  ///
  /// In en, this message translates to:
  /// **'Current Password'**
  String get profileCurrentPassword;

  /// No description provided for @profileNewPassword.
  ///
  /// In en, this message translates to:
  /// **'New Password'**
  String get profileNewPassword;

  /// No description provided for @profileConfirmNewPassword.
  ///
  /// In en, this message translates to:
  /// **'Confirm New Password'**
  String get profileConfirmNewPassword;

  /// No description provided for @profileTwoFactorAuth.
  ///
  /// In en, this message translates to:
  /// **'Two-Factor Authentication'**
  String get profileTwoFactorAuth;

  /// No description provided for @profileTwoFactorAuthDescription.
  ///
  /// In en, this message translates to:
  /// **'Add an extra layer of security to your account.'**
  String get profileTwoFactorAuthDescription;

  /// No description provided for @profileTwoFactorEnable.
  ///
  /// In en, this message translates to:
  /// **'Enable 2FA'**
  String get profileTwoFactorEnable;

  /// No description provided for @profileTwoFactorDisable.
  ///
  /// In en, this message translates to:
  /// **'Disable 2FA'**
  String get profileTwoFactorDisable;

  /// No description provided for @profileTwoFactorSetup.
  ///
  /// In en, this message translates to:
  /// **'Set Up Two-Factor Authentication'**
  String get profileTwoFactorSetup;

  /// No description provided for @profileTwoFactorScanQr.
  ///
  /// In en, this message translates to:
  /// **'Scan this QR code with your authenticator app.'**
  String get profileTwoFactorScanQr;

  /// No description provided for @profileTwoFactorEnterCode.
  ///
  /// In en, this message translates to:
  /// **'Enter the 6-digit code from your authenticator app.'**
  String get profileTwoFactorEnterCode;

  /// No description provided for @profileTwoFactorBackupCodes.
  ///
  /// In en, this message translates to:
  /// **'Backup Codes'**
  String get profileTwoFactorBackupCodes;

  /// No description provided for @profileTwoFactorBackupCodesDescription.
  ///
  /// In en, this message translates to:
  /// **'Save these codes in a safe place. You can use them to sign in if you lose access to your authenticator app.'**
  String get profileTwoFactorBackupCodesDescription;

  /// No description provided for @profileOauthAccounts.
  ///
  /// In en, this message translates to:
  /// **'Linked Accounts'**
  String get profileOauthAccounts;

  /// No description provided for @profileOauthAccountsDescription.
  ///
  /// In en, this message translates to:
  /// **'Manage your linked social accounts.'**
  String get profileOauthAccountsDescription;

  /// No description provided for @profileOauthLink.
  ///
  /// In en, this message translates to:
  /// **'Link Account'**
  String get profileOauthLink;

  /// No description provided for @profileOauthUnlink.
  ///
  /// In en, this message translates to:
  /// **'Unlink'**
  String get profileOauthUnlink;

  /// No description provided for @profileOauthUnlinkConfirm.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to unlink this account?'**
  String get profileOauthUnlinkConfirm;

  /// No description provided for @profileTrustedDevices.
  ///
  /// In en, this message translates to:
  /// **'Trusted Devices'**
  String get profileTrustedDevices;

  /// No description provided for @profileTrustedDevicesDescription.
  ///
  /// In en, this message translates to:
  /// **'Manage the devices that can access your account.'**
  String get profileTrustedDevicesDescription;

  /// No description provided for @profileDeviceCurrent.
  ///
  /// In en, this message translates to:
  /// **'Current Device'**
  String get profileDeviceCurrent;

  /// No description provided for @profileDeviceLastActive.
  ///
  /// In en, this message translates to:
  /// **'Last active {date}'**
  String profileDeviceLastActive(String date);

  /// No description provided for @profileDeviceRevoke.
  ///
  /// In en, this message translates to:
  /// **'Revoke Access'**
  String get profileDeviceRevoke;

  /// No description provided for @profileDeviceRevokeConfirm.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to revoke access for this device?'**
  String get profileDeviceRevokeConfirm;

  /// No description provided for @profileDeviceRevokeAll.
  ///
  /// In en, this message translates to:
  /// **'Revoke All Devices'**
  String get profileDeviceRevokeAll;

  /// No description provided for @profileDeleteAccount.
  ///
  /// In en, this message translates to:
  /// **'Delete Account'**
  String get profileDeleteAccount;

  /// No description provided for @profileDeleteAccountDescription.
  ///
  /// In en, this message translates to:
  /// **'Permanently delete your account and all associated data.'**
  String get profileDeleteAccountDescription;

  /// No description provided for @profileDeleteAccountConfirm.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to delete your account? This action cannot be undone.'**
  String get profileDeleteAccountConfirm;

  /// No description provided for @profileDeleteAccountButton.
  ///
  /// In en, this message translates to:
  /// **'Delete My Account'**
  String get profileDeleteAccountButton;

  /// No description provided for @profileSubscriptionStatus.
  ///
  /// In en, this message translates to:
  /// **'Subscription Status'**
  String get profileSubscriptionStatus;

  /// No description provided for @profileMemberSince.
  ///
  /// In en, this message translates to:
  /// **'Member since {date}'**
  String profileMemberSince(String date);

  /// No description provided for @configImportTitle.
  ///
  /// In en, this message translates to:
  /// **'Import Configuration'**
  String get configImportTitle;

  /// No description provided for @configImportQrScanTitle.
  ///
  /// In en, this message translates to:
  /// **'Scan QR Code'**
  String get configImportQrScanTitle;

  /// No description provided for @configImportQrScanDescription.
  ///
  /// In en, this message translates to:
  /// **'Point your camera at a VPN configuration QR code.'**
  String get configImportQrScanDescription;

  /// No description provided for @configImportScanQrButton.
  ///
  /// In en, this message translates to:
  /// **'Scan QR Code'**
  String get configImportScanQrButton;

  /// No description provided for @configImportFromClipboard.
  ///
  /// In en, this message translates to:
  /// **'Import from Clipboard'**
  String get configImportFromClipboard;

  /// No description provided for @configImportFromClipboardDescription.
  ///
  /// In en, this message translates to:
  /// **'Paste a configuration link or text from your clipboard.'**
  String get configImportFromClipboardDescription;

  /// No description provided for @configImportFromFile.
  ///
  /// In en, this message translates to:
  /// **'Import from File'**
  String get configImportFromFile;

  /// No description provided for @configImportFromFileDescription.
  ///
  /// In en, this message translates to:
  /// **'Select a configuration file from your device.'**
  String get configImportFromFileDescription;

  /// No description provided for @configImportPreviewTitle.
  ///
  /// In en, this message translates to:
  /// **'Configuration Preview'**
  String get configImportPreviewTitle;

  /// No description provided for @configImportPreviewServer.
  ///
  /// In en, this message translates to:
  /// **'Server'**
  String get configImportPreviewServer;

  /// No description provided for @configImportPreviewProtocol.
  ///
  /// In en, this message translates to:
  /// **'Protocol'**
  String get configImportPreviewProtocol;

  /// No description provided for @configImportPreviewPort.
  ///
  /// In en, this message translates to:
  /// **'Port'**
  String get configImportPreviewPort;

  /// No description provided for @configImportConfirmButton.
  ///
  /// In en, this message translates to:
  /// **'Import Configuration'**
  String get configImportConfirmButton;

  /// No description provided for @configImportCancelButton.
  ///
  /// In en, this message translates to:
  /// **'Cancel Import'**
  String get configImportCancelButton;

  /// No description provided for @configImportSuccess.
  ///
  /// In en, this message translates to:
  /// **'Configuration imported successfully.'**
  String get configImportSuccess;

  /// No description provided for @configImportError.
  ///
  /// In en, this message translates to:
  /// **'Failed to import configuration.'**
  String get configImportError;

  /// No description provided for @configImportInvalidFormat.
  ///
  /// In en, this message translates to:
  /// **'Invalid configuration format.'**
  String get configImportInvalidFormat;

  /// No description provided for @configImportDuplicate.
  ///
  /// In en, this message translates to:
  /// **'This configuration already exists.'**
  String get configImportDuplicate;

  /// No description provided for @configImportCameraPermission.
  ///
  /// In en, this message translates to:
  /// **'Camera permission is required to scan QR codes.'**
  String get configImportCameraPermission;

  /// No description provided for @notificationCenterTitle.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get notificationCenterTitle;

  /// No description provided for @notificationCenterEmpty.
  ///
  /// In en, this message translates to:
  /// **'No notifications yet.'**
  String get notificationCenterEmpty;

  /// No description provided for @notificationCenterMarkAllRead.
  ///
  /// In en, this message translates to:
  /// **'Mark All as Read'**
  String get notificationCenterMarkAllRead;

  /// No description provided for @notificationCenterClearAll.
  ///
  /// In en, this message translates to:
  /// **'Clear All'**
  String get notificationCenterClearAll;

  /// No description provided for @notificationTypeConnectionStatus.
  ///
  /// In en, this message translates to:
  /// **'Connection Status'**
  String get notificationTypeConnectionStatus;

  /// No description provided for @notificationTypeServerSwitch.
  ///
  /// In en, this message translates to:
  /// **'Server Switch'**
  String get notificationTypeServerSwitch;

  /// No description provided for @notificationTypeSubscriptionExpiry.
  ///
  /// In en, this message translates to:
  /// **'Subscription Expiry'**
  String get notificationTypeSubscriptionExpiry;

  /// No description provided for @notificationTypeSecurityAlert.
  ///
  /// In en, this message translates to:
  /// **'Security Alert'**
  String get notificationTypeSecurityAlert;

  /// No description provided for @notificationTypePromotion.
  ///
  /// In en, this message translates to:
  /// **'Promotion'**
  String get notificationTypePromotion;

  /// No description provided for @notificationTypeSystemUpdate.
  ///
  /// In en, this message translates to:
  /// **'System Update'**
  String get notificationTypeSystemUpdate;

  /// No description provided for @notificationConnected.
  ///
  /// In en, this message translates to:
  /// **'Connected to {serverName}'**
  String notificationConnected(String serverName);

  /// No description provided for @notificationDisconnected.
  ///
  /// In en, this message translates to:
  /// **'Disconnected from VPN.'**
  String get notificationDisconnected;

  /// No description provided for @notificationServerSwitched.
  ///
  /// In en, this message translates to:
  /// **'Switched to {serverName}.'**
  String notificationServerSwitched(String serverName);

  /// No description provided for @notificationSubscriptionExpiring.
  ///
  /// In en, this message translates to:
  /// **'Your subscription expires in {count, plural, =1{1 day} other{{count} days}}.'**
  String notificationSubscriptionExpiring(int count);

  /// No description provided for @notificationSubscriptionExpired.
  ///
  /// In en, this message translates to:
  /// **'Your subscription has expired. Renew to continue using CyberVPN.'**
  String get notificationSubscriptionExpired;

  /// No description provided for @notificationUnreadCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =0{No unread notifications} =1{1 unread notification} other{{count} unread notifications}}'**
  String notificationUnreadCount(int count);

  /// No description provided for @referralDashboardTitle.
  ///
  /// In en, this message translates to:
  /// **'Referral Program'**
  String get referralDashboardTitle;

  /// No description provided for @referralDashboardDescription.
  ///
  /// In en, this message translates to:
  /// **'Invite friends and earn rewards.'**
  String get referralDashboardDescription;

  /// No description provided for @referralShareLink.
  ///
  /// In en, this message translates to:
  /// **'Share Referral Link'**
  String get referralShareLink;

  /// No description provided for @referralCopyLink.
  ///
  /// In en, this message translates to:
  /// **'Copy Link'**
  String get referralCopyLink;

  /// No description provided for @referralLinkCopied.
  ///
  /// In en, this message translates to:
  /// **'Referral link copied to clipboard.'**
  String get referralLinkCopied;

  /// No description provided for @referralCodeLabel.
  ///
  /// In en, this message translates to:
  /// **'Your Referral Code'**
  String get referralCodeLabel;

  /// No description provided for @referralRewardsEarned.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =0{No rewards earned} =1{1 reward earned} other{{count} rewards earned}}'**
  String referralRewardsEarned(int count);

  /// No description provided for @referralFriendsInvited.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =0{No friends invited} =1{1 friend invited} other{{count} friends invited}}'**
  String referralFriendsInvited(int count);

  /// No description provided for @referralRewardDescription.
  ///
  /// In en, this message translates to:
  /// **'Get {days} free days for each friend who subscribes.'**
  String referralRewardDescription(int days);

  /// No description provided for @referralHistory.
  ///
  /// In en, this message translates to:
  /// **'Referral History'**
  String get referralHistory;

  /// No description provided for @referralPending.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get referralPending;

  /// No description provided for @referralCompleted.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get referralCompleted;

  /// No description provided for @referralExpired.
  ///
  /// In en, this message translates to:
  /// **'Expired'**
  String get referralExpired;

  /// No description provided for @diagnosticsTitle.
  ///
  /// In en, this message translates to:
  /// **'Diagnostics'**
  String get diagnosticsTitle;

  /// No description provided for @diagnosticsDescription.
  ///
  /// In en, this message translates to:
  /// **'Test your connection and troubleshoot issues.'**
  String get diagnosticsDescription;

  /// No description provided for @speedTestTitle.
  ///
  /// In en, this message translates to:
  /// **'Speed Test'**
  String get speedTestTitle;

  /// No description provided for @speedTestStart.
  ///
  /// In en, this message translates to:
  /// **'Start Speed Test'**
  String get speedTestStart;

  /// No description provided for @speedTestRunning.
  ///
  /// In en, this message translates to:
  /// **'Testing...'**
  String get speedTestRunning;

  /// No description provided for @speedTestDownloadSpeed.
  ///
  /// In en, this message translates to:
  /// **'Download Speed'**
  String get speedTestDownloadSpeed;

  /// No description provided for @speedTestUploadSpeed.
  ///
  /// In en, this message translates to:
  /// **'Upload Speed'**
  String get speedTestUploadSpeed;

  /// No description provided for @speedTestPing.
  ///
  /// In en, this message translates to:
  /// **'Ping'**
  String get speedTestPing;

  /// No description provided for @speedTestPingMs.
  ///
  /// In en, this message translates to:
  /// **'{value} ms'**
  String speedTestPingMs(int value);

  /// No description provided for @speedTestMbps.
  ///
  /// In en, this message translates to:
  /// **'{value} Mbps'**
  String speedTestMbps(String value);

  /// No description provided for @speedTestResult.
  ///
  /// In en, this message translates to:
  /// **'Speed Test Result'**
  String get speedTestResult;

  /// No description provided for @speedTestHistory.
  ///
  /// In en, this message translates to:
  /// **'Speed Test History'**
  String get speedTestHistory;

  /// No description provided for @speedTestStepConnecting.
  ///
  /// In en, this message translates to:
  /// **'Connecting to test server...'**
  String get speedTestStepConnecting;

  /// No description provided for @speedTestStepDownload.
  ///
  /// In en, this message translates to:
  /// **'Testing download speed...'**
  String get speedTestStepDownload;

  /// No description provided for @speedTestStepUpload.
  ///
  /// In en, this message translates to:
  /// **'Testing upload speed...'**
  String get speedTestStepUpload;

  /// No description provided for @speedTestStepPing.
  ///
  /// In en, this message translates to:
  /// **'Measuring latency...'**
  String get speedTestStepPing;

  /// No description provided for @speedTestStepComplete.
  ///
  /// In en, this message translates to:
  /// **'Test complete.'**
  String get speedTestStepComplete;

  /// No description provided for @speedTestNoVpn.
  ///
  /// In en, this message translates to:
  /// **'Connect to VPN before running a speed test.'**
  String get speedTestNoVpn;

  /// No description provided for @logViewerTitle.
  ///
  /// In en, this message translates to:
  /// **'Log Viewer'**
  String get logViewerTitle;

  /// No description provided for @logViewerEmpty.
  ///
  /// In en, this message translates to:
  /// **'No logs available.'**
  String get logViewerEmpty;

  /// No description provided for @logViewerExportButton.
  ///
  /// In en, this message translates to:
  /// **'Export Logs'**
  String get logViewerExportButton;

  /// No description provided for @logViewerClearButton.
  ///
  /// In en, this message translates to:
  /// **'Clear Logs'**
  String get logViewerClearButton;

  /// No description provided for @logViewerClearConfirm.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to clear all logs?'**
  String get logViewerClearConfirm;

  /// No description provided for @logViewerFilterLabel.
  ///
  /// In en, this message translates to:
  /// **'Filter'**
  String get logViewerFilterLabel;

  /// No description provided for @logViewerFilterAll.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get logViewerFilterAll;

  /// No description provided for @logViewerFilterError.
  ///
  /// In en, this message translates to:
  /// **'Errors'**
  String get logViewerFilterError;

  /// No description provided for @logViewerFilterWarning.
  ///
  /// In en, this message translates to:
  /// **'Warnings'**
  String get logViewerFilterWarning;

  /// No description provided for @logViewerFilterInfo.
  ///
  /// In en, this message translates to:
  /// **'Info'**
  String get logViewerFilterInfo;

  /// No description provided for @logViewerCopied.
  ///
  /// In en, this message translates to:
  /// **'Log entry copied to clipboard.'**
  String get logViewerCopied;

  /// No description provided for @logViewerExportSuccess.
  ///
  /// In en, this message translates to:
  /// **'Logs exported successfully.'**
  String get logViewerExportSuccess;

  /// No description provided for @logViewerExportError.
  ///
  /// In en, this message translates to:
  /// **'Failed to export logs.'**
  String get logViewerExportError;

  /// No description provided for @widgetConnectLabel.
  ///
  /// In en, this message translates to:
  /// **'Connect VPN'**
  String get widgetConnectLabel;

  /// No description provided for @widgetDisconnectLabel.
  ///
  /// In en, this message translates to:
  /// **'Disconnect VPN'**
  String get widgetDisconnectLabel;

  /// No description provided for @widgetStatusLabel.
  ///
  /// In en, this message translates to:
  /// **'VPN Status'**
  String get widgetStatusLabel;

  /// No description provided for @widgetServerLabel.
  ///
  /// In en, this message translates to:
  /// **'Current Server'**
  String get widgetServerLabel;

  /// No description provided for @quickActionConnect.
  ///
  /// In en, this message translates to:
  /// **'Connect'**
  String get quickActionConnect;

  /// No description provided for @quickActionDisconnect.
  ///
  /// In en, this message translates to:
  /// **'Disconnect'**
  String get quickActionDisconnect;

  /// No description provided for @quickActionServers.
  ///
  /// In en, this message translates to:
  /// **'Servers'**
  String get quickActionServers;

  /// No description provided for @quickActionSpeedTest.
  ///
  /// In en, this message translates to:
  /// **'Speed Test'**
  String get quickActionSpeedTest;

  /// No description provided for @quickActionSettings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get quickActionSettings;

  /// No description provided for @quickActionSupport.
  ///
  /// In en, this message translates to:
  /// **'Support'**
  String get quickActionSupport;

  /// No description provided for @errorConnectionFailed.
  ///
  /// In en, this message translates to:
  /// **'Connection failed. Please try again.'**
  String get errorConnectionFailed;

  /// No description provided for @errorConnectionTimeout.
  ///
  /// In en, this message translates to:
  /// **'Connection timed out. Check your internet connection.'**
  String get errorConnectionTimeout;

  /// No description provided for @errorServerUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Server is currently unavailable. Try another server.'**
  String get errorServerUnavailable;

  /// No description provided for @errorInvalidConfig.
  ///
  /// In en, this message translates to:
  /// **'Invalid configuration. Please reimport your settings.'**
  String get errorInvalidConfig;

  /// No description provided for @errorSubscriptionExpired.
  ///
  /// In en, this message translates to:
  /// **'Your subscription has expired. Please renew to continue.'**
  String get errorSubscriptionExpired;

  /// No description provided for @errorSubscriptionRequired.
  ///
  /// In en, this message translates to:
  /// **'A subscription is required to use this feature.'**
  String get errorSubscriptionRequired;

  /// No description provided for @errorAuthenticationFailed.
  ///
  /// In en, this message translates to:
  /// **'Authentication failed. Please log in again.'**
  String get errorAuthenticationFailed;

  /// No description provided for @errorTokenExpired.
  ///
  /// In en, this message translates to:
  /// **'Session expired. Please log in again.'**
  String get errorTokenExpired;

  /// No description provided for @errorNetworkUnreachable.
  ///
  /// In en, this message translates to:
  /// **'Network unreachable. Check your connection.'**
  String get errorNetworkUnreachable;

  /// No description provided for @errorPermissionDenied.
  ///
  /// In en, this message translates to:
  /// **'Permission denied.'**
  String get errorPermissionDenied;

  /// No description provided for @errorRateLimited.
  ///
  /// In en, this message translates to:
  /// **'Too many requests. Please wait a moment.'**
  String get errorRateLimited;

  /// No description provided for @errorUnexpected.
  ///
  /// In en, this message translates to:
  /// **'An unexpected error occurred. Please try again.'**
  String get errorUnexpected;

  /// No description provided for @errorServerError.
  ///
  /// In en, this message translates to:
  /// **'Server error. Please try again later.'**
  String get errorServerError;

  /// No description provided for @errorInvalidCredentials.
  ///
  /// In en, this message translates to:
  /// **'Invalid email or password.'**
  String get errorInvalidCredentials;

  /// No description provided for @errorAccountLocked.
  ///
  /// In en, this message translates to:
  /// **'Your account has been locked. Please contact support.'**
  String get errorAccountLocked;

  /// No description provided for @errorWeakPassword.
  ///
  /// In en, this message translates to:
  /// **'Password is too weak. Use at least 8 characters with letters and numbers.'**
  String get errorWeakPassword;

  /// No description provided for @errorEmailAlreadyInUse.
  ///
  /// In en, this message translates to:
  /// **'This email is already registered.'**
  String get errorEmailAlreadyInUse;

  /// No description provided for @errorInvalidEmail.
  ///
  /// In en, this message translates to:
  /// **'Please enter a valid email address.'**
  String get errorInvalidEmail;

  /// No description provided for @errorFieldRequired.
  ///
  /// In en, this message translates to:
  /// **'This field is required.'**
  String get errorFieldRequired;

  /// No description provided for @errorPaymentFailed.
  ///
  /// In en, this message translates to:
  /// **'Payment failed. Please try again or use a different method.'**
  String get errorPaymentFailed;

  /// No description provided for @errorQrScanFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed to scan QR code. Please try again.'**
  String get errorQrScanFailed;

  /// No description provided for @errorTelegramAuthCancelled.
  ///
  /// In en, this message translates to:
  /// **'Telegram login was cancelled.'**
  String get errorTelegramAuthCancelled;

  /// No description provided for @errorTelegramAuthFailed.
  ///
  /// In en, this message translates to:
  /// **'Telegram authentication failed. Please try again.'**
  String get errorTelegramAuthFailed;

  /// No description provided for @errorTelegramAuthExpired.
  ///
  /// In en, this message translates to:
  /// **'Telegram login expired. Please try again.'**
  String get errorTelegramAuthExpired;

  /// No description provided for @errorTelegramNotInstalled.
  ///
  /// In en, this message translates to:
  /// **'Telegram is not installed on this device.'**
  String get errorTelegramNotInstalled;

  /// No description provided for @errorTelegramAuthInvalid.
  ///
  /// In en, this message translates to:
  /// **'Invalid Telegram authentication data.'**
  String get errorTelegramAuthInvalid;

  /// No description provided for @errorBiometricUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Biometric authentication is not available on this device.'**
  String get errorBiometricUnavailable;

  /// No description provided for @errorBiometricNotEnrolled.
  ///
  /// In en, this message translates to:
  /// **'No biometric data enrolled. Please set up fingerprint or face recognition in device settings.'**
  String get errorBiometricNotEnrolled;

  /// No description provided for @errorBiometricFailed.
  ///
  /// In en, this message translates to:
  /// **'Biometric authentication failed. Please try again.'**
  String get errorBiometricFailed;

  /// No description provided for @errorBiometricLocked.
  ///
  /// In en, this message translates to:
  /// **'Biometric authentication is locked. Try again later or use your password.'**
  String get errorBiometricLocked;

  /// No description provided for @errorSessionExpired.
  ///
  /// In en, this message translates to:
  /// **'Your session has expired. Please log in again.'**
  String get errorSessionExpired;

  /// No description provided for @errorAccountDisabled.
  ///
  /// In en, this message translates to:
  /// **'Your account has been disabled. Please contact support.'**
  String get errorAccountDisabled;

  /// No description provided for @errorRateLimitedWithCountdown.
  ///
  /// In en, this message translates to:
  /// **'Too many attempts. Please try again in {seconds, plural, =1{1 second} other{{seconds} seconds}}.'**
  String errorRateLimitedWithCountdown(int seconds);

  /// No description provided for @errorOfflineLoginRequired.
  ///
  /// In en, this message translates to:
  /// **'You need to be online to log in. Please check your connection.'**
  String get errorOfflineLoginRequired;

  /// No description provided for @errorOfflineSessionExpired.
  ///
  /// In en, this message translates to:
  /// **'Your cached session has expired. Please connect to the internet to log in.'**
  String get errorOfflineSessionExpired;

  /// No description provided for @a11yConnectButton.
  ///
  /// In en, this message translates to:
  /// **'Connect to VPN server'**
  String get a11yConnectButton;

  /// No description provided for @a11yDisconnectButton.
  ///
  /// In en, this message translates to:
  /// **'Disconnect from VPN server'**
  String get a11yDisconnectButton;

  /// No description provided for @a11yServerStatusOnline.
  ///
  /// In en, this message translates to:
  /// **'Server is online'**
  String get a11yServerStatusOnline;

  /// No description provided for @a11yServerStatusOffline.
  ///
  /// In en, this message translates to:
  /// **'Server is offline'**
  String get a11yServerStatusOffline;

  /// No description provided for @a11yServerStatusMaintenance.
  ///
  /// In en, this message translates to:
  /// **'Server is under maintenance'**
  String get a11yServerStatusMaintenance;

  /// No description provided for @a11ySpeedIndicator.
  ///
  /// In en, this message translates to:
  /// **'Current speed: {speed}'**
  String a11ySpeedIndicator(String speed);

  /// No description provided for @a11yConnectionStatus.
  ///
  /// In en, this message translates to:
  /// **'Connection status: {status}'**
  String a11yConnectionStatus(String status);

  /// No description provided for @a11yServerSelect.
  ///
  /// In en, this message translates to:
  /// **'Select server {name} in {country}'**
  String a11yServerSelect(String name, String country);

  /// No description provided for @a11yNavigationMenu.
  ///
  /// In en, this message translates to:
  /// **'Navigation menu'**
  String get a11yNavigationMenu;

  /// No description provided for @a11yCloseDialog.
  ///
  /// In en, this message translates to:
  /// **'Close dialog'**
  String get a11yCloseDialog;

  /// No description provided for @a11yToggleSwitch.
  ///
  /// In en, this message translates to:
  /// **'Toggle {label}'**
  String a11yToggleSwitch(String label);

  /// No description provided for @a11yNotificationBadge.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =0{No notifications} =1{1 notification} other{{count} notifications}}'**
  String a11yNotificationBadge(int count);

  /// No description provided for @a11yLoadingIndicator.
  ///
  /// In en, this message translates to:
  /// **'Loading'**
  String get a11yLoadingIndicator;

  /// No description provided for @a11yRefreshContent.
  ///
  /// In en, this message translates to:
  /// **'Refresh content'**
  String get a11yRefreshContent;

  /// No description provided for @a11yBackButton.
  ///
  /// In en, this message translates to:
  /// **'Go back'**
  String get a11yBackButton;

  /// No description provided for @a11ySearchField.
  ///
  /// In en, this message translates to:
  /// **'Search'**
  String get a11ySearchField;

  /// No description provided for @rootDetectionDialogTitle.
  ///
  /// In en, this message translates to:
  /// **'Rooted/Jailbroken Device Detected'**
  String get rootDetectionDialogTitle;

  /// No description provided for @rootDetectionDialogDescription.
  ///
  /// In en, this message translates to:
  /// **'Your device appears to be rooted (Android) or jailbroken (iOS). While CyberVPN will continue to work, please note that using a rooted/jailbroken device may expose you to security risks.\n\nWe understand that users in censored regions often rely on rooted devices for additional privacy tools. CyberVPN will not block your access, but we recommend being cautious about the apps you install and the permissions you grant.'**
  String get rootDetectionDialogDescription;

  /// No description provided for @rootDetectionDialogDismiss.
  ///
  /// In en, this message translates to:
  /// **'I Understand'**
  String get rootDetectionDialogDismiss;

  /// No description provided for @loginEmailLabel.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get loginEmailLabel;

  /// No description provided for @loginEmailHint.
  ///
  /// In en, this message translates to:
  /// **'Enter your email'**
  String get loginEmailHint;

  /// No description provided for @loginPasswordLabel.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get loginPasswordLabel;

  /// No description provided for @loginPasswordHint.
  ///
  /// In en, this message translates to:
  /// **'Enter your password'**
  String get loginPasswordHint;

  /// No description provided for @loginShowPassword.
  ///
  /// In en, this message translates to:
  /// **'Show password'**
  String get loginShowPassword;

  /// No description provided for @loginHidePassword.
  ///
  /// In en, this message translates to:
  /// **'Hide password'**
  String get loginHidePassword;

  /// No description provided for @loginRememberMe.
  ///
  /// In en, this message translates to:
  /// **'Remember me'**
  String get loginRememberMe;

  /// No description provided for @loginButton.
  ///
  /// In en, this message translates to:
  /// **'Login'**
  String get loginButton;

  /// No description provided for @loginContinueWithTelegram.
  ///
  /// In en, this message translates to:
  /// **'Continue with Telegram'**
  String get loginContinueWithTelegram;

  /// No description provided for @registerTitle.
  ///
  /// In en, this message translates to:
  /// **'Create Account'**
  String get registerTitle;

  /// No description provided for @registerSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Join CyberVPN for a secure experience'**
  String get registerSubtitle;

  /// No description provided for @registerPasswordHint.
  ///
  /// In en, this message translates to:
  /// **'Create a password'**
  String get registerPasswordHint;

  /// No description provided for @registerConfirmPasswordLabel.
  ///
  /// In en, this message translates to:
  /// **'Confirm Password'**
  String get registerConfirmPasswordLabel;

  /// No description provided for @registerConfirmPasswordHint.
  ///
  /// In en, this message translates to:
  /// **'Re-enter your password'**
  String get registerConfirmPasswordHint;

  /// No description provided for @registerConfirmPasswordError.
  ///
  /// In en, this message translates to:
  /// **'Please confirm your password'**
  String get registerConfirmPasswordError;

  /// No description provided for @registerPasswordMismatch.
  ///
  /// In en, this message translates to:
  /// **'Passwords do not match'**
  String get registerPasswordMismatch;

  /// No description provided for @registerReferralCodeLabel.
  ///
  /// In en, this message translates to:
  /// **'Referral Code (optional)'**
  String get registerReferralCodeLabel;

  /// No description provided for @registerReferralCodeHint.
  ///
  /// In en, this message translates to:
  /// **'Enter referral code'**
  String get registerReferralCodeHint;

  /// No description provided for @registerReferralApplied.
  ///
  /// In en, this message translates to:
  /// **'Applied!'**
  String get registerReferralApplied;

  /// No description provided for @registerReferralFromLink.
  ///
  /// In en, this message translates to:
  /// **'Referral code applied from link'**
  String get registerReferralFromLink;

  /// No description provided for @registerAgreePrefix.
  ///
  /// In en, this message translates to:
  /// **'I agree to the '**
  String get registerAgreePrefix;

  /// No description provided for @registerTermsAndConditions.
  ///
  /// In en, this message translates to:
  /// **'Terms & Conditions'**
  String get registerTermsAndConditions;

  /// No description provided for @registerAndSeparator.
  ///
  /// In en, this message translates to:
  /// **' and '**
  String get registerAndSeparator;

  /// No description provided for @registerAcceptTermsError.
  ///
  /// In en, this message translates to:
  /// **'Please accept the Terms & Conditions'**
  String get registerAcceptTermsError;

  /// No description provided for @registerButton.
  ///
  /// In en, this message translates to:
  /// **'Register'**
  String get registerButton;

  /// No description provided for @registerOrSeparator.
  ///
  /// In en, this message translates to:
  /// **'OR'**
  String get registerOrSeparator;

  /// No description provided for @registerAlreadyHaveAccount.
  ///
  /// In en, this message translates to:
  /// **'Already have an account? '**
  String get registerAlreadyHaveAccount;

  /// No description provided for @registerLoginLink.
  ///
  /// In en, this message translates to:
  /// **'Login'**
  String get registerLoginLink;

  /// No description provided for @telegramNotInstalledTitle.
  ///
  /// In en, this message translates to:
  /// **'Telegram Not Installed'**
  String get telegramNotInstalledTitle;

  /// No description provided for @telegramNotInstalledMessage.
  ///
  /// In en, this message translates to:
  /// **'The Telegram app is not installed on your device. You can install it from the app store or use the web version.'**
  String get telegramNotInstalledMessage;

  /// No description provided for @telegramUseWeb.
  ///
  /// In en, this message translates to:
  /// **'Use Web'**
  String get telegramUseWeb;

  /// No description provided for @telegramInstall.
  ///
  /// In en, this message translates to:
  /// **'Install'**
  String get telegramInstall;

  /// No description provided for @appLockTitle.
  ///
  /// In en, this message translates to:
  /// **'CyberVPN Locked'**
  String get appLockTitle;

  /// No description provided for @appLockSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Authenticate to continue'**
  String get appLockSubtitle;

  /// No description provided for @appLockUnlockButton.
  ///
  /// In en, this message translates to:
  /// **'Unlock'**
  String get appLockUnlockButton;

  /// No description provided for @appLockUnlockWithBiometric.
  ///
  /// In en, this message translates to:
  /// **'Unlock with {biometricLabel}'**
  String appLockUnlockWithBiometric(String biometricLabel);

  /// No description provided for @appLockTooManyAttempts.
  ///
  /// In en, this message translates to:
  /// **'Too many failed attempts'**
  String get appLockTooManyAttempts;

  /// No description provided for @appLockUsePin.
  ///
  /// In en, this message translates to:
  /// **'Use device PIN'**
  String get appLockUsePin;

  /// No description provided for @appLockTryAgain.
  ///
  /// In en, this message translates to:
  /// **'Try {biometricLabel} again'**
  String appLockTryAgain(String biometricLabel);

  /// No description provided for @appLockLocalizedReason.
  ///
  /// In en, this message translates to:
  /// **'Unlock CyberVPN with your device PIN'**
  String get appLockLocalizedReason;

  /// No description provided for @biometricSettingsTitle.
  ///
  /// In en, this message translates to:
  /// **'Security'**
  String get biometricSettingsTitle;

  /// No description provided for @biometricAuthSection.
  ///
  /// In en, this message translates to:
  /// **'Biometric Authentication'**
  String get biometricAuthSection;

  /// No description provided for @biometricLoginLabel.
  ///
  /// In en, this message translates to:
  /// **'Biometric Login'**
  String get biometricLoginLabel;

  /// No description provided for @biometricLoginDescription.
  ///
  /// In en, this message translates to:
  /// **'Use biometrics to sign in quickly'**
  String get biometricLoginDescription;

  /// No description provided for @biometricLoginEnabled.
  ///
  /// In en, this message translates to:
  /// **'Biometric login enabled'**
  String get biometricLoginEnabled;

  /// No description provided for @biometricLoginDisabled.
  ///
  /// In en, this message translates to:
  /// **'Biometric login disabled'**
  String get biometricLoginDisabled;

  /// No description provided for @biometricVerificationRequired.
  ///
  /// In en, this message translates to:
  /// **'Biometric verification required'**
  String get biometricVerificationRequired;

  /// No description provided for @biometricEnterCredentialsTitle.
  ///
  /// In en, this message translates to:
  /// **'Enter credentials'**
  String get biometricEnterCredentialsTitle;

  /// No description provided for @biometricEnterCredentialsMessage.
  ///
  /// In en, this message translates to:
  /// **'Enter your login credentials to enable quick sign-in with biometrics.'**
  String get biometricEnterCredentialsMessage;

  /// No description provided for @biometricSave.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get biometricSave;

  /// No description provided for @biometricAppLockLabel.
  ///
  /// In en, this message translates to:
  /// **'App Lock'**
  String get biometricAppLockLabel;

  /// No description provided for @biometricAppLockDescription.
  ///
  /// In en, this message translates to:
  /// **'Require biometrics when returning to app (30+ seconds)'**
  String get biometricAppLockDescription;

  /// No description provided for @biometricAppLockEnabled.
  ///
  /// In en, this message translates to:
  /// **'App lock enabled'**
  String get biometricAppLockEnabled;

  /// No description provided for @biometricAppLockDisabled.
  ///
  /// In en, this message translates to:
  /// **'App lock disabled'**
  String get biometricAppLockDisabled;

  /// No description provided for @biometricUnavailableTitle.
  ///
  /// In en, this message translates to:
  /// **'Biometrics Unavailable'**
  String get biometricUnavailableTitle;

  /// No description provided for @biometricUnavailableMessage.
  ///
  /// In en, this message translates to:
  /// **'Your device does not support biometric authentication, or no biometrics are enrolled.'**
  String get biometricUnavailableMessage;

  /// No description provided for @biometricLoadingState.
  ///
  /// In en, this message translates to:
  /// **'Loading...'**
  String get biometricLoadingState;

  /// No description provided for @biometricUnavailableState.
  ///
  /// In en, this message translates to:
  /// **'Unavailable'**
  String get biometricUnavailableState;

  /// No description provided for @biometricLabelFingerprint.
  ///
  /// In en, this message translates to:
  /// **'Fingerprint'**
  String get biometricLabelFingerprint;

  /// No description provided for @biometricLabelGeneric.
  ///
  /// In en, this message translates to:
  /// **'Biometrics'**
  String get biometricLabelGeneric;

  /// No description provided for @biometricAvailableOnDevice.
  ///
  /// In en, this message translates to:
  /// **'Available on this device'**
  String get biometricAvailableOnDevice;

  /// No description provided for @biometricSettingsChanged.
  ///
  /// In en, this message translates to:
  /// **'Your biometric settings have changed. Please sign in with your password and re-enable biometric login in settings.'**
  String get biometricSettingsChanged;

  /// No description provided for @biometricPasswordChanged.
  ///
  /// In en, this message translates to:
  /// **'Your password has changed. Please sign in with your password.'**
  String get biometricPasswordChanged;

  /// No description provided for @settingsNotificationPrefsTitle.
  ///
  /// In en, this message translates to:
  /// **'Notification Preferences'**
  String get settingsNotificationPrefsTitle;

  /// No description provided for @settingsNotificationConnectionLabel.
  ///
  /// In en, this message translates to:
  /// **'Connection Status'**
  String get settingsNotificationConnectionLabel;

  /// No description provided for @settingsNotificationConnectionDescription.
  ///
  /// In en, this message translates to:
  /// **'Get notified when VPN connects or disconnects'**
  String get settingsNotificationConnectionDescription;

  /// No description provided for @settingsNotificationServerLabel.
  ///
  /// In en, this message translates to:
  /// **'Server Changes'**
  String get settingsNotificationServerLabel;

  /// No description provided for @settingsNotificationServerDescription.
  ///
  /// In en, this message translates to:
  /// **'Get notified when server is switched'**
  String get settingsNotificationServerDescription;

  /// No description provided for @settingsNotificationSubscriptionLabel.
  ///
  /// In en, this message translates to:
  /// **'Subscription Alerts'**
  String get settingsNotificationSubscriptionLabel;

  /// No description provided for @settingsNotificationSubscriptionDescription.
  ///
  /// In en, this message translates to:
  /// **'Get notified about subscription expiry'**
  String get settingsNotificationSubscriptionDescription;

  /// No description provided for @settingsNotificationSecurityLabel.
  ///
  /// In en, this message translates to:
  /// **'Security Alerts'**
  String get settingsNotificationSecurityLabel;

  /// No description provided for @settingsNotificationSecurityDescription.
  ///
  /// In en, this message translates to:
  /// **'Get notified about security events'**
  String get settingsNotificationSecurityDescription;

  /// No description provided for @settingsNotificationPromotionLabel.
  ///
  /// In en, this message translates to:
  /// **'Promotions'**
  String get settingsNotificationPromotionLabel;

  /// No description provided for @settingsNotificationPromotionDescription.
  ///
  /// In en, this message translates to:
  /// **'Receive promotional notifications'**
  String get settingsNotificationPromotionDescription;

  /// No description provided for @settingsNotificationUpdateLabel.
  ///
  /// In en, this message translates to:
  /// **'System Updates'**
  String get settingsNotificationUpdateLabel;

  /// No description provided for @settingsNotificationUpdateDescription.
  ///
  /// In en, this message translates to:
  /// **'Get notified about app updates'**
  String get settingsNotificationUpdateDescription;

  /// No description provided for @settingsVpnProtocolWireGuard.
  ///
  /// In en, this message translates to:
  /// **'WireGuard'**
  String get settingsVpnProtocolWireGuard;

  /// No description provided for @settingsVpnProtocolOpenVpn.
  ///
  /// In en, this message translates to:
  /// **'OpenVPN'**
  String get settingsVpnProtocolOpenVpn;

  /// No description provided for @settingsVpnProtocolIkev2.
  ///
  /// In en, this message translates to:
  /// **'IKEv2'**
  String get settingsVpnProtocolIkev2;

  /// No description provided for @settingsVpnProtocolAuto.
  ///
  /// In en, this message translates to:
  /// **'Auto'**
  String get settingsVpnProtocolAuto;

  /// No description provided for @settingsThemeDark.
  ///
  /// In en, this message translates to:
  /// **'Dark'**
  String get settingsThemeDark;

  /// No description provided for @settingsThemeLight.
  ///
  /// In en, this message translates to:
  /// **'Light'**
  String get settingsThemeLight;

  /// No description provided for @settingsThemeSystem.
  ///
  /// In en, this message translates to:
  /// **'System'**
  String get settingsThemeSystem;

  /// No description provided for @settingsLanguageSearchHint.
  ///
  /// In en, this message translates to:
  /// **'Search languages'**
  String get settingsLanguageSearchHint;

  /// No description provided for @settingsVersionInfo.
  ///
  /// In en, this message translates to:
  /// **'Version Info'**
  String get settingsVersionInfo;

  /// No description provided for @settingsPrivacyAndTerms.
  ///
  /// In en, this message translates to:
  /// **'Privacy & Terms'**
  String get settingsPrivacyAndTerms;

  /// No description provided for @settingsContactSupport.
  ///
  /// In en, this message translates to:
  /// **'Contact Support'**
  String get settingsContactSupport;

  /// No description provided for @settingsAppVersion.
  ///
  /// In en, this message translates to:
  /// **'App version {version}'**
  String settingsAppVersion(String version);

  /// No description provided for @settingsBuildNumber.
  ///
  /// In en, this message translates to:
  /// **'Build {build}'**
  String settingsBuildNumber(String build);

  /// No description provided for @settingsRateApp.
  ///
  /// In en, this message translates to:
  /// **'Rate CyberVPN'**
  String get settingsRateApp;

  /// No description provided for @settingsShareApp.
  ///
  /// In en, this message translates to:
  /// **'Share with Friends'**
  String get settingsShareApp;

  /// No description provided for @settingsDeleteData.
  ///
  /// In en, this message translates to:
  /// **'Delete All Data'**
  String get settingsDeleteData;

  /// No description provided for @profileSaveButton.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get profileSaveButton;

  /// No description provided for @profileSaveSuccess.
  ///
  /// In en, this message translates to:
  /// **'Profile updated successfully'**
  String get profileSaveSuccess;

  /// No description provided for @profileAvatarChange.
  ///
  /// In en, this message translates to:
  /// **'Change Avatar'**
  String get profileAvatarChange;

  /// No description provided for @profileAvatarRemove.
  ///
  /// In en, this message translates to:
  /// **'Remove Avatar'**
  String get profileAvatarRemove;

  /// No description provided for @profilePasswordUpdated.
  ///
  /// In en, this message translates to:
  /// **'Password updated successfully'**
  String get profilePasswordUpdated;

  /// No description provided for @profilePasswordRequirements.
  ///
  /// In en, this message translates to:
  /// **'Password must be at least 8 characters with letters and numbers'**
  String get profilePasswordRequirements;

  /// No description provided for @profileAccountInfo.
  ///
  /// In en, this message translates to:
  /// **'Account Information'**
  String get profileAccountInfo;

  /// No description provided for @profileSecuritySection.
  ///
  /// In en, this message translates to:
  /// **'Security'**
  String get profileSecuritySection;

  /// No description provided for @profileDangerZone.
  ///
  /// In en, this message translates to:
  /// **'Danger Zone'**
  String get profileDangerZone;

  /// No description provided for @profileDeleteConfirmInput.
  ///
  /// In en, this message translates to:
  /// **'Type DELETE to confirm'**
  String get profileDeleteConfirmInput;

  /// No description provided for @profileDeleteInProgress.
  ///
  /// In en, this message translates to:
  /// **'Deleting account...'**
  String get profileDeleteInProgress;

  /// No description provided for @profileSessionInfo.
  ///
  /// In en, this message translates to:
  /// **'Session Information'**
  String get profileSessionInfo;

  /// No description provided for @profileLastLogin.
  ///
  /// In en, this message translates to:
  /// **'Last login: {date}'**
  String profileLastLogin(String date);

  /// No description provided for @profileCreatedAt.
  ///
  /// In en, this message translates to:
  /// **'Account created: {date}'**
  String profileCreatedAt(String date);

  /// No description provided for @configImportManualEntry.
  ///
  /// In en, this message translates to:
  /// **'Manual Entry'**
  String get configImportManualEntry;

  /// No description provided for @configImportManualDescription.
  ///
  /// In en, this message translates to:
  /// **'Enter VPN configuration details manually.'**
  String get configImportManualDescription;

  /// No description provided for @configImportServerAddress.
  ///
  /// In en, this message translates to:
  /// **'Server Address'**
  String get configImportServerAddress;

  /// No description provided for @configImportServerPort.
  ///
  /// In en, this message translates to:
  /// **'Port'**
  String get configImportServerPort;

  /// No description provided for @configImportProtocol.
  ///
  /// In en, this message translates to:
  /// **'Protocol'**
  String get configImportProtocol;

  /// No description provided for @configImportPrivateKey.
  ///
  /// In en, this message translates to:
  /// **'Private Key'**
  String get configImportPrivateKey;

  /// No description provided for @configImportPublicKey.
  ///
  /// In en, this message translates to:
  /// **'Public Key'**
  String get configImportPublicKey;

  /// No description provided for @configImportConfigName.
  ///
  /// In en, this message translates to:
  /// **'Configuration Name'**
  String get configImportConfigName;

  /// No description provided for @configImportConfigNameHint.
  ///
  /// In en, this message translates to:
  /// **'Enter a name for this configuration'**
  String get configImportConfigNameHint;

  /// No description provided for @configImportSaving.
  ///
  /// In en, this message translates to:
  /// **'Saving configuration...'**
  String get configImportSaving;

  /// No description provided for @configImportDeleteConfirm.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to delete this configuration?'**
  String get configImportDeleteConfirm;

  /// No description provided for @configImportDeleteSuccess.
  ///
  /// In en, this message translates to:
  /// **'Configuration deleted.'**
  String get configImportDeleteSuccess;

  /// No description provided for @configImportNoConfigs.
  ///
  /// In en, this message translates to:
  /// **'No imported configurations yet.'**
  String get configImportNoConfigs;

  /// No description provided for @configImportManageTitle.
  ///
  /// In en, this message translates to:
  /// **'Manage Configurations'**
  String get configImportManageTitle;

  /// No description provided for @configImportActiveLabel.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get configImportActiveLabel;

  /// No description provided for @configImportConnectButton.
  ///
  /// In en, this message translates to:
  /// **'Connect'**
  String get configImportConnectButton;

  /// No description provided for @configImportEditButton.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get configImportEditButton;

  /// No description provided for @configImportDeleteButton.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get configImportDeleteButton;

  /// No description provided for @subscriptionTitle.
  ///
  /// In en, this message translates to:
  /// **'Subscription Plans'**
  String get subscriptionTitle;

  /// No description provided for @subscriptionCurrentPlan.
  ///
  /// In en, this message translates to:
  /// **'Current Plan'**
  String get subscriptionCurrentPlan;

  /// No description provided for @subscriptionFreePlan.
  ///
  /// In en, this message translates to:
  /// **'Free'**
  String get subscriptionFreePlan;

  /// No description provided for @subscriptionTrialPlan.
  ///
  /// In en, this message translates to:
  /// **'Trial'**
  String get subscriptionTrialPlan;

  /// No description provided for @subscriptionBasicPlan.
  ///
  /// In en, this message translates to:
  /// **'Basic'**
  String get subscriptionBasicPlan;

  /// No description provided for @subscriptionPremiumPlan.
  ///
  /// In en, this message translates to:
  /// **'Premium'**
  String get subscriptionPremiumPlan;

  /// No description provided for @subscriptionMonthly.
  ///
  /// In en, this message translates to:
  /// **'Monthly'**
  String get subscriptionMonthly;

  /// No description provided for @subscriptionYearly.
  ///
  /// In en, this message translates to:
  /// **'Yearly'**
  String get subscriptionYearly;

  /// No description provided for @subscriptionLifetime.
  ///
  /// In en, this message translates to:
  /// **'Lifetime'**
  String get subscriptionLifetime;

  /// No description provided for @subscriptionPricePerMonth.
  ///
  /// In en, this message translates to:
  /// **'{price}/month'**
  String subscriptionPricePerMonth(String price);

  /// No description provided for @subscriptionPricePerYear.
  ///
  /// In en, this message translates to:
  /// **'{price}/year'**
  String subscriptionPricePerYear(String price);

  /// No description provided for @subscriptionSavePercent.
  ///
  /// In en, this message translates to:
  /// **'Save {percent}%'**
  String subscriptionSavePercent(int percent);

  /// No description provided for @subscriptionSubscribeButton.
  ///
  /// In en, this message translates to:
  /// **'Subscribe'**
  String get subscriptionSubscribeButton;

  /// No description provided for @subscriptionRestorePurchases.
  ///
  /// In en, this message translates to:
  /// **'Restore Purchases'**
  String get subscriptionRestorePurchases;

  /// No description provided for @subscriptionRestoreSuccess.
  ///
  /// In en, this message translates to:
  /// **'Purchases restored successfully'**
  String get subscriptionRestoreSuccess;

  /// No description provided for @subscriptionRestoreNotFound.
  ///
  /// In en, this message translates to:
  /// **'No previous purchases found'**
  String get subscriptionRestoreNotFound;

  /// No description provided for @subscriptionCancelButton.
  ///
  /// In en, this message translates to:
  /// **'Cancel Subscription'**
  String get subscriptionCancelButton;

  /// No description provided for @subscriptionCancelConfirm.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to cancel your subscription?'**
  String get subscriptionCancelConfirm;

  /// No description provided for @subscriptionCancelSuccess.
  ///
  /// In en, this message translates to:
  /// **'Subscription cancelled'**
  String get subscriptionCancelSuccess;

  /// No description provided for @subscriptionRenewButton.
  ///
  /// In en, this message translates to:
  /// **'Renew Subscription'**
  String get subscriptionRenewButton;

  /// No description provided for @subscriptionExpiresOn.
  ///
  /// In en, this message translates to:
  /// **'Expires on {date}'**
  String subscriptionExpiresOn(String date);

  /// No description provided for @subscriptionAutoRenew.
  ///
  /// In en, this message translates to:
  /// **'Auto-renew enabled'**
  String get subscriptionAutoRenew;

  /// No description provided for @subscriptionFeatureUnlimitedData.
  ///
  /// In en, this message translates to:
  /// **'Unlimited data'**
  String get subscriptionFeatureUnlimitedData;

  /// No description provided for @subscriptionFeatureAllServers.
  ///
  /// In en, this message translates to:
  /// **'Access to all servers'**
  String get subscriptionFeatureAllServers;

  /// No description provided for @subscriptionFeatureNoAds.
  ///
  /// In en, this message translates to:
  /// **'No ads'**
  String get subscriptionFeatureNoAds;

  /// No description provided for @subscriptionFeaturePriority.
  ///
  /// In en, this message translates to:
  /// **'Priority support'**
  String get subscriptionFeaturePriority;

  /// No description provided for @subscriptionFeatureDevices.
  ///
  /// In en, this message translates to:
  /// **'Up to {count} devices'**
  String subscriptionFeatureDevices(int count);

  /// No description provided for @subscriptionTrafficUsed.
  ///
  /// In en, this message translates to:
  /// **'{used} of {total} used'**
  String subscriptionTrafficUsed(String used, String total);

  /// No description provided for @subscriptionUpgradePrompt.
  ///
  /// In en, this message translates to:
  /// **'Upgrade for more features'**
  String get subscriptionUpgradePrompt;

  /// No description provided for @subscriptionProcessing.
  ///
  /// In en, this message translates to:
  /// **'Processing payment...'**
  String get subscriptionProcessing;

  /// No description provided for @subscriptionPaymentMethod.
  ///
  /// In en, this message translates to:
  /// **'Payment Method'**
  String get subscriptionPaymentMethod;

  /// No description provided for @serverListTitle.
  ///
  /// In en, this message translates to:
  /// **'Server List'**
  String get serverListTitle;

  /// No description provided for @serverListSearchHint.
  ///
  /// In en, this message translates to:
  /// **'Search servers...'**
  String get serverListSearchHint;

  /// No description provided for @serverListFilterAll.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get serverListFilterAll;

  /// No description provided for @serverListFilterFavorites.
  ///
  /// In en, this message translates to:
  /// **'Favorites'**
  String get serverListFilterFavorites;

  /// No description provided for @serverListFilterRecommended.
  ///
  /// In en, this message translates to:
  /// **'Recommended'**
  String get serverListFilterRecommended;

  /// No description provided for @serverListNoResults.
  ///
  /// In en, this message translates to:
  /// **'No servers found'**
  String get serverListNoResults;

  /// No description provided for @serverListPing.
  ///
  /// In en, this message translates to:
  /// **'{ping} ms'**
  String serverListPing(int ping);

  /// No description provided for @serverListLoad.
  ///
  /// In en, this message translates to:
  /// **'{load}% load'**
  String serverListLoad(int load);

  /// No description provided for @serverListAddFavorite.
  ///
  /// In en, this message translates to:
  /// **'Add to favorites'**
  String get serverListAddFavorite;

  /// No description provided for @serverListRemoveFavorite.
  ///
  /// In en, this message translates to:
  /// **'Remove from favorites'**
  String get serverListRemoveFavorite;

  /// No description provided for @serverListConnecting.
  ///
  /// In en, this message translates to:
  /// **'Connecting to {server}...'**
  String serverListConnecting(String server);

  /// No description provided for @serverListSortBy.
  ///
  /// In en, this message translates to:
  /// **'Sort by'**
  String get serverListSortBy;

  /// No description provided for @serverListSortName.
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get serverListSortName;

  /// No description provided for @serverListSortPing.
  ///
  /// In en, this message translates to:
  /// **'Ping'**
  String get serverListSortPing;

  /// No description provided for @serverListSortLoad.
  ///
  /// In en, this message translates to:
  /// **'Load'**
  String get serverListSortLoad;

  /// No description provided for @notificationSettingsTitle.
  ///
  /// In en, this message translates to:
  /// **'Notification Settings'**
  String get notificationSettingsTitle;

  /// No description provided for @notificationEnablePush.
  ///
  /// In en, this message translates to:
  /// **'Enable Push Notifications'**
  String get notificationEnablePush;

  /// No description provided for @notificationEnablePushDescription.
  ///
  /// In en, this message translates to:
  /// **'Receive important updates about your VPN connection'**
  String get notificationEnablePushDescription;

  /// No description provided for @notificationSoundLabel.
  ///
  /// In en, this message translates to:
  /// **'Notification Sound'**
  String get notificationSoundLabel;

  /// No description provided for @notificationVibrationLabel.
  ///
  /// In en, this message translates to:
  /// **'Vibration'**
  String get notificationVibrationLabel;

  /// No description provided for @notificationQuietHoursLabel.
  ///
  /// In en, this message translates to:
  /// **'Quiet Hours'**
  String get notificationQuietHoursLabel;

  /// No description provided for @notificationQuietHoursDescription.
  ///
  /// In en, this message translates to:
  /// **'Mute notifications during specified hours'**
  String get notificationQuietHoursDescription;

  /// No description provided for @diagnosticsNetworkCheck.
  ///
  /// In en, this message translates to:
  /// **'Network Check'**
  String get diagnosticsNetworkCheck;

  /// No description provided for @diagnosticsDnsCheck.
  ///
  /// In en, this message translates to:
  /// **'DNS Resolution'**
  String get diagnosticsDnsCheck;

  /// No description provided for @diagnosticsLatencyCheck.
  ///
  /// In en, this message translates to:
  /// **'Latency Check'**
  String get diagnosticsLatencyCheck;

  /// No description provided for @diagnosticsFirewallCheck.
  ///
  /// In en, this message translates to:
  /// **'Firewall Check'**
  String get diagnosticsFirewallCheck;

  /// No description provided for @diagnosticsStatusPassed.
  ///
  /// In en, this message translates to:
  /// **'Passed'**
  String get diagnosticsStatusPassed;

  /// No description provided for @diagnosticsStatusFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed'**
  String get diagnosticsStatusFailed;

  /// No description provided for @diagnosticsStatusRunning.
  ///
  /// In en, this message translates to:
  /// **'Running...'**
  String get diagnosticsStatusRunning;

  /// No description provided for @diagnosticsRunAll.
  ///
  /// In en, this message translates to:
  /// **'Run All Checks'**
  String get diagnosticsRunAll;

  /// No description provided for @diagnosticsShareResults.
  ///
  /// In en, this message translates to:
  /// **'Share Results'**
  String get diagnosticsShareResults;

  /// No description provided for @commonSave.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get commonSave;

  /// No description provided for @commonDelete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get commonDelete;

  /// No description provided for @commonEdit.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get commonEdit;

  /// No description provided for @commonClose.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get commonClose;

  /// No description provided for @commonBack.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get commonBack;

  /// No description provided for @commonNext.
  ///
  /// In en, this message translates to:
  /// **'Next'**
  String get commonNext;

  /// No description provided for @commonDone.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get commonDone;

  /// No description provided for @commonSearch.
  ///
  /// In en, this message translates to:
  /// **'Search'**
  String get commonSearch;

  /// No description provided for @commonLoading.
  ///
  /// In en, this message translates to:
  /// **'Loading...'**
  String get commonLoading;

  /// No description provided for @commonNoData.
  ///
  /// In en, this message translates to:
  /// **'No data available'**
  String get commonNoData;

  /// No description provided for @commonRefresh.
  ///
  /// In en, this message translates to:
  /// **'Refresh'**
  String get commonRefresh;

  /// No description provided for @commonCopy.
  ///
  /// In en, this message translates to:
  /// **'Copy'**
  String get commonCopy;

  /// No description provided for @commonCopied.
  ///
  /// In en, this message translates to:
  /// **'Copied to clipboard'**
  String get commonCopied;

  /// No description provided for @commonShare.
  ///
  /// In en, this message translates to:
  /// **'Share'**
  String get commonShare;

  /// No description provided for @commonYes.
  ///
  /// In en, this message translates to:
  /// **'Yes'**
  String get commonYes;

  /// No description provided for @commonNo.
  ///
  /// In en, this message translates to:
  /// **'No'**
  String get commonNo;

  /// No description provided for @commonOk.
  ///
  /// In en, this message translates to:
  /// **'OK'**
  String get commonOk;

  /// No description provided for @commonContinue.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get commonContinue;

  /// No description provided for @commonSkip.
  ///
  /// In en, this message translates to:
  /// **'Skip'**
  String get commonSkip;

  /// No description provided for @commonLearnMore.
  ///
  /// In en, this message translates to:
  /// **'Learn More'**
  String get commonLearnMore;

  /// No description provided for @errorNoConnection.
  ///
  /// In en, this message translates to:
  /// **'No internet connection. Please check your network.'**
  String get errorNoConnection;

  /// No description provided for @errorTimeout.
  ///
  /// In en, this message translates to:
  /// **'Request timed out. Please try again.'**
  String get errorTimeout;

  /// No description provided for @errorGeneric.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong. Please try again.'**
  String get errorGeneric;

  /// No description provided for @errorLoadingData.
  ///
  /// In en, this message translates to:
  /// **'Failed to load data.'**
  String get errorLoadingData;

  /// No description provided for @errorSavingData.
  ///
  /// In en, this message translates to:
  /// **'Failed to save data.'**
  String get errorSavingData;

  /// No description provided for @errorSessionInvalid.
  ///
  /// In en, this message translates to:
  /// **'Your session is invalid. Please log in again.'**
  String get errorSessionInvalid;

  /// No description provided for @a11yShowPassword.
  ///
  /// In en, this message translates to:
  /// **'Show password'**
  String get a11yShowPassword;

  /// No description provided for @a11yHidePassword.
  ///
  /// In en, this message translates to:
  /// **'Hide password'**
  String get a11yHidePassword;

  /// No description provided for @a11yServerPing.
  ///
  /// In en, this message translates to:
  /// **'Server ping: {ping} milliseconds'**
  String a11yServerPing(int ping);

  /// No description provided for @a11yServerLoad.
  ///
  /// In en, this message translates to:
  /// **'Server load: {load} percent'**
  String a11yServerLoad(int load);

  /// No description provided for @a11yFavoriteServer.
  ///
  /// In en, this message translates to:
  /// **'Favorite server'**
  String get a11yFavoriteServer;

  /// No description provided for @a11yRemoveFavorite.
  ///
  /// In en, this message translates to:
  /// **'Remove from favorites'**
  String get a11yRemoveFavorite;

  /// No description provided for @a11ySubscriptionActive.
  ///
  /// In en, this message translates to:
  /// **'Active subscription'**
  String get a11ySubscriptionActive;

  /// No description provided for @a11ySubscriptionExpired.
  ///
  /// In en, this message translates to:
  /// **'Expired subscription'**
  String get a11ySubscriptionExpired;

  /// No description provided for @a11yBiometricLogin.
  ///
  /// In en, this message translates to:
  /// **'Biometric login toggle'**
  String get a11yBiometricLogin;

  /// No description provided for @a11yAppLockToggle.
  ///
  /// In en, this message translates to:
  /// **'App lock toggle'**
  String get a11yAppLockToggle;

  /// No description provided for @a11yProtocolSelect.
  ///
  /// In en, this message translates to:
  /// **'Select VPN protocol'**
  String get a11yProtocolSelect;

  /// No description provided for @a11yThemeSelect.
  ///
  /// In en, this message translates to:
  /// **'Select theme mode'**
  String get a11yThemeSelect;

  /// No description provided for @a11yLanguageSelect.
  ///
  /// In en, this message translates to:
  /// **'Select language'**
  String get a11yLanguageSelect;

  /// No description provided for @a11yNotificationToggle.
  ///
  /// In en, this message translates to:
  /// **'Toggle notification for {type}'**
  String a11yNotificationToggle(String type);

  /// No description provided for @a11ySpeedTestProgress.
  ///
  /// In en, this message translates to:
  /// **'Speed test in progress'**
  String get a11ySpeedTestProgress;

  /// No description provided for @a11yDiagnosticsProgress.
  ///
  /// In en, this message translates to:
  /// **'Diagnostics in progress'**
  String get a11yDiagnosticsProgress;

  /// No description provided for @a11yTrafficUsage.
  ///
  /// In en, this message translates to:
  /// **'Traffic usage: {percent} percent'**
  String a11yTrafficUsage(int percent);

  /// No description provided for @a11yConnectionDuration.
  ///
  /// In en, this message translates to:
  /// **'Connected for {duration}'**
  String a11yConnectionDuration(String duration);

  /// No description provided for @quickSetupTitle.
  ///
  /// In en, this message translates to:
  /// **'Quick Setup'**
  String get quickSetupTitle;

  /// No description provided for @quickSetupWelcome.
  ///
  /// In en, this message translates to:
  /// **'Let\'s get you connected'**
  String get quickSetupWelcome;

  /// No description provided for @quickSetupSelectServer.
  ///
  /// In en, this message translates to:
  /// **'Select a server to get started'**
  String get quickSetupSelectServer;

  /// No description provided for @quickSetupRecommended.
  ///
  /// In en, this message translates to:
  /// **'Recommended for you'**
  String get quickSetupRecommended;

  /// No description provided for @quickSetupConnectButton.
  ///
  /// In en, this message translates to:
  /// **'Connect Now'**
  String get quickSetupConnectButton;

  /// No description provided for @quickSetupSkip.
  ///
  /// In en, this message translates to:
  /// **'Skip for now'**
  String get quickSetupSkip;

  /// No description provided for @quickSetupComplete.
  ///
  /// In en, this message translates to:
  /// **'You\'re all set!'**
  String get quickSetupComplete;

  /// No description provided for @splashLoading.
  ///
  /// In en, this message translates to:
  /// **'Loading...'**
  String get splashLoading;

  /// No description provided for @splashInitializing.
  ///
  /// In en, this message translates to:
  /// **'Initializing...'**
  String get splashInitializing;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) => <String>[
    'ar',
    'cs',
    'da',
    'de',
    'en',
    'es',
    'fa',
    'fr',
    'he',
    'hi',
    'id',
    'it',
    'ja',
    'ko',
    'ms',
    'nl',
    'pl',
    'pt',
    'ro',
    'ru',
    'sv',
    'th',
    'tr',
    'uk',
    'vi',
    'zh',
  ].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when language+script codes are specified.
  switch (locale.languageCode) {
    case 'zh':
      {
        switch (locale.scriptCode) {
          case 'Hant':
            return AppLocalizationsZhHant();
        }
        break;
      }
  }

  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'ar':
      return AppLocalizationsAr();
    case 'cs':
      return AppLocalizationsCs();
    case 'da':
      return AppLocalizationsDa();
    case 'de':
      return AppLocalizationsDe();
    case 'en':
      return AppLocalizationsEn();
    case 'es':
      return AppLocalizationsEs();
    case 'fa':
      return AppLocalizationsFa();
    case 'fr':
      return AppLocalizationsFr();
    case 'he':
      return AppLocalizationsHe();
    case 'hi':
      return AppLocalizationsHi();
    case 'id':
      return AppLocalizationsId();
    case 'it':
      return AppLocalizationsIt();
    case 'ja':
      return AppLocalizationsJa();
    case 'ko':
      return AppLocalizationsKo();
    case 'ms':
      return AppLocalizationsMs();
    case 'nl':
      return AppLocalizationsNl();
    case 'pl':
      return AppLocalizationsPl();
    case 'pt':
      return AppLocalizationsPt();
    case 'ro':
      return AppLocalizationsRo();
    case 'ru':
      return AppLocalizationsRu();
    case 'sv':
      return AppLocalizationsSv();
    case 'th':
      return AppLocalizationsTh();
    case 'tr':
      return AppLocalizationsTr();
    case 'uk':
      return AppLocalizationsUk();
    case 'vi':
      return AppLocalizationsVi();
    case 'zh':
      return AppLocalizationsZh();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
