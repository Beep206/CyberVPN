# PRD: CyberVPN Mobile UX Elevation

> **Version**: 1.0
> **Date**: 2026-02-07
> **Status**: Draft
> **Scope**: Flutter mobile app (`cybervpn_mobile/`)
> **Based on**: 4 parallel expert analyses (Animations, Adaptive UI, Navigation, Networking)

---

## 1. Executive Summary

Four independent expert audits of the CyberVPN mobile app revealed a **production-capable foundation** with significant unrealized potential. The app scores well on architecture (A-) and networking (A-) but underperforms on visual polish (B-) and animation maturity (3/5).

**Key insight**: The app has 11 unused Lottie animations, a sophisticated WebSocket client that's never activated, and a cyberpunk design system that's only partially applied. This PRD consolidates all findings into a prioritized execution plan across 6 epics.

### Current Scores

| Area | Score | Target |
|------|-------|--------|
| Navigation Architecture | A- (85/100) | A (92/100) |
| Networking & API | A- (88/100) | A+ (95/100) |
| Visual Polish | B- (81/100) | A (90/100) |
| Responsive/Adaptive | C+ (58/100) | B+ (82/100) |
| Animation Maturity | 3/5 | 5/5 |
| Accessibility | 72/100 | 85/100 |

---

## 2. Goals & Non-Goals

### Goals
- Integrate all 11 existing Lottie animations into production screens
- Activate WebSocket client for real-time server status updates
- Fix all text overflow and hardcoded layout issues (P0 bugs)
- Add cyberpunk-themed micro-interactions and effects
- Implement server map view and global settings search
- Achieve WCAG AA compliance across all screens
- Optimize tablet layouts for all primary screens

### Non-Goals
- Backend API changes (tracked separately)
- New feature development (subscription, referral system)
- App Store submission process
- Performance profiling / benchmarking (separate effort)
- Rive migration (stay with Lottie for now)

---

## 3. Epic 1: Critical UI Fixes (P0)

> **Priority**: P0 - Must fix before any public release
> **Effort**: 2-3 days
> **Impact**: Prevents crashes and unusable states

### 3.1 Text Overflow Protection

**Problem**: Multiple screens lack `TextOverflow.ellipsis` on dynamic text, causing overflow on small screens with large fonts.

**Affected files**:
- `profile_dashboard_screen.dart:354-358` - Stats card values (e.g., "999.9 GB")
- `server_list_screen.dart:339-350` - Search field missing `maxLines: 1`
- `settings_screen.dart` - Long locale names and notification counts
- All subtitle `Text` widgets across settings tiles

**Solution**: Add `overflow: TextOverflow.ellipsis` and `maxLines: 1` to all dynamic text widgets.

**Acceptance criteria**:
- [ ] No text overflow at 1.3x text scale on 320dp-wide screen
- [ ] All stats cards handle 6+ digit values gracefully
- [ ] Search fields constrained to single line

### 3.2 Hardcoded Layout Constraints

**Problem**: Multiple screens use magic numbers instead of responsive calculations.

**Affected files & lines**:
- `profile_dashboard_screen.dart:265` - `width: (MediaQuery.sizeOf(context).width - Spacing.md * 2 - Spacing.sm) / 2` (brittle)
- `login_screen.dart:202` - `ConstrainedBox(maxWidth: 420)` (hardcoded)
- `connection_screen.dart` - Fixed 24px padding, no tablet layout
- Various screens - `SizedBox(height: 80)` instead of safe area padding

**Solution**:
```dart
// Replace hardcoded calculations with LayoutBuilder
LayoutBuilder(builder: (context, constraints) {
  final cols = constraints.maxWidth >= 900 ? 4 :
               constraints.maxWidth >= 600 ? 3 : 2;
  return GridView.count(crossAxisCount: cols, children: cards);
})

// Replace magic bottom padding with proper safe area
MediaQuery.of(context).viewPadding.bottom + Spacing.lg
```

**Acceptance criteria**:
- [ ] Zero hardcoded pixel values for layout dimensions
- [ ] All screens render correctly on 320dp, 375dp, 414dp, 768dp, 1024dp widths
- [ ] Bottom content never obscured by navigation bar

