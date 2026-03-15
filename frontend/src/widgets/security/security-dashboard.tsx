'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { ArchitectureStack } from './architecture-stack';
import { ThreatRadar } from './threat-radar';
import { ClassifiedContent } from './classified-content';
import { ProtocolGrid } from './protocol-grid';

// Lazy load the heavy 3D shield scene
const SecurityShield3D = dynamic(() => import('@/3d/scenes/SecurityShield3D'), { ssr: false });

export type SecurityLayerId = 'bareMetal' | 'network' | 'crypto' | 'client';

export function SecurityDashboard() {
    const [activeLayer, setActiveLayer] = useState<SecurityLayerId>('bareMetal');

    return (
        <div className="relative w-full min-h-[calc(100vh-4rem)] bg-black flex flex-col overflow-x-hidden">
            
            {/* HERO SECTION: The Shield & Threat Radar */}
            <div className="relative w-full h-[80vh] flex flex-col md:flex-row border-b border-grid-line/30">
                
                {/* 3D Background (Aegis Shield) */}
                <div className="absolute inset-0 z-0 pointer-events-none">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.8)_100%)] z-10" />
                    <SecurityShield3D activeLayer={activeLayer} />
                </div>

                {/* Left: Architecture Stack selector */}
                <div className="w-full md:w-[400px] lg:w-[450px] relative z-20 flex flex-col h-full border-r border-grid-line/30 bg-black/60 backdrop-blur-md">
                    <ArchitectureStack activeLayer={activeLayer} setActiveLayer={setActiveLayer} />
                </div>

                {/* Right: Live Threat Radar */}
                <div className="hidden md:flex flex-1 relative z-20 h-full p-8 md:p-12 items-center justify-end pointer-events-none">
                    <ThreatRadar />
                </div>
            </div>

            {/* CONTENT SECTION: Classified Text & Protocols */}
            <div className="w-full max-w-7xl mx-auto px-6 py-24 grid grid-cols-1 lg:grid-cols-2 gap-24 relative z-20">
                <ClassifiedContent />
                <ProtocolGrid />
            </div>

        </div>
    );
}
