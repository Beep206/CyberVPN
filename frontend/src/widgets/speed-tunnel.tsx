'use client';

import { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import * as THREE from 'three';
import { usePathname } from 'next/navigation';
import { motion } from 'motion/react';
import { useTheme } from 'next-themes';
import { Check, Shield, Zap } from 'lucide-react';
import { TiltCard } from '@/shared/ui/tilt-card';
import { ErrorBoundary } from '@/shared/ui/error-boundary';

// Types
interface ServerInfo {
    country: string;
    flag: string;
    city: string;
}

const SERVERS: ServerInfo[] = [
    { country: 'USA', flag: '🇺🇸', city: 'New York' },
    { country: 'Germany', flag: '🇩🇪', city: 'Frankfurt' },
    { country: 'Netherlands', flag: '🇳🇱', city: 'Amsterdam' },
    { country: 'Japan', flag: '🇯🇵', city: 'Tokyo' },
    { country: 'Singapore', flag: '🇸🇬', city: 'Singapore' },
    { country: 'United Kingdom', flag: '🇬🇧', city: 'London' },
    { country: 'France', flag: '🇫🇷', city: 'Paris' },
    { country: 'Canada', flag: '🇨🇦', city: 'Toronto' },
    { country: 'Australia', flag: '🇦🇺', city: 'Sydney' },
    { country: 'South Korea', flag: '🇰🇷', city: 'Seoul' },
];

function ServerCard({ server, index }: { server: ServerInfo, index: number }) {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: index * 0.1 }}
        >
            <TiltCard className="p-6 rounded-xl border border-border/50 dark:border-white/10 bg-background/40 backdrop-blur-md hover:border-neon-cyan/50 hover:dark:border-neon-cyan/60 transition-all duration-300 group">
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <span className="text-3xl">{server.flag}</span>
                        <div>
                            <h4 className="font-bold font-display text-foreground text-lg">{server.country}</h4>
                            <span className="text-xs text-muted-foreground font-mono uppercase">{server.city}</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs font-bold text-green-500 font-mono">ONLINE</span>
                    </div>
                </div>

                {/* Specs Grid */}
                <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="p-3 rounded-lg bg-black/20 border border-white/5 flex items-center gap-2">
                        <Zap className="w-4 h-4 text-neon-cyan" />
                        <span className="text-sm font-mono font-bold text-foreground">10 Gbit/s</span>
                    </div>
                    <div className="p-3 rounded-lg bg-black/20 border border-white/5 flex items-center gap-2">
                        <Shield className="w-4 h-4 text-neon-purple" />
                        <span className="text-sm font-mono font-bold text-foreground">XHTTP</span>
                    </div>
                </div>

                {/* Features */}
                <div className="flex items-center justify-between pt-4 border-t border-white/5">
                    <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground group-hover:text-foreground transition-colors">
                        <Check className="w-3 h-3 text-green-500" />
                        <span>Torrent</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground group-hover:text-foreground transition-colors">
                        <Check className="w-3 h-3 text-green-500" />
                        <span>No-Ads YT</span>
                    </div>
                </div>
            </TiltCard>
        </motion.div>
    );
}

// Module-level factory — outside render, not analyzed by React Compiler
function generateStarfieldData(count: number) {
    const positions = new Float32Array(count * 3);
    const initialZ = new Float32Array(count);
    for (let i = 0; i < count; i++) {
        const x = (Math.random() - 0.5) * 50;
        const y = (Math.random() - 0.5) * 50;
        const zPos = Math.random() * 100;
        positions[i * 3] = x;
        positions[i * 3 + 1] = y;
        positions[i * 3 + 2] = zPos;
        initialZ[i] = zPos;
    }
    return { positions, initialZ };
}