### 3.3 Safe Area Handling

**Problem**: Inconsistent safe area handling - some screens use `SizedBox(height: 80)` instead of proper `MediaQuery.viewPadding`.

**Solution**: Create `Spacing.navBarClearance` token and replace all hardcoded bottom paddings.

**Acceptance criteria**:
- [ ] Content visible on iPhone 15 Pro Max (dynamic island + home indicator)
- [ ] Content visible on Pixel 8 Pro (gesture navigation)
- [ ] No magic number bottom paddings

### 3.4 Keyboard Overlap Handling

**Problem**: Long forms (RegisterScreen) may hide submit button when keyboard appears.

**Solution**: Ensure `Scaffold(resizeToAvoidBottomInset: true)` on all form screens + `LayoutBuilder` checks.

**Acceptance criteria**:
- [ ] Submit button visible with keyboard open on smallest supported screen
- [ ] Form scrollable when keyboard overlaps input fields

---

## 4. Epic 2: Lottie Animation Integration

> **Priority**: P1 - High impact, low effort (assets already exist)
> **Effort**: 3-4 days
> **Impact**: Dramatically improves perceived polish

### 4.1 VPN Connection Animations

**Problem**: 11 Lottie animation files exist in `assets/animations/` but NONE are integrated into production screens. The app uses basic `CircularProgressIndicator` where rich animations should appear.

**Files to integrate**:

| Asset | Target Screen | Replaces | Priority |
|-------|--------------|----------|----------|
| `connecting.json` | `connection_screen.dart` | CircularProgressIndicator during VPN connect | Critical |
| `connected_success.json` | `connection_screen.dart` | No current success feedback | Critical |
| `speed_test.json` | `speed_test_screen.dart` | Static speed test UI | High |
| `empty_state.json` | `server_list_screen.dart:451` | Static `Icon(Icons.search_off)` | High |

**Implementation for connection screen**:
```dart
// Replace loading indicator with Lottie
if (vpnState is VpnConnecting)
  Lottie.asset('assets/animations/connecting.json', width: 120, height: 120)

// One-shot success animation
if (vpnState is VpnConnected && !_hasPlayedSuccess)
  Lottie.asset('assets/animations/connected_success.json', repeat: false,
    onLoaded: (composition) => _hasPlayedSuccess = true)
```

**Acceptance criteria**:
- [ ] `connecting.json` plays during VPN connection attempt
- [ ] `connected_success.json` plays once on successful connection
- [ ] `empty_state.json` shown when server search returns no results
- [ ] `speed_test.json` plays during speed test execution
- [ ] All Lottie animations respect `MediaQuery.disableAnimations`

### 4.2 Onboarding Animations

**Problem**: Onboarding pages use placeholder icons instead of the prepared Lottie assets.

**Files**:
| Asset | Onboarding Page |
|-------|----------------|
| `onboarding_privacy.json` | Page 1 (Privacy) |
| `onboarding_connect.json` | Page 2 (Connect) |
| `onboarding_globe.json` | Page 3 (Global) |
| `get_started.json` | Page 4 (Get Started) |

**Target file**: `onboarding_screen.dart` / `onboarding_page_widget.dart`

**Acceptance criteria**:
- [ ] Each onboarding page displays its corresponding Lottie animation
- [ ] Animations auto-play when page becomes visible
- [ ] Animations pause when page is not visible (performance)

### 4.3 Hero Transitions for Server Flags

**Problem**: `FlagWidget` has `heroTag` support (`server_card.dart:150`) but the server detail screen has no matching `Hero` widget.

**Solution**: Add `Hero(tag: 'server_flag_${server.id}')` wrapper to the flag on the server detail screen.

**Acceptance criteria**:
- [ ] Flag smoothly animates from list card to detail screen header
- [ ] Animation works in both directions (push and pop)

---

## 5. Epic 3: Cyberpunk Visual Effects

> **Priority**: P1 - Brand differentiation
> **Effort**: 5-7 days
> **Impact**: Matches the cyberpunk brand aesthetic established in the admin panel

### 5.1 GlitchText Widget

