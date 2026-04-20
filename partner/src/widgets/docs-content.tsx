'use client';

import type { ReactNode } from 'react';
import { useEffect } from 'react';

export function DocsContent({
  children,
  onSectionChange,
}: {
  children: ReactNode;
  onSectionChange: (id: string) => void;
}) {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            onSectionChange(entry.target.id);
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
  }, [onSectionChange]);

  return (
    <div className="w-full flex-1 max-w-3xl space-y-24 pb-24 lg:space-y-32 lg:pb-[55vh]">
      {children}
    </div>
  );
}
