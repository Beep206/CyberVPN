'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import dynamic from 'next/dynamic';
import { EndpointsSidebar } from './endpoints-sidebar';
import { EndpointDetails } from './endpoint-details';
import { CodeTerminal } from './code-terminal';

const ApiNexus3D = dynamic(() => import('@/3d/scenes/ApiNexus3D'), { ssr: false });

export type EndpointCategory = 'auth' | 'servers';
export type EndpointId = 'generateToken' | 'listServers' | 'connect';

export interface ActiveEndpoint {
    category: EndpointCategory;
    id: EndpointId;
}

export function ApiDashboard() {
    const t = useTranslations('Api');
    const [activeEndpoint, setActiveEndpoint] = useState<ActiveEndpoint>({
        category: 'auth',
        id: 'generateToken'
    });

    return (
        <div className="relative w-full min-h-[calc(100vh-4rem)] bg-black flex flex-col">
            
            {/* BACKGROUND EXPANSE: Fullscreen 3D Scene */}
            <div className="absolute inset-0 z-0 bg-[#020205] overflow-hidden">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.9)_100%)] z-10 pointer-events-none" />
                <ApiNexus3D activeEndpoint={activeEndpoint} />
            </div>

            {/* FOREGROUND LAYOUT */}
            <div className="relative z-20 w-full h-full flex flex-col md:flex-row pointer-events-none">
                
                {/* LEFT: Sidebar / Endpoints List */}
                <div className="w-full md:w-[320px] lg:w-[380px] h-full flex-shrink-0 flex flex-col pointer-events-auto border-r border-grid-line/30 bg-black/60 backdrop-blur-xl">
                    <div className="p-6 md:p-8 shrink-0">
                        <h1 className="font-display text-3xl font-bold text-white uppercase tracking-tighter drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]">
                            {t('title')}
                        </h1>
                        <p className="font-mono text-muted-foreground mt-4 text-xs leading-relaxed">
                            {t('description')}
                        </p>
                    </div>

                    <div className="flex-1 overflow-y-auto no-scrollbar pb-24 px-6 md:px-8">
                        <EndpointsSidebar activeEndpoint={activeEndpoint} setActiveEndpoint={setActiveEndpoint} />
                    </div>
                </div>

                {/* MIDDLE/RIGHT: Content Area */}
                <div className="flex-1 h-full flex flex-col lg:flex-row overflow-y-auto lg:overflow-hidden pointer-events-auto">
                    
                    {/* MIDDLE: Endpoint Details */}
                    <div className="flex-1 p-6 md:p-8 lg:p-12 lg:overflow-y-auto no-scrollbar">
                        <EndpointDetails activeEndpoint={activeEndpoint} />
                    </div>

                    {/* RIGHT: Code Terminal */}
                    <div className="w-full lg:w-[500px] xl:w-[600px] shrink-0 p-6 md:p-8 lg:p-12 bg-black/80 lg:bg-transparent backdrop-blur-2xl lg:backdrop-blur-none border-t lg:border-t-0 lg:border-l border-grid-line/30">
                        <CodeTerminal activeEndpoint={activeEndpoint} />
                    </div>
                </div>

            </div>
        </div>
    );
}