**Problem**: Screen titles use plain `Text` widgets with no cyberpunk flavor.

**Solution**: Create reusable `GlitchText` widget with RGB split effect on entrance.

**Implementation**:
- Stack 3 text layers (red, green, main) with animated offsets
- Trigger on page entrance, settle after 500ms
- Use `SingleTickerProviderStateMixin` for performance
- Respect `MediaQuery.disableAnimations`

**Target locations**:
- Connection screen title
- Server list header
- Settings screen title
- Profile screen header

**Acceptance criteria**:
- [ ] `GlitchText` widget created in `shared/widgets/`
- [ ] Applied to all primary screen headers
- [ ] Animation settles to clean text after 500ms
- [ ] Disabled when accessibility animations are off

### 5.2 Neon Glow Pulsing

**Problem**: `cyberpunkGlow()` helper exists but is rarely used. Cards have border glow but buttons and active indicators don't.

**Solution**: Enhance `ConnectButton` glow animation and apply neon effects to:
- Connect button (animate blurRadius 18 -> 30 -> 18 over 1500ms when connected)
- Speed indicator icons (upload/download)
- Server card protocol badges
- Premium subscription badge

**Acceptance criteria**:
- [ ] Connected state has pulsing neon glow
- [ ] All primary action buttons have glow in Cyberpunk theme
- [ ] Material You theme uses standard Material 3 elevation (no glow)

### 5.3 Status Dot Pulse Animation

**Problem**: Connection status dot (`_StatusDot` in `connection_screen.dart:184-210`) is static.

**Solution**: Add subtle scale pulse (1.0 -> 1.1 -> 1.0) over 2000ms when VPN is connected.

**Acceptance criteria**:
- [ ] Dot pulses continuously while VPN connected
- [ ] Stops pulsing immediately on disconnect
- [ ] Uses `RepaintBoundary` for isolation

### 5.4 Scanline Overlay (Optional)

**Problem**: Cyberpunk aesthetic commonly uses CRT scanline effects; the app has none.

**Solution**: Create toggleable `ScanlineOverlay` widget with very subtle (2% opacity) horizontal lines.

**Implementation**: Add toggle in Appearance settings screen. Default: OFF.

**Acceptance criteria**:
- [ ] Scanline overlay available in Cyberpunk theme settings
- [ ] Default OFF (opt-in effect)
- [ ] Uses `IgnorePointer` so it doesn't block taps
- [ ] Performance: no measurable frame drop

### 5.5 Cyberpunk Component Library

**Problem**: Missing reusable cyberpunk widgets leads to inconsistent theme application.

**New widgets to create**:
1. `CyberButton` - Neon border button with glow animation on press
2. `CyberCard` - Card with animated border glow (generalize from existing cards)
3. `CyberProgressBar` - Neon progress bar with scan animation
4. `CyberDivider` - Animated neon line divider
5. `CyberBadge` - Status badge with pulsing neon effect

**Acceptance criteria**:
- [ ] All 5 widgets created in `shared/widgets/cyber/`
- [ ] Each widget adapts to current theme (cyberpunk vs Material You)
- [ ] Used consistently across all screens

---

## 6. Epic 4: Responsive & Adaptive UI

> **Priority**: P1 - Required for tablet users
> **Effort**: 8-10 days
> **Impact**: Unlocks tablet market, improves all screen sizes

### 6.1 Tablet Layout Optimization

**Problem**: Only `ServerListScreen` has a proper tablet layout. All other screens are phone-only.

**Screens to optimize**:

| Screen | Current | Target (>600dp) |
|--------|---------|-----------------|
| Connection | Single column, fixed padding | Side-by-side: connect button + stats panel |
| Profile Dashboard | 2-column hardcoded grid | 3-4 column adaptive grid with `LayoutBuilder` |
| Settings | Single list | 2-column: categories left, detail right |
| Login/Register | 420px max width | Centered card (max 480px) with background illustration |
| Appearance | Cramped theme cards | Larger preview cards in 2-column grid |

**Solution**: Use `LayoutBuilder` + `ResponsiveLayout` breakpoint helper (already exists in `shared/widgets/responsive_layout.dart`).

