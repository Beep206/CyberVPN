# Root cause analysis of 36 VLESS+Reality client failures

**Every major pain point in VLESS+Reality VPN clients traces to one of five architectural fault lines**: the decoupled multi-process architecture (TUN ↔ tun2socks ↔ Go core), Go runtime incompatibility with mobile constraints, aggressive OS power management vs. persistent-tunnel requirements, the absence of standardized configuration formats, and the fundamental tension between censorship resistance and protocol fragility. This report dissects each of the 36 identified problems to its code-level, architecture-level, or platform-level root cause.

These apps — v2rayNG, Hiddify, NekoBox, Streisand, FoXray, Shadowrocket, V2Box — share a common architecture: a native mobile shell wrapping a Go-based proxy engine (xray-core or sing-box) via gomobile bindings, with a TUN interface bridging the OS network stack to userspace proxy logic. Most failures originate in the seams between these layers.

---

## Network and protocol-layer root causes

### 1. "Connected but not working" — VPN shows active, no traffic flows

The root cause is a **decoupling between VPN API status reporting and actual data-plane health**. Android's `VpnService` reports "connected" the instant `VpnService.Builder.establish()` creates the TUN file descriptor — a purely control-plane event. The data plane (xray-core/sing-box proxying traffic via SOCKS5 on `127.0.0.1:10808`) operates independently.

