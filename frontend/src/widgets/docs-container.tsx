'use client';

import { useState } from 'react';
import { DocsSidebar } from './docs-sidebar';
import { DocsContent } from './docs-content';
import { DocsScene } from './docs-scene';

export function DocsContainer() {
    const [activeSection, setActiveSection] = useState('getting_started');

    return (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 px-4 pt-12 pb-32">
            
            {/* Left Sidebar (25%) */}
            <div className="lg:col-span-3 hidden lg:block">
                <div className="sticky top-24">
                    <DocsSidebar activeSection={activeSection} onSectionChange={setActiveSection} />
                </div>
            </div>

            {/* Center Content (40%) */}
            <div className="lg:col-span-5 relative z-10 w-full overflow-x-hidden p-4 md:p-0">
                <DocsContent onSectionChange={setActiveSection} />
            </div>

            {/* Right WebGL Scene (35%) */}
            <div className="lg:col-span-4 hidden lg:block pointer-events-none">
                <div className="sticky top-24 h-[600px] border border-terminal-border/40 rounded-xl overflow-hidden shadow-[0_0_30px_rgba(0,255,255,0.05)]">
                    <DocsScene activeSection={activeSection} />
                </div>
            </div>

        </div>
    );
}