**Acceptance criteria**:
- [ ] All 5 screens have distinct tablet layouts
- [ ] Server list sidebar width is responsive (25-30% of screen, min 280, max 400)
- [ ] No horizontal overflow on any screen at any breakpoint

### 6.2 Orientation Support

**Problem**: No `OrientationBuilder` usage detected. App is portrait-only by default.

**Solution**: Add landscape layouts for top 3 screens:
- Connection screen: Horizontal layout (button left, stats right)
- Server list: Wider search bar, 2-column grid for servers
- Profile dashboard: Stats cards in single row

**Acceptance criteria**:
- [ ] Connection, Servers, Profile screens have landscape layouts
- [ ] No overflow in landscape on any supported device
- [ ] Orientation changes preserve scroll position and state

### 6.3 Platform-Adaptive Widgets

**Problem**: Entire app uses Material widgets on iOS. iOS users expect native feel.

**Solution**: Create adaptive widget wrappers:

```dart
// AdaptiveSwitch
Platform.isIOS ? CupertinoSwitch(...) : Switch(...)

// AdaptiveAppBar
Platform.isIOS ? CupertinoNavigationBar(...) : AppBar(...)

// AdaptiveDialog
Platform.isIOS ? CupertinoAlertDialog(...) : AlertDialog(...)
```

**Widgets to make adaptive**:
- Switch (19 instances using `Platform.isAndroid`/`Platform.isIOS`)
- Navigation bar transitions (Cupertino slide on iOS, Material fade on Android)
- Action sheets (CupertinoActionSheet on iOS, BottomSheet on Android)
- Dialogs (CupertinoAlertDialog on iOS, AlertDialog on Android)

**Acceptance criteria**:
- [ ] Adaptive wrappers created in `shared/widgets/adaptive/`
- [ ] All switches use `AdaptiveSwitch`
- [ ] iOS page transitions use Cupertino slide
- [ ] Android page transitions use Material fade

### 6.4 Dark Theme Improvements

**Problem**: Missing OLED-friendly pure black mode and high contrast mode.

**Solution**:
1. Add "Pure OLED" brightness option (`#000000` backgrounds) to appearance settings
2. Add high contrast mode detection via `MediaQuery.highContrast`
3. Complete Material 3 surface tokens (`surfaceBright`, `surfaceDim`, etc.)

**Acceptance criteria**:
- [ ] OLED mode option in Appearance settings
- [ ] High contrast mode auto-activates when OS setting enabled
- [ ] All Material 3 surface tokens defined

---

## 7. Epic 5: Navigation UX Enhancements

> **Priority**: P2 - Quality of life improvements
> **Effort**: 8-10 days
> **Impact**: Competitive parity with top VPN apps

### 7.1 Server Map View

**Problem**: No map-based server selection. Most competitor VPN apps (NordVPN, ExpressVPN, Surfshark) offer a world map for server selection.

**Solution**: Add map view toggle in Servers tab app bar. Show servers on interactive world map with:
- Country markers with server count badges
- Color-coded latency indicators (green < 50ms, yellow < 100ms, red > 100ms)
- Tap marker to expand country → select specific server
- Zoom to region gestures

**Implementation**: Use `flutter_map` + OpenStreetMap tiles (no Google Maps API key needed).

**Acceptance criteria**:
- [ ] Map/List toggle button in Servers tab app bar
- [ ] All server countries shown on map with markers
- [ ] Tap marker → show server selector bottom sheet
- [ ] Latency color coding on markers
- [ ] Map preference persisted between sessions

### 7.2 Recent Servers Section

**Problem**: No quick access to recently used servers. Users must search or scroll to find servers they've used before.

**Solution**: Add horizontal scrolling carousel at top of server list showing last 5 connected servers.

**Implementation**:
- Store last 5 server IDs in SharedPreferences
- Horizontal `ListView` with `ServerMiniCard` widget
- Tap to instant-connect (no detail screen)
- "Clear recent" option

**Acceptance criteria**:
- [ ] Recent servers section at top of server list
- [ ] Shows last 5 unique servers
- [ ] Tap to connect, long-press for detail
- [ ] Empty state: "Connect to a server to see it here"

