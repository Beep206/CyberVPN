# CyberVPN iOS XrayTunnel Network Extension

This directory contains the iOS Network Extension target for running XRay VPN directly inside iOS via `NEPacketTunnelProvider`.

## Overview
- **Bundle ID**: `com.cybervpn.vpnextension`
- **Parent App Bundle ID**: `com.cybervpn.mobile`
- **App Group**: `group.com.cybervpn` (allows state sharing with the main app)
- **Frameworks**:
  - `NetworkExtension.framework`
  - `XRay.xcframework` (provided by `flutter_v2ray_plus`)
  - `Tun2SocksKit`

## Setup in Xcode
1. In Xcode, select `Runner.xcworkspace`.
2. Add a new target: `File -> New -> Target -> Network Extension`.
3. Select `Packet Tunnel Provider`, language `Swift`.
4. Name the target `XrayTunnel`.
5. Under `Signing & Capabilities`:
   - Enable **Network Extensions** -> select **Packet Tunnel**.
   - Enable **App Groups** -> check `group.com.cybervpn`.
6. Set the bundle identifier to `com.cybervpn.vpnextension`.
7. Replace the generated template files with the files from this directory (`PacketTunnelProvider.swift`, `Info.plist`, `XrayTunnel.entitlements`).
8. In CocoaPods `Podfile`, ensure `flutter_v2ray_plus` is accessible or add:
   ```ruby
   target 'XrayTunnel' do
     use_frameworks!
     pod 'flutter_v2ray_plus', :path => '../packages/flutter_v2ray_plus'
   end
   ```
