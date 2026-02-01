# Accessibility Testing Checklist - Task 124

## Test Environment Setup

### Android (TalkBack)
- Device: Android 10+ (API level 29+)
- Enable TalkBack: Settings → Accessibility → TalkBack → Toggle On
- Gestures: Swipe right/left to navigate, double-tap to activate
- Read from top: Swipe down then right
- TalkBack settings: Settings → Accessibility → TalkBack → Settings

### iOS (VoiceOver)
- Device: iOS 14+
- Enable VoiceOver: Settings → Accessibility → VoiceOver → Toggle On
- Gestures: Swipe right/left to navigate, double-tap to activate
- Rotor: Rotate two fingers to switch navigation modes
- Read from top: Three-finger swipe up

## Screen-by-Screen Testing

### 1. Connection Screen (/features/vpn/presentation/screens/connection_screen.dart)

#### Top Bar Status
- [ ] Status dot is excluded from semantics tree (decorative)
- [ ] Status text announces: "Connection status: {Not Protected|Connecting|Protected|etc.}"
- [ ] Subscription badge announces: "Premium subscription active"

#### Connect Button
- [ ] Disconnected state: "Connect to VPN, Tap to connect to the VPN server"
- [ ] Connecting state: "Connecting to VPN, Please wait, connection in progress" (disabled)
- [ ] Connected state: "Disconnect from VPN, Tap to disconnect from the VPN server"
- [ ] Disconnecting state: "Disconnecting from VPN, Please wait, connection in progress" (disabled)
- [ ] Reconnecting state: "Reconnecting to VPN, Please wait, connection in progress" (disabled)
- [ ] Error state: "Retry VPN connection, Tap to retry the connection"
- [ ] Touch target is 120x120dp (exceeds 44x44dp minimum)
- [ ] Button is correctly identified as a button by screen readers

#### Connection Info
- [ ] Server row announces: "Connected to {server name} server in {city}, {country}"
- [ ] Country flag emoji is excluded from semantics
- [ ] Protocol chip announces: "Using {Reality|XHTTP|WS-TLS|Shadowsocks} protocol"
- [ ] Protocol chip is read-only (not interactive)

#### Speed Indicators
- [ ] Speed indicator announces: "Download speed: {X MB/s}, Upload speed: {Y MB/s}"
- [ ] Direction icons (up/down arrows) excluded from semantics
- [ ] Marked as read-only (not interactive)

#### Session Stats
- [ ] Duration stat announces: "Duration: {time}"
- [ ] Data usage stat announces: "Data Used: {amount}"
- [ ] Icons excluded from semantics tree

### 2. Server List Screen (/features/servers/presentation/screens/server_list_screen.dart)

#### Top Controls
- [ ] App bar title "Servers" is announced
- [ ] Search field is accessible with hint text
- [ ] Clear search button is accessible when text is present
- [ ] Sort dropdown announces current selection and is operable

#### Quick Select
- [ ] Fastest button announces: "Select fastest server, Tap to automatically connect to the fastest available server"
- [ ] Lightning bolt icon excluded from semantics

#### Server Cards (for each server)
- [ ] Card announces: "{Server name} server in {city}, {status}, Latency: {X} milliseconds, {Y} percent load{, premium server}{, custom server}"
- [ ] Card identified as button with hint "Tap to view server details and connect"
- [ ] Country flag emoji excluded from semantics
- [ ] Protocol badge (VLESS/VMESS/etc.) text is readable but decorative styling excluded
- [ ] Ping indicator announces latency or "Measuring latency" or "Latency unknown"
- [ ] Ping indicator has button semantics when tappable with hint "Tap to re-test server latency"
- [ ] Favorite star button announces: "Add to favorites" or "Remove from favorites"
- [ ] Favorite star button has hint: "Tap to toggle favorite status"
- [ ] Favorite star touch target is 44x44dp minimum
- [ ] Load bar is visual only (not announced separately, included in card label)

#### Section Headers
- [ ] "Favorites" header is readable
- [ ] Favorite count badge is readable
- [ ] Expand/collapse chevron indicates state (testing navigation order)
- [ ] "Custom Servers" header is readable
- [ ] Custom server count is readable

### 3. Settings Screens

#### Settings Tile - Navigation Variant
- [ ] Announces: "{Title}, {subtitle}, Tap to open {title} settings"
- [ ] Identified as button
- [ ] Chevron icon excluded from semantics

#### Settings Tile - Toggle Variant
- [ ] Announces: "{Title}, {enabled|disabled}, Tap to {enable|disable} {title}"
- [ ] Toggle state is clearly communicated
- [ ] Entire tile is tappable
- [ ] Switch widget is accessible