### 7.3 Global Settings Search

**Problem**: Settings are organized in groups but not searchable. Users must navigate through menus to find specific settings.

**Solution**: Add search icon in Settings app bar → full-screen search overlay.

**Implementation**:
- Index all settings items with keywords
- Fuzzy search matching
- Navigate directly to setting on tap
- Recently searched items

**Acceptance criteria**:
- [ ] Search icon in Settings screen app bar
- [ ] Search matches setting name and description
- [ ] Tap result navigates to correct settings screen
- [ ] Works in all 27 locales

### 7.4 Server Quick Actions Bottom Sheet

**Problem**: Server cards only support tap (navigate to detail) and favorite star. No quick actions.

**Solution**: Long-press server card → bottom sheet with:
- Connect to this server
- Add/remove from favorites
- Copy server address
- View server details
- Report issue

**Acceptance criteria**:
- [ ] Long-press triggers bottom sheet
- [ ] All 5 actions functional
- [ ] Bottom sheet uses Cyberpunk/Material styling based on theme
- [ ] Haptic feedback on long-press

### 7.5 In-App Delete Account Flow

**Problem**: Delete account opens external web link (`settings_screen.dart:290-295`), breaking UX flow.

**Solution**: Implement in-app multi-step deletion flow:
1. "Delete Account" button → Confirmation dialog with consequences
2. Password/biometric re-authentication
3. Final confirmation with countdown timer (5s)
4. API call to delete → Success screen with logout

**Acceptance criteria**:
- [ ] Entire flow is in-app (no web redirect)
- [ ] Requires authentication before deletion
- [ ] Shows clear consequences (data loss, subscription cancellation)
- [ ] 5-second cooldown before final delete button is active

---

## 8. Epic 6: Networking & Real-Time

> **Priority**: P1-P2 mixed
> **Effort**: 6-8 days
> **Impact**: Better performance, real-time experience

### 8.1 Activate WebSocket Client

**Problem**: A complete WebSocket client exists (`websocket_client.dart`, 481 lines) with ticket-based auth, auto-reconnection, and typed events - but it's **never connected** from any screen.

**Solution**: Activate WebSocket connection post-login for real-time updates.

**Events to handle**:
| Event | Action |
|-------|--------|
| `ServerStatusChanged` | Invalidate server list provider → UI auto-updates |
| `SubscriptionUpdated` | Refresh subscription status |
| `NotificationReceived` | Show in-app banner |
| `ForceDisconnect` | Disconnect VPN, show explanation dialog |

**Implementation**:
```dart
// In AuthNotifier after successful login
final wsClient = ref.read(websocketProvider);
await wsClient.connect();

wsClient.serverStatusEvents.listen((event) {
  ref.invalidate(serverRepositoryProvider);
});
```

**Acceptance criteria**:
- [ ] WebSocket connects on login, disconnects on logout
- [ ] Server status changes reflected in real-time (no manual refresh needed)
- [ ] Subscription changes trigger UI update
- [ ] Connection survives app backgrounding (auto-reconnect)
- [ ] No duplicate connections

### 8.2 API Pagination

**Problem**: No pagination on any endpoint. `/servers` returns ALL servers in one request.

**Affected endpoints**:
- `/servers` (potentially 500+ servers)
- `/payments/history`
- `/referral/recent`
- `/devices`

**Solution**: Add offset/limit query params + infinite scroll UI.

```dart
Future<List<ServerEntity>> fetchServers({
  int offset = 0,
  int limit = 50,
}) async {
  final response = await _apiClient.get<Map<String, dynamic>>(
    '/servers',
    queryParameters: {'offset': offset, 'limit': limit},
  );
}
```

**Acceptance criteria**:
- [ ] Server list loads in pages of 50
- [ ] Infinite scroll with loading indicator at bottom
- [ ] Pull-to-refresh resets pagination
- [ ] Total count shown in UI ("42 of 350 servers")

### 8.3 Request Deduplication

**Problem**: Multiple widgets watching the same Riverpod provider can trigger duplicate API calls on rebuild.

**Solution**: Implement in-flight request cache in `ApiClient`:

