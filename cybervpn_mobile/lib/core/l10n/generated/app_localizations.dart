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
