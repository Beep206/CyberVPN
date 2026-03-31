'use client';

import { useEffect, useState } from 'react';
import { DocsScene } from './docs-scene';
import { DocsSidebar } from './docs-sidebar';

export function DocsInteractiveRail() {
  const [activeSection, setActiveSection] = useState('getting_started');

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      {
        rootMargin: '-100px 0px -40% 0px',
        threshold: 0,
      },
    );

    const sections = document.querySelectorAll('section[data-anchor]');
    sections.forEach((section) => observer.observe(section));

    return () => observer.disconnect();
  }, []);

  return (
    <>
      <div
        data-testid="docs-container-sidebar"
        className="order-2 lg:order-1 lg:col-span-3"
      >
        <div className="lg:sticky lg:top-24">
          <DocsSidebar activeSection={activeSection} onSectionChange={setActiveSection} />
        </div>
      </div>

      <div
        data-testid="docs-container-scene"
        className="order-3 hidden lg:block lg:col-span-3 pointer-events-none"
      >
        <div className="sticky top-24 h-[600px] overflow-hidden rounded-xl border border-terminal-border/40 shadow-[0_0_30px_rgba(0,255,255,0.05)]">
          <DocsScene activeSection={activeSection} />
        </div>
      </div>
    </>
  );
}