```dart
final Map<String, Future<Response>> _pendingRequests = {};

Future<Response<T>> get<T>(String path, ...) async {
  final key = '$path?$queryParameters';
  if (_pendingRequests.containsKey(key)) {
    return _pendingRequests[key]! as Future<Response<T>>;
  }
  // ... execute and cache
}
```

**Acceptance criteria**:
- [ ] Identical concurrent GET requests deduplicated
- [ ] POST/PATCH/DELETE never deduplicated
- [ ] Cache cleared after response received

### 8.4 Real ICMP Ping Measurement

**Problem**: Current "ping" uses DNS lookup timing (`InternetAddress.lookup`), which returns cached results and doesn't measure real latency.

**Solution**: Implement platform channel for native ICMP ping or use HTTP HEAD requests to measure RTT.

**Acceptance criteria**:
- [ ] Ping values reflect actual network latency to server
- [ ] Ping refreshes periodically (every 30s for visible servers)
- [ ] Results cached with 30s TTL

### 8.5 Image Caching Strategy

**Problem**: No explicit image caching for avatars, flags, server icons.

**Solution**: Use `cached_network_image` package with configurable TTL and size limits.

**Acceptance criteria**:
- [ ] All network images use `CachedNetworkImage`
- [ ] Cache TTL: 7 days for flags, 1 day for avatars
- [ ] Cache size limit: 50MB
- [ ] Placeholder shimmer while loading

---

## 9. Epic 7: Micro-Interactions & Polish

> **Priority**: P2 - Delight factor
> **Effort**: 5-6 days
> **Impact**: Perceived quality and professional feel

### 9.1 Form Interactions

**Problem**: Login/register forms have no animated feedback for focus, validation errors, or submission.

**Improvements**:
1. **Input field focus**: Animated border color change + subtle scale (1.0 -> 1.01)
2. **Validation error shake**: Horizontal shake animation (5px amplitude, 3 cycles, 300ms)
3. **Button loading state**: Replace text with inline spinner during API call
4. **Success feedback**: Brief green checkmark animation on successful submit

**Target files**: `login_screen.dart`, `register_screen.dart`, `forgot_password_screen.dart`

**Acceptance criteria**:
- [ ] All form fields have animated focus state
- [ ] Invalid fields shake on submit attempt
- [ ] Submit buttons show loading spinner during API calls
- [ ] Success state shown before navigation

### 9.2 UsageRing Entrance Animation

**Problem**: Usage ring on profile dashboard appears instantly with no animation.

**Solution**: Use `TweenAnimationBuilder` to animate from 0 to current value:

```dart
TweenAnimationBuilder<double>(
  tween: Tween(begin: 0.0, end: _ratio),
  duration: const Duration(milliseconds: 800),
  curve: Curves.easeOutCubic,
  builder: (context, value, child) =>
    CircularProgressIndicator(value: value),
)
```

**Acceptance criteria**:
- [ ] Ring animates from 0% to actual value on first render
- [ ] Animation duration: 800ms with easeOutCubic
- [ ] Only animates once per screen visit (not on rebuild)

### 9.3 Country Group Expand/Collapse Animation

**Problem**: Country groups in server list toggle instantly with no animation.

**Solution**: Add `AnimatedRotation` for arrow icon + `AnimatedCrossFade` or `SizeTransition` for content.

**Acceptance criteria**:
- [ ] Arrow rotates 180 degrees on expand/collapse
- [ ] Content slides in/out smoothly (200ms)
- [ ] Scroll position adjusts to keep header visible

### 9.4 Custom Pull-to-Refresh

**Problem**: Server list uses default `RefreshIndicator` which doesn't match cyberpunk theme.

**Solution**: Custom refresh indicator with cyberpunk-styled spinner (neon ring with scan effect).

**Acceptance criteria**:
- [ ] Custom refresh indicator on server list
- [ ] Matches current theme (cyberpunk glow or Material default)
- [ ] Haptic feedback on pull threshold

### 9.5 Stats Card Staggered Entrance

**Problem**: Profile dashboard stats cards appear all at once.

**Solution**: Use existing `StaggeredListItem` widget (already well-implemented) for stats cards.

