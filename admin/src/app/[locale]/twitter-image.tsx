import { ImageResponse } from 'next/og'

export const alt = 'VPN Command Center'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default function TwitterImage() {
    return new ImageResponse(
        (
            <div
                style={{
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: '#050505',
                    backgroundImage:
                        'radial-gradient(circle at 50% 50%, rgba(0, 255, 255, 0.08) 0%, transparent 50%)',
                }}
            >
                <div
                    style={{
                        position: 'absolute',
                        top: 0,
                        left: '10%',
                        right: '10%',
                        height: '2px',
                        background: 'linear-gradient(90deg, transparent, #00ffff, transparent)',
                    }}
                />
                <div
                    style={{
                        fontSize: '64px',
                        fontWeight: 900,
                        color: '#00ffff',
                        textTransform: 'uppercase',
                        letterSpacing: '0.15em',
                        textShadow: '0 0 20px rgba(0, 255, 255, 0.5), 0 0 40px rgba(0, 255, 255, 0.3)',
                    }}
                >
                    VPN COMMAND CENTER
                </div>
                <div
                    style={{
                        fontSize: '24px',
                        color: '#00ff88',
                        marginTop: '16px',
                        letterSpacing: '0.3em',
                        textTransform: 'uppercase',
                    }}
                >
                    ADMIN DASHBOARD
                </div>
                <div
                    style={{
                        display: 'flex',
                        gap: '32px',
                        marginTop: '48px',
                        fontSize: '14px',
                        color: 'rgba(255, 255, 255, 0.4)',
                        fontFamily: 'monospace',
                        letterSpacing: '0.1em',
                    }}
                >
                    <span>ENCRYPTION: QUANTUM-SAFE</span>
                    <span style={{ color: '#ff00ff' }}>|</span>
                    <span>STATUS: OPERATIONAL</span>
                    <span style={{ color: '#ff00ff' }}>|</span>
                    <span>NODES: ONLINE</span>
                </div>
                <div
                    style={{
                        position: 'absolute',
                        bottom: 0,
                        left: '10%',
                        right: '10%',
                        height: '2px',
                        background: 'linear-gradient(90deg, transparent, #ff00ff, transparent)',
                    }}
                />
            </div>
        ),
        { ...size }
    )
}