#### Settings Tile - Radio Variant
- [ ] Announces: "{Title}{, selected}, Tap to select {title}"
- [ ] Selection state is clearly communicated
- [ ] Radio button is accessible

### 4. Diagnostics/Monitoring Screens

#### Speed Test
- [ ] Speedometer gauge has appropriate semantic labels
- [ ] Test start/stop buttons are accessible
- [ ] Results are announced when test completes

#### Logs
- [ ] Log entries are readable
- [ ] Copy/Share buttons are accessible

## General Accessibility Verification

### Navigation Order
- [ ] Navigation follows logical visual order (top to bottom, left to right)
- [ ] No trapped focus scenarios
- [ ] All interactive elements reachable via swipe navigation
- [ ] No infinite loops in navigation order

### Touch Targets
- [ ] All interactive elements meet 44x44dp minimum (WCAG 2.1 Level AAA)
- [ ] Verified for:
  - [ ] Connect button (120x120dp)
  - [ ] Favorite star buttons (44x44dp)
  - [ ] Settings tiles (full height of ListTile ~56dp)
  - [ ] Server cards (full height of card)
  - [ ] Ping indicator chips
  - [ ] Action chips (Fastest button)

### State Announcements
- [ ] Loading states are announced
- [ ] Error states are announced
- [ ] Success states are announced (connection established)
- [ ] Progress indicators have labels

### Color Contrast (WCAG 2.1 Level AA: 4.5:1)

#### Connection Screen
- [ ] Status text on dark background
- [ ] Connect button text (white on colored background)
- [ ] Speed indicator text
- [ ] Session stats text

#### Server List
- [ ] Server name text
- [ ] City/country text (gray on dark)
- [ ] Ping indicator text (white on colored chips)
- [ ] Protocol badge text

#### Settings
- [ ] Setting title text
- [ ] Setting subtitle text (gray on surface)

Use contrast checking tools:
- Chrome DevTools: Inspect element → Accessibility pane
- Online tool: https://webaim.org/resources/contrastchecker/
- Figma: Color Contrast Checker plugin

### Semantic Properties Used

Verify correct usage across codebase:
- [ ] `label`: Descriptive text for all interactive and informative elements
- [ ] `hint`: Additional context for interactive elements
- [ ] `button: true`: All tappable elements that perform actions
- [ ] `readOnly: true`: Informational elements (speed, ping, duration, etc.)
- [ ] `enabled`: Connect button during transitional states
- [ ] `toggled`: Toggle switches
- [ ] `selected`: Radio buttons and selection states
- [ ] `ExcludeSemantics`: Decorative icons, status dots, flag emojis

### Edge Cases

- [ ] Empty server list announces appropriate message
- [ ] No network connectivity states
- [ ] First-time user flow (no server selected)
- [ ] Expired subscription states
- [ ] Custom server import flow

## Testing Methodology

### Manual Testing Steps
1. Enable screen reader (TalkBack or VoiceOver)
2. Close eyes or look away from screen
3. Navigate entire app using only swipe gestures
4. Verify all information is announced correctly
5. Verify all actions can be completed
6. Test primary user flows:
   - Connect/disconnect from VPN
   - Select a different server
   - Toggle settings
   - View diagnostics

### Automated Testing (Future Enhancement)
Consider adding semantic tests in Flutter test suite:
```dart
testWidgets('Connect button has accessibility label', (tester) async {
  await tester.pumpWidget(const ConnectButton());
  final semantics = tester.getSemantics(find.byType(ConnectButton));
  expect(semantics.label, contains('Connect to VPN'));
  expect(semantics.isButton, isTrue);
});
```

## Known Limitations

1. **Dynamic Content**: Speed indicators update frequently - ensure updates don't interrupt screen reader flow
2. **Animations**: Pulse animations on connect button don't interfere with semantics
3. **Shimmer Loading**: Ping test shimmer animation announces "Measuring latency"
4. **Language Support**: Semantic labels are currently in English only - will need i18n support

## Sign-off Checklist

- [ ] All screens tested with TalkBack (Android)
- [ ] All screens tested with VoiceOver (iOS)
- [ ] All interactive elements accessible
- [ ] All informational content announced
- [ ] Navigation order is logical
- [ ] Touch targets verified (minimum 44x44dp)
- [ ] Color contrast verified (minimum 4.5:1)
- [ ] No accessibility regressions introduced
- [ ] Documentation updated

## References

- [Flutter Accessibility Guide](https://docs.flutter.dev/development/accessibility-and-localization/accessibility)
- [Material Design Accessibility](https://m3.material.io/foundations/accessible-design/overview)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Android TalkBack Testing](https://support.google.com/accessibility/android/answer/6283677)
- [iOS VoiceOver Testing](https://support.apple.com/guide/iphone/turn-on-and-practice-voiceover-iph3e2e415f/ios)
