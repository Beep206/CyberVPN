# Design Doc: CyberVPN Landing Page Redesign (Anti-DPI Focus)

**Status:** Draft / Pending Review
**Date:** March 14, 2026
**Topic:** Frontend Landing Page Optimization
**Objective:** Replace generic marketing "fluff" with high-signal technical value propositions centered around the VLESS-Reality protocol.

---

## 1. Vision & Strategy

### 1.1 The Core Problem
Current landing page uses generic VPN marketing language ("Military Grade Encryption", "Digital Fortress") which fails to communicate the actual technical superiority of the CyberVPN stack to a tech-savvy audience looking for censorship circumvention.

### 1.2 The Solution: "Anti-DPI Engine"
Position CyberVPN not just as a "privacy tool", but as a high-performance **Anti-DPI Engine**. 
- **Primary Hero Message:** Total invisibility to ISP filters.
- **Protocol Transparency:** Openly state the use of VLESS-Reality and Xray-core.
- **Performance Facts:** Focus on 10 Gbit/s and low latency rather than "lightning speed".

---

## 2. Information Architecture (No-Fluff Structure)

### 2.1 Hero Section: "Signal Through Noise"
- **Tagline:** `PROTOCOL: VLESS-REALITY (ACTIVE) | CORE: XRAY-CORE`
- **Headline:** `НЕВИДИМЫЙ VPN. РАБОТАЕТ НА VLESS-REALITY`
- **Sub-headline:** `Обход DPI-блокировок любой сложности. Маскировка трафика под стандартный HTTPS. Скорость до 10 Гбит/с без потерь на инкапсуляцию.`
- **CTAs:**
  - Primary: `ЗАПУСТИТЬ В TELEGRAM` (Fastest activation)
  - Secondary: `СКАЧАТЬ ПРИЛОЖЕНИЕ` (Cross-platform)

### 2.2 Feature Matrix: "Technological Superiority"
1. **Stealth Mode (Reality):** Traffic is indistinguishable from visiting Google/Microsoft/Apple. No VPN fingerprinting.
2. **Backbone Performance:** Native 10 Gbit/s uplinks in Tier-3 data centers. Optimized for 4K/8K streaming and low-ping gaming.
3. **RAM-Only Infrastructure:** No disks, no logs, no persistence. Infrastructure is wiped on every restart.
4. **Intelligent Routing:** Global mesh of 100+ nodes with automated latency-based selection.
5. **Native Multi-Platform:** One subscription for Telegram Bot, iOS, Android, Windows, macOS, and Linux.
6. **Advanced Protocols:** Full support for VLESS, Trojan, and Shadowsocks-2022 for maximum compatibility.

### 2.3 Specialized Conversion Blocks (NEW)

#### A. Block: "How Reality Works" (Visual/Text Scheme)
- **Concept:** Explain the masquerade effect.
- **Content:** "Your ISP sees a request to `microsoft.com` or `google.com`. They don't see an encrypted tunnel. They see a normal user browsing the web. Access granted."

#### B. Block: "Legacy vs Next-Gen" (Comparison Table)
| Feature | Legacy VPN (WireGuard/OpenVPN) | CyberVPN (VLESS-Reality) |
|---------|--------------------------------|--------------------------|
| **DPI Detection** | Easily fingerprinted and blocked | Indistinguishable from HTTPS |
| **Speed under Load** | Throttled by ISP deep inspection | Full backbone speed (10Gbps) |
| **IP Blocking Risk** | High (static patterns) | Zero (dynamic Reality masking) |
| **Privacy Layer** | Standard encryption | RAM-only encryption (Zero-trace) |

#### C. Block: "Node Status Dashboard" (Live Feed)
- **Concept:** Real-time transparency for the tech-savvy.
- **Data Points:** 
  - `Node-RU-01: Reality (ONLINE) | 24ms`
  - `Node-DE-12: Reality (ONLINE) | 15ms`
  - `Node-US-03: VLESS-gRPC (ONLINE) | 110ms`

#### D. Block: "30-Second Path" (Telegram Activation)
- **Step 1:** Launch the bot (@CyberVPN_Bot).
- **Step 2:** One-tap Trial Activation (2 days / 2GB).
- **Step 3:** Import config to any app and stay free.

#### E. Block: "Network Infrastructure Stats"
- **Total Bandwidth:** 1.2 Tbps Backbone capacity.
- **Nodes:** 100+ Active high-performance nodes.
- **Global Coverage:** 50+ Countries, 100+ Cities.
- **Uptime:** 99.9% Network availability.

### 2.4 Technical Specs Block
- **Encryption:** ChaCha20-Poly1305 / AES-128-GCM.
- **Transport:** TCP, gRPC, WebSocket (HTTP Upgrade).
- **Network:** 10Gbps Uplinks, Global IPv6 Support.

### 2.5 Pricing Grid
- **Basic:** Trial / Entry level.
- **Pro:** Most popular.
- **Ultra:** High bandwidth.
- **Cyber:** Premium / Full access.

---

## 3. Implementation Details (Data Schema)

### 3.1 i18n Update (`landing.json`)
Structure includes new technical keys for all 39 locales.

### 3.2 Visual Constraints
- **Color Palette:** Matrix Green (#00ff88), Neon Cyan (#00ffff), Terminal Black (#0a0a0a).
- **Animations:** 3D Global Network background, ScrambleText for stats, Scanlines.

---

## 4. Success Criteria
1. **Zero Fluff:** No "Military Grade" or marketing slogans.
2. **High Signal:** Every block provides technical value.
3. **Frictionless Conversion:** 30-second path to first connection.

---

## 5. Review & Approval
- [ ] Technical review of protocol naming.
- [ ] UX review of the live dashboard.
- [ ] Localization sanity check (39 languages).