function WarpStarfield({ speed = 2.0, color = "#00ffff" }: { speed?: number, color?: string }) {
    const points = useRef<THREE.Points>(null!);
    const count = 3000;

    const [{ positions }] = useState(() => generateStarfieldData(count));

    /* eslint-disable react-hooks/immutability -- Float32Array mutations in animation loop are intentional */
    useFrame((state, delta) => {
        // Warp effect: Move stars towards camera
        for (let i = 0; i < count; i++) {
            const i3 = i * 3;
            // Move z
            positions[i3 + 2] += (speed * 10 * delta);

            // Loop back
            if (positions[i3 + 2] > 20) {
                positions[i3 + 2] = -80; // Reset far back
                // Reshuffle x/y for variety
                positions[i3] = (Math.random() - 0.5) * 50;
                positions[i3 + 1] = (Math.random() - 0.5) * 50;
            }
        }
        points.current.geometry.attributes.position.needsUpdate = true;

        // Slight rotation for dizziness/speed feel
        points.current.rotation.z += delta * 0.1;
    });
    /* eslint-enable react-hooks/immutability */

    return (
        <points ref={points}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    count={count}
                    args={[positions, 3]}
                />
            </bufferGeometry>
            <pointsMaterial
                size={0.15}
                color={color}
                transparent
                opacity={0.8}
                sizeAttenuation={true}
                depthWrite={false}
                blending={THREE.AdditiveBlending}
            />
        </points>
    );
}

function SpeedTunnelScene() {
    const { resolvedTheme } = useTheme();
    const isDark = resolvedTheme === 'dark';

    // Theme Colors
    const bgColor = isDark ? '#000000' : '#a1a1aa'; // Significantly darker grey for light mode
    const fogColor = isDark ? '#000000' : '#a1a1aa';
    const starColor1 = isDark ? '#00ffff' : '#0891b2'; // Cyan (Neon vs Darker for contrast)
    const starColor2 = isDark ? '#ff00ff' : '#9333ea'; // Purple (Neon vs Darker for contrast)

    return (
        <div className="w-full h-full absolute inset-0 bg-background transition-colors duration-500">
            <ErrorBoundary fallback={<div className="w-full h-full bg-background flex items-center justify-center text-xs text-muted-foreground">Speed Tunnel Disabled (Extension Conflict)</div>}>
                <Canvas
                    camera={{ position: [0, 0, 5], fov: 60 }}
                    gl={{ antialias: false }} // Performance
                    dpr={[1, 1.5]}
                >
                    <color attach="background" args={[bgColor]} />
                    <fog attach="fog" args={[fogColor, 5, 20]} />

                    <WarpStarfield speed={3} color={starColor1} />
                    <WarpStarfield speed={4} color={starColor2} />

                    {/* Only enable intensive bloom in dark mode to avoid "blinding white" effect */}
                    {isDark ? (
                        <EffectComposer enableNormalPass={false}>
                            <Bloom luminanceThreshold={0.5} radius={0.8} intensity={2} />
                        </EffectComposer>
                    ) : (
                        // Minimal or no bloom for light mode
                        <EffectComposer enableNormalPass={false}>
                            <Bloom luminanceThreshold={1.1} radius={0.5} intensity={0.5} />
                        </EffectComposer>
                    )}
                </Canvas>
            </ErrorBoundary>
        </div>
    );
}

export function SpeedTunnel() {
    const pathname = usePathname();

    return (
        <section className="relative min-h-screen w-full py-20 overflow-hidden flex flex-col items-center justify-center bg-background">
            <SpeedTunnelScene key={pathname} />

            <div className="container relative z-10 px-4">
                <motion.div
                    initial={{ opacity: 0, y: 50 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="text-center mb-16"
                >
                    <h2 className="text-4xl md:text-6xl font-display font-bold text-foreground mb-4 drop-shadow-2xl">
                        GLOBAL <span className="text-neon-cyan">ULTRASPEED</span> NETWORK
                    </h2>
                    <p className="text-muted-foreground font-mono text-lg max-w-2xl mx-auto">
                        100+ Locations. 10 Gbit/s Channels. Zero Limits.
                    </p>
                </motion.div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
                    {SERVERS.map((server, index) => (
                        <div key={server.country} className={index === SERVERS.length - 1 ? "lg:col-start-2" : ""}>
                            <ServerCard server={server} index={index} />
                        </div>
                    ))}
                </div>
            </div>

            {/* Speedometer Decoration */}
            <div className="absolute bottom-0 left-0 w-full flex justify-center z-10 pointer-events-none">
                <div className="w-full h-32 bg-gradient-to-t from-background to-transparent" />
            </div>
        </section>
    );
}
