'use client';

import { useEffect } from 'react';
import { useSearchParams } from 'next/navigation';

export function HelpFaqClient({
  categoryIds,
}: {
  categoryIds: readonly string[];
}) {
  const searchParams = useSearchParams();
  const category = searchParams.get('category');

  useEffect(() => {
    if (!category || !categoryIds.includes(category)) {
      return;
    }

    const element = document.getElementById(`faq-${category}`);

    if (!element) {
      return;
    }

    const frameId = window.requestAnimationFrame(() => {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    return () => {
      window.cancelAnimationFrame(frameId);
    };
  }, [category, categoryIds]);

  return null;
}
