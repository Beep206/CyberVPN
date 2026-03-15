'use client';

import { useState, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { PrivacyIndex } from './privacy-index';
import { PrivacyContent } from './privacy-content';

// Lazy load the 3D scene to prevent SSR issues
const PrivacyVault3D = dynamic(() => import('@/3d/scenes/PrivacyVault3D'), { ssr: false });

export type PrivacySectionId = 'introduction' | 'dataCollection' | 'noLogs' | 'encryption' | 'thirdParties';

export function PrivacyDashboard() {
    const [activeSection, setActiveSection] = useState<PrivacySectionId>('introduction');
    const [scrollDepth, setScrollDepth] = useState(0);
    const containerRef = useRef<HTMLDivElement>(null);

    // Track scroll depth for the 3D scene parallax effect
    useEffect(() => {
        const handleScroll = () => {
            if (containerRef.current) {
                const scrollY = containerRef.current.scrollTop;
                const maxScroll = containerRef.current.scrollHeight - containerRef.current.clientHeight;
                const depth = Math.min(Math.max(scrollY / maxScroll, 0), 1);
                setScrollDepth(depth);
            }
        };

        const container = containerRef.current;
        if (container) {
            container.addEventListener('scroll', handleScroll);
        }
        return () => {
            if (container) container.removeEventListener('scroll', handleScroll);
        };
    }, []);

    return (
        <div className="relative w-full h-[calc(100vh-4rem)] bg-black flex flex-col overflow-hidden">
            
            {/* BACKGROUND EXPANSE: Fullscreen 3D Scene */}
            <div className="absolute inset-0 z-0 bg-[#020205] overflow-hidden">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.9)_100%)] z-10 pointer-events-none" />
                <PrivacyVault3D activeSection={activeSection} scrollDepth={scrollDepth} />
            </div>

            {/* FOREGROUND LAYOUT */}
            <div className="relative z-20 w-full h-full flex flex-col md:flex-row pointer-events-none">
                
                {/* LEFT: Sidebar / Table of Contents */}
                <div className="w-full md:w-[320px] lg:w-[380px] h-full flex-shrink-0 flex flex-col pointer-events-auto border-r border-grid-line/30 bg-black/60 backdrop-blur-xl">
                    <PrivacyIndex activeSection={activeSection} setActiveSection={setActiveSection} />
                </div>

                {/* RIGHT: Scrollable Content Area */}
                <div 
                    ref={containerRef}
                    className="flex-1 h-full overflow-y-auto pointer-events-auto scroll-smooth no-scrollbar"
                >
                    <PrivacyContent setActiveSection={setActiveSection} />
                </div>

            </div>
        </div>
    );
}
