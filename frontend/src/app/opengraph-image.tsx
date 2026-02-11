import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const alt = 'CyberVPN - Advanced VPN Service';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          fontSize: 64,
          background: 'linear-gradient(135deg, #0a0e1a 0%, #1a1e2e 50%, #0a0e1a 100%)',
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#00ffff',
          fontFamily: 'monospace',
        }}
      >
        <div style={{ fontSize: 80, fontWeight: 'bold', marginBottom: 20 }}>
          CYBER<span style={{ color: '#00ff88' }}>VPN</span>
        </div>
        <div style={{ fontSize: 32, color: '#888', marginTop: 10 }}>
          Advanced VPN Service
        </div>
      </div>
    ),
    { ...size }
  );
}