**Acceptance criteria**:
- [ ] Stats cards fade in with 50ms stagger
- [ ] Only animates on first render (not tab switch back)
- [ ] Respects `MediaQuery.disableAnimations`

---

## 10. Accessibility Improvements

> **Priority**: P1 - Compliance requirement
> **Effort**: 3-4 days (integrated into other epics)

### 10.1 WCAG AA Contrast Validation

**Problem**: Cyberpunk theme colors tested but Material You colors not validated. No automated testing.

**Solution**:
- Programmatically validate all color pairs in theme
- Fix any failures (minimum 4.5:1 for body text, 3:1 for large text)
- Add contrast test to CI/CD

### 10.2 Semantic Hints

**Problem**: Widgets have labels but missing descriptive hints.

**Example fix**:
```dart
// Before
Semantics(label: 'Fast server')

// After
Semantics(label: 'Fast server', hint: 'Automatically connects to fastest available server')
```

### 10.3 Focus Management

**Problem**: No `FocusScope` management detected. Tab order may be incorrect on forms.

**Solution**: Implement explicit focus traversal order on all forms (login, register, settings).

### 10.4 Haptic Feedback Expansion

**Problem**: `HapticService` exists but is underutilized (only on server selection and refresh).

**Add haptic feedback to**:
- All button taps (light impact)
- Toggle switches (medium impact)
- Error states (notification feedback)
- Pull-to-refresh threshold (medium impact)
- Navigation tab changes (selection feedback)

---

## 11. Technical Design Tokens

### New Design Tokens to Add (`tokens.dart`)

```dart
class CyberEffects {
  // Glow intensities
  static const double glowLight = 0.15;
  static const double glowMedium = 0.35;
  static const double glowHeavy = 0.6;

  // Neon border widths
  static const double neonBorderThin = 1.0;
  static const double neonBorderMedium = 2.0;
  static const double neonBorderThick = 3.0;
}

class Spacing {
  // Add to existing
  static double navBarClearance(BuildContext context) =>
    MediaQuery.of(context).viewPadding.bottom + Spacing.lg;
}
```

---

## 12. File Impact Map

### New Files to Create

| File | Epic | Description |
|------|------|-------------|
| `shared/widgets/cyber/cyber_button.dart` | E3 | Neon glow button |
| `shared/widgets/cyber/cyber_card.dart` | E3 | Animated border card |
| `shared/widgets/cyber/cyber_progress_bar.dart` | E3 | Neon progress bar |
| `shared/widgets/cyber/cyber_divider.dart` | E3 | Neon line divider |
| `shared/widgets/cyber/cyber_badge.dart` | E3 | Pulsing status badge |
| `shared/widgets/glitch_text.dart` | E3 | RGB split text effect |
| `shared/widgets/scanline_overlay.dart` | E3 | CRT scanline toggle |
| `shared/widgets/adaptive/adaptive_switch.dart` | E4 | iOS/Android switch |
| `shared/widgets/adaptive/adaptive_dialog.dart` | E4 | Platform dialog |
| `features/servers/presentation/screens/server_map_screen.dart` | E5 | Map view |
| `features/servers/presentation/widgets/recent_servers_carousel.dart` | E5 | Recent servers |
| `features/settings/presentation/widgets/settings_search.dart` | E5 | Global search |

### Existing Files to Modify

| File | Epics | Changes |
|------|-------|---------|
| `connection_screen.dart` | E1, E2, E3, E4 | Lottie integration, status dot pulse, tablet layout |
| `server_list_screen.dart` | E1, E2, E5, E7 | Overflow fixes, empty state Lottie, map toggle, recent servers |
| `profile_dashboard_screen.dart` | E1, E4, E7 | Grid fix, tablet layout, usage ring animation, staggered cards |
| `login_screen.dart` | E1, E4, E7 | Responsive width, adaptive widgets, form animations |
| `settings_screen.dart` | E1, E5 | Overflow fixes, search button |
| `onboarding_screen.dart` | E2 | Lottie page illustrations |
| `app_router.dart` | E5 | Server map route, settings search route |
| `main_shell_screen.dart` | E5 | Notification badge on tab |
| `tokens.dart` | E3 | CyberEffects tokens |
| `server_card.dart` | E5, E7 | Long-press quick actions, expand animation |
| `api_client.dart` | E6 | Request deduplication |
| `server_repository_impl.dart` | E6 | Pagination, real ping |
| `auth_provider.dart` | E6 | WebSocket activation post-login |

