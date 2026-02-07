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

  /// No description provided for @onboardingConnectTitle.
  ///
  /// In en, this message translates to:
  /// **'One Tap Connect'**
  String get onboardingConnectTitle;

  /// No description provided for @onboardingConnectDescription.
  ///
  /// In en, this message translates to:
  /// **'Connect to hundreds of servers worldwide with a single tap.'**
  String get onboardingConnectDescription;

  /// No description provided for @onboardingGlobeTitle.
  ///
  /// In en, this message translates to:
  /// **'Global Network'**
  String get onboardingGlobeTitle;

  /// No description provided for @onboardingGlobeDescription.
  ///
  /// In en, this message translates to:
  /// **'Access content from anywhere with our worldwide server network.'**
  String get onboardingGlobeDescription;

  /// No description provided for @onboardingGetStartedTitle.
  ///
  /// In en, this message translates to:
  /// **'Ready to Go'**
  String get onboardingGetStartedTitle;

  /// No description provided for @onboardingGetStartedDescription.
  ///
  /// In en, this message translates to:
  /// **'Your secure connection is just one tap away.'**
  String get onboardingGetStartedDescription;

  /// No description provided for @onboardingNoPages.
  ///
  /// In en, this message translates to:
  /// **'No onboarding pages'**
  String get onboardingNoPages;

  /// No description provided for @permissionSetupTitle.
  ///
  /// In en, this message translates to:
  /// **'Set Up Permissions'**
  String get permissionSetupTitle;

  /// No description provided for @permissionSetupSubtitle.
  ///
  /// In en, this message translates to:
  /// **'CyberVPN needs permission to create a VPN tunnel'**
  String get permissionSetupSubtitle;

  /// No description provided for @permissionVpnTitle.
  ///
  /// In en, this message translates to:
  /// **'VPN Connection'**
  String get permissionVpnTitle;

  /// No description provided for @permissionVpnDescription.
  ///
  /// In en, this message translates to:
  /// **'CyberVPN creates a secure tunnel to protect your data'**
  String get permissionVpnDescription;

  /// No description provided for @permissionGrantButton.
  ///
  /// In en, this message translates to:
  /// **'Grant Permission'**
  String get permissionGrantButton;

  /// No description provided for @permissionContinueAnyway.
  ///
  /// In en, this message translates to:
  /// **'Continue Anyway'**
  String get permissionContinueAnyway;

  /// No description provided for @permissionAllSet.
  ///
  /// In en, this message translates to:
  /// **'All Set!'**
  String get permissionAllSet;

  /// No description provided for @permissionAlmostReady.
  ///
  /// In en, this message translates to:
  /// **'Almost Ready'**
  String get permissionAlmostReady;

  /// No description provided for @permissionEnableLater.
  ///
  /// In en, this message translates to:
  /// **'You can enable these permissions later in Settings if needed'**
  String get permissionEnableLater;

  /// No description provided for @permissionAppReady.
  ///
  /// In en, this message translates to:
  /// **'Your app is configured and ready to use'**
  String get permissionAppReady;

  /// No description provided for @permissionOpenSettings.
  ///
  /// In en, this message translates to:
  /// **'Open Settings'**
  String get permissionOpenSettings;

  /// No description provided for @permissionEnableInSettings.
  ///
  /// In en, this message translates to:
  /// **'Please enable permissions in your device Settings'**
  String get permissionEnableInSettings;

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

  /// No description provided for @configImportPasteLink.
  ///
  /// In en, this message translates to:
  /// **'Paste VPN config link'**
  String get configImportPasteLink;

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

  /// No description provided for @notificationCenterEmptyDescription.
  ///
  /// In en, this message translates to:
  /// **'When you receive notifications, they will appear here.'**
  String get notificationCenterEmptyDescription;

  /// No description provided for @notificationCenterLoadError.
  ///
  /// In en, this message translates to:
  /// **'Failed to load notifications'**
  String get notificationCenterLoadError;

  /// No description provided for @notificationCenterDismissed.
  ///
  /// In en, this message translates to:
  /// **'Notification dismissed'**
  String get notificationCenterDismissed;

  /// No description provided for @notificationTimeJustNow.
  ///
  /// In en, this message translates to:
  /// **'Just now'**
  String get notificationTimeJustNow;

  /// No description provided for @notificationTimeMinutesAgo.
  ///
  /// In en, this message translates to:
  /// **'{count}m ago'**
  String notificationTimeMinutesAgo(int count);

  /// No description provided for @notificationTimeHoursAgo.
  ///
  /// In en, this message translates to:
  /// **'{count}h ago'**
  String notificationTimeHoursAgo(int count);

  /// No description provided for @notificationTimeDaysAgo.
  ///
  /// In en, this message translates to:
  /// **'{count}d ago'**
  String notificationTimeDaysAgo(int count);

  /// No description provided for @notificationTimeWeeksAgo.
  ///
  /// In en, this message translates to:
  /// **'{count}w ago'**
  String notificationTimeWeeksAgo(int count);

  /// No description provided for @notificationTimeMonthsAgo.
  ///
  /// In en, this message translates to:
  /// **'{count}mo ago'**
  String notificationTimeMonthsAgo(int count);

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
  /// **'ALL'**
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

  /// No description provided for @loginSigningIn.
  ///
  /// In en, this message translates to:
  /// **'Signing in, please wait'**
  String get loginSigningIn;

  /// No description provided for @loginHint.
  ///
  /// In en, this message translates to:
  /// **'Sign in to your account'**
  String get loginHint;

  /// No description provided for @loginContinueWithTelegram.
  ///
  /// In en, this message translates to:
  /// **'Continue with Telegram'**
  String get loginContinueWithTelegram;

  /// No description provided for @loginTitle.
  ///
  /// In en, this message translates to:
  /// **'CyberVPN'**
  String get loginTitle;

  /// No description provided for @loginSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Secure your connection'**
  String get loginSubtitle;

  /// No description provided for @loginOrUsePassword.
  ///
  /// In en, this message translates to:
  /// **'OR USE PASSWORD'**
  String get loginOrUsePassword;

  /// No description provided for @loginOrSeparator.
  ///
  /// In en, this message translates to:
  /// **'OR'**
  String get loginOrSeparator;

  /// No description provided for @loginNoAccount.
  ///
  /// In en, this message translates to:
  /// **'Don\'t have an account? '**
  String get loginNoAccount;

  /// No description provided for @loginRegisterLink.
  ///
  /// In en, this message translates to:
  /// **'Register'**
  String get loginRegisterLink;

  /// No description provided for @loginBiometricFaceId.
  ///
  /// In en, this message translates to:
  /// **'Sign in with Face ID'**
  String get loginBiometricFaceId;

  /// No description provided for @loginBiometricFingerprint.
  ///
  /// In en, this message translates to:
  /// **'Sign in with fingerprint'**
  String get loginBiometricFingerprint;

  /// No description provided for @loginBiometricGeneric.
  ///
  /// In en, this message translates to:
  /// **'Sign in with biometrics'**
  String get loginBiometricGeneric;

  /// No description provided for @loginBiometricAuthenticating.
  ///
  /// In en, this message translates to:
  /// **'Authenticating with biometrics, please wait'**
  String get loginBiometricAuthenticating;

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

  /// No description provided for @appLockBiometricFaceId.
  ///
  /// In en, this message translates to:
  /// **'Face ID'**
  String get appLockBiometricFaceId;

  /// No description provided for @appLockBiometricFingerprint.
  ///
  /// In en, this message translates to:
  /// **'fingerprint'**
  String get appLockBiometricFingerprint;

  /// No description provided for @appLockBiometricGeneric.
  ///
  /// In en, this message translates to:
  /// **'biometrics'**
  String get appLockBiometricGeneric;

  /// No description provided for @appLockAuthenticating.
  ///
  /// In en, this message translates to:
  /// **'Authenticating, please wait'**
  String get appLockAuthenticating;

  /// No description provided for @appLockUnlockHint.
  ///
  /// In en, this message translates to:
  /// **'Authenticate to unlock the app'**
  String get appLockUnlockHint;

  /// No description provided for @appLockPinHint.
  ///
  /// In en, this message translates to:
  /// **'Unlock using your device PIN or passcode'**
  String get appLockPinHint;

  /// No description provided for @appLockFailedAttempts.
  ///
  /// In en, this message translates to:
  /// **'Failed attempts: {current}/{max}'**
  String appLockFailedAttempts(int current, int max);

  /// No description provided for @appLockFailedAttemptsA11y.
  ///
  /// In en, this message translates to:
  /// **'Failed authentication attempts: {current} out of {max}'**
  String appLockFailedAttemptsA11y(int current, int max);

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

  /// No description provided for @biometricSignInReason.
  ///
  /// In en, this message translates to:
  /// **'Sign in to CyberVPN'**
  String get biometricSignInReason;

  /// No description provided for @biometricSignInHint.
  ///
  /// In en, this message translates to:
  /// **'Use biometrics to sign in quickly'**
  String get biometricSignInHint;

  /// No description provided for @formEmailLabel.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get formEmailLabel;

  /// No description provided for @formEmailHint.
  ///
  /// In en, this message translates to:
  /// **'Enter your email'**
  String get formEmailHint;

  /// No description provided for @formPasswordLabel.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get formPasswordLabel;

  /// No description provided for @formPasswordHint.
  ///
  /// In en, this message translates to:
  /// **'Enter your password'**
  String get formPasswordHint;

  /// No description provided for @formShowPassword.
  ///
  /// In en, this message translates to:
  /// **'Show password'**
  String get formShowPassword;

  /// No description provided for @formHidePassword.
  ///
  /// In en, this message translates to:
  /// **'Hide password'**
  String get formHidePassword;

  /// No description provided for @registerPasswordStrengthWeak.
  ///
  /// In en, this message translates to:
  /// **'Weak'**
  String get registerPasswordStrengthWeak;

  /// No description provided for @registerPasswordStrengthMedium.
  ///
  /// In en, this message translates to:
  /// **'Medium'**
  String get registerPasswordStrengthMedium;

  /// No description provided for @registerPasswordStrengthStrong.
  ///
  /// In en, this message translates to:
  /// **'Strong'**
  String get registerPasswordStrengthStrong;

  /// No description provided for @registerAcceptTermsA11y.
  ///
  /// In en, this message translates to:
  /// **'Accept Terms and Conditions and Privacy Policy'**
  String get registerAcceptTermsA11y;

  /// No description provided for @registerAcceptTermsA11yHint.
  ///
  /// In en, this message translates to:
  /// **'Required to create account'**
  String get registerAcceptTermsA11yHint;

  /// No description provided for @registerReferralValidA11y.
  ///
  /// In en, this message translates to:
  /// **'Valid referral code'**
  String get registerReferralValidA11y;

  /// No description provided for @registerReferralAppliedA11y.
  ///
  /// In en, this message translates to:
  /// **'Referral code applied successfully'**
  String get registerReferralAppliedA11y;

  /// No description provided for @registerCreatingAccount.
  ///
  /// In en, this message translates to:
  /// **'Creating account, please wait'**
  String get registerCreatingAccount;

  /// No description provided for @registerHint.
  ///
  /// In en, this message translates to:
  /// **'Create your account'**
  String get registerHint;

  /// No description provided for @registerLoginA11y.
  ///
  /// In en, this message translates to:
  /// **'Go to login screen'**
  String get registerLoginA11y;

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

  /// No description provided for @subscriptionDaysRemaining.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 day remaining} other{{count} days remaining}}'**
  String subscriptionDaysRemaining(int count);

  /// No description provided for @subscriptionExpiringSoon.
  ///
  /// In en, this message translates to:
  /// **'Expiring soon'**
  String get subscriptionExpiringSoon;

  /// No description provided for @subscriptionRenewNow.
  ///
  /// In en, this message translates to:
  /// **'Renew Now'**
  String get subscriptionRenewNow;

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
  /// **'No servers match your search'**
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

  /// No description provided for @quickSetupReadyToProtect.
  ///
  /// In en, this message translates to:
  /// **'Ready to protect you'**
  String get quickSetupReadyToProtect;

  /// No description provided for @quickSetupBestServer.
  ///
  /// In en, this message translates to:
  /// **'We\'ve selected the best server for you'**
  String get quickSetupBestServer;

  /// No description provided for @quickSetupFindingServer.
  ///
  /// In en, this message translates to:
  /// **'Finding the best server...'**
  String get quickSetupFindingServer;

  /// No description provided for @quickSetupYoureProtected.
  ///
  /// In en, this message translates to:
  /// **'You\'re protected!'**
  String get quickSetupYoureProtected;

  /// No description provided for @quickSetupConnectionSecure.
  ///
  /// In en, this message translates to:
  /// **'Your connection is now secure'**
  String get quickSetupConnectionSecure;

  /// No description provided for @quickSetupTakeYourTime.
  ///
  /// In en, this message translates to:
  /// **'Take your time - you can connect anytime from the main screen'**
  String get quickSetupTakeYourTime;

  /// No description provided for @quickSetupNoServers.
  ///
  /// In en, this message translates to:
  /// **'No available servers found. Please try again later.'**
  String get quickSetupNoServers;

  /// No description provided for @quickSetupConnectionTimeout.
  ///
  /// In en, this message translates to:
  /// **'Connection timeout. Please try selecting a different server.'**
  String get quickSetupConnectionTimeout;

  /// No description provided for @quickSetupConnectionFailed.
  ///
  /// In en, this message translates to:
  /// **'Connection failed: {error}'**
  String quickSetupConnectionFailed(String error);

  /// No description provided for @quickSetupChooseServer.
  ///
  /// In en, this message translates to:
  /// **'Choose Server'**
  String get quickSetupChooseServer;

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

  /// No description provided for @profileDeviceManagement.
  ///
  /// In en, this message translates to:
  /// **'Device Management'**
  String get profileDeviceManagement;

  /// No description provided for @profileDevicesConnected.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 device connected} other{{count} devices connected}}'**
  String profileDevicesConnected(int count);

  /// No description provided for @profileDeviceLimitReached.
  ///
  /// In en, this message translates to:
  /// **'Device limit reached. Remove a device to add new ones.'**
  String get profileDeviceLimitReached;

  /// No description provided for @profileRemoveDevice.
  ///
  /// In en, this message translates to:
  /// **'Remove Device'**
  String get profileRemoveDevice;

  /// No description provided for @profileRemoveDeviceConfirm.
  ///
  /// In en, this message translates to:
  /// **'Remove {deviceName}?\n\nYou\'ll need to log in again on this device if you want to use it later.'**
  String profileRemoveDeviceConfirm(String deviceName);

  /// No description provided for @profileRemoveDeviceConfirmShort.
  ///
  /// In en, this message translates to:
  /// **'Remove {deviceName}?\n\nYou\'ll need to log in again on this device.'**
  String profileRemoveDeviceConfirmShort(String deviceName);

  /// No description provided for @profileRemovingDevice.
  ///
  /// In en, this message translates to:
  /// **'Removing device...'**
  String get profileRemovingDevice;

  /// No description provided for @profileDeviceRemovedSuccess.
  ///
  /// In en, this message translates to:
  /// **'{deviceName} removed successfully'**
  String profileDeviceRemovedSuccess(String deviceName);

  /// No description provided for @profileRemoveDeviceFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed to remove device: {error}'**
  String profileRemoveDeviceFailed(String error);

  /// No description provided for @profileThisDevice.
  ///
  /// In en, this message translates to:
  /// **'This device'**
  String get profileThisDevice;

  /// No description provided for @profileRemoveDeviceTooltip.
  ///
  /// In en, this message translates to:
  /// **'Remove device'**
  String get profileRemoveDeviceTooltip;

  /// No description provided for @profileNoDevicesConnected.
  ///
  /// In en, this message translates to:
  /// **'No devices connected'**
  String get profileNoDevicesConnected;

  /// No description provided for @profileConnectToRegister.
  ///
  /// In en, this message translates to:
  /// **'Connect to VPN to register this device'**
  String get profileConnectToRegister;

  /// No description provided for @profileDeviceLastActiveNever.
  ///
  /// In en, this message translates to:
  /// **'Never'**
  String get profileDeviceLastActiveNever;

  /// No description provided for @profileDeviceLastActiveJustNow.
  ///
  /// In en, this message translates to:
  /// **'Just now'**
  String get profileDeviceLastActiveJustNow;

  /// No description provided for @profileDeviceLastActiveMinutes.
  ///
  /// In en, this message translates to:
  /// **'{count}m ago'**
  String profileDeviceLastActiveMinutes(int count);

  /// No description provided for @profileDeviceLastActiveHours.
  ///
  /// In en, this message translates to:
  /// **'{count}h ago'**
  String profileDeviceLastActiveHours(int count);

  /// No description provided for @profileDeviceLastActiveDays.
  ///
  /// In en, this message translates to:
  /// **'{count}d ago'**
  String profileDeviceLastActiveDays(int count);

  /// No description provided for @profileRemoveButton.
  ///
  /// In en, this message translates to:
  /// **'Remove'**
  String get profileRemoveButton;

  /// No description provided for @profileTwoFactorEnabled.
  ///
  /// In en, this message translates to:
  /// **'2FA Enabled'**
  String get profileTwoFactorEnabled;

  /// No description provided for @profileTwoFactorDisabledStatus.
  ///
  /// In en, this message translates to:
  /// **'2FA Disabled'**
  String get profileTwoFactorDisabledStatus;

  /// No description provided for @profileTwoFactorProtected.
  ///
  /// In en, this message translates to:
  /// **'Your account is protected with two-factor authentication'**
  String get profileTwoFactorProtected;

  /// No description provided for @profileTwoFactorEnablePrompt.
  ///
  /// In en, this message translates to:
  /// **'Enable 2FA to secure your account'**
  String get profileTwoFactorEnablePrompt;

  /// No description provided for @profileTwoFactorWhatIs.
  ///
  /// In en, this message translates to:
  /// **'What is Two-Factor Authentication?'**
  String get profileTwoFactorWhatIs;

  /// No description provided for @profileTwoFactorFullDescription.
  ///
  /// In en, this message translates to:
  /// **'Two-factor authentication (2FA) adds an extra layer of security to your account. You\'ll need both your password and a code from your authenticator app to sign in.'**
  String get profileTwoFactorFullDescription;

  /// No description provided for @profileTwoFactorEnhancedSecurity.
  ///
  /// In en, this message translates to:
  /// **'Enhanced Security'**
  String get profileTwoFactorEnhancedSecurity;

  /// No description provided for @profileTwoFactorEnhancedSecurityDesc.
  ///
  /// In en, this message translates to:
  /// **'Protects your account from unauthorized access'**
  String get profileTwoFactorEnhancedSecurityDesc;

  /// No description provided for @profileTwoFactorAuthenticatorApp.
  ///
  /// In en, this message translates to:
  /// **'Authenticator App'**
  String get profileTwoFactorAuthenticatorApp;

  /// No description provided for @profileTwoFactorAuthenticatorAppDesc.
  ///
  /// In en, this message translates to:
  /// **'Use any TOTP app like Google Authenticator or Authy'**
  String get profileTwoFactorAuthenticatorAppDesc;

  /// No description provided for @profileTwoFactorBackupCodesDesc.
  ///
  /// In en, this message translates to:
  /// **'Receive backup codes for account recovery'**
  String get profileTwoFactorBackupCodesDesc;

  /// No description provided for @profileTwoFactorStep1.
  ///
  /// In en, this message translates to:
  /// **'Step 1: Scan QR Code'**
  String get profileTwoFactorStep1;

  /// No description provided for @profileTwoFactorStep2.
  ///
  /// In en, this message translates to:
  /// **'Step 2: Verify Code'**
  String get profileTwoFactorStep2;

  /// No description provided for @profileTwoFactorScanQrShort.
  ///
  /// In en, this message translates to:
  /// **'Scan this QR code with your authenticator app'**
  String get profileTwoFactorScanQrShort;

  /// No description provided for @profileTwoFactorEnterManually.
  ///
  /// In en, this message translates to:
  /// **'Enter manually'**
  String get profileTwoFactorEnterManually;

  /// No description provided for @profileTwoFactorSecretKey.
  ///
  /// In en, this message translates to:
  /// **'Secret Key:'**
  String get profileTwoFactorSecretKey;

  /// No description provided for @profileTwoFactorEnterCodeShort.
  ///
  /// In en, this message translates to:
  /// **'Enter the 6-digit code from your authenticator app'**
  String get profileTwoFactorEnterCodeShort;

  /// No description provided for @profileTwoFactorCodeLabel.
  ///
  /// In en, this message translates to:
  /// **'6-digit code'**
  String get profileTwoFactorCodeLabel;

  /// No description provided for @profileTwoFactorVerifyAndEnable.
  ///
  /// In en, this message translates to:
  /// **'Verify and Enable'**
  String get profileTwoFactorVerifyAndEnable;

  /// No description provided for @profileTwoFactorActive.
  ///
  /// In en, this message translates to:
  /// **'Two-Factor Authentication is Active'**
  String get profileTwoFactorActive;

  /// No description provided for @profileTwoFactorActiveDesc.
  ///
  /// In en, this message translates to:
  /// **'Your account is protected with two-factor authentication. You\'ll need to enter a code from your authenticator app every time you sign in.'**
  String get profileTwoFactorActiveDesc;

  /// No description provided for @profileTwoFactorViewBackupCodes.
  ///
  /// In en, this message translates to:
  /// **'View Backup Codes'**
  String get profileTwoFactorViewBackupCodes;

  /// No description provided for @profileTwoFactorCopyAll.
  ///
  /// In en, this message translates to:
  /// **'Copy All'**
  String get profileTwoFactorCopyAll;

  /// No description provided for @profileTwoFactorBackupCodesInstructions.
  ///
  /// In en, this message translates to:
  /// **'Save these backup codes in a safe place. Each code can only be used once to sign in if you lose access to your authenticator app.'**
  String get profileTwoFactorBackupCodesInstructions;

  /// No description provided for @profileTwoFactorDisableConfirmTitle.
  ///
  /// In en, this message translates to:
  /// **'Disable Two-Factor Authentication?'**
  String get profileTwoFactorDisableConfirmTitle;

  /// No description provided for @profileTwoFactorDisableWarning.
  ///
  /// In en, this message translates to:
  /// **'Disabling 2FA will make your account less secure. You\'ll only need your password to sign in.'**
  String get profileTwoFactorDisableWarning;

  /// No description provided for @profileTwoFactorDisableButton.
  ///
  /// In en, this message translates to:
  /// **'Disable'**
  String get profileTwoFactorDisableButton;

  /// No description provided for @profileTwoFactorEnterVerificationCode.
  ///
  /// In en, this message translates to:
  /// **'Enter Verification Code'**
  String get profileTwoFactorEnterVerificationCode;

  /// No description provided for @profileTwoFactorFailedSetupData.
  ///
  /// In en, this message translates to:
  /// **'Failed to load setup data'**
  String get profileTwoFactorFailedSetupData;

  /// No description provided for @profileSocialAccounts.
  ///
  /// In en, this message translates to:
  /// **'Social Accounts'**
  String get profileSocialAccounts;

  /// No description provided for @profileSocialAccountsDescription.
  ///
  /// In en, this message translates to:
  /// **'Link your social accounts for easier sign-in and account recovery.'**
  String get profileSocialAccountsDescription;

  /// No description provided for @profileSocialLinked.
  ///
  /// In en, this message translates to:
  /// **'Linked'**
  String get profileSocialLinked;

  /// No description provided for @profileSocialNotLinked.
  ///
  /// In en, this message translates to:
  /// **'Not Linked'**
  String get profileSocialNotLinked;

  /// No description provided for @profileSocialLink.
  ///
  /// In en, this message translates to:
  /// **'Link'**
  String get profileSocialLink;

  /// No description provided for @profileSocialCompleteAuth.
  ///
  /// In en, this message translates to:
  /// **'Complete authorization in your browser, then return to the app.'**
  String get profileSocialCompleteAuth;

  /// No description provided for @profileSocialUnlinkConfirm.
  ///
  /// In en, this message translates to:
  /// **'Unlink {provider}?'**
  String profileSocialUnlinkConfirm(String provider);

  /// No description provided for @profileSocialUnlinkDescription.
  ///
  /// In en, this message translates to:
  /// **'You will need to re-authorize to link this account again. This will not delete your {provider} account.'**
  String profileSocialUnlinkDescription(String provider);

  /// No description provided for @profileGreetingMorning.
  ///
  /// In en, this message translates to:
  /// **'Good morning'**
  String get profileGreetingMorning;

  /// No description provided for @profileGreetingAfternoon.
  ///
  /// In en, this message translates to:
  /// **'Good afternoon'**
  String get profileGreetingAfternoon;

  /// No description provided for @profileGreetingEvening.
  ///
  /// In en, this message translates to:
  /// **'Good evening'**
  String get profileGreetingEvening;

  /// No description provided for @profileNoProfileData.
  ///
  /// In en, this message translates to:
  /// **'No profile data available.'**
  String get profileNoProfileData;

  /// No description provided for @profileQuickActions.
  ///
  /// In en, this message translates to:
  /// **'Quick Actions'**
  String get profileQuickActions;

  /// No description provided for @profileInviteFriends.
  ///
  /// In en, this message translates to:
  /// **'Invite Friends'**
  String get profileInviteFriends;

  /// No description provided for @profileSecuritySettings.
  ///
  /// In en, this message translates to:
  /// **'Security Settings'**
  String get profileSecuritySettings;

  /// No description provided for @profileStatsTraffic.
  ///
  /// In en, this message translates to:
  /// **'Traffic'**
  String get profileStatsTraffic;

  /// No description provided for @profileStatsUnlimited.
  ///
  /// In en, this message translates to:
  /// **'Unlimited'**
  String get profileStatsUnlimited;

  /// No description provided for @profileStatsDaysLeft.
  ///
  /// In en, this message translates to:
  /// **'Days Left'**
  String get profileStatsDaysLeft;

  /// No description provided for @profileStatsDevices.
  ///
  /// In en, this message translates to:
  /// **'Devices'**
  String get profileStatsDevices;

  /// No description provided for @profileStatsNoPlan.
  ///
  /// In en, this message translates to:
  /// **'No Plan'**
  String get profileStatsNoPlan;

  /// No description provided for @profileSubActive.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get profileSubActive;

  /// No description provided for @profileSubTrial.
  ///
  /// In en, this message translates to:
  /// **'Trial'**
  String get profileSubTrial;

  /// No description provided for @profileSubExpired.
  ///
  /// In en, this message translates to:
  /// **'Expired'**
  String get profileSubExpired;

  /// No description provided for @profileSubCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get profileSubCancelled;

  /// No description provided for @profileSubPending.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get profileSubPending;

  /// No description provided for @profileDeleteDangerZoneDesc.
  ///
  /// In en, this message translates to:
  /// **'This action cannot be undone'**
  String get profileDeleteDangerZoneDesc;

  /// No description provided for @profileDeleteWhatWillBeDeleted.
  ///
  /// In en, this message translates to:
  /// **'What will be deleted?'**
  String get profileDeleteWhatWillBeDeleted;

  /// No description provided for @profileDeletePermanentlyDeleted.
  ///
  /// In en, this message translates to:
  /// **'The following data will be permanently deleted:'**
  String get profileDeletePermanentlyDeleted;

  /// No description provided for @profileDeletePersonalInfo.
  ///
  /// In en, this message translates to:
  /// **'Personal Information'**
  String get profileDeletePersonalInfo;

  /// No description provided for @profileDeletePersonalInfoDesc.
  ///
  /// In en, this message translates to:
  /// **'Email, username, and profile data'**
  String get profileDeletePersonalInfoDesc;

  /// No description provided for @profileDeleteSubscriptionHistory.
  ///
  /// In en, this message translates to:
  /// **'Subscription & Payment History'**
  String get profileDeleteSubscriptionHistory;

  /// No description provided for @profileDeleteSubscriptionHistoryDesc.
  ///
  /// In en, this message translates to:
  /// **'All active subscriptions and transaction records'**
  String get profileDeleteSubscriptionHistoryDesc;

  /// No description provided for @profileDeleteVpnConfigs.
  ///
  /// In en, this message translates to:
  /// **'VPN Configurations'**
  String get profileDeleteVpnConfigs;

  /// No description provided for @profileDeleteVpnConfigsDesc.
  ///
  /// In en, this message translates to:
  /// **'Server settings and connection preferences'**
  String get profileDeleteVpnConfigsDesc;

  /// No description provided for @profileDeleteAppSettings.
  ///
  /// In en, this message translates to:
  /// **'App Settings'**
  String get profileDeleteAppSettings;

  /// No description provided for @profileDeleteAppSettingsDesc.
  ///
  /// In en, this message translates to:
  /// **'All preferences and customizations'**
  String get profileDeleteAppSettingsDesc;

  /// No description provided for @profileDeleteGracePeriod.
  ///
  /// In en, this message translates to:
  /// **'30-Day Grace Period'**
  String get profileDeleteGracePeriod;

  /// No description provided for @profileDeleteGracePeriodDesc.
  ///
  /// In en, this message translates to:
  /// **'Your account will be scheduled for deletion. You can cancel this request within 30 days by logging back in. After this period, all data will be permanently deleted.'**
  String get profileDeleteGracePeriodDesc;

  /// No description provided for @profileDeleteStorePolicy.
  ///
  /// In en, this message translates to:
  /// **'In compliance with App Store and Google Play data deletion policies, all personal data will be permanently removed from our servers.'**
  String get profileDeleteStorePolicy;

  /// No description provided for @profileDeleteContinue.
  ///
  /// In en, this message translates to:
  /// **'Continue with Deletion'**
  String get profileDeleteContinue;

  /// No description provided for @profileDeleteVerifyIdentity.
  ///
  /// In en, this message translates to:
  /// **'Verify Your Identity'**
  String get profileDeleteVerifyIdentity;

  /// No description provided for @profileDeleteVerifyIdentityDesc.
  ///
  /// In en, this message translates to:
  /// **'For security reasons, please re-enter your credentials to confirm account deletion.'**
  String get profileDeleteVerifyIdentityDesc;

  /// No description provided for @profileDeletePasswordLabel.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get profileDeletePasswordLabel;

  /// No description provided for @profileDeletePasswordHint.
  ///
  /// In en, this message translates to:
  /// **'Enter your password'**
  String get profileDeletePasswordHint;

  /// No description provided for @profileDeleteVerifyAndContinue.
  ///
  /// In en, this message translates to:
  /// **'Verify and Continue'**
  String get profileDeleteVerifyAndContinue;

  /// No description provided for @profileDeleteFinalConfirmation.
  ///
  /// In en, this message translates to:
  /// **'Final Confirmation'**
  String get profileDeleteFinalConfirmation;

  /// No description provided for @profileDeleteFinalConfirmationDesc.
  ///
  /// In en, this message translates to:
  /// **'This is your last chance to cancel. Once confirmed, your account will be scheduled for permanent deletion.'**
  String get profileDeleteFinalConfirmationDesc;

  /// No description provided for @profileDeleteIrreversible.
  ///
  /// In en, this message translates to:
  /// **'This action is irreversible'**
  String get profileDeleteIrreversible;

  /// No description provided for @profileDeleteIrreversibleList.
  ///
  /// In en, this message translates to:
  /// **'• All data will be permanently deleted after 30 days\n• Active subscriptions will be cancelled\n• You will be immediately logged out\n• This cannot be undone'**
  String get profileDeleteIrreversibleList;

  /// No description provided for @profileDeleteScheduledSuccess.
  ///
  /// In en, this message translates to:
  /// **'Account deletion scheduled successfully'**
  String get profileDeleteScheduledSuccess;

  /// No description provided for @settingsVpnProtocolPreference.
  ///
  /// In en, this message translates to:
  /// **'Protocol Preference'**
  String get settingsVpnProtocolPreference;

  /// No description provided for @settingsAutoConnectOnLaunchLabel.
  ///
  /// In en, this message translates to:
  /// **'Auto-connect on launch'**
  String get settingsAutoConnectOnLaunchLabel;

  /// No description provided for @settingsAutoConnectOnLaunchDescription.
  ///
  /// In en, this message translates to:
  /// **'Connect to VPN when the app starts'**
  String get settingsAutoConnectOnLaunchDescription;

  /// No description provided for @settingsAutoConnectUntrustedWifiLabel.
  ///
  /// In en, this message translates to:
  /// **'Auto-connect on untrusted WiFi'**
  String get settingsAutoConnectUntrustedWifiLabel;

  /// No description provided for @settingsAutoConnectUntrustedWifiDescription.
  ///
  /// In en, this message translates to:
  /// **'Automatically connect when joining open networks'**
  String get settingsAutoConnectUntrustedWifiDescription;

  /// No description provided for @settingsManageTrustedNetworks.
  ///
  /// In en, this message translates to:
  /// **'Manage trusted networks'**
  String get settingsManageTrustedNetworks;

  /// No description provided for @settingsNoTrustedNetworks.
  ///
  /// In en, this message translates to:
  /// **'No networks marked as trusted'**
  String get settingsNoTrustedNetworks;

  /// No description provided for @settingsTrustedNetworkCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 trusted network} other{{count} trusted networks}}'**
  String settingsTrustedNetworkCount(int count);

  /// No description provided for @settingsSecuritySection.
  ///
  /// In en, this message translates to:
  /// **'Security'**
  String get settingsSecuritySection;

  /// No description provided for @settingsKillSwitchSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Block traffic if VPN disconnects unexpectedly'**
  String get settingsKillSwitchSubtitle;

  /// No description provided for @settingsKillSwitchDialogTitle.
  ///
  /// In en, this message translates to:
  /// **'Enable Kill Switch?'**
  String get settingsKillSwitchDialogTitle;

  /// No description provided for @settingsKillSwitchDialogContent.
  ///
  /// In en, this message translates to:
  /// **'When enabled, all internet traffic will be blocked if the VPN connection drops unexpectedly. This protects your privacy but may temporarily prevent internet access.'**
  String get settingsKillSwitchDialogContent;

  /// No description provided for @settingsKillSwitchDialogEnable.
  ///
  /// In en, this message translates to:
  /// **'Enable'**
  String get settingsKillSwitchDialogEnable;

  /// No description provided for @settingsDnsProviderSection.
  ///
  /// In en, this message translates to:
  /// **'DNS Provider'**
  String get settingsDnsProviderSection;

  /// No description provided for @settingsDnsCustomAddressLabel.
  ///
  /// In en, this message translates to:
  /// **'Custom DNS address'**
  String get settingsDnsCustomAddressLabel;

  /// No description provided for @settingsDnsCustomAddressHint.
  ///
  /// In en, this message translates to:
  /// **'e.g. 1.0.0.1'**
  String get settingsDnsCustomAddressHint;

  /// No description provided for @settingsAdvancedSection.
  ///
  /// In en, this message translates to:
  /// **'Advanced'**
  String get settingsAdvancedSection;

  /// No description provided for @settingsSplitTunnelingSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Choose which apps use the VPN'**
  String get settingsSplitTunnelingSubtitle;

  /// No description provided for @settingsMtuAutoLabel.
  ///
  /// In en, this message translates to:
  /// **'MTU: Auto'**
  String get settingsMtuAutoLabel;

  /// No description provided for @settingsMtuAutoDescription.
  ///
  /// In en, this message translates to:
  /// **'Automatically determine optimal packet size'**
  String get settingsMtuAutoDescription;

  /// No description provided for @settingsMtuManualLabel.
  ///
  /// In en, this message translates to:
  /// **'MTU: Manual'**
  String get settingsMtuManualLabel;

  /// No description provided for @settingsMtuManualDescription.
  ///
  /// In en, this message translates to:
  /// **'Set a custom MTU value'**
  String get settingsMtuManualDescription;

  /// No description provided for @settingsMtuValueLabel.
  ///
  /// In en, this message translates to:
  /// **'MTU value'**
  String get settingsMtuValueLabel;

  /// No description provided for @settingsMtuValueHint.
  ///
  /// In en, this message translates to:
  /// **'1280-1500'**
  String get settingsMtuValueHint;

  /// No description provided for @settingsChangesApplyOnNextConnection.
  ///
  /// In en, this message translates to:
  /// **'Changes apply on next connection'**
  String get settingsChangesApplyOnNextConnection;

  /// No description provided for @settingsLoadError.
  ///
  /// In en, this message translates to:
  /// **'Failed to load settings'**
  String get settingsLoadError;

  /// No description provided for @settingsNotificationCountEnabled.
  ///
  /// In en, this message translates to:
  /// **'{count} of 4 enabled'**
  String settingsNotificationCountEnabled(int count);

  /// No description provided for @settingsAccountSecurity.
  ///
  /// In en, this message translates to:
  /// **'Account & Security'**
  String get settingsAccountSecurity;

  /// No description provided for @settingsAccountSecuritySubtitle.
  ///
  /// In en, this message translates to:
  /// **'Profile, password, 2FA'**
  String get settingsAccountSecuritySubtitle;

  /// No description provided for @settingsVersionLabel.
  ///
  /// In en, this message translates to:
  /// **'Version'**
  String get settingsVersionLabel;

  /// No description provided for @settingsOpenSourceLicenses.
  ///
  /// In en, this message translates to:
  /// **'Open-source licenses'**
  String get settingsOpenSourceLicenses;

  /// No description provided for @settingsDebugDiagnostics.
  ///
  /// In en, this message translates to:
  /// **'Debug & Diagnostics'**
  String get settingsDebugDiagnostics;

  /// No description provided for @settingsDebugAbout.
  ///
  /// In en, this message translates to:
  /// **'Debug & About'**
  String get settingsDebugAbout;

  /// No description provided for @settingsDebugAboutSubtitle.
  ///
  /// In en, this message translates to:
  /// **'App version, logs, developer options'**
  String get settingsDebugAboutSubtitle;

  /// No description provided for @settingsCouldNotOpenUrl.
  ///
  /// In en, this message translates to:
  /// **'Could not open URL'**
  String get settingsCouldNotOpenUrl;

  /// No description provided for @settingsDiagnosticsSection.
  ///
  /// In en, this message translates to:
  /// **'Diagnostics'**
  String get settingsDiagnosticsSection;

  /// No description provided for @settingsLogEntryCount.
  ///
  /// In en, this message translates to:
  /// **'{count} entries'**
  String settingsLogEntryCount(int count);

  /// No description provided for @settingsCacheDataSection.
  ///
  /// In en, this message translates to:
  /// **'Cache & Data'**
  String get settingsCacheDataSection;

  /// No description provided for @settingsClearCacheLabel.
  ///
  /// In en, this message translates to:
  /// **'Clear Cache'**
  String get settingsClearCacheLabel;

  /// No description provided for @settingsClearCacheDescription.
  ///
  /// In en, this message translates to:
  /// **'Remove cached server lists and configs'**
  String get settingsClearCacheDescription;

  /// No description provided for @settingsResetSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Restore defaults'**
  String get settingsResetSubtitle;

  /// No description provided for @settingsAppVersionLabel.
  ///
  /// In en, this message translates to:
  /// **'App Version'**
  String get settingsAppVersionLabel;

  /// No description provided for @settingsXrayCoreVersionLabel.
  ///
  /// In en, this message translates to:
  /// **'Xray-core Version'**
  String get settingsXrayCoreVersionLabel;

  /// No description provided for @settingsDeveloperOptions.
  ///
  /// In en, this message translates to:
  /// **'Developer Options'**
  String get settingsDeveloperOptions;

  /// No description provided for @settingsDeveloperRawConfig.
  ///
  /// In en, this message translates to:
  /// **'Raw VPN Config Viewer'**
  String get settingsDeveloperRawConfig;

  /// No description provided for @settingsDeveloperRawConfigSubtitle.
  ///
  /// In en, this message translates to:
  /// **'View current Xray configuration'**
  String get settingsDeveloperRawConfigSubtitle;

  /// No description provided for @settingsDeveloperForceCrash.
  ///
  /// In en, this message translates to:
  /// **'Force Crash (Sentry Test)'**
  String get settingsDeveloperForceCrash;

  /// No description provided for @settingsDeveloperForceCrashSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Test error reporting'**
  String get settingsDeveloperForceCrashSubtitle;

  /// No description provided for @settingsDeveloperExperimental.
  ///
  /// In en, this message translates to:
  /// **'Experimental Features'**
  String get settingsDeveloperExperimental;

  /// No description provided for @settingsDeveloperExperimentalSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Enable unreleased features'**
  String get settingsDeveloperExperimentalSubtitle;

  /// No description provided for @settingsLogLevelLabel.
  ///
  /// In en, this message translates to:
  /// **'Log Level'**
  String get settingsLogLevelLabel;

  /// No description provided for @settingsLogLevelDebug.
  ///
  /// In en, this message translates to:
  /// **'Debug'**
  String get settingsLogLevelDebug;

  /// No description provided for @settingsLogLevelInfo.
  ///
  /// In en, this message translates to:
  /// **'Info'**
  String get settingsLogLevelInfo;

  /// No description provided for @settingsLogLevelWarning.
  ///
  /// In en, this message translates to:
  /// **'Warning'**
  String get settingsLogLevelWarning;

  /// No description provided for @settingsLogLevelError.
  ///
  /// In en, this message translates to:
  /// **'Error'**
  String get settingsLogLevelError;

  /// No description provided for @settingsLogLevelDebugDescription.
  ///
  /// In en, this message translates to:
  /// **'Detailed diagnostic information'**
  String get settingsLogLevelDebugDescription;

  /// No description provided for @settingsLogLevelInfoDescription.
  ///
  /// In en, this message translates to:
  /// **'General informational messages'**
  String get settingsLogLevelInfoDescription;

  /// No description provided for @settingsLogLevelWarningDescription.
  ///
  /// In en, this message translates to:
  /// **'Potential issues'**
  String get settingsLogLevelWarningDescription;

  /// No description provided for @settingsLogLevelErrorDescription.
  ///
  /// In en, this message translates to:
  /// **'Errors only'**
  String get settingsLogLevelErrorDescription;

  /// No description provided for @settingsNoLogsToExport.
  ///
  /// In en, this message translates to:
  /// **'No logs to export'**
  String get settingsNoLogsToExport;

  /// No description provided for @settingsClearCacheDialogTitle.
  ///
  /// In en, this message translates to:
  /// **'Clear Cache?'**
  String get settingsClearCacheDialogTitle;

  /// No description provided for @settingsClearCacheDialogContent.
  ///
  /// In en, this message translates to:
  /// **'This will remove cached server lists and VPN configurations. Your settings will not be affected.'**
  String get settingsClearCacheDialogContent;

  /// No description provided for @settingsClearCacheDialogConfirm.
  ///
  /// In en, this message translates to:
  /// **'Clear'**
  String get settingsClearCacheDialogConfirm;

  /// No description provided for @settingsCacheClearedSuccess.
  ///
  /// In en, this message translates to:
  /// **'Cache cleared successfully'**
  String get settingsCacheClearedSuccess;

  /// No description provided for @settingsResetDialogTitle.
  ///
  /// In en, this message translates to:
  /// **'Reset All Settings?'**
  String get settingsResetDialogTitle;

  /// No description provided for @settingsResetDialogContent.
  ///
  /// In en, this message translates to:
  /// **'This will restore all settings to their default values. This action cannot be undone.'**
  String get settingsResetDialogContent;

  /// No description provided for @settingsResetDialogConfirm.
  ///
  /// In en, this message translates to:
  /// **'Reset'**
  String get settingsResetDialogConfirm;

  /// No description provided for @settingsResetSuccess.
  ///
  /// In en, this message translates to:
  /// **'Settings reset successfully'**
  String get settingsResetSuccess;

  /// No description provided for @settingsDeveloperModeActivated.
  ///
  /// In en, this message translates to:
  /// **'Developer mode activated'**
  String get settingsDeveloperModeActivated;

  /// No description provided for @settingsDeveloperRawConfigDialogTitle.
  ///
  /// In en, this message translates to:
  /// **'Raw VPN Config'**
  String get settingsDeveloperRawConfigDialogTitle;

  /// No description provided for @settingsDeveloperForceCrashDialogTitle.
  ///
  /// In en, this message translates to:
  /// **'Force Crash'**
  String get settingsDeveloperForceCrashDialogTitle;

  /// No description provided for @settingsDeveloperForceCrashDialogContent.
  ///
  /// In en, this message translates to:
  /// **'This will intentionally crash the app to test error reporting via Sentry. Only use this for debugging purposes.\n\nAre you sure you want to continue?'**
  String get settingsDeveloperForceCrashDialogContent;

  /// No description provided for @settingsDeveloperCrashNow.
  ///
  /// In en, this message translates to:
  /// **'Crash Now'**
  String get settingsDeveloperCrashNow;

  /// No description provided for @settingsNoLanguagesFound.
  ///
  /// In en, this message translates to:
  /// **'No languages found'**
  String get settingsNoLanguagesFound;

  /// No description provided for @settingsTrustedNetworksTitle.
  ///
  /// In en, this message translates to:
  /// **'Trusted Networks'**
  String get settingsTrustedNetworksTitle;

  /// No description provided for @settingsTrustedAddManually.
  ///
  /// In en, this message translates to:
  /// **'Add network manually'**
  String get settingsTrustedAddManually;

  /// No description provided for @settingsTrustedAddCurrentWifi.
  ///
  /// In en, this message translates to:
  /// **'Add Current WiFi Network'**
  String get settingsTrustedAddCurrentWifi;

  /// No description provided for @settingsTrustedDetectingNetwork.
  ///
  /// In en, this message translates to:
  /// **'Detecting network...'**
  String get settingsTrustedDetectingNetwork;

  /// No description provided for @settingsTrustedInfoDescription.
  ///
  /// In en, this message translates to:
  /// **'Trusted networks won\'t trigger auto-connect. Add your home or work WiFi networks here.'**
  String get settingsTrustedInfoDescription;

  /// No description provided for @settingsTrustedEmptyTitle.
  ///
  /// In en, this message translates to:
  /// **'No trusted networks'**
  String get settingsTrustedEmptyTitle;

  /// No description provided for @settingsTrustedEmptyDescription.
  ///
  /// In en, this message translates to:
  /// **'Add networks you trust, like your home WiFi, to prevent auto-connecting when on these networks.'**
  String get settingsTrustedEmptyDescription;

  /// No description provided for @settingsTrustedNetworkSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Trusted network'**
  String get settingsTrustedNetworkSubtitle;

  /// No description provided for @settingsTrustedRemoveTooltip.
  ///
  /// In en, this message translates to:
  /// **'Remove from trusted'**
  String get settingsTrustedRemoveTooltip;

  /// No description provided for @settingsTrustedAddDialogTitle.
  ///
  /// In en, this message translates to:
  /// **'Add Trusted Network'**
  String get settingsTrustedAddDialogTitle;

  /// No description provided for @settingsTrustedSsidLabel.
  ///
  /// In en, this message translates to:
  /// **'Network name (SSID)'**
  String get settingsTrustedSsidLabel;

  /// No description provided for @settingsTrustedSsidHint.
  ///
  /// In en, this message translates to:
  /// **'e.g. My Home WiFi'**
  String get settingsTrustedSsidHint;

  /// No description provided for @settingsTrustedAddButton.
  ///
  /// In en, this message translates to:
  /// **'Add'**
  String get settingsTrustedAddButton;

  /// No description provided for @settingsTrustedRemoveDialogTitle.
  ///
  /// In en, this message translates to:
  /// **'Remove Network?'**
  String get settingsTrustedRemoveDialogTitle;

  /// No description provided for @settingsTrustedRemoveDialogContent.
  ///
  /// In en, this message translates to:
  /// **'Remove \"{ssid}\" from trusted networks?'**
  String settingsTrustedRemoveDialogContent(String ssid);

  /// No description provided for @settingsTrustedRemoveButton.
  ///
  /// In en, this message translates to:
  /// **'Remove'**
  String get settingsTrustedRemoveButton;

  /// No description provided for @settingsTrustedNotConnected.
  ///
  /// In en, this message translates to:
  /// **'Not connected to WiFi or SSID unavailable'**
  String get settingsTrustedNotConnected;

  /// No description provided for @settingsTrustedAddedNetwork.
  ///
  /// In en, this message translates to:
  /// **'Added \"{ssid}\" to trusted networks'**
  String settingsTrustedAddedNetwork(String ssid);

  /// No description provided for @settingsTrustedPermissionTitle.
  ///
  /// In en, this message translates to:
  /// **'Permission Required'**
  String get settingsTrustedPermissionTitle;

  /// No description provided for @settingsTrustedPermissionPermanent.
  ///
  /// In en, this message translates to:
  /// **'Location permission is required to detect WiFi networks. Please enable it in your device settings.'**
  String get settingsTrustedPermissionPermanent;

  /// No description provided for @settingsTrustedPermissionRequired.
  ///
  /// In en, this message translates to:
  /// **'Location permission is required to detect WiFi network names. This is a platform requirement for privacy reasons.'**
  String get settingsTrustedPermissionRequired;

  /// No description provided for @settingsTrustedOpenSettings.
  ///
  /// In en, this message translates to:
  /// **'Open Settings'**
  String get settingsTrustedOpenSettings;

  /// No description provided for @settingsTrustedTryAgain.
  ///
  /// In en, this message translates to:
  /// **'Try Again'**
  String get settingsTrustedTryAgain;

  /// No description provided for @settingsAppearanceLoadError.
  ///
  /// In en, this message translates to:
  /// **'Failed to load appearance settings'**
  String get settingsAppearanceLoadError;

  /// No description provided for @settingsBrightnessSection.
  ///
  /// In en, this message translates to:
  /// **'Brightness'**
  String get settingsBrightnessSection;

  /// No description provided for @settingsTextSizeSection.
  ///
  /// In en, this message translates to:
  /// **'Text Size'**
  String get settingsTextSizeSection;

  /// No description provided for @settingsDynamicColorLabel.
  ///
  /// In en, this message translates to:
  /// **'Dynamic Color'**
  String get settingsDynamicColorLabel;

  /// No description provided for @settingsDynamicColorDescription.
  ///
  /// In en, this message translates to:
  /// **'Use colors from your wallpaper'**
  String get settingsDynamicColorDescription;

  /// No description provided for @settingsOledModeLabel.
  ///
  /// In en, this message translates to:
  /// **'OLED Dark Mode'**
  String get settingsOledModeLabel;

  /// No description provided for @settingsOledModeDescription.
  ///
  /// In en, this message translates to:
  /// **'Use pure black backgrounds for maximum battery savings on OLED displays'**
  String get settingsOledModeDescription;

  /// No description provided for @settingsHighContrastLabel.
  ///
  /// In en, this message translates to:
  /// **'High Contrast'**
  String get settingsHighContrastLabel;

  /// No description provided for @settingsHighContrastDetected.
  ///
  /// In en, this message translates to:
  /// **'High contrast mode is enabled at the system level. Colors are optimized for maximum readability.'**
  String get settingsHighContrastDetected;

  /// No description provided for @settingsAnimationsSection.
  ///
  /// In en, this message translates to:
  /// **'Animations'**
  String get settingsAnimationsSection;

  /// No description provided for @settingsReduceAnimations.
  ///
  /// In en, this message translates to:
  /// **'Reduce Animations'**
  String get settingsReduceAnimations;

  /// No description provided for @settingsAnimationsDisabled.
  ///
  /// In en, this message translates to:
  /// **'System animations are disabled'**
  String get settingsAnimationsDisabled;

  /// No description provided for @settingsAnimationsEnabled.
  ///
  /// In en, this message translates to:
  /// **'System animations are enabled'**
  String get settingsAnimationsEnabled;

  /// No description provided for @settingsAnimationsSystemDisabled.
  ///
  /// In en, this message translates to:
  /// **'Animations are disabled at the system level.'**
  String get settingsAnimationsSystemDisabled;

  /// No description provided for @settingsThemeMaterialYou.
  ///
  /// In en, this message translates to:
  /// **'Material You'**
  String get settingsThemeMaterialYou;

  /// No description provided for @settingsThemeCyberpunk.
  ///
  /// In en, this message translates to:
  /// **'Cyberpunk'**
  String get settingsThemeCyberpunk;

  /// No description provided for @settingsTextScaleSystem.
  ///
  /// In en, this message translates to:
  /// **'System'**
  String get settingsTextScaleSystem;

  /// No description provided for @settingsTextScaleSmall.
  ///
  /// In en, this message translates to:
  /// **'Small'**
  String get settingsTextScaleSmall;

  /// No description provided for @settingsTextScaleDefault.
  ///
  /// In en, this message translates to:
  /// **'Default'**
  String get settingsTextScaleDefault;

  /// No description provided for @settingsTextScaleLarge.
  ///
  /// In en, this message translates to:
  /// **'Large'**
  String get settingsTextScaleLarge;

  /// No description provided for @settingsTextScaleExtraLarge.
  ///
  /// In en, this message translates to:
  /// **'Extra Large'**
  String get settingsTextScaleExtraLarge;

  /// No description provided for @settingsTextScaleSystemDescription.
  ///
  /// In en, this message translates to:
  /// **'Uses your device accessibility settings'**
  String get settingsTextScaleSystemDescription;

  /// No description provided for @settingsTextScaleSmallDescription.
  ///
  /// In en, this message translates to:
  /// **'Smaller text for more content on screen'**
  String get settingsTextScaleSmallDescription;

  /// No description provided for @settingsTextScaleDefaultDescription.
  ///
  /// In en, this message translates to:
  /// **'Default text size'**
  String get settingsTextScaleDefaultDescription;

  /// No description provided for @settingsTextScaleLargeDescription.
  ///
  /// In en, this message translates to:
  /// **'Larger text for improved readability'**
  String get settingsTextScaleLargeDescription;

  /// No description provided for @settingsTextScaleExtraLargeDescription.
  ///
  /// In en, this message translates to:
  /// **'Maximum text size for accessibility'**
  String get settingsTextScaleExtraLargeDescription;

  /// No description provided for @settingsTextSizePreview.
  ///
  /// In en, this message translates to:
  /// **'Preview: The quick brown fox jumps over the lazy dog.'**
  String get settingsTextSizePreview;

  /// No description provided for @settingsNotificationLoadError.
  ///
  /// In en, this message translates to:
  /// **'Failed to load notification settings'**
  String get settingsNotificationLoadError;

  /// No description provided for @settingsNotificationGeneralSection.
  ///
  /// In en, this message translates to:
  /// **'General'**
  String get settingsNotificationGeneralSection;

  /// No description provided for @settingsNotificationExpiryLabel.
  ///
  /// In en, this message translates to:
  /// **'Subscription expiry'**
  String get settingsNotificationExpiryLabel;

  /// No description provided for @settingsNotificationExpiryDescription.
  ///
  /// In en, this message translates to:
  /// **'Reminders before your subscription expires'**
  String get settingsNotificationExpiryDescription;

  /// No description provided for @settingsNotificationPromotionalDescription.
  ///
  /// In en, this message translates to:
  /// **'Offers, discounts, and new features'**
  String get settingsNotificationPromotionalDescription;

  /// No description provided for @settingsNotificationReferralLabel.
  ///
  /// In en, this message translates to:
  /// **'Referral activity'**
  String get settingsNotificationReferralLabel;

  /// No description provided for @settingsNotificationReferralDescription.
  ///
  /// In en, this message translates to:
  /// **'Updates on your referral rewards'**
  String get settingsNotificationReferralDescription;

  /// No description provided for @settingsNotificationSecuritySection.
  ///
  /// In en, this message translates to:
  /// **'Security'**
  String get settingsNotificationSecuritySection;

  /// No description provided for @settingsNotificationSecurityRequired.
  ///
  /// In en, this message translates to:
  /// **'Required for account security. Cannot be disabled.'**
  String get settingsNotificationSecurityRequired;

  /// No description provided for @settingsNotificationVpnSection.
  ///
  /// In en, this message translates to:
  /// **'VPN Notification'**
  String get settingsNotificationVpnSection;

  /// No description provided for @settingsNotificationVpnSpeedLabel.
  ///
  /// In en, this message translates to:
  /// **'Show speed in VPN notification'**
  String get settingsNotificationVpnSpeedLabel;

  /// No description provided for @settingsNotificationVpnSpeedDescription.
  ///
  /// In en, this message translates to:
  /// **'Display connection speed in persistent notification'**
  String get settingsNotificationVpnSpeedDescription;

  /// No description provided for @settingsDeveloperExperimentalEnabled.
  ///
  /// In en, this message translates to:
  /// **'Experimental features enabled'**
  String get settingsDeveloperExperimentalEnabled;

  /// No description provided for @settingsDeveloperExperimentalDisabled.
  ///
  /// In en, this message translates to:
  /// **'Experimental features disabled'**
  String get settingsDeveloperExperimentalDisabled;

  /// No description provided for @configImportSubscriptionUrlTitle.
  ///
  /// In en, this message translates to:
  /// **'Subscription URL Import'**
  String get configImportSubscriptionUrlTitle;

  /// No description provided for @configImportPasteFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed to paste from clipboard'**
  String get configImportPasteFailed;

  /// No description provided for @configImportServersImported.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{Imported 1 server} other{Imported {count} servers}}'**
  String configImportServersImported(int count);

  /// No description provided for @configImportSubscriptionFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed to import subscription URL'**
  String get configImportSubscriptionFailed;

  /// No description provided for @configImportSubscriptionUrlLabel.
  ///
  /// In en, this message translates to:
  /// **'Subscription URL'**
  String get configImportSubscriptionUrlLabel;

  /// No description provided for @configImportSubscriptionUrlHint.
  ///
  /// In en, this message translates to:
  /// **'Enter subscription URL'**
  String get configImportSubscriptionUrlHint;

  /// No description provided for @configImportPasteTooltip.
  ///
  /// In en, this message translates to:
  /// **'Paste from clipboard'**
  String get configImportPasteTooltip;

  /// No description provided for @configImportPleaseEnterUrl.
  ///
  /// In en, this message translates to:
  /// **'Please enter a URL'**
  String get configImportPleaseEnterUrl;

  /// No description provided for @configImportPleaseEnterValidUrl.
  ///
  /// In en, this message translates to:
  /// **'Please enter a valid URL'**
  String get configImportPleaseEnterValidUrl;

  /// No description provided for @configImportImporting.
  ///
  /// In en, this message translates to:
  /// **'Importing...'**
  String get configImportImporting;

  /// No description provided for @configImportImportButton.
  ///
  /// In en, this message translates to:
  /// **'Import'**
  String get configImportImportButton;

  /// No description provided for @configImportNoSubscriptionUrls.
  ///
  /// In en, this message translates to:
  /// **'No subscription URLs imported yet'**
  String get configImportNoSubscriptionUrls;

  /// No description provided for @configImportNoSubscriptionUrlsHint.
  ///
  /// In en, this message translates to:
  /// **'Enter a subscription URL above to import servers'**
  String get configImportNoSubscriptionUrlsHint;

  /// No description provided for @configImportDeleteSubscriptionTitle.
  ///
  /// In en, this message translates to:
  /// **'Delete Subscription'**
  String get configImportDeleteSubscriptionTitle;

  /// No description provided for @configImportDeleteSubscriptionContent.
  ///
  /// In en, this message translates to:
  /// **'Delete all {count} servers from this subscription?'**
  String configImportDeleteSubscriptionContent(int count);

  /// No description provided for @configImportSubscriptionDeleted.
  ///
  /// In en, this message translates to:
  /// **'Subscription deleted'**
  String get configImportSubscriptionDeleted;

  /// No description provided for @configImportRefreshTooltip.
  ///
  /// In en, this message translates to:
  /// **'Refresh subscription'**
  String get configImportRefreshTooltip;

  /// No description provided for @configImportDeleteTooltip.
  ///
  /// In en, this message translates to:
  /// **'Delete subscription'**
  String get configImportDeleteTooltip;

  /// No description provided for @configImportSubscriptionRefreshed.
  ///
  /// In en, this message translates to:
  /// **'Subscription refreshed'**
  String get configImportSubscriptionRefreshed;

  /// No description provided for @configImportServerCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 server} other{{count} servers}}'**
  String configImportServerCount(int count);

  /// No description provided for @configImportLastUpdated.
  ///
  /// In en, this message translates to:
  /// **'Last updated: {timeAgo}'**
  String configImportLastUpdated(String timeAgo);

  /// No description provided for @configImportTimeJustNow.
  ///
  /// In en, this message translates to:
  /// **'Just now'**
  String get configImportTimeJustNow;

  /// No description provided for @configImportTimeMinutesAgo.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 minute ago} other{{count} minutes ago}}'**
  String configImportTimeMinutesAgo(int count);

  /// No description provided for @configImportTimeHoursAgo.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 hour ago} other{{count} hours ago}}'**
  String configImportTimeHoursAgo(int count);

  /// No description provided for @configImportTimeDaysAgo.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 day ago} other{{count} days ago}}'**
  String configImportTimeDaysAgo(int count);

  /// No description provided for @configImportDeleteServerTitle.
  ///
  /// In en, this message translates to:
  /// **'Delete Server'**
  String get configImportDeleteServerTitle;

  /// No description provided for @configImportRemoveServerContent.
  ///
  /// In en, this message translates to:
  /// **'Remove \"{name}\" from your custom servers?'**
  String configImportRemoveServerContent(String name);

  /// No description provided for @configImportServerRemoved.
  ///
  /// In en, this message translates to:
  /// **'Server removed'**
  String get configImportServerRemoved;

  /// No description provided for @configImportRenameServerTitle.
  ///
  /// In en, this message translates to:
  /// **'Rename Server'**
  String get configImportRenameServerTitle;

  /// No description provided for @configImportServerNameLabel.
  ///
  /// In en, this message translates to:
  /// **'Server name'**
  String get configImportServerNameLabel;

  /// No description provided for @configImportServerRenamed.
  ///
  /// In en, this message translates to:
  /// **'Server renamed'**
  String get configImportServerRenamed;

  /// No description provided for @configImportServerReachable.
  ///
  /// In en, this message translates to:
  /// **'Server is reachable'**
  String get configImportServerReachable;

  /// No description provided for @configImportServerUnreachable.
  ///
  /// In en, this message translates to:
  /// **'Server is unreachable'**
  String get configImportServerUnreachable;

  /// No description provided for @configImportExportQrTitle.
  ///
  /// In en, this message translates to:
  /// **'Export as QR'**
  String get configImportExportQrTitle;

  /// No description provided for @configImportFromSubscriptionUrl.
  ///
  /// In en, this message translates to:
  /// **'Import from Subscription URL'**
  String get configImportFromSubscriptionUrl;

  /// No description provided for @configImportNoServersAtUrl.
  ///
  /// In en, this message translates to:
  /// **'No servers found at URL'**
  String get configImportNoServersAtUrl;

  /// No description provided for @configImportCustomServersTitle.
  ///
  /// In en, this message translates to:
  /// **'Custom Servers'**
  String get configImportCustomServersTitle;

  /// No description provided for @configImportClearAllButton.
  ///
  /// In en, this message translates to:
  /// **'Clear All'**
  String get configImportClearAllButton;

  /// No description provided for @configImportClearAllTitle.
  ///
  /// In en, this message translates to:
  /// **'Clear All Servers'**
  String get configImportClearAllTitle;

  /// No description provided for @configImportClearAllContent.
  ///
  /// In en, this message translates to:
  /// **'This will remove all custom servers. This action cannot be undone.'**
  String get configImportClearAllContent;

  /// No description provided for @configImportAllServersRemoved.
  ///
  /// In en, this message translates to:
  /// **'All custom servers removed'**
  String get configImportAllServersRemoved;

  /// No description provided for @configImportNoCustomServers.
  ///
  /// In en, this message translates to:
  /// **'No Custom Servers'**
  String get configImportNoCustomServers;

  /// No description provided for @configImportNoCustomServersHint.
  ///
  /// In en, this message translates to:
  /// **'Import VPN configurations via QR code, clipboard, or subscription URL.'**
  String get configImportNoCustomServersHint;

  /// No description provided for @configImportImportServerButton.
  ///
  /// In en, this message translates to:
  /// **'Import Server'**
  String get configImportImportServerButton;

  /// No description provided for @configImportFailedToLoadServers.
  ///
  /// In en, this message translates to:
  /// **'Failed to load servers'**
  String get configImportFailedToLoadServers;

  /// No description provided for @configImportSourceQrCode.
  ///
  /// In en, this message translates to:
  /// **'QR Code'**
  String get configImportSourceQrCode;

  /// No description provided for @configImportSourceClipboard.
  ///
  /// In en, this message translates to:
  /// **'Clipboard'**
  String get configImportSourceClipboard;

  /// No description provided for @configImportSourceSubscription.
  ///
  /// In en, this message translates to:
  /// **'Subscription'**
  String get configImportSourceSubscription;

  /// No description provided for @configImportSourceDeepLink.
  ///
  /// In en, this message translates to:
  /// **'Deep Link'**
  String get configImportSourceDeepLink;

  /// No description provided for @configImportSourceManual.
  ///
  /// In en, this message translates to:
  /// **'Manual'**
  String get configImportSourceManual;

  /// No description provided for @configImportTestConnection.
  ///
  /// In en, this message translates to:
  /// **'Test Connection'**
  String get configImportTestConnection;

  /// No description provided for @configImportEditName.
  ///
  /// In en, this message translates to:
  /// **'Edit Name'**
  String get configImportEditName;

  /// No description provided for @configImportNotTested.
  ///
  /// In en, this message translates to:
  /// **'Not tested'**
  String get configImportNotTested;

  /// No description provided for @configImportReachable.
  ///
  /// In en, this message translates to:
  /// **'Reachable'**
  String get configImportReachable;

  /// No description provided for @configImportUnreachable.
  ///
  /// In en, this message translates to:
  /// **'Unreachable'**
  String get configImportUnreachable;

  /// No description provided for @configImportTesting.
  ///
  /// In en, this message translates to:
  /// **'Testing...'**
  String get configImportTesting;

  /// No description provided for @configImportServerAdded.
  ///
  /// In en, this message translates to:
  /// **'Server added: {name}'**
  String configImportServerAdded(String name);

  /// No description provided for @configImportNoValidConfig.
  ///
  /// In en, this message translates to:
  /// **'No valid VPN config in clipboard'**
  String get configImportNoValidConfig;

  /// No description provided for @configImportNoConfigInClipboard.
  ///
  /// In en, this message translates to:
  /// **'No VPN configuration found in clipboard'**
  String get configImportNoConfigInClipboard;

  /// No description provided for @configImportSwitchCamera.
  ///
  /// In en, this message translates to:
  /// **'Switch camera'**
  String get configImportSwitchCamera;

  /// No description provided for @configImportNotValidConfig.
  ///
  /// In en, this message translates to:
  /// **'Not a valid VPN configuration'**
  String get configImportNotValidConfig;

  /// No description provided for @configImportConfigFound.
  ///
  /// In en, this message translates to:
  /// **'VPN Configuration Found'**
  String get configImportConfigFound;

  /// No description provided for @configImportNameLabel.
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get configImportNameLabel;

  /// No description provided for @configImportUnknownServer.
  ///
  /// In en, this message translates to:
  /// **'Unknown Server'**
  String get configImportUnknownServer;

  /// No description provided for @configImportProtocolLabel.
  ///
  /// In en, this message translates to:
  /// **'Protocol'**
  String get configImportProtocolLabel;

  /// No description provided for @configImportAddressLabel.
  ///
  /// In en, this message translates to:
  /// **'Address'**
  String get configImportAddressLabel;

  /// No description provided for @configImportAddServerButton.
  ///
  /// In en, this message translates to:
  /// **'Add Server'**
  String get configImportAddServerButton;

  /// No description provided for @configImportScanAnother.
  ///
  /// In en, this message translates to:
  /// **'Scan Another'**
  String get configImportScanAnother;

  /// No description provided for @configImportPointCamera.
  ///
  /// In en, this message translates to:
  /// **'Point your camera at a VPN QR code'**
  String get configImportPointCamera;

  /// No description provided for @configImportCameraPermissionRequired.
  ///
  /// In en, this message translates to:
  /// **'Camera Permission Required'**
  String get configImportCameraPermissionRequired;

  /// No description provided for @configImportCameraPermissionMessage.
  ///
  /// In en, this message translates to:
  /// **'Please grant camera access in your device settings to scan QR codes.'**
  String get configImportCameraPermissionMessage;

  /// No description provided for @configImportCameraError.
  ///
  /// In en, this message translates to:
  /// **'Camera Error'**
  String get configImportCameraError;

  /// No description provided for @configImportCameraStartFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed to start camera.'**
  String get configImportCameraStartFailed;

  /// No description provided for @configImportFailedToAddServer.
  ///
  /// In en, this message translates to:
  /// **'Failed to add server'**
  String get configImportFailedToAddServer;

  /// No description provided for @configImportTransportLabel.
  ///
  /// In en, this message translates to:
  /// **'Transport'**
  String get configImportTransportLabel;

  /// No description provided for @configImportSecurityLabel.
  ///
  /// In en, this message translates to:
  /// **'Security'**
  String get configImportSecurityLabel;

  /// No description provided for @configImportVpnConfigDetected.
  ///
  /// In en, this message translates to:
  /// **'VPN Config Detected'**
  String get configImportVpnConfigDetected;

  /// No description provided for @configImportFoundConfigs.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{Found 1 VPN configuration in your clipboard} other{Found {count} VPN configurations in your clipboard}}'**
  String configImportFoundConfigs(int count);

  /// No description provided for @configImportImportConfig.
  ///
  /// In en, this message translates to:
  /// **'Import Config'**
  String get configImportImportConfig;

  /// No description provided for @configImportImportAll.
  ///
  /// In en, this message translates to:
  /// **'Import All ({count})'**
  String configImportImportAll(int count);

  /// No description provided for @configImportDismiss.
  ///
  /// In en, this message translates to:
  /// **'Dismiss'**
  String get configImportDismiss;

  /// No description provided for @configImportDontAskAgain.
  ///
  /// In en, this message translates to:
  /// **'Don\'t ask again'**
  String get configImportDontAskAgain;

  /// No description provided for @configImportSuccessCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{Successfully imported 1 config} other{Successfully imported {count} configs}}'**
  String configImportSuccessCount(int count);

  /// No description provided for @configImportPartialSuccess.
  ///
  /// In en, this message translates to:
  /// **'Imported {success} config(s), {failure} failed'**
  String configImportPartialSuccess(int success, int failure);

  /// No description provided for @configImportFailureCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{Failed to import config} other{Failed to import {count} configs}}'**
  String configImportFailureCount(int count);

  /// No description provided for @subscriptionChooseYourPlan.
  ///
  /// In en, this message translates to:
  /// **'Choose Your Plan'**
  String get subscriptionChooseYourPlan;

  /// No description provided for @subscriptionDuration1Month.
  ///
  /// In en, this message translates to:
  /// **'1 Month'**
  String get subscriptionDuration1Month;

  /// No description provided for @subscriptionDuration3Months.
  ///
  /// In en, this message translates to:
  /// **'3 Months'**
  String get subscriptionDuration3Months;

  /// No description provided for @subscriptionDuration1Year.
  ///
  /// In en, this message translates to:
  /// **'1 Year'**
  String get subscriptionDuration1Year;

  /// No description provided for @subscriptionCardView.
  ///
  /// In en, this message translates to:
  /// **'Card View'**
  String get subscriptionCardView;

  /// No description provided for @subscriptionComparePlans.
  ///
  /// In en, this message translates to:
  /// **'Compare Plans'**
  String get subscriptionComparePlans;

  /// No description provided for @subscriptionNoPlansForDuration.
  ///
  /// In en, this message translates to:
  /// **'No plans available for this duration.'**
  String get subscriptionNoPlansForDuration;

  /// No description provided for @subscriptionFeatureLabel.
  ///
  /// In en, this message translates to:
  /// **'Feature'**
  String get subscriptionFeatureLabel;

  /// No description provided for @subscriptionPriceLabel.
  ///
  /// In en, this message translates to:
  /// **'Price'**
  String get subscriptionPriceLabel;

  /// No description provided for @subscriptionTrafficLabel.
  ///
  /// In en, this message translates to:
  /// **'Traffic'**
  String get subscriptionTrafficLabel;

  /// No description provided for @subscriptionDevicesLabel.
  ///
  /// In en, this message translates to:
  /// **'Devices'**
  String get subscriptionDevicesLabel;

  /// No description provided for @subscriptionDurationLabel.
  ///
  /// In en, this message translates to:
  /// **'Duration'**
  String get subscriptionDurationLabel;

  /// No description provided for @subscriptionTrafficGb.
  ///
  /// In en, this message translates to:
  /// **'{count} GB'**
  String subscriptionTrafficGb(int count);

  /// No description provided for @subscriptionUnlimited.
  ///
  /// In en, this message translates to:
  /// **'Unlimited'**
  String get subscriptionUnlimited;

  /// No description provided for @subscriptionDurationDays.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 day} other{{count} days}}'**
  String subscriptionDurationDays(int count);

  /// No description provided for @subscriptionCompletePurchase.
  ///
  /// In en, this message translates to:
  /// **'Complete Purchase'**
  String get subscriptionCompletePurchase;

  /// No description provided for @subscriptionReviewYourOrder.
  ///
  /// In en, this message translates to:
  /// **'Review Your Order'**
  String get subscriptionReviewYourOrder;

  /// No description provided for @subscriptionContinueToPayment.
  ///
  /// In en, this message translates to:
  /// **'Continue to Payment'**
  String get subscriptionContinueToPayment;

  /// No description provided for @subscriptionTotal.
  ///
  /// In en, this message translates to:
  /// **'Total'**
  String get subscriptionTotal;

  /// No description provided for @subscriptionSelectPaymentMethod.
  ///
  /// In en, this message translates to:
  /// **'Select Payment Method'**
  String get subscriptionSelectPaymentMethod;

  /// No description provided for @subscriptionPayNow.
  ///
  /// In en, this message translates to:
  /// **'Pay Now'**
  String get subscriptionPayNow;

  /// No description provided for @subscriptionDoNotCloseApp.
  ///
  /// In en, this message translates to:
  /// **'Please do not close the app.'**
  String get subscriptionDoNotCloseApp;

  /// No description provided for @subscriptionActivated.
  ///
  /// In en, this message translates to:
  /// **'Subscription Activated!'**
  String get subscriptionActivated;

  /// No description provided for @subscriptionActivatedMessage.
  ///
  /// In en, this message translates to:
  /// **'You are now subscribed to {planName}.'**
  String subscriptionActivatedMessage(String planName);

  /// No description provided for @subscriptionSecureVpnAccess.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 day of secure VPN access} other{{count} days of secure VPN access}}'**
  String subscriptionSecureVpnAccess(int count);

  /// No description provided for @subscriptionStartUsingVpn.
  ///
  /// In en, this message translates to:
  /// **'Start Using VPN'**
  String get subscriptionStartUsingVpn;

  /// No description provided for @subscriptionPaymentFailed.
  ///
  /// In en, this message translates to:
  /// **'Payment Failed'**
  String get subscriptionPaymentFailed;

  /// No description provided for @subscriptionTryAgain.
  ///
  /// In en, this message translates to:
  /// **'Try Again'**
  String get subscriptionTryAgain;

  /// No description provided for @subscriptionPurchase.
  ///
  /// In en, this message translates to:
  /// **'Purchase'**
  String get subscriptionPurchase;

  /// No description provided for @subscriptionPurchaseFlowFor.
  ///
  /// In en, this message translates to:
  /// **'Purchase flow for: {planName}'**
  String subscriptionPurchaseFlowFor(String planName);

  /// No description provided for @subscriptionSelectPaymentMethodSnack.
  ///
  /// In en, this message translates to:
  /// **'Please select a payment method'**
  String get subscriptionSelectPaymentMethodSnack;

  /// No description provided for @subscriptionPopular.
  ///
  /// In en, this message translates to:
  /// **'Popular'**
  String get subscriptionPopular;

  /// No description provided for @subscriptionBestValue.
  ///
  /// In en, this message translates to:
  /// **'Best Value'**
  String get subscriptionBestValue;

  /// No description provided for @subscriptionFreeTrial.
  ///
  /// In en, this message translates to:
  /// **'Free Trial'**
  String get subscriptionFreeTrial;

  /// No description provided for @subscriptionTrafficGbFeature.
  ///
  /// In en, this message translates to:
  /// **'{count} GB traffic'**
  String subscriptionTrafficGbFeature(int count);

  /// No description provided for @subscriptionUnlimitedTraffic.
  ///
  /// In en, this message translates to:
  /// **'Unlimited traffic'**
  String get subscriptionUnlimitedTraffic;

  /// No description provided for @subscriptionUpToDevices.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{Up to 1 device} other{Up to {count} devices}}'**
  String subscriptionUpToDevices(int count);

  /// No description provided for @subscriptionPerMonth.
  ///
  /// In en, this message translates to:
  /// **'/ month'**
  String get subscriptionPerMonth;

  /// No description provided for @subscriptionPer3Months.
  ///
  /// In en, this message translates to:
  /// **'/ 3 months'**
  String get subscriptionPer3Months;

  /// No description provided for @subscriptionPerYear.
  ///
  /// In en, this message translates to:
  /// **'/ year'**
  String get subscriptionPerYear;

  /// No description provided for @subscriptionPerLifetime.
  ///
  /// In en, this message translates to:
  /// **'/ lifetime'**
  String get subscriptionPerLifetime;

  /// No description provided for @subscriptionStartFreeTrial.
  ///
  /// In en, this message translates to:
  /// **'Start Free Trial'**
  String get subscriptionStartFreeTrial;

  /// No description provided for @subscriptionDataUsage.
  ///
  /// In en, this message translates to:
  /// **'Data Usage'**
  String get subscriptionDataUsage;

  /// No description provided for @subscriptionPercentUsed.
  ///
  /// In en, this message translates to:
  /// **'{percent} used'**
  String subscriptionPercentUsed(String percent);

  /// No description provided for @subscriptionNoPaymentMethods.
  ///
  /// In en, this message translates to:
  /// **'No payment methods available.'**
  String get subscriptionNoPaymentMethods;

  /// No description provided for @subscriptionApplePay.
  ///
  /// In en, this message translates to:
  /// **'Apple Pay'**
  String get subscriptionApplePay;

  /// No description provided for @subscriptionPayWithApplePay.
  ///
  /// In en, this message translates to:
  /// **'Pay with Apple Pay'**
  String get subscriptionPayWithApplePay;

  /// No description provided for @subscriptionGooglePay.
  ///
  /// In en, this message translates to:
  /// **'Google Pay'**
  String get subscriptionGooglePay;

  /// No description provided for @subscriptionPayWithGooglePay.
  ///
  /// In en, this message translates to:
  /// **'Pay with Google Pay'**
  String get subscriptionPayWithGooglePay;

  /// No description provided for @subscriptionCryptoBot.
  ///
  /// In en, this message translates to:
  /// **'CryptoBot'**
  String get subscriptionCryptoBot;

  /// No description provided for @subscriptionPayWithCrypto.
  ///
  /// In en, this message translates to:
  /// **'Pay with Crypto'**
  String get subscriptionPayWithCrypto;

  /// No description provided for @subscriptionYooKassa.
  ///
  /// In en, this message translates to:
  /// **'YooKassa'**
  String get subscriptionYooKassa;

  /// No description provided for @subscriptionPayWithCard.
  ///
  /// In en, this message translates to:
  /// **'Pay with Card (RU)'**
  String get subscriptionPayWithCard;

  /// No description provided for @subscriptionQuarterly.
  ///
  /// In en, this message translates to:
  /// **'Quarterly'**
  String get subscriptionQuarterly;

  /// No description provided for @serverTooltipFastest.
  ///
  /// In en, this message translates to:
  /// **'Tap Fastest to auto-select best server'**
  String get serverTooltipFastest;

  /// No description provided for @serverSortRecommended.
  ///
  /// In en, this message translates to:
  /// **'Recommended'**
  String get serverSortRecommended;

  /// No description provided for @serverSortCountry.
  ///
  /// In en, this message translates to:
  /// **'Country'**
  String get serverSortCountry;

  /// No description provided for @serverSortLatency.
  ///
  /// In en, this message translates to:
  /// **'Latency'**
  String get serverSortLatency;

  /// No description provided for @serverSortLoad.
  ///
  /// In en, this message translates to:
  /// **'Load'**
  String get serverSortLoad;

  /// No description provided for @serverFastest.
  ///
  /// In en, this message translates to:
  /// **'Fastest'**
  String get serverFastest;

  /// No description provided for @serverFailedToLoad.
  ///
  /// In en, this message translates to:
  /// **'Failed to load servers'**
  String get serverFailedToLoad;

  /// No description provided for @serverNotFound.
  ///
  /// In en, this message translates to:
  /// **'Server not found'**
  String get serverNotFound;

  /// No description provided for @serverListClearSearch.
  ///
  /// In en, this message translates to:
  /// **'Clear search'**
  String get serverListClearSearch;

  /// No description provided for @serverSelectPrompt.
  ///
  /// In en, this message translates to:
  /// **'Select a server to view details'**
  String get serverSelectPrompt;

  /// No description provided for @serverSingle.
  ///
  /// In en, this message translates to:
  /// **'Server'**
  String get serverSingle;

  /// No description provided for @serverDetailAddress.
  ///
  /// In en, this message translates to:
  /// **'Address'**
  String get serverDetailAddress;

  /// No description provided for @serverDetailProtocol.
  ///
  /// In en, this message translates to:
  /// **'Protocol'**
  String get serverDetailProtocol;

  /// No description provided for @serverDetailStatus.
  ///
  /// In en, this message translates to:
  /// **'Status'**
  String get serverDetailStatus;

  /// No description provided for @serverDetailOnline.
  ///
  /// In en, this message translates to:
  /// **'Online'**
  String get serverDetailOnline;

  /// No description provided for @serverDetailOffline.
  ///
  /// In en, this message translates to:
  /// **'Offline'**
  String get serverDetailOffline;

  /// No description provided for @serverDetailTier.
  ///
  /// In en, this message translates to:
  /// **'Tier'**
  String get serverDetailTier;

  /// No description provided for @serverDetailPremium.
  ///
  /// In en, this message translates to:
  /// **'Premium'**
  String get serverDetailPremium;

  /// No description provided for @serverDetailLatency.
  ///
  /// In en, this message translates to:
  /// **'Latency'**
  String get serverDetailLatency;

  /// No description provided for @serverDetailNotTested.
  ///
  /// In en, this message translates to:
  /// **'Not tested'**
  String get serverDetailNotTested;

  /// No description provided for @serverDetailServerLoad.
  ///
  /// In en, this message translates to:
  /// **'Server Load'**
  String get serverDetailServerLoad;

  /// No description provided for @serverDetailUptime.
  ///
  /// In en, this message translates to:
  /// **'Uptime'**
  String get serverDetailUptime;

  /// No description provided for @serverDetailUptimeValue.
  ///
  /// In en, this message translates to:
  /// **'99.9%'**
  String get serverDetailUptimeValue;

  /// No description provided for @serverDetailUptimeNA.
  ///
  /// In en, this message translates to:
  /// **'N/A'**
  String get serverDetailUptimeNA;

  /// No description provided for @serverDetailUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Unavailable'**
  String get serverDetailUnavailable;

  /// No description provided for @serverDetailConnectingTo.
  ///
  /// In en, this message translates to:
  /// **'Connecting to {name}...'**
  String serverDetailConnectingTo(String name);

  /// No description provided for @serverDetailFailedToConnect.
  ///
  /// In en, this message translates to:
  /// **'Failed to connect: {error}'**
  String serverDetailFailedToConnect(String error);

  /// No description provided for @serverCustomBadge.
  ///
  /// In en, this message translates to:
  /// **'CUSTOM'**
  String get serverCustomBadge;

  /// No description provided for @serverFavoritesTitle.
  ///
  /// In en, this message translates to:
  /// **'Favorites'**
  String get serverFavoritesTitle;

  /// No description provided for @serverNoFavoritesTitle.
  ///
  /// In en, this message translates to:
  /// **'No favorites yet'**
  String get serverNoFavoritesTitle;

  /// No description provided for @serverNoFavoritesDescription.
  ///
  /// In en, this message translates to:
  /// **'Tap the star icon on any server to add it here.'**
  String get serverNoFavoritesDescription;

  /// No description provided for @serverPingUnknown.
  ///
  /// In en, this message translates to:
  /// **'-- ms'**
  String get serverPingUnknown;

  /// No description provided for @serverPingMs.
  ///
  /// In en, this message translates to:
  /// **'{ping} ms'**
  String serverPingMs(int ping);

  /// No description provided for @a11ySelectFastestServer.
  ///
  /// In en, this message translates to:
  /// **'Select fastest server'**
  String get a11ySelectFastestServer;

  /// No description provided for @a11ySelectFastestServerHint.
  ///
  /// In en, this message translates to:
  /// **'Tap to automatically connect to the fastest available server'**
  String get a11ySelectFastestServerHint;

  /// No description provided for @a11yServerCardHint.
  ///
  /// In en, this message translates to:
  /// **'Tap to view server details and connect'**
  String get a11yServerCardHint;

  /// No description provided for @a11yToggleFavoriteHint.
  ///
  /// In en, this message translates to:
  /// **'Tap to toggle favorite status'**
  String get a11yToggleFavoriteHint;

  /// No description provided for @a11yMeasuringLatency.
  ///
  /// In en, this message translates to:
  /// **'Measuring latency'**
  String get a11yMeasuringLatency;

  /// No description provided for @a11yLatencyUnknown.
  ///
  /// In en, this message translates to:
  /// **'Latency unknown'**
  String get a11yLatencyUnknown;

  /// No description provided for @a11yLatencyMs.
  ///
  /// In en, this message translates to:
  /// **'Latency: {ping} milliseconds'**
  String a11yLatencyMs(int ping);

  /// No description provided for @a11yRetestLatencyHint.
  ///
  /// In en, this message translates to:
  /// **'Tap to re-test server latency'**
  String get a11yRetestLatencyHint;

  /// No description provided for @a11yServerInCity.
  ///
  /// In en, this message translates to:
  /// **'{name} server in {city}'**
  String a11yServerInCity(String name, String city);

  /// No description provided for @a11yStatusOnline.
  ///
  /// In en, this message translates to:
  /// **'online'**
  String get a11yStatusOnline;

  /// No description provided for @a11yStatusOffline.
  ///
  /// In en, this message translates to:
  /// **'offline'**
  String get a11yStatusOffline;

  /// No description provided for @a11yLatencyMsShort.
  ///
  /// In en, this message translates to:
  /// **'{ping} milliseconds latency'**
  String a11yLatencyMsShort(int ping);

  /// No description provided for @a11yLatencyUnknownShort.
  ///
  /// In en, this message translates to:
  /// **'latency unknown'**
  String get a11yLatencyUnknownShort;

  /// No description provided for @a11yLoadPercent.
  ///
  /// In en, this message translates to:
  /// **'{load} percent load'**
  String a11yLoadPercent(int load);

  /// No description provided for @a11yPremiumServer.
  ///
  /// In en, this message translates to:
  /// **'premium server'**
  String get a11yPremiumServer;

  /// No description provided for @a11yCustomServer.
  ///
  /// In en, this message translates to:
  /// **'custom server'**
  String get a11yCustomServer;

  /// No description provided for @serverCustomCountry.
  ///
  /// In en, this message translates to:
  /// **'Custom'**
  String get serverCustomCountry;

  /// No description provided for @referralTitle.
  ///
  /// In en, this message translates to:
  /// **'Referrals'**
  String get referralTitle;

  /// No description provided for @referralYourStats.
  ///
  /// In en, this message translates to:
  /// **'Your Stats'**
  String get referralYourStats;

  /// No description provided for @referralRecentReferrals.
  ///
  /// In en, this message translates to:
  /// **'Recent Referrals'**
  String get referralRecentReferrals;

  /// No description provided for @referralActive.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get referralActive;

  /// No description provided for @referralJoinedDate.
  ///
  /// In en, this message translates to:
  /// **'Joined {date}'**
  String referralJoinedDate(String date);

  /// No description provided for @referralNoReferralsYet.
  ///
  /// In en, this message translates to:
  /// **'No referrals yet'**
  String get referralNoReferralsYet;

  /// No description provided for @referralShareCodePrompt.
  ///
  /// In en, this message translates to:
  /// **'Share your code to start earning rewards!'**
  String get referralShareCodePrompt;

  /// No description provided for @referralComingSoonTitle.
  ///
  /// In en, this message translates to:
  /// **'Referral Program Coming Soon'**
  String get referralComingSoonTitle;

  /// No description provided for @referralComingSoonDescription.
  ///
  /// In en, this message translates to:
  /// **'Invite friends and earn rewards when they subscribe. Stay tuned for our upcoming referral program!'**
  String get referralComingSoonDescription;

  /// No description provided for @referralNotifyMeConfirmation.
  ///
  /// In en, this message translates to:
  /// **'We\'ll notify you when referrals launch!'**
  String get referralNotifyMeConfirmation;

  /// No description provided for @referralNotifyMe.
  ///
  /// In en, this message translates to:
  /// **'Notify Me'**
  String get referralNotifyMe;

  /// No description provided for @referralCodeCopied.
  ///
  /// In en, this message translates to:
  /// **'Referral code copied!'**
  String get referralCodeCopied;

  /// No description provided for @referralShareMessage.
  ///
  /// In en, this message translates to:
  /// **'Join CyberVPN with my referral link: {link}'**
  String referralShareMessage(String link);

  /// No description provided for @referralCopyCode.
  ///
  /// In en, this message translates to:
  /// **'Copy code'**
  String get referralCopyCode;

  /// No description provided for @referralQrCodeSemantics.
  ///
  /// In en, this message translates to:
  /// **'Referral QR code'**
  String get referralQrCodeSemantics;

  /// No description provided for @referralStatsTotalInvited.
  ///
  /// In en, this message translates to:
  /// **'Total Invited'**
  String get referralStatsTotalInvited;

  /// No description provided for @referralStatsPaidUsers.
  ///
  /// In en, this message translates to:
  /// **'Paid Users'**
  String get referralStatsPaidUsers;

  /// No description provided for @referralStatsPoints.
  ///
  /// In en, this message translates to:
  /// **'Points'**
  String get referralStatsPoints;

  /// No description provided for @referralStatsBalance.
  ///
  /// In en, this message translates to:
  /// **'Balance'**
  String get referralStatsBalance;

  /// No description provided for @diagnosticConnectionTitle.
  ///
  /// In en, this message translates to:
  /// **'Connection Diagnostics'**
  String get diagnosticConnectionTitle;

  /// No description provided for @diagnosticSteps.
  ///
  /// In en, this message translates to:
  /// **'Diagnostic Steps'**
  String get diagnosticSteps;

  /// No description provided for @diagnosticRunningTests.
  ///
  /// In en, this message translates to:
  /// **'Running connection tests...'**
  String get diagnosticRunningTests;

  /// No description provided for @diagnosticCompleted.
  ///
  /// In en, this message translates to:
  /// **'Diagnostics completed'**
  String get diagnosticCompleted;

  /// No description provided for @diagnosticTapToStart.
  ///
  /// In en, this message translates to:
  /// **'Tap Run Again to start'**
  String get diagnosticTapToStart;

  /// No description provided for @diagnosticUnknownStep.
  ///
  /// In en, this message translates to:
  /// **'Unknown Step'**
  String get diagnosticUnknownStep;

  /// No description provided for @diagnosticExportReport.
  ///
  /// In en, this message translates to:
  /// **'Export Report'**
  String get diagnosticExportReport;

  /// No description provided for @diagnosticRunning.
  ///
  /// In en, this message translates to:
  /// **'Running...'**
  String get diagnosticRunning;

  /// No description provided for @diagnosticRunAgain.
  ///
  /// In en, this message translates to:
  /// **'Run Again'**
  String get diagnosticRunAgain;

  /// No description provided for @diagnosticReportTitle.
  ///
  /// In en, this message translates to:
  /// **'CyberVPN Connection Diagnostics Report'**
  String get diagnosticReportTitle;

  /// No description provided for @diagnosticReportRanAt.
  ///
  /// In en, this message translates to:
  /// **'Ran at: {time}'**
  String diagnosticReportRanAt(String time);

  /// No description provided for @diagnosticReportTotalDuration.
  ///
  /// In en, this message translates to:
  /// **'Total duration: {seconds}s'**
  String diagnosticReportTotalDuration(int seconds);

  /// No description provided for @diagnosticReportSteps.
  ///
  /// In en, this message translates to:
  /// **'Steps:'**
  String get diagnosticReportSteps;

  /// No description provided for @diagnosticReportStatus.
  ///
  /// In en, this message translates to:
  /// **'Status: {status}'**
  String diagnosticReportStatus(String status);

  /// No description provided for @diagnosticReportDuration.
  ///
  /// In en, this message translates to:
  /// **'Duration: {duration}'**
  String diagnosticReportDuration(String duration);

  /// No description provided for @diagnosticReportDurationNa.
  ///
  /// In en, this message translates to:
  /// **'N/A'**
  String get diagnosticReportDurationNa;

  /// No description provided for @diagnosticReportMessage.
  ///
  /// In en, this message translates to:
  /// **'Message: {message}'**
  String diagnosticReportMessage(String message);

  /// No description provided for @diagnosticReportSuggestion.
  ///
  /// In en, this message translates to:
  /// **'Suggestion: {suggestion}'**
  String diagnosticReportSuggestion(String suggestion);

  /// No description provided for @diagnosticStatusPending.
  ///
  /// In en, this message translates to:
  /// **'PENDING'**
  String get diagnosticStatusPending;

  /// No description provided for @diagnosticStatusRunning.
  ///
  /// In en, this message translates to:
  /// **'RUNNING'**
  String get diagnosticStatusRunning;

  /// No description provided for @diagnosticStatusSuccess.
  ///
  /// In en, this message translates to:
  /// **'SUCCESS'**
  String get diagnosticStatusSuccess;

  /// No description provided for @diagnosticStatusFailed.
  ///
  /// In en, this message translates to:
  /// **'FAILED'**
  String get diagnosticStatusFailed;

  /// No description provided for @diagnosticStatusWarning.
  ///
  /// In en, this message translates to:
  /// **'WARNING'**
  String get diagnosticStatusWarning;

  /// No description provided for @speedTestWithVpn.
  ///
  /// In en, this message translates to:
  /// **'Test with VPN'**
  String get speedTestWithVpn;

  /// No description provided for @speedTestNoResults.
  ///
  /// In en, this message translates to:
  /// **'No speed tests yet'**
  String get speedTestNoResults;

  /// No description provided for @speedTestTapToStart.
  ///
  /// In en, this message translates to:
  /// **'Tap Start to measure your connection'**
  String get speedTestTapToStart;

  /// No description provided for @speedTestHistoryLabel.
  ///
  /// In en, this message translates to:
  /// **'History'**
  String get speedTestHistoryLabel;

  /// No description provided for @speedTestShareTitle.
  ///
  /// In en, this message translates to:
  /// **'CyberVPN Speed Test Results'**
  String get speedTestShareTitle;

  /// No description provided for @speedTestShareDownload.
  ///
  /// In en, this message translates to:
  /// **'Download: {value} Mbps'**
  String speedTestShareDownload(String value);

  /// No description provided for @speedTestShareUpload.
  ///
  /// In en, this message translates to:
  /// **'Upload: {value} Mbps'**
  String speedTestShareUpload(String value);

  /// No description provided for @speedTestShareLatency.
  ///
  /// In en, this message translates to:
  /// **'Latency: {value} ms'**
  String speedTestShareLatency(int value);

  /// No description provided for @speedTestShareJitter.
  ///
  /// In en, this message translates to:
  /// **'Jitter: {value} ms'**
  String speedTestShareJitter(int value);

  /// No description provided for @speedTestShareVpnOn.
  ///
  /// In en, this message translates to:
  /// **'VPN: ON'**
  String get speedTestShareVpnOn;

  /// No description provided for @speedTestShareVpnOff.
  ///
  /// In en, this message translates to:
  /// **'VPN: OFF'**
  String get speedTestShareVpnOff;

  /// No description provided for @speedTestShareTestedAt.
  ///
  /// In en, this message translates to:
  /// **'Tested: {time}'**
  String speedTestShareTestedAt(String time);

  /// No description provided for @speedTestVpnOn.
  ///
  /// In en, this message translates to:
  /// **'VPN ON'**
  String get speedTestVpnOn;

  /// No description provided for @speedTestVpnOff.
  ///
  /// In en, this message translates to:
  /// **'VPN OFF'**
  String get speedTestVpnOff;

  /// No description provided for @speedTestLatency.
  ///
  /// In en, this message translates to:
  /// **'Latency'**
  String get speedTestLatency;

  /// No description provided for @speedTestJitter.
  ///
  /// In en, this message translates to:
  /// **'Jitter'**
  String get speedTestJitter;

  /// No description provided for @speedTestCompare.
  ///
  /// In en, this message translates to:
  /// **'Compare'**
  String get speedTestCompare;

  /// No description provided for @speedTestHideCompare.
  ///
  /// In en, this message translates to:
  /// **'Hide Compare'**
  String get speedTestHideCompare;

  /// No description provided for @logViewerAutoScroll.
  ///
  /// In en, this message translates to:
  /// **'Auto-scroll'**
  String get logViewerAutoScroll;

  /// No description provided for @logViewerTotalEntries.
  ///
  /// In en, this message translates to:
  /// **'{count} total entries'**
  String logViewerTotalEntries(int count);

  /// No description provided for @logViewerFiltered.
  ///
  /// In en, this message translates to:
  /// **'{count} filtered'**
  String logViewerFiltered(int count);

  /// No description provided for @logViewerSearchHint.
  ///
  /// In en, this message translates to:
  /// **'Search logs...'**
  String get logViewerSearchHint;

  /// No description provided for @logViewerNoLogsToExport.
  ///
  /// In en, this message translates to:
  /// **'No logs to export'**
  String get logViewerNoLogsToExport;

  /// No description provided for @logViewerClearAllTitle.
  ///
  /// In en, this message translates to:
  /// **'Clear All Logs?'**
  String get logViewerClearAllTitle;

  /// No description provided for @logViewerClearCannotUndo.
  ///
  /// In en, this message translates to:
  /// **'This action cannot be undone'**
  String get logViewerClearCannotUndo;

  /// No description provided for @logViewerClearedSuccess.
  ///
  /// In en, this message translates to:
  /// **'Logs cleared successfully'**
  String get logViewerClearedSuccess;

  /// No description provided for @logViewerNoLogsAvailable.
  ///
  /// In en, this message translates to:
  /// **'No logs available'**
  String get logViewerNoLogsAvailable;

  /// No description provided for @logViewerNoLogsMatchFilters.
  ///
  /// In en, this message translates to:
  /// **'No logs match filters'**
  String get logViewerNoLogsMatchFilters;

  /// No description provided for @logViewerFilterDebug.
  ///
  /// In en, this message translates to:
  /// **'DEBUG'**
  String get logViewerFilterDebug;

  /// No description provided for @logViewerFilterInfo2.
  ///
  /// In en, this message translates to:
  /// **'INFO'**
  String get logViewerFilterInfo2;

  /// No description provided for @logViewerFilterWarning2.
  ///
  /// In en, this message translates to:
  /// **'WARNING'**
  String get logViewerFilterWarning2;

  /// No description provided for @logViewerFilterError2.
  ///
  /// In en, this message translates to:
  /// **'ERROR'**
  String get logViewerFilterError2;

  /// No description provided for @connectionStatusNotProtected.
  ///
  /// In en, this message translates to:
  /// **'Not Protected'**
  String get connectionStatusNotProtected;

  /// No description provided for @connectionStatusProtected.
  ///
  /// In en, this message translates to:
  /// **'Protected'**
  String get connectionStatusProtected;

  /// No description provided for @connectionStatusReconnecting.
  ///
  /// In en, this message translates to:
  /// **'Reconnecting...'**
  String get connectionStatusReconnecting;

  /// No description provided for @connectionStatusConnectionError.
  ///
  /// In en, this message translates to:
  /// **'Connection Error'**
  String get connectionStatusConnectionError;

  /// No description provided for @connectionSelectServer.
  ///
  /// In en, this message translates to:
  /// **'Select a server to connect'**
  String get connectionSelectServer;

  /// No description provided for @connectionPremium.
  ///
  /// In en, this message translates to:
  /// **'Premium'**
  String get connectionPremium;

  /// No description provided for @connectionDuration.
  ///
  /// In en, this message translates to:
  /// **'Duration'**
  String get connectionDuration;

  /// No description provided for @connectionMonitorSpeedTooltip.
  ///
  /// In en, this message translates to:
  /// **'Monitor your real-time speed here'**
  String get connectionMonitorSpeedTooltip;

  /// No description provided for @a11yConnectToVpn.
  ///
  /// In en, this message translates to:
  /// **'Connect to VPN'**
  String get a11yConnectToVpn;

  /// No description provided for @a11yConnectingToVpn.
  ///
  /// In en, this message translates to:
  /// **'Connecting to VPN'**
  String get a11yConnectingToVpn;

  /// No description provided for @a11yDisconnectFromVpn.
  ///
  /// In en, this message translates to:
  /// **'Disconnect from VPN'**
  String get a11yDisconnectFromVpn;

  /// No description provided for @a11yDisconnectingFromVpn.
  ///
  /// In en, this message translates to:
  /// **'Disconnecting from VPN'**
  String get a11yDisconnectingFromVpn;

  /// No description provided for @a11yReconnectingToVpn.
  ///
  /// In en, this message translates to:
  /// **'Reconnecting to VPN'**
  String get a11yReconnectingToVpn;

  /// No description provided for @a11yRetryVpnConnection.
  ///
  /// In en, this message translates to:
  /// **'Retry VPN connection'**
  String get a11yRetryVpnConnection;

  /// No description provided for @a11yTapToConnect.
  ///
  /// In en, this message translates to:
  /// **'Tap to connect to the VPN server'**
  String get a11yTapToConnect;

  /// No description provided for @a11yTapToDisconnect.
  ///
  /// In en, this message translates to:
  /// **'Tap to disconnect from the VPN server'**
  String get a11yTapToDisconnect;

  /// No description provided for @a11yTapToRetry.
  ///
  /// In en, this message translates to:
  /// **'Tap to retry the connection'**
  String get a11yTapToRetry;

  /// No description provided for @a11yPleaseWaitConnectionInProgress.
  ///
  /// In en, this message translates to:
  /// **'Please wait, connection in progress'**
  String get a11yPleaseWaitConnectionInProgress;

  /// No description provided for @a11yPremiumSubscriptionActive.
  ///
  /// In en, this message translates to:
  /// **'Premium subscription active'**
  String get a11yPremiumSubscriptionActive;

  /// No description provided for @a11yUsingProtocol.
  ///
  /// In en, this message translates to:
  /// **'Using {protocol} protocol'**
  String a11yUsingProtocol(String protocol);

  /// No description provided for @a11yConnectionDurationValue.
  ///
  /// In en, this message translates to:
  /// **'Connection duration: {duration}'**
  String a11yConnectionDurationValue(String duration);

  /// No description provided for @a11yIpAddress.
  ///
  /// In en, this message translates to:
  /// **'IP address: {ip}'**
  String a11yIpAddress(String ip);

  /// No description provided for @a11yDownloadUploadSpeed.
  ///
  /// In en, this message translates to:
  /// **'Download speed: {download}, Upload speed: {upload}'**
  String a11yDownloadUploadSpeed(String download, String upload);

  /// No description provided for @a11yConnectedToServer.
  ///
  /// In en, this message translates to:
  /// **'Connected to {name} server in {city}, {country}'**
  String a11yConnectedToServer(String name, String city, String country);

  /// No description provided for @errorSomethingWentWrong.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong'**
  String get errorSomethingWentWrong;

  /// No description provided for @errorUnexpectedDescription.
  ///
  /// In en, this message translates to:
  /// **'An unexpected error occurred. You can report this issue or restart the app.'**
  String get errorUnexpectedDescription;

  /// No description provided for @errorFeatureCrashed.
  ///
  /// In en, this message translates to:
  /// **'The {feature} feature encountered an error.'**
  String errorFeatureCrashed(String feature);

  /// No description provided for @errorReport.
  ///
  /// In en, this message translates to:
  /// **'Report'**
  String get errorReport;

  /// No description provided for @errorReported.
  ///
  /// In en, this message translates to:
  /// **'Reported'**
  String get errorReported;

  /// No description provided for @errorRestart.
  ///
  /// In en, this message translates to:
  /// **'Restart'**
  String get errorRestart;

  /// No description provided for @offlineLabel.
  ///
  /// In en, this message translates to:
  /// **'Offline'**
  String get offlineLabel;

  /// No description provided for @offlineYouAreOffline.
  ///
  /// In en, this message translates to:
  /// **'You are offline'**
  String get offlineYouAreOffline;

  /// No description provided for @offlineSomeFeaturesUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Some features unavailable'**
  String get offlineSomeFeaturesUnavailable;

  /// No description provided for @offlineNotAvailable.
  ///
  /// In en, this message translates to:
  /// **'Not available offline'**
  String get offlineNotAvailable;

  /// No description provided for @offlineLastSyncJustNow.
  ///
  /// In en, this message translates to:
  /// **'Last sync: just now'**
  String get offlineLastSyncJustNow;

  /// No description provided for @offlineLastSyncMinutes.
  ///
  /// In en, this message translates to:
  /// **'Last sync: {count}m ago'**
  String offlineLastSyncMinutes(int count);

  /// No description provided for @offlineLastSyncHours.
  ///
  /// In en, this message translates to:
  /// **'Last sync: {count}h ago'**
  String offlineLastSyncHours(int count);

  /// No description provided for @offlineLastSyncDays.
  ///
  /// In en, this message translates to:
  /// **'Last sync: {count}d ago'**
  String offlineLastSyncDays(int count);

  /// No description provided for @updateRequired.
  ///
  /// In en, this message translates to:
  /// **'Update Required'**
  String get updateRequired;

  /// No description provided for @updateAvailable.
  ///
  /// In en, this message translates to:
  /// **'Update Available'**
  String get updateAvailable;

  /// No description provided for @updateMandatoryDescription.
  ///
  /// In en, this message translates to:
  /// **'A mandatory update is required to continue using CyberVPN.'**
  String get updateMandatoryDescription;

  /// No description provided for @updateOptionalDescription.
  ///
  /// In en, this message translates to:
  /// **'A new version of CyberVPN is available with improvements and bug fixes.'**
  String get updateOptionalDescription;

  /// No description provided for @updateCurrentVersion.
  ///
  /// In en, this message translates to:
  /// **'Current Version:'**
  String get updateCurrentVersion;

  /// No description provided for @updateLatestVersion.
  ///
  /// In en, this message translates to:
  /// **'Latest Version:'**
  String get updateLatestVersion;

  /// No description provided for @updateRemindLater.
  ///
  /// In en, this message translates to:
  /// **'Remind me in 3 days'**
  String get updateRemindLater;

  /// No description provided for @updateNow.
  ///
  /// In en, this message translates to:
  /// **'Update Now'**
  String get updateNow;

  /// No description provided for @updateLater.
  ///
  /// In en, this message translates to:
  /// **'Later'**
  String get updateLater;

  /// No description provided for @splashTagline.
  ///
  /// In en, this message translates to:
  /// **'Secure. Private. Fast.'**
  String get splashTagline;

  /// No description provided for @navConnection.
  ///
  /// In en, this message translates to:
  /// **'Connection'**
  String get navConnection;

  /// No description provided for @autoConnectingToServer.
  ///
  /// In en, this message translates to:
  /// **'Auto-connecting to {server}...'**
  String autoConnectingToServer(String server);

  /// No description provided for @autoConnectingToVpn.
  ///
  /// In en, this message translates to:
  /// **'Auto-connecting to VPN...'**
  String get autoConnectingToVpn;

  /// No description provided for @autoConnectFailed.
  ///
  /// In en, this message translates to:
  /// **'Auto-connect failed: {message}'**
  String autoConnectFailed(String message);

  /// No description provided for @autoConnectSuccess.
  ///
  /// In en, this message translates to:
  /// **'Connected to {server}'**
  String autoConnectSuccess(String server);

  /// No description provided for @dismiss.
  ///
  /// In en, this message translates to:
  /// **'Dismiss'**
  String get dismiss;
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