Three specific failure modes produce this symptom. First, the **tun2socks bridge crashes silently**: v2rayNG uses `hev-socks5-tunnel` to bridge TUN packets to the local SOCKS5 proxy. If tun2socks is OOM-killed or fails to initialize, the VPN icon persists while no traffic flows (GitHub v2rayNG #3336 shows `tun2socks destroy` in logs while UI shows connected). Second, the **proxy core fails but the local listener stays bound**: xray-core's SOCKS listener on port 10808 starts before outbound connections are verified. A Reality handshake failure or DNS resolution failure for the server domain means the core accepts local connections but drops them silently (v2rayNG #4729). Third, **DNS bootstrap deadlocks** occur when the proxy server is specified by hostname and DNS resolution depends on the tunnel being up — a circular dependency documented in v2rayNG #1229 during Android "Always-on VPN" boot.

The architectural difficulty is fundamental: Android's VpnService API has **no built-in tunnel health reporting**. The app would need to implement its own HTTP CONNECT health-check through the tunnel, adding complexity and battery drain. The multi-component chain (Kotlin → JNI → tun2socks → SOCKS5 → Go core) means any single-link failure is invisible to the VPN status API.

### 7. DNS leaks and DNS resolution failures

DNS leaks stem from a **fundamental architectural mismatch between L4 proxy mode and L3 packet capture**. In SOCKS5/HTTP proxy mode (non-TUN), DNS queries from applications go directly to the system resolver before reaching the proxy — the proxy only sees already-resolved IP addresses. sing-box issue #1690 confirms: only TUN mode can prevent DNS leaks because SOCKS/HTTP proxies cannot intercept UDP DNS packets.

Even in TUN mode, leaks persist without three specific configuration flags: `sniff: true` (to detect DNS protocol), `hijack-dns` route rule (to redirect DNS to sing-box's resolver), and **`strict_route: true`** (to block OS-level multi-path DNS). Without `strict_route`, Windows sends DNS queries to ALL network interfaces simultaneously via "smart multi-homed name resolution," and Linux allows ICMP to bypass TUN entirely. Additional failure modes include IPv6 DNS leaks when TUN only configures IPv4 addresses (sing-box #1616), and FakeDNS loopback bugs where `tun + hijack-dns + fakeip` creates a resolution cycle that causes complete timeout (sing-box #2643).

### 8. No XHTTP/SplitHTTP transport support

XHTTP is an **xray-core-exclusive transport** first added mid-2024. Clients using sing-box as their engine (Hiddify, newer NekoBox) simply cannot use it because sing-box has not independently implemented the protocol. Even for xray-core-based clients like v2rayNG, the UI must be updated to parse XHTTP config fields and expose four operational modes (`packet-up`, `stream-one`, `stream-up`, `auto`), XMux connection pooling settings, and HTTP/1.1-3 transport options. Mobile clients bundle a specific xray-core version in their `.aar` file; if it predates XHTTP support, the transport doesn't exist in the binary. The protocol's complexity — sequence-number-based packet reordering, four modes, xmux connection pooling — makes cross-implementation significantly harder than WebSocket or HTTPUpgrade transports.

### 11. WhatsApp/Instagram specific connection failures

Meta apps fail because they **aggressively use QUIC (HTTP/3) over UDP** and **bypass system proxy settings entirely**. In SOCKS5/HTTP proxy mode, UDP traffic is never proxied — it goes directly or is dropped. WhatsApp uses its own networking stack with direct socket connections that ignore Android's system proxy configuration. A v2rayA discussion (#1414) confirms: "if in proxy mode, the system won't proxy some application (IG, whatsapp, TG...) ... try to make it in tproxy mode." Only TUN/VPN mode captures all traffic. Even in TUN mode, UDP relay through VLESS requires `"udp": true` in SOCKS settings, server-side UDP support, and XUDP protocol negotiation — if any piece is missing, QUIC connections fail silently while TCP-based apps work normally. On Windows, WhatsApp's UWP architecture adds another barrier: UWP apps cannot access localhost loopback by default, blocking local SOCKS/HTTP proxy connections (v2rayN #3414).

### 14. VLESS+Reality protocol-specific failures

Reality's failure modes are intrinsic to its anti-censorship design. The protocol embeds authentication data in the TLS ClientHello's **32-byte Session ID field** — bytes 0-2 contain the Xray version, and the remainder contains ECDH-derived encrypted authentication. The server verifies this by computing `client_public_key × server_private_key → shared_secret → HKDF → AuthKey`. **Any middlebox modification of the ClientHello destroys authentication.** Issue #2728 documents firewalls modifying the `key_share` extension (random 5-digit `keyShare.group` values like 27242 instead of X25519's value 29), breaking ECDH entirely. The code in `XTLS/REALITY/tls.go` loops searching for X25519 key share and never matches.

Additional failure triggers include **time synchronization drift** (the server checks `ClientTime` against `maxTimeDiff`), SNI/dest mismatches (the `dest` website must maintain a valid certificate), and the hard **TLS 1.3 requirement** — any uTLS fingerprint that negotiates TLS 1.2 causes an explicit rejection: `"Current fingerprint does not support TLS 1.3, REALITY handshake cannot establish."` The fundamental tension: stronger anti-probing measures make the handshake more fragile against middlebox interference.

### 18. Hiddify default DNS (1.1.1.1) blocks all traffic in China

This is a **DNS bootstrap chicken-and-egg problem**. Hiddify's default remote DNS is `udp://1.1.1.1` (Cloudflare), which the GFW blocks at the IP level. The failure chain: resolve proxy server domain (requires DNS) → connect to proxy → establish tunnel. Since DNS resolution happens *before* the tunnel is up, and the DNS server is unreachable, the entire chain deadlocks. GitHub issues #975, #775, #1235 all confirm 1.1.1.1 is blocked in China. Using `https://cloudflare-dns.com/dns-query` (domain-based) creates another circular dependency — resolving `cloudflare-dns.com` itself requires DNS. The UDP transport worsens the problem since plaintext UDP DNS is trivially dropped by the GFW. No universally reachable DNS server exists, making any hardcoded default fail in some censorship environment.

### 24. Traffic leak (bypasses VPN tunnel)

Traffic leaks arise from **six distinct mechanisms**. Without `strict_route: true`, the OS kernel can choose alternative routing paths — on Linux, all ICMP bypasses TUN; on Windows, DNS queries leak via multi-homed resolution. **IPv6 leaks** occur when TUN configures only IPv4 but the physical interface has IPv6 connectivity. The VPN app must exclude itself via `addDisallowedApplication()` to prevent routing loops, but this means the app's own requests (subscription updates, connectivity checks) leak. sing-box's `auto_detect_interface` binds proxy outbound connections to the physical interface — necessary to prevent loops, but if applied too broadly, non-proxy traffic escapes. Some apps use `SO_BINDTODEVICE` to bind directly to physical interfaces, bypassing VPN routing entirely. Apple's **MPTCP** also bypasses sing-box TUN by design.

### 29. uTLS "android" fingerprint causes connection failures

The "android" uTLS fingerprint fails because it **may not support TLS 1.3**, which Reality absolutely requires. The `HelloAndroid_11_OkHttp` fingerprint mimics an older Android OkHttp TLS stack that may lack proper TLS 1.3 cipher suites or X25519 key_share extensions. The Reality server specifically validates `keyShare.group == X25519` (value 29) with `len(keyShare.data) == 32`. Beyond connection failure, a critical uTLS bug (xray-core #5230) made ECH GREASE cipher suites in chrome fingerprints **passively identifiable with 50-100% accuracy** from December 2023 to October 2025. The recommended fingerprints are "chrome" or "firefox" — they reliably support TLS 1.3 with X25519. The architectural problem: uTLS fingerprints are static snapshots that must be manually updated as real browsers evolve; "android" represents a diverse ecosystem where no single fingerprint is accurate.

---

## Platform and OS-level root causes

### 2. VPN drops during device sleep/idle (background kill)

The root cause is a **multi-layered conflict between OS power management and persistent tunnel requirements**. Android Doze mode (6.0+) suspends all network access during idle. Lightweight Doze (7.0+) triggers even when the device is moving with screen off. App Standby Buckets (9.0+) classify apps into tiers where background network access is progressively restricted, and Android 14+ uses **ML-based adaptive restrictions** that can demote infrequently opened apps.

The most devastating factor is **OEM-specific battery optimization**. As documented on dontkillmyapp.com, Xiaomi's MIUI performs full process kills on "Clear all recent apps" — even foreground services are terminated. Samsung's "Deep Sleeping Apps" list aggressively kills background apps. Huawei's EMUI has its own independent power management. These OEM customizations are undocumented, not accessible via public APIs, and cannot be fully opted out without root access.

On iOS, the NetworkExtension runs as a separate process with strict **jetsam memory limits** (historically 15MB, inconsistently enforced on iOS 17). Go-based proxy engines via gomobile easily exceed these limits, causing silent kills. The `disconnectOnSleep` property on `NEVPNProtocol` must be explicitly set to `false` or iOS may disconnect the VPN during sleep.

### 15. No automatic reconnection after network change

When switching WiFi→cellular, the VPN's outbound socket was bound to the old interface (e.g., `wlan0`). After the switch, writes fail with `ENETUNREACH`. The app must detect the change via `ConnectivityManager.NetworkCallback`, tear down the old socket, create and `protect()` a new socket on the new network, re-establish the TLS+Reality handshake, and reconfigure TUN routing — a multi-second process during which traffic is blackholed. Unlike WireGuard (which has built-in session resumption) or IKEv2 (which has MOBIKE for mobility), **VLESS+Reality requires a full TLS 1.3 handshake** for reconnection, taking 1-3 seconds minimum. On iOS, changing `setTunnelNetworkSettings()` during reconnection can itself cause transient DNS leaks as the routing table is recreated.

### 21. Android TV not supported

Android TV requires a **Leanback launcher intent** (`android.intent.category.LEANBACK_LAUNCHER`) in the manifest — without it, the app is invisible on the home screen. All navigation must work via D-pad with explicit `nextFocusDown/Up/Left/Right` attributes, visible focus indicators, and no touch-only gestures. The `VpnService.prepare()` system dialog may not render properly or be navigable via D-pad on some TV builds. Google Play's TV section requires Leanback compliance testing with TV-specific assets. Supporting Android TV requires a **complete parallel UI implementation** — essentially building a second app shell around the same proxy engine, which is low-ROI for small open-source projects.

### 22. iOS 17+ compatibility breakage

Starting from **iOS 18.1**, `includeAllNetworks` must be set to `true` on `NEVPNProtocol` for the packet tunnel to receive traffic — previously, `includedRoutes = [NEIPv4Route.default()]` was sufficient. This undocumented change silently broke VPN apps. A developer on Apple Developer Forums (#769064) confirmed: packets simply stopped arriving through `packetFlow`. On iOS 17.3.1, the NetworkExtension memory limit was enforced at **15MB** on iPhone 14 Pro Max (Apple Forums #747474), despite Apple reportedly raising it to 50MB on iOS 15+. A developer using tun2socks + xray noted the extension disconnects automatically at 15MB. Additionally, `NEPacketTunnelProvider` enters a rare "connecting loop" bug on iOS 17.x (#746879) where the tunnel shows PID 0 and won't start — only fixable by removing the VPN profile. Apple's Technical Note TN3120 warns against using packet tunnels for non-VPN purposes, suggesting stricter enforcement is coming.

### 23. Push notifications blocked while VPN active

Apple Push Notification service requires a persistent TCP connection on **port 5223** to Apple's 17.0.0.0/8 servers. When VPN captures all traffic (route `0.0.0.0/0`), the existing APNs connection breaks because it was established on the physical interface before VPN activation — the routing table change invalidates its source IP. APNs must re-establish through the VPN tunnel, and if the exit node has poor connectivity to Apple's servers, notifications fail. With full-tunnel VPN on iOS, push notifications degrade from near-instant to **10-15 minute polling intervals** because iOS power management suspends the tunnel during sleep. The workaround of routing 17.0.0.0/8 outside the tunnel only fixes APNs — PushKit (used by WhatsApp, Telegram) requires connections to app-specific servers, making whitelisting impractical at scale.

### 30. macOS UX fundamentally broken

Most apps (FoXray, V2Box) are iOS apps ported via **Mac Catalyst** — fundamentally iPadOS apps with a compatibility shim that inherits iOS UI patterns (large touch targets, navigation controllers, tab bars) alien to macOS. Apple Developer Forums (#665975) documents NEVPNManager connections failing specifically in Catalyst builds even when identical code works on iOS. macOS VPN apps are expected to live as **menu bar status items** (`NSStatusItem`), which requires AppKit implementations that don't exist in iOS Catalyst apps. System proxy vs. TUN mode adds complexity absent on iOS: macOS supports system-wide HTTP/SOCKS proxy settings (System Preferences → Network → Proxies) alongside TUN-based routing, and users expect both options. Network service ordering, multiple interfaces (VLANs, Thunderbolt bridges), and System Extension approval flows (replacing kernel extensions) all differ from iOS's simpler model.

### 33. Internet breaks after disconnecting VPN (system corruption)

When the VPN process **crashes** (SIGKILL from OOM killer, OEM battery optimization) rather than shutting down gracefully, routing rules persist in the kernel. sing-box's `auto_route` creates `iproute2` rules (table 2022, rule index 9000) and nftables rules with marks (`0x2023`, `0x2024`) that survive process death. DNS settings configured via `VpnService.Builder.addDnsServer()` may point to an address inside the now-dead tunnel. On macOS, `set_system_proxy` modifies system proxy settings to `127.0.0.1:port` — if the app crashes, System Preferences still shows the proxy pointed at a dead server. sing-box issue #3725 documents lingering `sing-tun` network devices on Windows. On iOS, `cancelTunnelWithError()` with `includeAllNetworks = YES` can leave the routing table directing all traffic to a nonexistent tunnel. Android's documentation states file descriptor closure restores networking automatically, but **this only works for graceful closure, not abrupt process kills**.

### 34. Conflict with GoodbyeDPI/AdGuard

Android enforces a **hard single-VPN limitation**: "There can be only one VPN connection running at the same time. The existing interface is deactivated when a new one is created." This is framework-level enforcement in `VpnService.prepare()` — calling it for App B immediately revokes App A's VPN and calls `onRevoke()`. ByeDPI (GoodbyeDPI's Android port) uses `VpnService` to create a local TUN for DPI bypass packet manipulation, making it mutually exclusive with v2rayNG/Hiddify/NekoBox. AdGuard's documentation explicitly confirms the conflict. On rooted devices, both tools may use iptables/nftables directly — sing-box's nftables marks (`0x2023-0x2025`) can conflict with AdGuard's traffic redirection rules, causing misrouted or dropped packets. The only workarounds require root access (iptables proxy mode) or manual proxy chaining via local SOCKS5 sockets.

---

## App architecture, crashes, and performance root causes

### 3. Updates break existing configurations (regression bugs)

The core problem is **aggressive config schema evolution without versioning**. sing-box has broken config schemas in nearly every minor release with no `"version"` field in the JSON format. Version 1.8.0 deprecated GeoIP/Geosite for `rule-set`. Version 1.11.0 deprecated legacy outbounds (`block`, `dns`) for rule actions. Version 1.12.0 completely overhauled DNS server format (`"address": "https://1.1.1.1/dns-query"` → `"type": "https", "server": "1.1.1.1"`). Each version deprecates features with warnings then **removes them 2 versions later** — a ticking time bomb. No automated migration tool exists; `sing-box check` validates but doesn't transform. xray-core adds features like new uTLS fingerprints that cause `"unknown fingerprint"` errors in older clients. The app wrapper (Kotlin/Swift) and Go core (`.aar`/`.xcframework`) are developed by different teams on different release cycles — when the app updates its bundled core, config generation code may not update simultaneously.

### 4. App crashes on startup or during use

Three distinct failure mechanisms cause crashes. First, **xray-core contains numerous unrecovered Go panics**: `BurstObservatoryConfig.Build()` triggers `panic: nil pointer dereference` on empty config (xray-core #4756); `ACAutomaton.Match()` triggers index-out-of-range panic on malformed domains (#2478); interface conversion panics occur in splithttp dialer (#3560). In Go, unrecovered `panic` terminates the entire process. Second, the **iOS NetworkExtension 15MB memory limit** is devastating: the Go runtime consumes ~5-6MB at baseline, leaving only ~7-8MB for actual proxy operations. Go's garbage collector doesn't return memory promptly to the OS (designed for server workloads), and iOS jetsam kills the extension with no warning. A developer on iPhone 14 Pro Max with iOS 17.3.1 reported the extension killed at exactly 15MB. Third, **gomobile cannot recover from Go panics** across the FFI boundary — there is no `recover()` wrapper at the JNI/ObjC boundary by default, so a Go panic in the core kills the VPN service process.

### 5. Battery drain / device overheating

In TUN mode, **every single IP packet** traverses a userspace processing chain: kernel → TUN fd read → Go userspace → gvisor TCP/IP stack → proxy logic → encrypt → kernel socket → network. The Go process must wake for every packet, preventing CPU deep sleep. The gvisor userspace TCP/IP stack (used by sing-box) reimplements TCP in Go, adding significant CPU overhead. Pre-XTLS configurations perform **double TLS encryption** — the proxy tunnel is TLS-encrypted while inner HTTPS traffic is also TLS-encrypted, causing 2× CPU crypto operations per packet. Go runtime overhead adds goroutine scheduling, frequent GC pauses, and ~5MB baseline memory usage. Background operations — keepalive packets, periodic DNS resolution, URL testing for auto-select outbounds every 1-3 minutes, rule-set updates, and real-time traffic statistics — create continuous CPU load even when the user isn't actively browsing.

### 6. Subscription/config import failures

The fundamental cause is the **absence of a standardized subscription format**. The de facto V2RayN format (base64-encoded newline-separated share links) was never formally specified. Share link formats differ per protocol: `vmess://` uses base64-encoded JSON, `vless://` uses URI query parameters, `ss://` uses SIP002 format. VMess alone has two incompatible URL formats. URL encoding collisions cause real bugs: v2rayNG #3531 documents VLESS URLs with `?` or `=` in the `path` field incorrectly parsed in versions 1.8.36-1.8.39, with the `alpn` field lost entirely. Base64 encoding variants (standard vs. URL-safe, with/without padding) differ between servers. Different panels (3x-ui, Marzban, Hiddify Manager) generate subtly different subscription formats. Reality config parameters are specifically prone to loss — v2rayNG #2237 shows subscriptions loading only address, port, and UUID while other Reality parameters are dropped on Android.

### 13. Per-app proxy / split tunneling broken

Android's `VpnService.Builder.addAllowedApplication()` works at the UID level with hard constraints: you cannot mix allowed and disallowed lists; shared UIDs mean allowing one app allows its entire group; some system apps share UIDs with system services. sing-box #3387 reveals a deeper problem: even when `include_package` correctly routes only selected apps through the tunnel, **excluded apps still detect the VPN** via `NetworkCapabilities.NET_CAPABILITY_NOT_VPN` or by checking `/proc/net/if_inet6` for TUN interfaces. Banking apps that detect VPN presence will exit regardless of routing. v2rayNG #2355 documents that selecting any app in "allow" mode cuts internet for all other apps — because non-tunneled traffic hits the default TUN route without being proxied, and `strict_route` blocks it. Permission exceptions (`SecurityException` on work profiles) and IPv6 bypass when TUN only handles IPv4 add further failure modes.

### 17. QR code scanning failures

VLESS+Reality URLs are **200-500+ characters**, generating QR codes at Version 15-25+ density that stress scanner limits. v2rayNG uses the ZXing library, which has documented device-specific failures (ZXing #1958: 100% failure on Sony SOG07 while Samsung/Pixel work fine). Gallery import of QR codes returns null for Reality configs (v2rayNG #3106) due to ZXing's image decoding struggling with JPEG compression artifacts around QR modules. Camera API inconsistencies across OEM Android implementations affect autofocus behavior, and the high data density means even minor focus issues cause scan failure. Screenshot compression, gallery image resizing, and incorrect color space handling introduce quality loss in the image processing pipeline.

### 36. Crash from invalid config import

xray-core **systematically uses Go `panic` instead of `error` returns** in config parsing code paths. `BurstObservatoryConfig.Build()` at observatory.go:29 panics on nil `SubjectSelector`. `MustFromContext()` panics by design when a context value is missing. The `ACAutomaton.Match()` panics on malformed domain strings. The app wrappers perform no intermediate validation — share links are parsed into data structures, converted to JSON configs, and passed directly to `core.StartInstance()`. If a share link has missing parameters, a partially-valid config reaches Build() functions that assume valid input. Critically, **gomobile provides no panic recovery at the FFI boundary** — a Go panic in config parsing kills the entire VPN service process. sing-box is slightly better (`sing-box check` and `FATAL` errors instead of panics for many paths), but still fails hard on duplicate tags and legacy format removal.

---

## UI, features, and design-level root causes

### 9. Intrusive ads with no paid removal option

**V2Box** is the primary offender — App Store reviews confirm interstitial video ads approximately every 5th launch with no in-app purchase for removal. Modded APKs circulate specifically to remove these ads. The developer (HexaSoftware) relies on ad revenue because the app is free, and implementing StoreKit/IAP infrastructure for ad removal adds compliance overhead that a small developer building a proxy tool won't prioritize. The user base is largely in censorship-affected countries where App Store payment methods are limited. v2rayNG, Hiddify, and Streisand are ad-free. Shadowrocket is paid ($2.99) from the start.

### 12. Complex/confusing UI for non-technical users

A single VLESS+Reality outbound requires configuring: protocol type, UUID, address, port, encryption, flow control, transport type (7+ options), TLS settings, SNI, ALPN, uTLS fingerprint, Reality public key, short ID, spiderX, MUX settings, fragment settings, routing rules, and DNS configuration. v2rayNG and NekoBox are **thin GUI wrappers** that directly mirror xray-core/sing-box JSON structure — v2rayNG's manual config editor exposes raw JSON sections (inbounds, outbounds, routing, DNS). The tools serve a dual purpose: casual users wanting one-tap connection and advanced users needing granular control to evade DPI. This inherent tension between simplicity and configurability is the root cause. Hiddify and Streisand attempt abstraction but still expose routing modes, DNS settings, and TUN configuration options because censorship circumvention demands them.

### 16. Features moved behind paywall

**FoXray** is the most criticized: App Store reviews state features including connection latency testing (ping), auto-update subscription, always-on VPN, and server location display were progressively moved into the "Pro ToolBox" premium tier. The developer (YIGUO NETWORK INC.) uses progressive paywalling as a sustainability strategy. Apple's App Store doesn't support donations effectively, making IAP/subscription the primary revenue model. Apple's 30% cut compounds the problem — developers in censorship-affected regions face a paradox where their users most need the tool but are least able to pay.

### 19. No auto-subscription update

v2rayNG **completely lacks this feature** despite years of requests (GitHub #1035, #1392, #1910, #2514). This is a deliberate design/resource omission by the developer (2dust), not a technical impossibility. Android's Doze mode and battery optimization restrict background network activity — WorkManager could schedule updates, but reliable background fetch requires battery optimization exemption. iOS limits background fetch to system-determined intervals (typically 15+ minutes). FoXray has the feature but only in its premium tier. Hiddify has implemented auto-update using Flutter with sing-box. Shadowrocket has "Update on Open" and background auto-update toggle.

### 20. Localization/language display bugs

The primary user base includes Iran (Persian/Farsi — RTL), Arabic-speaking countries (RTL), and China (CJK). RTL support requires mirroring entire UI layouts, handling bidirectional text when mixing RTL text with LTR protocol names (e.g., "VLESS" in a Persian sentence), and using `start`/`end` instead of `left`/`right` in Android layouts. Community-driven translations via volunteer contributors suffer from machine translation, missing context, and inconsistent quality. CJK double-width characters break fixed-width UI layouts. Mixed-script rendering produces incorrect visual ordering due to Unicode BiDi algorithm edge cases.

### 25. VLESS-only protocol support

No major app is truly VLESS-only — v2rayNG, Hiddify, Shadowrocket, Streisand, and NekoBox all support VMess, Trojan, Shadowsocks, and more. This problem manifests in **niche or early-version forks** that wrap only xray-core's VLESS handler without implementing URL parsers for other protocol schemes. Since there's no universal URL standard — VMess uses base64 JSON, VLESS uses URI format, SS uses SIP002 — each protocol requires a separate parser. Some minimal clients strip protocols via Go build tags to reduce binary size. FoXray's App Store reviews mention VMess not running, suggesting protocol parsing bugs rather than intentional limitation.

### 26. Cannot delete individual configs / 27. No bulk URL import

Config deletion issues are **UI design oversights**. v2rayNG's developer explicitly stated "adding more unnecessary methods can make apps fragile" (GitHub #885). Subscription-linked configs reappear on next update, creating confusion about whether to delete configs or subscriptions. FoXray on Mac tells users to "swipe left" — an iOS gesture with no macOS equivalent, and the developer didn't implement right-click context menus. Bulk URL import faces format ambiguity (base64 vs. plaintext, newline-separated vs. JSON arrays) and protocol-specific parsing for each URL scheme. Most major apps now support multi-URL clipboard import, but the implementation varies in reliability.

### 35. No speed test feature (only latency)

These apps measure HTTP round-trip time (TCP + TLS + HTTP through the proxy chain), not throughput. Throughput testing is architecturally harder because it requires **downloading a sizable file (10-100MB) through the proxy**, consuming real bandwidth from user quota. No standard test endpoint exists on user-provided servers (unlike commercial VPNs with dedicated speed test infrastructure). With hundreds of configs (Iranian users report 2000-3000), throughput testing is impractical — it must be sequential since it saturates the connection, unlike parallelizable latency tests. LiteSpeedTest exists as a dedicated external tool specifically because the complexity warrants a separate application.

---

## Privacy, ecosystem, and availability root causes

### 10. Removed from app stores / availability issues

**v2rayNG was removed from Google Play on May 14, 2025** due to Google's July 2024 policy requiring VPN app developers to register as Organization accounts with verified business identity. Pseudonymous Chinese developers of censorship tools cannot comply. Apple systematically removes VPN apps from the China App Store (since 2017) and Russia App Store (60+ apps removed July-September 2024). sing-box faced Apple developer account problems requiring a Bundle Identifier change and re-listing as "sing-box VT." NekoBox's Google Play listing was **hijacked by a third party since May 2024** — MatsuriDayo explicitly warns the Play Store version is fake and non-open-source. Distribution has fragmented to GitHub APK releases, F-Droid, and TestFlight.

### 28. Subscription User-Agent leaks app identity

When fetching subscription URLs, these apps send identifying HTTP headers. Early v2rayNG versions sent the Dalvik UA leaking **device model, Android version, and brand** (GitHub #809). Later versions sent `v2rayNG/1.8.12`, fixing the device leak but explicitly identifying the app. Censors or compromised subscription servers can identify which VPN app each user runs, enabling targeted blocking. GitHub #809 warned: "cyber police could use this to achieve precise strikes." v2rayNG only added configurable User-Agent in **v1.10.31 (December 2025)**. Most other apps still send identifiable User-Agent strings by default.

### 31. Privacy concern: usage data tracking

**V2Box** embeds ad network SDKs (likely AdMob) that collect device identifiers, IP addresses, and usage patterns — significant for a VPN app. **Hiddify** uses Sentry for crash reporting, collecting stack traces, device info, and breadcrumbs with explicit user consent. Closed-source iOS apps (Shadowrocket, FoXray, Streisand) lack transparency about data collection. **v2rayNG** and **NekoBox** are fully open-source with no analytics SDKs — the most privacy-respecting options. Hiddify's `QUERY_ALL_PACKAGES` permission (for per-app proxy) is technically necessary but sensitive as it enumerates all installed applications.

### 32. Project abandoned/minimally maintained

**NekoRay (desktop)** is explicitly archived with its repo titled "不再维护" (no longer maintained). **NekoBox for Android** receives sporadic updates with the developer stating non-critical bugs "may not be fixed" and directing casual users to FlClash. The README contains "白嫖用户建议去死" (freeloading users can go die), indicating extreme maintainer frustration. **SagerNet** was abandoned in favor of sing-box development. Root causes of burnout include single-maintainer project structure, political/legal risk for developers in China, app store compliance burden, upstream dependency churn (sing-box's breaking changes every release), hostile user demands without contributions, and **no sustainable revenue model** — only sing-box has GitHub Sponsors-based funding.

---

## Conclusion: Five architectural fault lines

The 36 pain points converge on five structural weaknesses that are unlikely to be fully resolved within the current ecosystem architecture.

**The gomobile FFI boundary is a reliability cliff.** Go panics cannot be caught across the JNI/ObjC bridge, turning every unchecked nil pointer in xray-core into a crash. The Go runtime's memory model is fundamentally incompatible with iOS's 15MB NetworkExtension limit, creating an inherent ceiling on mobile reliability. Until the cores either adopt a memory-safe language for mobile bindings or implement comprehensive panic recovery, crashes will persist.

**The TUN userspace architecture trades privacy for battery life.** Processing every IP packet through Go userspace prevents CPU deep sleep and adds double-encryption overhead. This is the price of capturing all traffic (necessary for censorship circumvention) rather than using application-level proxying (which leaks DNS and UDP). No architectural solution exists within the current model — only hardware acceleration or kernel-level proxy support could resolve this.

**The absence of configuration standards creates cascading fragility.** No version field in configs, no standardized subscription format, no universal share-link specification. Every app, panel, and core version makes slightly different assumptions, producing a combinatorial explosion of import failures, broken updates, and format incompatibilities.

**Mobile OS power management is fundamentally hostile to persistent tunnels.** Android Doze, OEM battery optimization, iOS jetsam, and background execution limits all work against the persistent-connection model that VLESS+Reality requires. The protocol's full TLS 1.3 handshake requirement makes reconnection slow, unlike WireGuard's stateful resumption.

**The single-developer open-source model is unsustainable.** Most apps are maintained by anonymous individuals under political risk, with no revenue model, facing hostile users and constant platform policy changes. The ecosystem's fragmentation — dozens of wrapper apps around two core engines — dilutes development effort while multiplying maintenance burden.