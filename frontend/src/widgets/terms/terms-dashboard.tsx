'use client';

import { useState, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { ComplianceScanner } from './compliance-scanner';
import { TermsContent } from './terms-content';
import { SignatureTerminal } from './signature-terminal';

// Lazy load the 3D scene because WebGL struggles on SSR
const TermsMonolith3D = dynamic(() => import('@/3d/scenes/TermsMonolith3D'), { ssr: false });

export type TermsSectionId = 'acceptance' | 'prohibited' | 'service' | 'liability' | 'termination';

export function TermsDashboard() {
    const [activeSection, setActiveSection] = useState<TermsSectionId>('acceptance');
    const [scrollDepth, setScrollDepth] = useState(0);
    const [isAccepted, setIsAccepted] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    // Track scroll depth for the 3D scene (tilting up at the monolith)
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
            <div className={`absolute inset-0 z-0 transition-colors duration-1000 ${isAccepted ? 'bg-[#000502]' : 'bg-[#050202]'}`}>
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,transparent_0%,rgba(0,0,0,0.95)_100%)] z-10 pointer-events-none" />
                <TermsMonolith3D scrollDepth={scrollDepth} isAccepted={isAccepted} />
            </div>

            {/* FOREGROUND LAYOUT */}
            <div className="relative z-20 w-full h-full flex flex-col md:flex-row pointer-events-none">
                
                {/* LEFT: Compliance Scanner Sidebar */}
                <div className="w-full md:w-[320px] lg:w-[380px] h-full flex-shrink-0 flex flex-col pointer-events-auto border-r border-grid-line/30 bg-black/70 backdrop-blur-xl">
                    <ComplianceScanner 
                        activeSection={activeSection} 
                        setActiveSection={setActiveSection} 
                        isAccepted={isAccepted}
                    />
                </div>

                {/* RIGHT: Scrollable Content Area */}
                <div 
                    ref={containerRef}
                    className="flex-1 h-full overflow-y-auto pointer-events-auto scroll-smooth no-scrollbar relative"
                >
                    <TermsContent setActiveSection={setActiveSection} isAccepted={isAccepted} />
                    
                    {/* Final Acceptance Terminal at the very bottom */}
                    <SignatureTerminal isAccepted={isAccepted} onAccept={() => setIsAccepted(true)} />
                </div>

            </div>
        </div>
    );
}