---

## 13. Execution Priority & Dependencies

```
Phase 1 (Week 1-2): Foundation
├── Epic 1: Critical UI Fixes (P0) ← No dependencies
├── Epic 2: Lottie Integration (P1) ← No dependencies
└── Accessibility 10.1-10.4 (P1) ← Parallel with E1

Phase 2 (Week 2-3): Visual Identity
├── Epic 3: Cyberpunk Effects (P1) ← Depends on E1 (tokens)
└── Epic 4: Responsive/Adaptive (P1) ← Depends on E1 (layout fixes)

Phase 3 (Week 3-4): UX & Performance
├── Epic 5: Navigation Enhancements (P2) ← Independent
├── Epic 6: Networking & Real-Time (P1-P2) ← Independent
└── Epic 7: Micro-Interactions (P2) ← Depends on E3 (cyber components)
```

---

## 14. Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Text overflow crashes | Unknown | 0 | Automated UI tests at 1.3x scale |
| Tablet usability score | 2/5 | 4/5 | Manual QA on iPad Air |
| Animation coverage | 6 screens | All screens | Audit of AnimationController/Lottie usage |
| Lottie assets used | 0/11 | 11/11 | grep for `Lottie.asset` |
| WebSocket active | No | Yes | Connection monitor |
| WCAG AA compliance | 72% | 85%+ | Automated contrast checks |
| Settings search | None | Full | All settings indexed |
| API calls per session | Unmeasured | -30% | Deduplication + caching metrics |

---

## 15. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Lottie animations janky on low-end | High | Medium | Test on Moto G7, add `frameRate: FrameRate.max` |
| Cyberpunk effects reduce accessibility | High | Low | All effects respect `disableAnimations` |
| WebSocket increases battery drain | Medium | Medium | Disconnect on app background, reconnect on foreground |
| Map view adds 2MB+ to app size | Low | High | Use vector tiles, lazy-load map package |
| Backend endpoints not ready for pagination | Medium | High | Implement client-side pagination as fallback |
| 13 API endpoint misalignments | High | Confirmed | Coordinate with backend team before E6 |

---

## Appendix A: Backend Alignment Issues (Out of Scope, For Reference)

These 13 endpoint misalignments were discovered during the networking audit and need backend team action:

| Endpoint | Issue | Priority |
|----------|-------|----------|
| `GET /servers/:id/status` | Missing in backend | P2 |
| `GET /subscription/active` | Missing in backend | P1 |
| `POST /subscription/:id/cancel` | Missing in backend (GDPR) | P0 |
| `GET /referral/status` | No referral system in backend | P3 |
| `POST /payments/create` | Backend uses `/payments/crypto/invoice` | P2 |
| `POST /2fa/disable` | Method mismatch (mobile: POST, backend: DELETE) | P2 |
| `GET /oauth/telegram/callback` | Method mismatch (mobile: GET, backend: POST) | P2 |
| `POST /mobile/auth/biometric/enroll` | Backend TBD | P1 |
| + 5 more minor alignment issues | Various | P3 |

---

## Appendix B: Existing Strong Patterns to Preserve

These patterns scored highly in the audit and should NOT be changed:

1. **StaggeredListItem** - Best-practice accessible list animation
2. **SkeletonLoader system** - Comprehensive shimmer loading
3. **Auth interceptor** - JWT refresh with request queueing
4. **Cache strategy** - 5-mode caching (stale-while-revalidate default)
5. **Deep link parser** - Sealed class hierarchy with validation
6. **StatefulShellRoute** - Tab state preservation
7. **Quick actions handler** - Background navigation from app shortcuts
8. **Certificate pinning** - Production-grade MITM protection
9. **PII sanitization** - Log redaction for JWT/email
10. **Result pattern** - Type-safe error handling
